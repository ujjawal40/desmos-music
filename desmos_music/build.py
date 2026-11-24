"""Turn a song file (JSON) into a Desmos Graphing Calculator state.

Model (same as the @measure_plan demo):
  * x is time. A ticker advances the playhead variable t.
  * Each voice is a function v_name(x) returning pitch in OCTAVES relative
    to the base frequency B (so 1/12 = one semitone, 7/12 = a fifth).
  * The graph draws each voice's curve scrolling past the playhead, and a
    tone() expression plays it: tone(B * 2^(v_name(t)) * k, gain).
  * Where a voice is undefined (a piecewise with no matching branch), it is
    silent and nothing is drawn — that's how rhythm/gating works.

Voice kinds: `latex` (raw expression in x), `notes` ([start, dur, pitch]),
`seq` (tracker string), `hits` (drum grid). See README for every option.
"""

from __future__ import annotations

import difflib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .music import (
    DRUMS,
    ENVELOPES,
    TIMBRES,
    Hit,
    Note,
    arpeggiate,
    SongError,
    base_frequency,
    parse_hits,
    parse_key,
    parse_notes,
    parse_seq,
    resolve_preset,
)

NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")
PLAYHEAD_ID = "playhead"  # stable id so players can seek with setExpression
TICK_MS = 50  # ticker step; Desmos fires roughly every 20ms at best
RESERVED_HELPERS = {"t", "x", "y", "B", "S", "L", "e"}
KINDS = ("latex", "notes", "seq", "hits", "shepard")
SONG_KEYS = {"title", "description", "base", "base_hz", "key", "bpm", "time_scale", "window",
             "length", "sections", "helpers", "voices", "comment"}
VOICE_KEYS = set(KINDS) | {"name", "key", "step", "loop", "offset", "in", "env", "timbre", "detune",
                           "glide", "vibrato", "transpose", "swing", "arp", "arp_step", "dynamics", "drum", "gain", "muted", "color", "comment"}


def _check_keys(obj: dict, allowed: set, where: str) -> None:
    for k in obj:
        if k not in allowed:
            close = difflib.get_close_matches(k, sorted(allowed), n=1)
            hint = f" — did you mean '{close[0]}'?" if close else ""
            raise SongError(f"unknown key '{k}' in {where}{hint}")


def _fmt(n: float) -> str:
    """Number -> compact LaTeX-safe literal."""
    n = float(n)
    if n.is_integer():
        return str(int(n))
    out = f"{n:.6f}".rstrip("0").rstrip(".")
    return out if out not in ("0", "-0") else "0"


def _frac(num: float, den: int = 12) -> str:
    return f"\\frac{{{_fmt(num)}}}{{{den}}}"


def _clock(loop: float | None, offset: float = 0) -> str:
    x = f"x-{_fmt(offset)}" if offset else "x"
    if loop:
        return f"\\operatorname{{mod}}\\left({x},{_fmt(loop)}\\right)"
    return f"\\left({x}\\right)" if offset else "x"


def _piecewise(branches: list[str]) -> str:
    return "\\left\\{" + ",".join(branches) + "\\right\\}"


def _min(*terms: str) -> str:
    return "\\min\\left(" + ",".join(terms) + "\\right)"


# --- event -> LaTeX ---------------------------------------------------------

def _adsr(u: str, start: float, end: float, env: dict) -> str:
    a, d, s, r = (float(env.get(k, dv)) for k, dv in (("a", 0), ("d", 0), ("s", 1), ("r", 0)))
    since = f"{u}-{_fmt(start)}"
    terms = ["1"]
    if a > 0:
        terms.append(f"\\frac{{{since}}}{{{_fmt(a)}}}")
    if s < 1:
        if d > 0:
            terms.append(
                f"\\max\\left({_fmt(s)},1-\\frac{{{_fmt(1 - s)}\\left({since}-{_fmt(a)}\\right)}}{{{_fmt(d)}}}\\right)"
            )
        else:
            terms.append(_fmt(s))
    if r > 0:
        terms.append(f"\\frac{{{_fmt(end)}-{u}}}{{{_fmt(r)}}}")
    return terms[0] if len(terms) == 1 else _min(*terms)


def notes_to_latex(notes: list, loop: float | None, base_hz: float = 220, glide: float = 0) -> str:
    """[[start, duration, pitch], ...] -> Desmos piecewise in octaves.

    With `loop`, time wraps every `loop` units so the phrase repeats.
    """
    evs = parse_notes(notes, base_hz)
    return _melody_latex([(n.start, n.end, n.pitches[0]) for n in evs], _clock(loop), glide)


