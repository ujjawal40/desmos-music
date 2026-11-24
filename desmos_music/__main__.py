"""CLI.

  python -m desmos_music [songs...] [-o build]   build songs (default: songs/*.json)
  python -m desmos_music new NAME [--style S]    scaffold songs/NAME.json (basic, dune, interstellar)
  python -m desmos_music serve [--port 8000]     build all, then serve the local player
  python -m desmos_music stats [songs...]        duration, tone count, ranges, warnings
  python -m desmos_music import-midi FILE.mid    convert a MIDI file into songs/<name>.json
  python -m desmos_music watch                   rebuild songs whenever they change
"""

import argparse
import functools
import http.server
import json
import sys
import time
from pathlib import Path

from .build import SongError, build_file, load_song

TEMPLATE = {
    "title": "Untitled",
    "description": "",
    "base": "A3",
    "bpm": 72,
    "window": 8,
    "sections": [{"name": "intro", "start": 0, "end": 16}, {"name": "main", "start": 16, "end": 48}],
    "voices": [
        {"name": "drone", "latex": "-1", "timbre": "organ", "gain": 0.3,
         "dynamics": [[0, 0], [8, 1]], "color": "#c47f1a"},
        {"name": "arp", "seq": "A3 E4 A4 C5 B4 C5 A4 E4", "step": 0.5, "in": "main",
         "env": "pluck", "timbre": "organ", "gain": 0.4, "color": "#f5a623"},
        {"name": "kick", "hits": "X... x... X... x.x.", "step": 0.25, "in": "main", "gain": 0.8,
         "color": "#ffd27a"},
    ],
}


def manifest_entry(path) -> dict:
    """What the player needs to know about a song without parsing its state."""
    from .build import _sections

    song = load_song(path)
    sections = _sections(song)
    length = song.get("length") or (max(e for _, e in sections.values()) if sections else None)
    return {
        "name": Path(path).stem,
        "title": song["title"],
        "length": length,
        "sections": [{"name": n, "start": a, "end": b} for n, (a, b) in sections.items()],
    }


STYLES = {
    "basic": TEMPLATE,
    "interstellar": {
        "title": "Untitled", "description": "Space-organ starter: clock, pedal, arpeggio, pads.",
        "base": "A3", "key": "A3 minor", "bpm": 70, "window": 8,
        "sections": [{"name": "intro", "start": 0, "end": 16}, {"name": "build", "start": 16, "end": 48}],
        "voices": [
            {"name": "tick", "hits": "X . x . x . x .", "step": 0.5, "drum": "tick", "gain": 0.1},
            {"name": "pedal", "latex": "-1", "timbre": "organ", "detune": 6,
             "dynamics": [[0, 0], [12, 1]], "gain": 0.22, "color": "#5b7fa6"},
            {"name": "arp", "seq": "[A3m]:4 [F3]:4 [C3]:4 [E3]:4", "arp": "pulse", "arp_step": 0.5,
             "in": "build", "env": "organ", "timbre": "organ", "gain": 0.26, "color": "#9cc3e6"},
            {"name": "pad", "seq": "[A3m]:4 [F3]:4 [C3]:4 [E3]:4", "in": "build", "env": "pad",
             "timbre": "organ", "dynamics": [[16, 0], [32, 1]], "gain": 0.25, "color": "#3e5f86"},
        ],
    },
    "dune": {
        "title": "Untitled", "description": "Desert starter: drone, chant, war drums.",
        "base": "D4", "key": "D3 phrygian", "bpm": 64, "window": 8,
        "sections": [{"name": "intro", "start": 0, "end": 16}, {"name": "drums", "start": 16, "end": 48}],
        "voices": [
            {"name": "drone", "latex": "-2", "timbre": "reed", "detune": 9,
             "dynamics": [[0, 0], [8, 1]], "gain": 0.25, "color": "#8a5a1c"},
            {"name": "chant", "seq": "^1:3 ^b2 | ^1:2 ^7,:2 | ^1:4 | ^3:2 ^b2 ^1", "env": "voice",
             "timbre": "brass", "glide": 0.25, "vibrato": [1.5, 0.2], "gain": 0.24, "color": "#c47f1a"},
            {"name": "taiko", "hits": "X . . x X . x .", "step": 0.5, "drum": "taiko", "in": "drums",
             "gain": 0.55, "color": "#f5a623"},
        ],
    },
}


def build_all(songs, out: Path) -> int:
    built = []
    for s in songs:
        try:
            for path in build_file(s, out):
                print(f"wrote {path}")
        except SongError as e:
            print(f"{s}: {e}", file=sys.stderr)
            return 1
        built.append(manifest_entry(s))
    index = out / "index.json"
    known = {}
    if index.exists():
        known = {e["name"]: e for e in json.loads(index.read_text())}
    known.update({e["name"]: e for e in built})
    index.write_text(json.dumps(sorted(known.values(), key=lambda e: e["name"]), indent=2, ensure_ascii=False))
    return 0


