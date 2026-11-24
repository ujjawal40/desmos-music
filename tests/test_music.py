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
