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
