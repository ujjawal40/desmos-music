from conftest import load_song, one_voice

from desmos_music.stats import song_stats


def test_stats_counts_and_ranges():
    st = song_stats(one_voice(seq="A3 A4", timbre="organ"))
    assert st["tones"] == 3
    v = st["voices"][0]
    assert v["semitones"] == (0, 12)
    assert round(v["hz"][0]) == 220 and round(v["hz"][1]) == 440 * 4


def test_stats_for_bundled_song():
    st = song_stats(load_song("event_horizon.json"))
    assert st["length_beats"] == 96 and round(st["seconds"]) == 80
    assert st["tones"] == 23
    assert next(v for v in st["voices"] if v["name"] == "drone")["semitones"] == (-12, -12)
