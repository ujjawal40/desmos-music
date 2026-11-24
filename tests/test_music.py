import pytest

from desmos_music.music import SongError, note_hz, parse_hits, parse_seq, semitones

def test_note_names():
    assert note_hz("A4") == pytest.approx(440)
    assert note_hz("C4") == pytest.approx(261.6256, rel=1e-6)
    assert note_hz("Bb3") == pytest.approx(note_hz("A#3"))
    assert semitones("A3", 220) == 0
    assert semitones("E4", 220) == 7
    assert semitones(-5, 220) == -5
    with pytest.raises(SongError):
        note_hz("H2")


def test_seq_holds_rests_chords_durations():
    notes, length = parse_seq("A3 - . C4+E4:2 | 7", 0.5, 220)
    assert length == 4
    assert [(n.start, n.dur, n.pitches) for n in notes] == [
        (0, 1.0, [0]), (1.5, 2.0, [3, 7]), (3.5, 0.5, [7]),
    ]
    with pytest.raises(SongError):
        parse_seq("- A3", 1, 220)


def test_hits():
    hits, length = parse_hits("X.x. |..x.", 0.25)
    assert length == 2
    assert [(h.start, h.amp) for h in hits] == [(0, 1), (0.5, 0.6), (1.5, 0.6)]



def test_parse_key():
    from desmos_music.music import parse_key
    k = parse_key("D3 phrygian")
    assert k.tonic_hz == pytest.approx(note_hz("D3"))
    assert k.steps[1] == 1
    assert parse_key("C4").steps == [0, 2, 4, 5, 7, 9, 11]
    with pytest.raises(SongError, match="unknown scale"):
        parse_key("C4 blorp")


def test_scale_degrees():
    from desmos_music.music import parse_key
    k = parse_key("D3 phrygian")
    base = note_hz("D3")
    assert [semitones(d, base, k) for d in ["^1", "^2", "^3", "^5", "^8"]] == [0, 1, 3, 7, 12]
    assert semitones("^#4", base, k) == 6
    assert semitones("^5'", base, k) == 19
    assert semitones("^1,", base, k) == -12
    with pytest.raises(SongError, match="needs a 'key'"):
        semitones("^1", base)


def test_seq_with_degrees():
    from desmos_music.music import parse_key
    notes, _ = parse_seq("^1 ^2+^4", 1, note_hz("A3"), parse_key("A3 minor"))
    assert [n.pitches for n in notes] == [[0], [2, 5]]


def test_swing_delays_offbeats():
    hits, length = parse_hits("xxxx", 0.5, swing=0.75)
    assert [h.start for h in hits] == [0, 0.75, 1.0, 1.75]
    assert length == 2
    with pytest.raises(SongError):
        parse_hits("x", 1, swing=0.2)


def test_ghost_notes():
    notes, _ = parse_seq("A3 C4? E4", 1, 220)
    assert [n.amp for n in notes] == [1, 0.5, 1]
