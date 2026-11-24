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


DATA_BYTES = {0x80: 2, 0x90: 2, 0xA0: 2, 0xB0: 2, 0xC0: 1, 0xD0: 1, 0xE0: 2}


def read_events(track: bytes) -> list[tuple]:
    """Track chunk -> [(abs_tick, kind, payload)], handling running status.

    kinds: 'on' (channel, note, velocity), 'off' (channel, note),
    'tempo' (microseconds per beat), 'name' (str). Everything else is skipped.
    """
    events = []
    pos, tick, status = 0, 0, None
    while pos < len(track):
        delta, pos = read_varlen(track, pos)
        tick += delta
        if pos >= len(track):
            raise SongError("truncated MIDI event")
        b = track[pos]
        if b == 0xFF:  # meta
            mtype = track[pos + 1]
            length, pos = read_varlen(track, pos + 2)
            payload = track[pos:pos + length]
            pos += length
            if mtype == 0x51 and length == 3:
                events.append((tick, "tempo", int.from_bytes(payload, "big")))
            elif mtype == 0x03:
                events.append((tick, "name", payload.decode("latin-1")))
            elif mtype == 0x2F:
                break
            continue
        if b in (0xF0, 0xF7):  # sysex
            length, pos = read_varlen(track, pos + 1)
            pos += length
            continue
        if b & 0x80:
            status = b
            pos += 1
        elif status is None:
            raise SongError("MIDI data byte without a status byte")
        kind, ch = status & 0xF0, status & 0x0F
        args = track[pos:pos + DATA_BYTES[kind]]
        pos += DATA_BYTES[kind]
        if kind == 0x90 and args[1] > 0:
            events.append((tick, "on", (ch, args[0], args[1])))
        elif kind == 0x80 or kind == 0x90:
            events.append((tick, "off", (ch, args[0])))
    return events