def cmd_new(argv) -> int:
    p = argparse.ArgumentParser(prog="desmos_music new")
    p.add_argument("name")
    p.add_argument("--style", choices=sorted(STYLES), default="basic")
    args = p.parse_args(argv)
    path = Path("songs") / f"{args.name}.json"
    if path.exists():
        print(f"{path} already exists", file=sys.stderr)
        return 1
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps({**STYLES[args.style], "title": args.name}, indent=2) + "\n")
    print(f"created {path} — edit it, then: python -m desmos_music serve")
    return 0


def cmd_serve(argv) -> int:
    p = argparse.ArgumentParser(prog="desmos_music serve")
    p.add_argument("--port", type=int, default=8000)
    args = p.parse_args(argv)
    if build_all(sorted(Path("songs").glob("*.json")), Path("build")):
        return 1
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=".")
    with http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler) as srv:
        print(f"player: http://localhost:{args.port}/web/   (Ctrl+C to stop)")
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass
    return 0


def cmd_stats(argv) -> int:
    from .stats import lint, song_stats

    p = argparse.ArgumentParser(prog="desmos_music stats")
    p.add_argument("songs", nargs="*", type=Path)
    p.add_argument("--strict", action="store_true", help="exit 1 if there are warnings")
    args = p.parse_args(argv)
    total_warns = 0
    for path in args.songs or sorted(Path("songs").glob("*.json")):
        try:
            song = load_song(path)
            st, warns = song_stats(song), lint(song)
        except SongError as e:
            print(f"{path}: {e}", file=sys.stderr)
            return 1
        secs = f"{st['seconds']:.0f}s" if st["seconds"] else "open-ended"
        print(f"\n{st['title']}  ({path})")
        beats = f"{st['length_beats']:g}" if st["length_beats"] else "-"
        print(f"  {beats} beats, {secs}, B = {st['base_hz']:.1f} Hz, "
              f"{st['tones']} tones, {st['expressions']} expressions")
        for v in st["voices"]:
            hz = f"{v['hz'][0]:.0f}–{v['hz'][1]:.0f} Hz" if v["hz"] else "(latex)"
            print(f"  {v['name']:<10} {v['kind']:<8} gain {v['gain']:<5g} {hz}")
        for w in warns:
            print(f"  ! {w}")
        total_warns += len(warns)
    return 1 if args.strict and total_warns else 0


def cmd_import_midi(argv) -> int:
    from .midi import midi_to_song

    p = argparse.ArgumentParser(prog="desmos_music import-midi")
    p.add_argument("file", type=Path)
    p.add_argument("--name", help="song name (default: the MIDI file's name)")
    p.add_argument("--grid", type=float, default=0.25, help="quantize grid in beats, 0 = off")
    p.add_argument("--max-lanes", type=int, default=4, help="max simultaneous notes per track")
    p.add_argument("--force", action="store_true", help="overwrite an existing song")
    args = p.parse_args(argv)
    name = args.name or "".join(c if c.isalnum() else "_" for c in args.file.stem).lower()
    out = Path("songs") / f"{name}.json"
    if out.exists() and not args.force:
        print(f"{out} already exists (use --force)", file=sys.stderr)
        return 1
    try:
        song = midi_to_song(args.file.read_bytes(), name, args.grid, args.max_lanes)
    except (OSError, SongError) as e:
        print(f"{args.file}: {e}", file=sys.stderr)
        return 1
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(song, indent=2) + "\n")
    print(f"wrote {out} ({len(song['voices'])} voices, {song['length']:g} beats at {song['bpm']:g} bpm)")
    return 0


def rebuild_changed(seen: dict, out: Path = Path("build")) -> list[Path]:
    """Build every song whose mtime changed since `seen` (updated in place)."""
    changed = []
    for path in sorted(Path("songs").glob("*.json")):
        mtime = path.stat().st_mtime_ns
        if seen.get(path) != mtime:
            seen[path] = mtime
            changed.append(path)
            build_all([path], out)
    return changed


def cmd_watch(argv) -> int:
    p = argparse.ArgumentParser(prog="desmos_music watch")
    p.add_argument("--interval", type=float, default=0.5)
    args = p.parse_args(argv)
    seen: dict = {}
    rebuild_changed(seen)
    print("watching songs/ — Ctrl+C to stop")
    try:
        while True:
            time.sleep(args.interval)
            rebuild_changed(seen)
    except KeyboardInterrupt:
        return 0


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "new":
        return cmd_new(argv[1:])
    if argv and argv[0] == "serve":
        return cmd_serve(argv[1:])
    if argv and argv[0] == "stats":
        return cmd_stats(argv[1:])
    if argv and argv[0] == "import-midi":
        return cmd_import_midi(argv[1:])
    if argv and argv[0] == "watch":
        return cmd_watch(argv[1:])
    p = argparse.ArgumentParser(prog="desmos_music", description="Build Desmos music graphs from song files.")
    p.add_argument("songs", nargs="*", type=Path, help="song JSON files (default: songs/*.json)")
    p.add_argument("-o", "--out", type=Path, default=Path("build"), help="output folder")
    args = p.parse_args(argv)
    songs = args.songs or sorted(Path("songs").glob("*.json"))
    if not songs:
        print("no songs found", file=sys.stderr)
        return 1
    return build_all(songs, args.out)


if __name__ == "__main__":
    raise SystemExit(main())
