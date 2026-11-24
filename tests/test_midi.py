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


def test_split_lanes_keeps_melody_on_top():
    from desmos_music.midi import split_lanes
    notes = [(0, 2, 48, 1), (0, 1, 72, 1), (1, 1, 74, 1), (2, 1, 50, 1)]
    lanes = split_lanes(notes)
    assert [[n[2] for n in lane] for lane in lanes] == [[72, 74, 50], [48]]


def test_quantize():
    from desmos_music.midi import quantize
    assert quantize([(0.98, 0.49, 60, 1), (2.01, 0.02, 62, 1)], 0.25) == [
        (1.0, 0.5, 60, 1), (2.0, 0.25, 62, 1),
    ]
    assert quantize([(0.98, 0.49, 60, 1)], 0) == [(0.98, 0.49, 60, 1)]


def note_track(name, notes, ch=0, tempo=None):
    """notes: [(start_tick, dur_tick, midi)] -> track bytes."""
    evs = []
    for s, d, n in notes:
        evs += [(s, bytes([0x90 | ch, n, 100])), (s + d, bytes([0x80 | ch, n, 0]))]
    evs.sort(key=lambda e: (e[0], e[1][0] & 0xF0 == 0x90))
    out = b"\x00\xff\x03" + varlen(len(name)) + name.encode()
    if tempo:
        out += b"\x00\xff\x51\x03" + tempo.to_bytes(3, "big")
    t = 0
    for tick, msg in evs:
        out += varlen(tick - t) + msg
        t = tick
    return out + b"\x00\xff\x2f\x00"


def test_midi_to_song_builds():
    from desmos_music.build import build_state
    from desmos_music.midi import midi_to_song
    data = smf(
        note_track("Lead Line", [(0, 480, 69), (480, 480, 72)], tempo=600000),
        note_track("Pad", [(0, 960, 57), (0, 960, 60), (0, 960, 64)], ch=1),
        note_track("Kit", [(0, 120, 36)], ch=9),
    )
    song = midi_to_song(data, "demo")
    assert song["bpm"] == 100
    assert [v["name"] for v in song["voices"]] == ["LeadLine", "Pad", "Pad2", "Pad3"]
    assert song["voices"][0]["notes"] == [[0, 1, "A4"], [1, 1, "C5"]]
    assert song["length"] == 4
    build_state(song)


def test_first_tempo_wins_and_default_is_120():
    from desmos_music.midi import midi_to_song
    two = smf(note_track("a", [(0, 480, 60)], tempo=500000), note_track("b", [(0, 480, 62)], tempo=1000000))
    assert midi_to_song(two, "x")["bpm"] == 120
    none = smf(note_track("a", [(0, 480, 60)]))
    assert midi_to_song(none, "x")["bpm"] == 120
    slow = smf(note_track("a", [(0, 480, 60)], tempo=1000000))
    assert midi_to_song(slow, "x")["bpm"] == 60