def _cond(u: str, start: float, end: float) -> str:
    return f"{_fmt(start)}\\le {u}<{_fmt(end)}"


def _melody_latex(evs: list[tuple], u: str, glide: float) -> str:
    branches = []
    prev = None
    for start, end, p, *_ in evs:
        body = _frac(p)
        if glide > 0 and prev is not None and abs(prev[1] - start) < 1e-9 and prev[2] != p:
            q = prev[2]
            ramp = f"\\frac{{{u}-{_fmt(start)}}}{{{_fmt(glide)}}}"
            body = f"{_frac(q)}+{_frac(p - q)}{_min('1', ramp)}"
        branches.append(f"{_cond(u, start, end)}:{body}")
        prev = (start, end, p)
    return _piecewise(branches)


def _melody_env_latex(evs: list[tuple], u: str, env: dict) -> str:
    branches = []
    for s, e, _, amp in evs:
        shape = _adsr(u, s, e, env)
        if amp != 1:
            shape = _fmt(amp) if shape == "1" else f"{_fmt(amp)}{shape}"
        branches.append(f"{_cond(u, s, e)}:{shape}")
    return _piecewise(branches)


def _drum_latex(hits: list[Hit], u: str, loop, drum: dict) -> tuple[str, str]:
    top, bottom, decay, ln = (float(drum[k]) for k in ("top", "bottom", "decay", "len"))
    pitch, amp = [], []
    for i, h in enumerate(hits):
        # A hit is cut off by the next one (or the loop end): Desmos takes
        # the first matching branch, so overlaps would hide later hits.
        end = h.start + ln
        if i + 1 < len(hits):
            end = min(end, hits[i + 1].start)
        if loop:
            end = min(end, float(loop))
        cond = _cond(u, h.start, end)
        since = f"{u}-{_fmt(h.start)}"
        if top and decay:
            pitch.append(f"{cond}:{_fmt(bottom)}+{_fmt(top)}e^{{-{_fmt(decay)}\\left({since}\\right)}}")
        else:
            pitch.append(f"{cond}:{_fmt(bottom + top)}")
        amp.append(f"{cond}:{_fmt(h.amp)}\\left(1-\\frac{{{since}}}{{{_fmt(ln)}}}\\right)")
    return _piecewise(pitch), _piecewise(amp)


def _dynamics_latex(points: list) -> str:
    pts = sorted((float(a), float(b)) for a, b in points)
    if not pts:
        raise SongError("dynamics needs at least one [time, level] point")
    branches = [f"x<{_fmt(pts[0][0])}:{_fmt(pts[0][1])}"]
    for (t0, l0), (t1, l1) in zip(pts, pts[1:]):
        if t1 <= t0:
            continue
        slope = (l1 - l0) / (t1 - t0)
        body = _fmt(l0) if slope == 0 else f"{_fmt(l0)}+{_fmt(slope)}\\left(x-{_fmt(t0)}\\right)"
        branches.append(f"x<{_fmt(t1)}:{body}")
    branches.append(_fmt(pts[-1][1]))
    return _piecewise(branches)


# --- song -> tracks ---------------------------------------------------------

@dataclass
class Track:
    """One sounding line: one pitch function, one or more tone() calls."""
    name: str            # subscript for v_/p_/a_
    ctrl: str            # subscript for g_/m_/d_ (shared by chord voices)
    pitch: str           # LaTeX in x, octaves vs B
    amp: str | None      # LaTeX in x, 0..1 envelope
    color: str
    share: float = 1.0   # chord voices split the voice's gain
    partials: list = field(default_factory=list)  # [(multiple, cents, weight)]


def _partials(v: dict) -> list:
    amps = resolve_preset(v.get("timbre", "sine"), TIMBRES, "timbre")
    if not isinstance(amps, list) or not amps or any(a < 0 for a in amps):
        raise SongError(f"voice '{v['name']}': timbre must be a preset name or list of amplitudes")
    parts = [(k + 1, 0.0, float(a)) for k, a in enumerate(amps) if a > 0]
    detune = float(v.get("detune", 0))
    if detune:
        parts.append((1, detune, parts[0][2] * 0.8))
    total = sum(p[2] for p in parts)
    return [(m, c, w / total) for m, c, w in parts]


def _section_gate(v: dict, sections: dict) -> list[tuple[float, float]] | None:
    names = v.get("in")
    if names is None:
        return None
    if isinstance(names, str):
        names = [names]
    spans = []
    for n in names:
        if n not in sections:
            raise SongError(f"voice '{v['name']}' is in unknown section '{n}'")
        spans.append(sections[n])
    return spans


