# CLAUDE.md — context for Claude Code

## What this project is
A toolkit for making music **as Desmos graphs**, in the style of @measure_plan's viral clip (https://x.com/measure_plan/status/2122781804641804530, Nov 17 2026). In that clip he composes Dune-style music on a graphing calculator. The owner explicitly does **not** want a regular audio synth or DAW. The output must stay a Desmos graph where you can see the curves and hear them with `tone()`.

## What the original clip shows (read off the screen; the audio wasn't heard)
```
h = frac(x/2)          w = frac(x/8)
kick = { 1.5e^(-14h) - 2.1   if h < 0.3 }
high = { 19/12 - (w-0.5)/6   if w > 0.5 }
y = { kick, -1 + 3w²/12, 7/12 - w/12, -1, high }
```
Our reading of it is that `y` is pitch in octaves (that's why the denominators are 12). The clip has 6 sections, and only the first was transcribed. Desmos has no `frac`, so we use `mod(·,1)`.

## Layout
- `songs/*.json` — song definitions (the source of truth)
- `desmos_music/build.py` — song → Desmos state JSON (`build_state`), plus `notes_to_latex`
- `desmos_music/__main__.py` — CLI: `python -m desmos_music [songs...] -o build/`
- `build/` — generated output: `<song>.json` (state) and `<song>.console.js` (`Calc.setState(...)` to paste on desmos.com)
- `web/index.html` — local player using the Desmos API (demo key)
- `tests/` — pytest

## Verified facts
- The generated `dune_one` state loads on desmos.com/calculator with **zero expression errors** (checked through `Calc.expressionAnalysis`), and it renders like the clip.
- Desmos's `tone(freq, gain)` accepts 20–20000 Hz, with gain usually 0–1 (up to 10 at low frequencies).
- The ticker **does not** provide `dt`. `t→t+S·dt/1000` parsed `dt` as `d·t`. Use a fixed step (`TICK_MS` in build.py).
- Function definitions get plotted unless `hidden: true` is set. Graphs need `squareAxes: false`, or the y-range is ignored.
- User-defined names: single letters, optionally with an alphanumeric subscript (`v_{kick}`).
- Not yet verified: whether `tone()` makes sound through the embedded API in `web/index.html`.

## Roadmap / ideas (not built yet)
- Transcribe sections 2–6 of the clip into more songs, or into sections of one song.
- Song sections/arrangement: switch voice sets over time (`{t<16: ..., t<32: ...}`).
- Note names in the notes DSL (`"D3"` instead of semitone numbers), scales, chords.
- Envelopes as reusable helpers (attack/decay applied to gain, not only pitch).
- Timbre: voice option `harmonics: [1, 0.5, 0.25]` that emits extra `tone()` lines at 2^k multiples.
- MIDI → song JSON importer.
- Playhead-follow viewport option (curves drawn up to a moving dot, as in the clip).
- Pushing to Desmos: saving a graph needs an account; for now the user pastes the console script.

## Conventions
- Pitch is always in octaves relative to `B`. Keep the generator pure (dict in, dict out) and test it.
- Run `python -m pytest -q` and rebuild `build/` before committing.
