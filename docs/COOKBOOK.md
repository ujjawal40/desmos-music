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
