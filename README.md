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
python -m desmos_music            # builds every songs/*.json into build/
python -m pytest -q               # tests
```

Open the result in one of two ways:

1. **On desmos.com.** Open https://www.desmos.com/calculator, open the browser console, paste the contents of `build/dune_one.console.js`, and press Enter. Press ▶ on the ticker and turn on the sound icons in the **Audio** folder. Save the graph to get a shareable link.
2. **Local player.** Run `python -m http.server` in the repo root, then open http://localhost:8000/web/. This uses the Desmos API demo key, which is for local testing only.

## Writing a song

```json
{
  "title": "My piece",
  "base_hz": 220,
  "time_scale": 1,
  "window": 8,
  "helpers": { "h": "\\operatorname{mod}\\left(\\frac{x}{2},1\\right)" },
  "voices": [
    { "name": "kick",  "latex": "\\left\\{h\\left(x\\right)<0.3:1.5e^{-14h\\left(x\\right)}-2.1\\right\\}", "gain": 0.9 },
    { "name": "lead",  "notes": [[0, 2, 0], [2, 1, 3], [3, 1, 7]], "loop": 4, "gain": 0.3, "muted": true }
  ]
}
```

- `latex` voices take any Desmos expression in `x`.
- `notes` voices are `[start, duration, semitones]` lists, and the generator turns them into a piecewise function for you. `loop` repeats the phrase.
- Helper names must be single letters, other than `t x y B S L e`. Voice names must be alphanumeric.

## Known limits

- The Desmos ticker fires about every 20–50 ms, so timing isn't sample-accurate. That matters most for fast drums.
- `tone()` plays only sine waves. Richer timbres come from stacking several voices (overtones, detuning).