def _tracks_for_voice(v: dict, base_hz: float, song_key=None) -> list[Track]:
    name, color = v["name"], v.get("color", "#f5a623")
    step = float(v.get("step", 1))
    offset = float(v.get("offset", 0))
    key = parse_key(v["key"]) if "key" in v else song_key
    glide = float(v.get("glide", 0))
    env = v.get("env")
    env_dict = resolve_preset(env, ENVELOPES, "envelope") if env is not None else None

    if "latex" in v:
        amp = env if isinstance(env, str) and env not in ENVELOPES else None
        return [Track(name, name, v["latex"], amp, color)]

    if "shepard" in v:
        return _shepard_tracks(v, offset)

    if "hits" in v:
        hits, length = parse_hits(v["hits"], step, float(v.get("swing", 0.5)))
        loop = v.get("loop", length)
        u = _clock(loop, offset)
        drum = dict(resolve_preset(v.get("drum", "kick"), DRUMS, "drum"))
        for k in ("top", "bottom", "decay", "len"):
            drum.setdefault(k, DRUMS["kick"][k])
        pitch, amp = _drum_latex(hits, u, loop, drum)
        return [Track(name, name, pitch, amp, color)]

    if "seq" in v:
        notes, length = parse_seq(v["seq"], step, base_hz, key)
        loop = v.get("loop", length)
    else:
        notes = parse_notes(v["notes"], base_hz, key)
        loop = v.get("loop")

    if "arp" in v:
        notes = arpeggiate(notes, v["arp"], float(v.get("arp_step", 0.5)))
    width = max(len(n.pitches) for n in notes)
    u = _clock(loop, offset)
    tracks = []
    for i in range(width):
        evs = [(n.start, n.end, n.pitches[i], n.amp) for n in notes if len(n.pitches) > i]
        tname = name if width == 1 else f"{name}{i + 1}"
        pitch = _melody_latex(evs, u, glide)
        amp = None
        if isinstance(env, str) and env not in ENVELOPES:
            amp = env
        elif env_dict or any(e[3] != 1 for e in evs):
            amp = _melody_env_latex(evs, u, env_dict or {})
        tracks.append(Track(tname, name, pitch, amp, color, share=1 / width))
    return tracks


def _shepard_tracks(v: dict, offset: float) -> list[Track]:
    """Endless glissando: `layers` sines a fixed interval apart, each fading
    in at the bottom and out at the top, so the whole seems to rise forever."""
    cfg = {"period": 8, "layers": 4, "low": -2, "span": 4, "direction": "up", **v["shepard"]}
    n = int(cfg["layers"])
    if n < 2 or float(cfg["period"]) <= 0 or float(cfg["span"]) <= 0:
        raise SongError(f"voice '{v['name']}': shepard needs layers >= 2 and positive period/span")
    if cfg["direction"] not in ("up", "down"):
        raise SongError(f"voice '{v['name']}': shepard direction must be 'up' or 'down'")
    sign = "" if cfg["direction"] == "up" else "-"
    x = f"\\left(x-{_fmt(offset)}\\right)" if offset else "x"
    tracks = []
    for k in range(n):
        phase = (f"\\operatorname{{mod}}\\left({sign}\\frac{{{x}}}{{{_fmt(cfg['period'])}}}"
                 f"+{_fmt(k / n)},1\\right)")
        pitch = f"{_fmt(cfg['low'])}+{_fmt(cfg['span'])}{phase}"
        amp = f"\\sin\\left(\\pi{phase}\\right)^{{2}}"
        tracks.append(Track(f"{v['name']}{k + 1}", v["name"], pitch, amp,
                            v.get("color", "#f5a623"), share=2 / n))
    return tracks


def _sections(song: dict) -> dict:
    out = {}
    for s in song.get("sections", []):
        if isinstance(s, list):
            s = {"name": s[0], "start": s[1], "end": s[2]}
        n = s.get("name", "")
        if "start" not in s or "end" not in s:
            raise SongError(f"section '{n}' needs 'start' and 'end'")
        if not n or n in out:
            raise SongError(f"section names must be unique and non-empty ('{n}')")
        if float(s["end"]) <= float(s["start"]):
            raise SongError(f"section '{n}' ends before it starts")
        out[n] = (float(s["start"]), float(s["end"]))
    return out


