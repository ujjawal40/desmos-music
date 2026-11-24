"""Static facts about a song: duration, tone count, pitch/frequency ranges."""

from __future__ import annotations

from .build import _partials, _sections, build_state
from .music import (
    DRUMS,
    arpeggiate,
    base_frequency,
    parse_hits,
    parse_key,
    parse_notes,
    parse_seq,
    resolve_preset,
)


def _kind(v: dict) -> str:
    return next(k for k in ("latex", "notes", "seq", "hits", "shepard") if k in v)


def _range(v: dict, base_hz: float, song_key) -> tuple[float, float] | None:
    """Pitch range in semitones vs B, or None when it can't be known statically."""
    key = parse_key(v["key"]) if "key" in v else song_key
    kind = _kind(v)
    if kind in ("seq", "notes"):
        if kind == "seq":
            notes, _ = parse_seq(v["seq"], float(v.get("step", 1)), base_hz, key)
        else:
            notes = parse_notes(v["notes"], base_hz, key)
        if "arp" in v:
            notes = arpeggiate(notes, v["arp"], float(v.get("arp_step", 0.5)))
        ps = [p for n in notes for p in n.pitches]
        lo, hi = min(ps), max(ps)
    elif kind == "hits":
        d = dict(DRUMS["kick"])
        d.update(resolve_preset(v.get("drum", "kick"), DRUMS, "drum"))
        parse_hits(v["hits"], float(v.get("step", 1)))
        ends = (12 * d["bottom"], 12 * (d["bottom"] + d["top"]))
        lo, hi = min(ends), max(ends)
    elif kind == "shepard":
        cfg = {"low": -2, "span": 4, **v["shepard"]}
        lo, hi = 12 * cfg["low"], 12 * (cfg["low"] + cfg["span"])
    else:
        try:
            lo = hi = 12 * float(v["latex"])
        except ValueError:
            return None
    t = float(v.get("transpose", 0))
    vib = float(v["vibrato"][1]) if v.get("vibrato") else 0
    return lo + t - vib, hi + t + vib


def song_stats(song: dict) -> dict:
    state = build_state(song)  # validates
    base_hz = base_frequency(song)
    sections = _sections(song)
    length = song.get("length") or (max(e for _, e in sections.values()) if sections else None)
    speed = song.get("time_scale") or (song["bpm"] / 60 if "bpm" in song else 1)
    song_key = parse_key(song["key"]) if "key" in song else None
    tones = [e for e in state["expressions"]["list"] if "\\operatorname{tone}" in e.get("latex", "")]
    voices = []
    for v in song["voices"]:
        rng = _range(v, base_hz, song_key)
        parts = _partials(v)
        hz = None
        if rng:
            top_mult = max(m * 2 ** (c / 1200) for m, c, _ in parts)
            hz = (base_hz * 2 ** (rng[0] / 12), base_hz * 2 ** (rng[1] / 12) * top_mult)
        voices.append({
            "name": v["name"], "kind": _kind(v), "gain": float(v.get("gain", 0.3)),
            "semitones": rng, "hz": hz,
        })
    return {
        "title": song["title"],
        "base_hz": base_hz,
        "length_beats": length,
        "seconds": length / speed if length else None,
        "tones": len(tones),
        "expressions": len(state["expressions"]["list"]),
        "voices": voices,
    }


MAX_TONES = 32


def lint(song: dict) -> list[str]:
    """Warnings about things that build fine but will probably sound wrong."""
    st = song_stats(song)
    warns = []
    for v in st["voices"]:
        if v["hz"] and (v["hz"][0] < 20 or v["hz"][1] > 20000):
            warns.append(f"voice '{v['name']}' reaches {v['hz'][0]:.0f}–{v['hz'][1]:.0f} Hz; "
                         "Desmos tone() only plays 20–20000 Hz")
    if st["tones"] > MAX_TONES:
        warns.append(f"{st['tones']} tone() expressions; above ~{MAX_TONES} playback may stutter "
                     "(use simpler timbres or fewer voices)")
    return warns
