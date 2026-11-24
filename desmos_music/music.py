"""Music vocabulary: note names, sequences, drum patterns, presets.

Everything here is plain data in, plain data out — no LaTeX. build.py turns
the resulting events into Desmos expressions.

Time is in song units ("beats"); the ticker converts with S = units/second.
Pitch is in semitones relative to the song's base frequency B.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

NOTE_RE = re.compile(r"^([A-Ga-g])([#b]*)(-?\d+)$")
LETTER = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


class SongError(ValueError):
    pass


# --- pitch -----------------------------------------------------------------

def note_hz(name: str) -> float:
    """'A4' -> 440.0, 'C#3', 'Bb2', ... (scientific pitch notation)."""
    m = NOTE_RE.match(name.strip())
    if not m:
        raise SongError(f"bad note name '{name}' (use e.g. A3, C#4, Bb2)")
    letter, acc, octave = m.groups()
    midi = 12 * (int(octave) + 1) + LETTER[letter.upper()] + acc.count("#") - acc.count("b")
    return 440.0 * 2 ** ((midi - 69) / 12)


def semitones(pitch, base_hz: float) -> float:
    """Pitch (number of semitones, or note name) -> semitones above base_hz."""
    if isinstance(pitch, (int, float)) and not isinstance(pitch, bool):
        return float(pitch)
    if isinstance(pitch, str):
        try:
            return float(pitch)
        except ValueError:
            pass
        s = 12 * math.log2(note_hz(pitch) / base_hz)
        r = round(s)
        return float(r) if abs(s - r) < 1e-6 else round(s, 4)
    raise SongError(f"bad pitch {pitch!r}")


def base_frequency(song: dict) -> float:
    if "base" in song:
        return note_hz(song["base"])
    return float(song.get("base_hz", 220))


# --- scales ----------------------------------------------------------------

SCALES = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "lydian": [0, 2, 4, 6, 7, 9, 11],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "locrian": [0, 1, 3, 5, 6, 8, 10],
    "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
    "phrygian_dominant": [0, 1, 4, 5, 7, 8, 10],
    "double_harmonic": [0, 1, 4, 5, 7, 8, 11],
    "hungarian_minor": [0, 2, 3, 6, 7, 8, 11],
}
SCALES["ionian"] = SCALES["major"]
SCALES["aeolian"] = SCALES["minor"]


@dataclass
class Key:
    tonic_hz: float
    steps: list


def parse_key(text: str) -> Key:
    """'D3 phrygian' -> Key. The tonic needs an octave; mode defaults to major."""
    parts = text.split()
    if not parts or len(parts) > 2:
        raise SongError(f"bad key '{text}' (use e.g. 'D3 phrygian')")
    mode = parts[1].lower() if len(parts) == 2 else "major"
    if mode not in SCALES:
        raise SongError(f"unknown scale '{mode}' (have: {', '.join(sorted(SCALES))})")
    return Key(note_hz(parts[0]), SCALES[mode])


# --- events ----------------------------------------------------------------

@dataclass
class Note:
    start: float
    dur: float
    pitches: list  # semitones; several = chord

    @property
    def end(self) -> float:
        return self.start + self.dur


@dataclass
class Hit:
    start: float
    amp: float


def parse_notes(notes: list, base_hz: float) -> list[Note]:
    """[[start, duration, pitch], ...]; pitch may be a list for a chord."""
    out = []
    for i, n in enumerate(notes):
        if not isinstance(n, (list, tuple)) or len(n) != 3:
            raise SongError(f"note #{i} must be [start, duration, pitch]")
        start, dur, p = n
        if dur <= 0:
            raise SongError(f"note #{i} has non-positive duration")
        ps = p if isinstance(p, list) else [p]
        out.append(Note(float(start), float(dur), [semitones(x, base_hz) for x in ps]))
    if not out:
        raise SongError("notes voice needs at least one note")
    return out


def _split_dur(tok: str, step: float) -> tuple[str, float]:
    if ":" in tok:
        body, d = tok.rsplit(":", 1)
        try:
            dur = float(d)
        except ValueError:
            raise SongError(f"bad duration in '{tok}'") from None
        if dur <= 0:
            raise SongError(f"non-positive duration in '{tok}'")
        return body, dur
    return tok, step


def parse_seq(seq: str, step: float, base_hz: float) -> tuple[list[Note], float]:
    """Tracker-style sequence -> (notes, total length).

    Tokens, whitespace separated, each `step` long unless given `:dur`:
      A3  C#4  Bb2  7      a note (name or semitones above base)
      A3+C4+E4             a chord
      -                    hold the previous note one more step
      .  or  r             rest
      |                    bar line (ignored)
    """
    notes: list[Note] = []
    t = 0.0
    last_was_note = False
    for tok in seq.split():
        if tok == "|":
            continue
        if tok == "-":
            if not last_was_note:
                raise SongError("'-' (hold) must follow a note")
            notes[-1].dur += step
            t += step
            continue
        body, dur = _split_dur(tok, step)
        if body in (".", "r"):
            last_was_note = False
        else:
            notes.append(Note(t, dur, [semitones(p, base_hz) for p in body.split("+")]))
            last_was_note = True
        t += dur
    if not notes:
        raise SongError("seq has no notes")
    return notes, t


def parse_hits(pattern: str, step: float) -> tuple[list[Hit], float]:
    """Drum grid: 'X' accent, 'x' normal, '.' rest; spaces and '|' ignored."""
    hits = []
    t = 0.0
    for ch in pattern:
        if ch in " |\n\t":
            continue
        if ch == "X":
            hits.append(Hit(t, 1.0))
        elif ch == "x":
            hits.append(Hit(t, 0.6))
        elif ch != ".":
            raise SongError(f"bad drum character '{ch}' (use X x .)")
        t += step
    if not hits:
        raise SongError("hits pattern has no hits")
    return hits, t


# --- presets ---------------------------------------------------------------

# ADSR in song units: attack, decay, sustain level, release.
ENVELOPES = {
    "pluck": {"a": 0.01, "d": 0.35, "s": 0.25, "r": 0.05},
    "organ": {"a": 0.04, "d": 0, "s": 1, "r": 0.08},
    "pad": {"a": 0.8, "d": 0, "s": 1, "r": 0.8},
    "voice": {"a": 0.25, "d": 0.4, "s": 0.75, "r": 0.3},
    "bell": {"a": 0.005, "d": 1.2, "s": 0.0, "r": 0.05},
}

# Relative amplitudes of harmonics 1, 2, 3, ... (0 = skip). tone() is a pure
# sine, so these are how you get colour.
TIMBRES = {
    "sine": [1],
    "organ": [1, 0.7, 0, 0.45],          # 8' + 4' + 2' pipe stops
    "full_organ": [1, 0.7, 0.35, 0.45, 0, 0.2, 0, 0.25],
    "reed": [1, 0.6, 0.45, 0.3, 0.2],
    "hollow": [1, 0, 0.33, 0, 0.2],      # odd harmonics, clarinet-ish
    "brass": [1, 0.8, 0.6, 0.4, 0.25],
}

# Pitch-drop drums, in octaves vs B and song units:
#   pitch(τ) = bottom + top·e^(−decay·τ)   for 0 ≤ τ < len
DRUMS = {
    "kick": {"top": 1.5, "bottom": -2.1, "decay": 7, "len": 0.6},
    "taiko": {"top": 1.2, "bottom": -1.9, "decay": 4, "len": 1.0},
    "tom": {"top": 1.0, "bottom": -1.0, "decay": 6, "len": 0.5},
    "tick": {"top": 0, "bottom": 2.5, "decay": 0, "len": 0.12},
}


def resolve_preset(value, table: dict, what: str) -> dict | list:
    if isinstance(value, str):
        if value not in table:
            raise SongError(f"unknown {what} '{value}' (have: {', '.join(table)})")
        return table[value]
    return value
