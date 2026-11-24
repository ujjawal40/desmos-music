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
- `desmos_music/music.py` — note names, `seq`/`hits` parsers, presets (ENVELOPES, TIMBRES, DRUMS). No LaTeX here.
- `desmos_music/build.py` — song → Desmos state JSON (`build_state`): voices → Tracks → LaTeX
- `desmos_music/__main__.py` — CLI: `python -m desmos_music [songs...] -o build/`, `new NAME`, `serve`
- `build/` — generated output: `<song>.json` (state), `<song>.console.js` (`Calc.setState(...)` to paste on desmos.com), `index.json` (song list for the player)
- Songs: `dune_one` (clip transcription), `arrakis` (original Dune-style), `event_horizon` (original Interstellar-style). Bundled pieces are original compositions *in the style of* those scores; don't transcribe the copyrighted film themes.
- `web/index.html` — local player using the Desmos API (demo key)
- `tests/` — pytest

## Verified facts
- The generated `dune_one` state loads on desmos.com/calculator with **zero expression errors** (checked through `Calc.expressionAnalysis`), and it renders like the clip.
- Desmos's `tone(freq, gain)` accepts 20–20000 Hz, with gain usually 0–1 (up to 10 at low frequencies).
- The ticker **does not** provide `dt`. `t→t+S·dt/1000` parsed `dt` as `d·t`. Use a fixed step (`TICK_MS` in build.py).
- Function definitions get plotted unless `hidden: true` is set. Graphs need `squareAxes: false`, or the y-range is ignored.
- User-defined names: single letters, optionally with an alphanumeric subscript (`v_{kick}`).
- `dune_one`, `arrakis` and `event_horizon` all load with zero expression errors in the local player (API v1.11). Probed values match (notes, glide, chord split, gating, envelopes), and the ticker wraps with `mod(t+…, length)`.
- Desmos `\min(a,b,c)` accepts multiple args. Never join LaTeX factors as `\cdot` + letter (`\cdotm` breaks); use `\cdot ` with a space.
- Piecewise takes the first matching branch, so drum hits are cut off at the next hit.
- `calc.setState()` silently disconnects every `HelperExpression`. Re-create helpers after each setState (see `setGraph` in web/index.html).
- The playhead slider has the stable id `playhead`, so seek with `calc.setExpression({id: 'playhead', latex: 't=…'})`.
- Not yet verified: whether `tone()` makes sound through the embedded API in `web/index.html` (nobody has listened yet).

## Roadmap / ideas (not built yet)
- Transcribe sections 2–6 of the clip into more songs, or into sections of one song.
- Done: sections (`in`), note names, chords, ADSR envelopes, timbres, detune, glide, vibrato, dynamics, drum grids, offset.
- Scales/degree notation (`"key": "D phrygian"`, `seq: "1 b2 1 7"`).
- MIDI → song JSON importer.
- Playhead-follow viewport option (curves drawn up to a moving dot, as in the clip).
- Pushing to Desmos: saving a graph needs an account; for now the user pastes the console script.

## Conventions
- Pitch is always in octaves relative to `B`. Keep the generator pure (dict in, dict out) and test it.
- Run `python -m pytest -q` and rebuild `build/` before committing.
