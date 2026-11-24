# Cookbook: cinematic sounds from sine waves

`tone()` plays one sine wave. Everything below is built by stacking sines (timbre), shaping them over time (envelopes, dynamics), and moving pitch (glide, vibrato, latex curves). Copy a snippet into a song's `voices` and tweak it.

## Space-organ (Interstellar-style)

**Pipe-organ pedal drone.** Use a low root with the octave stops, plus a slight detune so it slowly beats:

```json
{"name": "pedal", "latex": "-1", "timbre": "organ", "detune": 7,
 "dynamics": [[0, 0], [12, 1]], "gain": 0.25}
```

`full_organ` adds the 3rd, 6th and 8th harmonics for a brighter, louder registration. Each harmonic is one more `tone()`, so use it on one voice, not every voice.

**Ticking clock.** Use a short high blip on each beat, accented once per bar:

```json
{"name": "tick", "hits": "X . x . x . x .", "step": 0.5, "drum": "tick", "gain": 0.12}
```

**Organ ostinato.** Write chord symbols and let the arpeggiator do the work. Eighth notes at 60–80 bpm sound right:

```json
{"name": "arp", "seq": "[A3m]:4 [F3]:4 [D3m]:4 [E3]:4", "arp": "pulse", "arp_step": 0.5,
 "env": "organ", "timbre": "organ", "gain": 0.25}
```

`pulse` alternates a moving line against the top note (0 3 1 3 2 3 1 3). For a calmer feel use `updown`.

**Slow swell.** A `pad` envelope on each chord, plus `dynamics` across the section:

```json
{"name": "pad", "seq": "[A3m]:8 [F3maj7]:8", "env": "pad", "timbre": "organ",
 "dynamics": [[48, 0], [56, 1]], "gain": 0.3}
```

## Desert epic (Dune-style)

**Scales.** `phrygian` (♭2) is the classic darkness. `phrygian_dominant` and `double_harmonic` add the augmented second that reads as "desert". Set it once on the song:

```json
"key": "D3 double_harmonic"
```

Then write melodies in degrees: `"^1:2 ^b2 ^1 ^7, ^1:4"`.

**War drums.** `taiko` is a long, low pitch-drop. Keep the pattern sparse and leave the gaps:

```json
{"name": "drums", "hits": "X . . x X . x .", "step": 0.5, "drum": "taiko", "gain": 0.6}
```

A little `swing` (0.55–0.6) makes it lurch rather than march.

**Throat chant.** Use a buzzy timbre low in the range, with slow slides and a slow wobble:

```json
{"name": "chant", "seq": "^1:3 ^b2 ^1:2 ^7,:2", "key": "D3 phrygian", "timbre": "brass",
 "env": "voice", "glide": 0.25, "vibrato": [1.5, 0.2], "gain": 0.25}
```

**Vocal wail.** Use a hollow (odd-harmonic) tone, high, with long glides and a wide vibrato. Glide only happens between notes that touch, so avoid rests inside a phrase:

```json
{"name": "wail", "seq": "D5:2 Eb5 D5 C5:2 Bb4 A4", "timbre": "hollow", "env": "voice",
 "glide": 0.18, "vibrato": [3, 0.35], "gain": 0.22}
```

## Tension

**Shepard tone.** It seems to rise forever, which is ideal under a build:

```json
{"name": "rise", "shepard": {"period": 8, "layers": 4, "low": -2, "span": 4}, "gain": 0.15}
```

**One-shot riser.** A latex voice that climbs across one section. In this example it climbs 2 octaves over 16 beats, from beat 48:

```json
{"name": "riser", "latex": "-1+\\frac{\\operatorname{mod}\\left(x,16\\right)}{8}", "in": "worm",
 "dynamics": [[48, 0], [62, 1], [64, 0]], "gain": 0.12}
```

**Braam / impact.** Use a loud low brass chord with a fast attack and long release, played once at a section start. A detune makes it rougher:

```json
{"name": "braam", "notes": [[32, 4, ["D2", "A2", "D3"]]], "timbre": "brass", "detune": 12,
 "env": {"a": 0.02, "d": 1.5, "s": 0.5, "r": 1.5}, "gain": 0.35}
```
