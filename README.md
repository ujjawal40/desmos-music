# desmos-music

Compose music as math functions in the Desmos Graphing Calculator. You can see every voice as a curve and hear it through Desmos's built-in `tone()` function.

Inspired by [@measure_plan's "Dune soundtrack on a graphing calculator"](https://x.com/measure_plan/status/2122781804641804530) clip. `songs/dune_one.json` rebuilds the first section of that clip from the formulas shown on screen.

## How it works

| Idea | In Desmos |
|---|---|
| Time | `x` on the graph; a ticker moves the playhead `t` forward |
| Pitch | each voice is `v_name(x)`, in **octaves** relative to base frequency `B` (1/12 = semitone, 7/12 = fifth) |
| Rhythm | clocks like `h(x) = mod(x/2, 1)`, plus piecewise `{condition: value}`. Where a voice is undefined, it's silent. |
| Drums | fast exponential pitch drops, e.g. kick `1.5e^(−14h) − 2.1` |
| Sound | `tone(B·2^(v_name(t)), gain·mute)` for each voice |
| Visuals | each curve scrolls left into the playhead at `x = 0` |

Each generated graph includes sliders for tempo (`S`), base pitch (`B`), visible window (`L`), and mute/gain for every voice (`m_name`, `g_name`).

## Quick start

```bash
python -m desmos_music serve       # build every song, serve http://localhost:8000/web/ (--port N)
python -m desmos_music new my_song --style dune   # or interstellar / basic
python -m desmos_music             # just build songs/*.json into build/
python -m desmos_music watch       # rebuild on save (tick "live" in the player)
python -m desmos_music stats       # duration, tone count, frequency ranges, warnings
python -m desmos_music import-midi tune.mid   # MIDI -> songs/tune.json
python -m pytest -q                # tests
```

Songs included:

| Song | What it is |
|---|---|
| `dune_one` | Transcription of the first section of @measure_plan's clip |
| `arrakis` | Original Dune-style piece: beating D drone, Phrygian throat chant, taiko war drums, sliding vocal wail, sandworm riser |
| `event_horizon` | Original Interstellar-style piece: ticking clock, pipe-organ drone, A-minor organ ostinato, pads, bass, slow melody |
| `tesseract` | Original Interstellar-style piece in E minor: 3+3+2 clock, organ "pulse" arpeggio, never-ending Shepard rise, bell coda |
| `docking` | Original high-tension piece in C minor: driving organ pulse, octave bass, fast Shepard rise, taiko, final locked chord |
| `sietch` | Original Dune-style piece in D double-harmonic: falling Shepard wind, chant with ghost notes, swung taiko, braam, wail |
| `tutorial_1`…`tutorial_5` | One idea each: drone → melody → chords/arpeggio → drums → sections and dynamics |

You can open a result in one of two ways:

1. **Local player.** `python -m desmos_music serve`, then pick a song and press ▶ on the ticker. This uses the Desmos API demo key, which is for local testing only.
2. **On desmos.com.** Open https://www.desmos.com/calculator, open the browser console, paste `build/<song>.console.js`, and press Enter. Save the graph to get a shareable link.

## Writing a song

For ready-made sounds (organ, clock, war drums, throat chant, Shepard riser) see [docs/COOKBOOK.md](docs/COOKBOOK.md).

Time is in **beats** (set `bpm`), pitch is in note names or semitones, and everything compiles down to plain Desmos functions you can see and edit.

```jsonc
{
  "title": "My piece",
  "base": "A3",            // B = this note's frequency (or "base_hz": 220)
  "bpm": 72,               // or "time_scale": units per second
  "window": 8,             // beats of history drawn behind the playhead
  "sections": [            // optional; the playhead loops at the end of the last section
    {"name": "intro", "start": 0, "end": 16},
    {"name": "main",  "start": 16, "end": 48}
  ],
  "voices": [ ... ]
}
```

### Voice kinds (exactly one per voice)

| Key | Example | Meaning |
|---|---|---|
| `latex` | `"-1"`, `"\\frac{7}{12}-\\frac{w(x)}{12}"` | Any Desmos expression in `x`, in octaves vs B |
| `seq` | `"A3 E4 - . C4+E4+G4:2 \| 7"` | Tracker string: note per `step`; `-` hold, `.`/`r` rest, `+` chord, `:2` explicit duration, `\|` bar line (ignored), numbers = semitones. Loops over its own length. |
| `notes` | `[[0, 2, "D3"], [2, 1, 3], [3, 1, ["A3","C4"]]]` | `[start, duration, pitch]` triples; add `"loop"` to repeat |
| `hits` | `"X..x X.x."` | Drum grid per `step`: `X` accent, `x` hit, `.` rest. Pitch-drop drum like the clip's kick. |
| `shepard` | `{"period": 8, "layers": 4, "low": -2, "span": 4, "direction": "up"}` | Shepard tone: stacked glissandi that seem to rise (or fall) forever. Good for tension. |

### Pitch notation

Anywhere a pitch goes (`seq` tokens, `notes` third field):

| Write | Means |
|---|---|
| `A3`, `C#4`, `Bb2` | Note names (scientific pitch, A4 = 440 Hz) |
| `7`, `-5` | Semitones above/below B |
| `^1`, `^b3`, `^#4`, `^5'`, `^1,` | Scale degree in the song's or voice's `key` (`'` = octave up, `,` = down, `^8` = octave) |
| `[A3m]`, `[F3maj7]`, `[E3sus4]` | Chord symbol: root with octave + `m 5 dim aug sus2 sus4 7 maj7 m7 m7b5 dim7 add9 madd9 m9` |
| `A3+C4+E4` | Any chord, note by note |
| `A3?` | Ghost note at half volume (`seq` only) |

`"key": "D3 phrygian"` takes a tonic with an octave plus one of `major minor dorian phrygian lydian mixolydian locrian harmonic_minor phrygian_dominant double_harmonic hungarian_minor`. The last few give the "desert" sound.

### Voice options

| Option | Default | What it does |
|---|---|---|
| `step` | `1` | Beats per `seq`/`hits` token (`0.5` = eighth notes) |
| `loop` | seq length | Repeat period. `0` = don't loop |
| `offset` | `0` | Shift the voice's clock so a phrase starts at beat N |
| `in` | always | Section name(s) the voice plays in |
| `env` | none | Per-note ADSR: `pluck`, `organ`, `pad`, `voice`, `bell`, or `{"a":..,"d":..,"s":..,"r":..}`. Can also be a LaTeX gain curve in `x`. |
| `timbre` | `sine` | Harmonic stack. Presets are `organ`, `full_organ`, `reed`, `hollow`, and `brass`, or a list of amplitudes for harmonics 1, 2, 3, ... Each harmonic is one extra `tone()`. |
| `detune` | `0` | Adds a copy this many cents sharp, which gives a slow beating/chorus |
| `glide` | `0` | Portamento time between back-to-back notes |
| `vibrato` | none | `[rate per beat, depth in semitones]` |
| `dynamics` | none | `[[beat, level], ...]` linear automation (crescendos and fades) |
| `drum` | `kick` | For `hits`: `kick`, `taiko`, `tom`, `tick`, or `{"top","bottom","decay","len"}` |
| `key` | song's key | Key for `^degree` pitches in this voice |
| `transpose` | `0` | Shift the whole voice by semitones (any voice kind) |
| `arp`, `arp_step` | none, `0.5` | Break chords into an arpeggio: `up`, `down`, `updown`, `alberti`, `pulse`, or indices like `"0 2 1 3"` (past the top wraps an octave up) |
| `swing` | `0.5` | For `hits`: where off-beats land (0.5 straight, ~0.67 shuffle) |
| `gain`, `muted`, `color` | `0.3`, `false`, orange | Mixer and look |

Helper names (`"helpers": {"h": ...}`) must be single letters, other than `t x y B S L e`.

### What gets generated

For voice `arp`: `v_{arp}(x)` is pitch in octaves (`p_{arp}` holds the ungated pattern when `in` is used), `a_{arp}(x)` is the note envelope, `d_{arp}(x)` is dynamics, and `g_{arp}`/`m_{arp}` are its gain and mute sliders. Chords become `v_{pad1}`, `v_{pad2}`, ..., which share one gain. Each `tone()` is
`tone(B·2^(v(t))·k, weight·g·m·a(t)·d(t))`.

## Importing MIDI

`python -m desmos_music import-midi file.mid [--name x] [--grid 0.25] [--max-lanes 4] [--force]`

- Every track/channel becomes `notes` voices. Overlapping notes are spread over monophonic lanes (`pad`, `pad2`, ...), because each `tone()` plays one pitch, and the top line stays in the first lane.
- Channel 10 (General MIDI drums) becomes `hits` voices: kicks go to `kick`, toms and snares to `tom`, hats to `tick`.
- Timing is quantized to `--grid` beats (`0` turns it off). The first tempo in the file sets `bpm`.
- The result is a normal song file. Edit it, add sections, change timbres.

## Player

`python -m desmos_music serve` opens a song picker with ▶/⏸ (or Space), ⏮ restart, a beat/section readout and a **Copy for desmos.com** button. Tick **live** while `watch` runs to hot-reload the graph on every save without losing the playhead.

## Known limits

- The Desmos ticker fires about every 20–50 ms, so timing isn't sample-accurate. That matters most for fast drums.
- `tone()` plays only sine waves. Richer timbres come from stacking several voices (overtones, detuning).
- Many voices × timbre partials means many `tone()` calls (≈20–25 in the bundled songs). Keep it moderate if playback stutters.