def validate(song: dict) -> None:
    for key in ("title", "voices"):
        if key not in song:
            raise SongError(f"song is missing '{key}'")
    _check_keys(song, SONG_KEYS, "song")
    helpers = song.get("helpers", {})
    for name in helpers:
        if len(name) != 1 or not name.isalpha() or name in RESERVED_HELPERS:
            raise SongError(
                f"helper '{name}' must be a single letter not in {sorted(RESERVED_HELPERS)}"
            )
    if not isinstance(song["voices"], list) or not song["voices"]:
        raise SongError("'voices' must be a non-empty list")
    seen = set()
    for v in song["voices"]:
        if not isinstance(v, dict):
            raise SongError(f"each voice must be an object, got {v!r}")
        name = v.get("name", "")
        _check_keys(v, VOICE_KEYS, f"voice '{name}'")
        if not NAME_RE.match(name):
            raise SongError(f"voice name '{name}' must be alphanumeric, starting with a letter")
        if name in seen:
            raise SongError(f"duplicate voice name '{name}'")
        seen.add(name)
        if sum(k in v for k in KINDS) != 1:
            raise SongError(f"voice '{name}' needs exactly one of {', '.join(KINDS)}")


class _Ids:
    def __init__(self):
        self.n = 0

    def __call__(self) -> str:
        self.n += 1
        return str(self.n)


