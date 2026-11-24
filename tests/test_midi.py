import struct

import pytest

from desmos_music.midi import read_chunks, read_varlen
from desmos_music.music import SongError


def varlen(n):
    out = [n & 0x7F]
    n >>= 7
    while n:
        out.insert(0, (n & 0x7F) | 0x80)
        n >>= 7
    return bytes(out)


def smf(*tracks, tpb=480, fmt=1):
    head = b"MThd" + struct.pack(">IHHH", 6, fmt, len(tracks), tpb)
    return head + b"".join(b"MTrk" + struct.pack(">I", len(t)) + t for t in tracks)


def test_varlen_roundtrip():
    for n in (0, 0x7F, 0x80, 480, 0x0FFFFFFF):
        assert read_varlen(varlen(n), 0) == (n, len(varlen(n)))


def test_read_chunks():
    header, tracks = read_chunks(smf(b"\x00\xff\x2f\x00", b"", tpb=96))
    assert header == {"format": 1, "ticks_per_beat": 96}
    assert tracks == [b"\x00\xff\x2f\x00", b""]
    with pytest.raises(SongError):
        read_chunks(b"RIFF....")


def test_read_events_running_status_and_meta():
    from desmos_music.midi import read_events
    track = (
        b"\x00\xff\x03\x04Lead"            # track name
        + b"\x00\xff\x51\x03\x07\xa1\x20"  # tempo 500000 (120 bpm)
        + b"\x00\x90\x45\x64"              # A4 on
        + varlen(480) + b"\x45\x00"        # running status: A4 vel 0 = off
        + b"\x00\x48\x50"                  # C5 on (still running status)
        + varlen(240) + b"\x80\x48\x40"    # explicit off
        + b"\x00\xf0\x02\x01\xf7"          # sysex, skipped
        + b"\x00\xff\x2f\x00"
    )
    assert read_events(track) == [
        (0, "name", "Lead"), (0, "tempo", 500000), (0, "on", (0, 69, 100)),
        (480, "off", (0, 69)), (480, "on", (0, 72, 80)), (720, "off", (0, 72)),
    ]


def test_pair_notes():
    from desmos_music.midi import pair_notes
    events = [
        (0, "on", (0, 60, 100)), (0, "on", (0, 64, 90)),
        (240, "off", (0, 60)), (480, "off", (0, 64)),
        (480, "on", (1, 67, 70)), (960, "tempo", 500000),
    ]
    assert pair_notes(events, 480) == [(0, 0.5, 60, 100), (0, 1.0, 64, 90), (1.0, 1.0, 67, 70)]
