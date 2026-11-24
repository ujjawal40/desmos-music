"""Minimal Standard MIDI File reader (format 0/1), no dependencies."""

from __future__ import annotations

import struct

from .music import SongError


def read_varlen(data: bytes, pos: int) -> tuple[int, int]:
    """MIDI variable-length quantity -> (value, new position)."""
    value = 0
    for _ in range(4):
        if pos >= len(data):
            raise SongError("truncated MIDI variable-length number")
        b = data[pos]
        pos += 1
        value = (value << 7) | (b & 0x7F)
        if not b & 0x80:
            return value, pos
    raise SongError("MIDI variable-length number longer than 4 bytes")


def read_chunks(data: bytes) -> tuple[dict, list[bytes]]:
    """Split a .mid file into its header fields and raw track chunks."""
    if data[:4] != b"MThd":
        raise SongError("not a MIDI file (missing MThd header)")
    (hlen,) = struct.unpack(">I", data[4:8])
    fmt, ntracks, division = struct.unpack(">HHH", data[8:14])
    if division & 0x8000:
        raise SongError("SMPTE-timed MIDI files are not supported")
    pos = 8 + hlen
    tracks = []
    while pos + 8 <= len(data):
        kind, (length,) = data[pos:pos + 4], struct.unpack(">I", data[pos + 4:pos + 8])
        body = data[pos + 8:pos + 8 + length]
        if kind == b"MTrk":
            tracks.append(body)
        pos += 8 + length
    if len(tracks) != ntracks:
        raise SongError(f"MIDI header says {ntracks} tracks, found {len(tracks)}")
    return {"format": fmt, "ticks_per_beat": division}, tracks
