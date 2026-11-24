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


def test_lint_frequency_range():
    from desmos_music.stats import lint
    assert lint(one_voice(seq="A3")) == []
    assert "20–20000" in lint(one_voice(seq="A3", transpose=-60))[0]


def test_lint_too_many_tones():
    from desmos_music.stats import lint
    many = one_voice(seq="[A3m9]+[C5m9]", timbre="full_organ")
    assert any("tone() expressions" in w for w in lint(many))


def test_lint_total_gain():
    from desmos_music.stats import lint
    s = one_voice(seq="A3", gain=1)
    s["voices"].append({"name": "b", "seq": "A3", "gain": 1})
    assert any("clip" in w for w in lint(s))
    s["voices"][1]["muted"] = True
    assert not any("clip" in w for w in lint(s))


def test_lint_phrase_alignment():
    from desmos_music.stats import lint
    s = one_voice(seq="A3:4 C4:4 E4:4", **{"in": "b"})  # 12-beat phrase
    s["sections"] = [["a", 0, 16], ["b", 16, 32]]
    assert any("4 beats into its 12-beat phrase" in w for w in lint(s))
    s["voices"][0]["offset"] = 16
    assert lint(s) == []


def test_lint_gain_is_per_section():
    from desmos_music.stats import lint
    s = one_voice(seq="A3", gain=1, **{"in": "a"})
    s["voices"].append({"name": "b", "seq": "A3", "gain": 1, "in": "b"})
    s["sections"] = [["a", 0, 4], ["b", 4, 8]]
    assert lint(s) == []
    s["voices"][1]["in"] = ["a", "b"]
    assert any("section 'a'" in w for w in lint(s))


def test_lint_phrase_alignment_ignores_continuous_play():
    from desmos_music.stats import lint
    s = one_voice(seq="A3:4 C4:4 E4:4", offset=0, **{"in": ["a", "b"]})
    s["sections"] = [["a", 0, 16], ["b", 16, 32]]
    assert lint(s) == []


# dune_one is a transcription of the clip's mix, so its gains stay as they were.
LINT_EXEMPT = {"dune_one.json"}


def test_bundled_songs_are_lint_clean():
    from conftest import ROOT

    from desmos_music.stats import lint
    for path in sorted((ROOT / "songs").glob("*.json")):
        if path.name not in LINT_EXEMPT:
            assert lint(load_song(path.name)) == [], path.name
