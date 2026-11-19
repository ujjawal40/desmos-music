"""Turn a song file (JSON) into a Desmos Graphing Calculator state.

Model (same as the @measure_plan demo):
  * x is time. A ticker advances the playhead variable t.
  * Each voice is a function v_name(x) returning pitch in OCTAVES relative
    to the base frequency B (so 1/12 = one semitone, 7/12 = a fifth).
  * The graph draws each voice's curve scrolling past the playhead, and a
    tone() expression plays it: tone(B * 2^(v_name(t)), gain * mute).
  * Where a voice is undefined (a piecewise with no matching branch), it is
    silent and nothing is drawn — that's how rhythm/gating works.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")
TICK_MS = 50  # ticker step; Desmos fires roughly every 20ms at best
RESERVED_HELPERS = {"t", "x", "y", "B", "S", "L", "e"}


class SongError(ValueError):
    pass


def _fmt(n: float) -> str:
    """Number -> compact LaTeX-safe literal."""
    if float(n).is_integer():
        return str(int(n))
    return repr(float(n))


def notes_to_latex(notes: list, loop: float | None) -> str:
    """[[start, duration, semitones], ...] -> Desmos piecewise in octaves.

    With `loop`, time wraps every `loop` units so the phrase repeats.
    """
    if not notes:
        raise SongError("notes voice needs at least one note")
    u = (
        f"\\operatorname{{mod}}\\left(x,{_fmt(loop)}\\right)" if loop else "x"
    )
    branches = []
    for i, note in enumerate(notes):
        if len(note) != 3:
            raise SongError(f"note #{i} must be [start, duration, semitones]")
        start, dur, semi = note
        if dur <= 0:
            raise SongError(f"note #{i} has non-positive duration")
        end = start + dur
        branches.append(
            f"{_fmt(start)}\\le {u}<{_fmt(end)}:\\frac{{{_fmt(semi)}}}{{12}}"
        )
    return "\\left\\{" + ",".join(branches) + "\\right\\}"


def validate(song: dict) -> None:
    for key in ("title", "voices"):
        if key not in song:
            raise SongError(f"song is missing '{key}'")
    helpers = song.get("helpers", {})
    for name in helpers:
        if len(name) != 1 or not name.isalpha() or name in RESERVED_HELPERS:
            raise SongError(
                f"helper '{name}' must be a single letter not in {sorted(RESERVED_HELPERS)}"
            )
    seen = set()
    for v in song["voices"]:
        name = v.get("name", "")
        if not NAME_RE.match(name):
            raise SongError(f"voice name '{name}' must be alphanumeric, starting with a letter")
        if name in seen:
            raise SongError(f"duplicate voice name '{name}'")
        seen.add(name)
        if ("latex" in v) == ("notes" in v):
            raise SongError(f"voice '{name}' needs exactly one of 'latex' or 'notes'")


class _Ids:
    def __init__(self):
        self.n = 0

    def __call__(self) -> str:
        self.n += 1
        return str(self.n)


def build_state(song: dict) -> dict:
    validate(song)
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
    note(f"{song['title']}\n{song.get('description', '')}\n"
         "Press the ▶ on the ticker (top of the list) and unmute the tones in 'Audio'.")

    # --- Controls -------------------------------------------------------
    c = folder("Controls", collapsed=False)
    expr("t=0", c, slider={"hardMin": True, "min": "0", "max": "64"})
    expr(f"B={_fmt(song.get('base_hz', 220))}", c,
         slider={"hardMin": True, "hardMax": True, "min": "55", "max": "880"})
    expr(f"S={_fmt(song.get('time_scale', 1))}", c,
         slider={"hardMin": True, "min": "0.25", "max": "4", "step": "0.05"})
    expr(f"L={_fmt(window)}", c, slider={"hardMin": True, "min": "1", "max": "32"})
    for v in song["voices"]:
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
    for v in song["voices"]:
        body = v["latex"] if "latex" in v else notes_to_latex(v["notes"], v.get("loop"))
        expr(f"v_{{{v['name']}}}\\left(x\\right)={body}", vf, hidden=True)

    # --- Visuals: curves scroll left into the playhead at x=0 ----------
    g = folder("Graph", collapsed=False)
    for v in song["voices"]:
        n, color = v["name"], v.get("color", "#f5a623")
        expr(f"y=v_{{{n}}}\\left(x+t\\right)\\left\\{{-L<x<0\\right\\}}\\left\\{{m_{{{n}}}=1\\right\\}}",
             g, color=color, lineWidth="3")
        expr(f"\\left(0,v_{{{n}}}\\left(t\\right)\\right)\\left\\{{m_{{{n}}}=1\\right\\}}",
             g, color=color, pointSize="12")
    expr("x=0", g, color="#888888", lineStyle="DASHED", lineOpacity="0.4")

    # --- Audio ---------------------------------------------------------
    a = folder("Audio", collapsed=False)
    for v in song["voices"]:
        n = v["name"]
        expr(f"\\operatorname{{tone}}\\left(B\\cdot2^{{v_{{{n}}}\\left(t\\right)}},g_{{{n}}}m_{{{n}}}\\right)", a)

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
                "handlerLatex": f"t\\to t+{_fmt(TICK_MS / 1000)}S",
                "minStepLatex": str(TICK_MS),
                "open": True,
                "playing": False,
            },
        },
    }


def build_file(song_path: Path, out_dir: Path) -> list[Path]:
    song = json.loads(Path(song_path).read_text())
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
