import argparse
import sys
from pathlib import Path

from .build import SongError, build_file


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="desmos_music", description="Build Desmos music graphs from song files.")
    p.add_argument("songs", nargs="*", type=Path, help="song JSON files (default: songs/*.json)")
    p.add_argument("-o", "--out", type=Path, default=Path("build"), help="output folder")
    args = p.parse_args(argv)

    songs = args.songs or sorted(Path("songs").glob("*.json"))
    if not songs:
        print("no songs found", file=sys.stderr)
        return 1
    for s in songs:
        try:
            for out in build_file(s, args.out):
                print(f"wrote {out}")
        except SongError as e:
            print(f"{s}: {e}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
