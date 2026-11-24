# Changelog

## 0.2.0 — 2026-11-23

### Composing
- Note names (`A3`, `Bb2`), scale degrees in a `key` (`^1 ^b2 ^5'`), chord symbols (`[A3m]`, `[F3maj7]`) and ghost notes (`A3?`).
- `seq` tracker strings and `hits` drum grids alongside `latex` and `notes`.
- Chords split into one voice per note, with the gain shared between them. `arp` / `arp_step` arpeggiate them.
- ADSR envelopes (`env`), harmonic timbres (`timbre`), `detune`, `glide`, `vibrato`, `transpose`, `swing`, `offset`.
- `dynamics` automation, `sections` with per-voice `in`, and a playhead that loops at the end of the song.
- `shepard` voice kind for endless rises and falls.
- Drum presets: `kick`, `taiko`, `tom`, `tick`. Timbres: `organ`, `full_organ`, `reed`, `hollow`, `brass`.

### Tools
- `new --style basic|dune|interstellar`, `serve`, `watch`, `stats [--strict]`, `import-midi`, `build --check`.
- Lint warnings for out-of-range frequencies, too many `tone()` calls, clipping risk per section, and phrases that enter mid-phrase.
- Unknown keys get a "did you mean" hint. Bad JSON, sections, vibrato and dynamics give clear errors.
- MIDI import: dependency-free SMF reader, polyphony split into lanes, quantize, GM drums turned into `hits`.

### Player
- Song picker from `build/index.json`, play/pause (Space), restart, beat/section readout, copy-for-desmos.com, remembers the last song, live reload that keeps the playhead.

### Songs
- New original pieces: `arrakis`, `sietch` (Dune-style), `event_horizon`, `tesseract`, `docking` (Interstellar-style), and five tutorials.
- All songs load in Desmos with zero expression errors.

### Infrastructure
- CI runs tests on Python 3.9, 3.11 and 3.12, checks that `build/` is current, and prints the song report.

## 0.1.0

- First version: song JSON → Desmos state, `dune_one` transcription, local player.
