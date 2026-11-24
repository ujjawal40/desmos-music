"""CLI.

  python -m desmos_music [songs...] [-o build]   build songs (default: songs/*.json)
  python -m desmos_music new NAME                scaffold songs/NAME.json
  python -m desmos_music serve [--port 8000]     build all, then serve the local player
  python -m desmos_music stats [songs...]        duration, tone count, ranges, warnings
"""

import argparse
import functools
import http.server
import json
import sys
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


def build_all(songs, out: Path) -> int:
    built = []
    for s in songs:
        try:
            for path in build_file(s, out):
                print(f"wrote {path}")
        except SongError as e:
            print(f"{s}: {e}", file=sys.stderr)
            return 1
        built.append({"name": Path(s).stem, "title": load_song(s)["title"]})
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
    args = p.parse_args(argv)
    path = Path("songs") / f"{args.name}.json"
    if path.exists():
        print(f"{path} already exists", file=sys.stderr)
        return 1
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps({**TEMPLATE, "title": args.name}, indent=2) + "\n")
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
        print(f"  {st['length_beats'] or '-'} beats, {secs}, B = {st['base_hz']:.1f} Hz, "
              f"{st['tones']} tones, {st['expressions']} expressions")
        for v in st["voices"]:
            hz = f"{v['hz'][0]:.0f}–{v['hz'][1]:.0f} Hz" if v["hz"] else "(latex)"
            print(f"  {v['name']:<10} {v['kind']:<8} gain {v['gain']:<5g} {hz}")
        for w in warns:
            print(f"  ! {w}")
        total_warns += len(warns)
    return 1 if args.strict and total_warns else 0


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "new":
        return cmd_new(argv[1:])
    if argv and argv[0] == "serve":
        return cmd_serve(argv[1:])
    if argv and argv[0] == "stats":
        return cmd_stats(argv[1:])
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