def build_state(song: dict) -> dict:
    validate(song)
    base_hz = base_frequency(song)
    sections = _sections(song)
    length = song.get("length") or (max(e for _, e in sections.values()) if sections else None)
    speed = song.get("time_scale") or (song["bpm"] / 60 if "bpm" in song else 1)

    voices = song["voices"]
    song_key = parse_key(song["key"]) if "key" in song else None
    tracks_by_voice = [(v, _tracks_for_voice(v, base_hz, song_key)) for v in voices]
    all_names = [t.name for _, ts in tracks_by_voice for t in ts]
    if len(all_names) != len(set(all_names)):
        raise SongError(f"voice names collide after chord expansion: {all_names}")

    nid = _Ids()
    exprs: list[dict] = []

    def folder(title: str, collapsed: bool = True) -> str:
        fid = nid()
        exprs.append({"type": "folder", "id": fid, "title": title, "collapsed": collapsed})
        return fid

    def expr(latex: str, folder_id: str | None = None, **extra) -> None:
        e = {"type": "expression", "id": nid(), "latex": latex}
        if folder_id:
            e["folderId"] = folder_id
        e.update(extra)
        exprs.append(e)

    def note(text: str, folder_id: str | None = None) -> None:
        e = {"type": "text", "id": nid(), "text": text}
        if folder_id:
            e["folderId"] = folder_id
        exprs.append(e)

    window = song.get("window", 8)
    plan = ""
    if sections:
        plan = "\nSections: " + " → ".join(f"{n} ({_fmt(a)}–{_fmt(b)})" for n, (a, b) in sections.items())
    note(f"{song['title']}\n{song.get('description', '')}{plan}\n"
         "Press ▶ on the ticker (top of the list) and unmute the tones in 'Audio'.")

    # --- Controls -------------------------------------------------------
    c = folder("Controls", collapsed=False)
    expr("t=0", c, slider={"hardMin": True, "min": "0", "max": _fmt(length or 64)})
    exprs[-1]["id"] = PLAYHEAD_ID
    expr(f"B={_fmt(round(base_hz, 4))}", c,
         slider={"hardMin": True, "hardMax": True, "min": "55", "max": "880"})
    expr(f"S={_fmt(round(speed, 4))}", c,
         slider={"hardMin": True, "min": "0.25", "max": _fmt(max(4, round(speed * 2, 2))), "step": "0.05"})
    expr(f"L={_fmt(window)}", c, slider={"hardMin": True, "min": "1", "max": "32"})
    for v in voices:
        n = v["name"]
        expr(f"m_{{{n}}}={0 if v.get('muted') else 1}", c,
             slider={"hardMin": True, "hardMax": True, "min": "0", "max": "1", "step": "1"})
        expr(f"g_{{{n}}}={_fmt(v.get('gain', 0.3))}", c,
             slider={"hardMin": True, "hardMax": True, "min": "0", "max": "1", "step": "0.01"})

    # --- Clock helpers --------------------------------------------------
    helpers = song.get("helpers", {})
    if helpers:
        h = folder("Clocks / helpers")
        for name, latex in helpers.items():
            expr(f"{name}\\left(x\\right)={latex}", h, hidden=True)

    # --- Voice definitions ---------------------------------------------
    vf = folder("Voices (pitch in octaves vs B)")
    for v, tracks in tracks_by_voice:
        gate = _section_gate(v, sections)
        vib = v.get("vibrato")
        for tr in tracks:
            body = tr.pitch
            if v.get("transpose"):
                body = f"{body}+{_frac(float(v['transpose']))}"
            if vib:
                rate, depth = vib
                body = f"{body}+{_frac(depth)}\\sin\\left({_fmt(2 * rate)}\\pi x\\right)"
            if gate:
                expr(f"p_{{{tr.name}}}\\left(x\\right)={body}", vf, hidden=True)
                body = _piecewise([f"{_cond('x', a, b)}:p_{{{tr.name}}}\\left(x\\right)" for a, b in gate])
            expr(f"v_{{{tr.name}}}\\left(x\\right)={body}", vf, hidden=True)
            if tr.amp:
                expr(f"a_{{{tr.name}}}\\left(x\\right)={tr.amp}", vf, hidden=True)
        if v.get("dynamics"):
            expr(f"d_{{{v['name']}}}\\left(x\\right)={_dynamics_latex(v['dynamics'])}", vf, hidden=True)

    # --- Visuals: the last L units of each curve, ending at the playhead --
    g = folder("Graph", collapsed=False)
    for v, tracks in tracks_by_voice:
        n = v["name"]
        for tr in tracks:
            expr(f"y=v_{{{tr.name}}}\\left(x+t\\right)\\left\\{{-L<x<0\\right\\}}\\left\\{{m_{{{n}}}=1\\right\\}}",
                 g, color=tr.color, lineWidth="3")
            expr(f"\\left(0,v_{{{tr.name}}}\\left(t\\right)\\right)\\left\\{{m_{{{n}}}=1\\right\\}}",
                 g, color=tr.color, pointSize="12")
    expr("x=0", g, color="#888888", lineStyle="DASHED", lineOpacity="0.4")
    for sname, (a, _) in sections.items():
        expr(f"\\left({_fmt(a)}-t,2.6\\right)", g, color="#888888", label=sname,
             showLabel=True, pointSize="6")

    # --- Audio ---------------------------------------------------------
    a = folder("Audio", collapsed=False)
    for v, tracks in tracks_by_voice:
        n = v["name"]
        for tr in tracks:
            for mult, cents, weight in _partials(v):
                weight *= tr.share
                freq = f"B\\cdot2^{{v_{{{tr.name}}}\\left(t\\right)"
                freq += f"+{_fmt(cents / 1200)}}}" if cents else "}"
                if mult != 1:
                    freq += f"\\cdot{mult}"
                gain = [f"g_{{{n}}}m_{{{n}}}"]
                if abs(weight - 1) > 1e-9:
                    gain.insert(0, _fmt(round(weight, 4)))
                if tr.amp:
                    gain.append(f"a_{{{tr.name}}}\\left(t\\right)")
                if v.get("dynamics"):
                    gain.append(f"d_{{{n}}}\\left(t\\right)")
                gain_latex = "\\cdot ".join(gain)
                expr(f"\\operatorname{{tone}}\\left({freq},{gain_latex}\\right)", a)

    step = _fmt(TICK_MS / 1000)
    handler = (f"t\\to\\operatorname{{mod}}\\left(t+{step}S,{_fmt(length)}\\right)"
               if length else f"t\\to t+{step}S")
    return {
        "version": 11,
        "randomSeed": "desmos-music",
        "graph": {
            "viewport": {"xmin": -window - 0.5, "xmax": 1.5, "ymin": -3, "ymax": 3},
            "showGrid": False,
            "squareAxes": False,
        },
        "expressions": {
            "list": exprs,
            "ticker": {
                "handlerLatex": handler,
                "minStepLatex": str(TICK_MS),
                "open": True,
                "playing": False,
            },
        },
    }


def load_song(song_path: Path) -> dict:
    try:
        song = json.loads(Path(song_path).read_text())
    except json.JSONDecodeError as e:
        raise SongError(f"invalid JSON at line {e.lineno}, column {e.colno}: {e.msg}") from None
    if not isinstance(song, dict):
        raise SongError("a song file must contain a JSON object")
    return song


def build_file(song_path: Path, out_dir: Path) -> list[Path]:
    song = load_song(song_path)
    state = build_state(song)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(song_path).stem
    state_json = json.dumps(state, indent=2, ensure_ascii=False)
    json_path = out_dir / f"{stem}.json"
    json_path.write_text(state_json)
    console_path = out_dir / f"{stem}.console.js"
    console_path.write_text(
        "// Paste into the browser console on https://www.desmos.com/calculator\n"
        f"Calc.setState({json.dumps(state, ensure_ascii=False)});\n"
    )
    return [json_path, console_path]
