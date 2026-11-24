import json

import pytest
from conftest import ROOT, latexes
from conftest import load_song as load
from conftest import one_voice as song

from desmos_music.build import SongError, build_state, notes_to_latex


def test_dune_builds():
    state = build_state(load("dune_one.json"))
    latex = [e.get("latex", "") for e in state["expressions"]["list"]]
    assert any(l.startswith("v_{kick}") for l in latex)
    assert sum("\\operatorname{tone}" in l for l in latex) == 6
    assert state["expressions"]["ticker"]["handlerLatex"].startswith("t\\to")


def test_ids_unique():
    state = build_state(load("dune_one.json"))
    ids = [e["id"] for e in state["expressions"]["list"]]
    assert len(ids) == len(set(ids))


def test_notes_latex():
    out = notes_to_latex([[0, 1, 0], [1, 1, 7]], loop=2)
    assert "\\frac{7}{12}" in out and "\\operatorname{mod}" in out


def test_rejects_duplicate_voice():
    with pytest.raises(SongError):
        build_state({"title": "x", "voices": [{"name": "a", "latex": "0"}, {"name": "a", "latex": "1"}]})


def test_rejects_bad_helper():
    with pytest.raises(SongError):
        build_state({"title": "x", "helpers": {"t": "0"}, "voices": [{"name": "a", "latex": "0"}]})


# --- generator features --------------------------------------------------------

def test_chord_splits_into_voices_and_shares_gain():
    ls = latexes(build_state(song(seq="A3+C4+E4:4")))
    assert any(l.startswith("v_{a1}") for l in ls) and any(l.startswith("v_{a3}") for l in ls)
    tones = [l for l in ls if "tone" in l]
    assert len(tones) == 3 and all("0.3333\\cdot g_{a}m_{a}" in l for l in tones)


def test_timbre_adds_partials():
    tones = [l for l in latexes(build_state(song(latex="0", timbre="organ"))) if "tone" in l]
    assert len(tones) == 3 and any("\\cdot4," in l for l in tones)


def test_envelope_and_dynamics_in_gain():
    ls = latexes(build_state(song(seq="A3 C4", env="pluck", dynamics=[[0, 0], [4, 1]])))
    assert any(l.startswith("a_{a}") and "\\min" in l for l in ls)
    assert any(l.startswith("d_{a}") for l in ls)
    tone = next(l for l in ls if "tone" in l)
    assert "a_{a}\\left(t\\right)" in tone and "d_{a}\\left(t\\right)" in tone


def test_sections_gate_voice_and_loop_ticker():
    s = song(seq="A3", **{"in": "b"})
    s["sections"] = [["a", 0, 8], ["b", 8, 16]]
    state = build_state(s)
    ls = latexes(state)
    assert any(l.startswith("p_{a}") for l in ls)
    assert any(l.startswith("v_{a}") and "8\\le x<16" in l for l in ls)
    assert "mod" in state["expressions"]["ticker"]["handlerLatex"]
    with pytest.raises(SongError):
        build_state({**s, "voices": [{"name": "a", "seq": "A3", "in": "nope"}]})


def test_drum_hits_do_not_overlap():
    ls = latexes(build_state(song(hits="Xx", step=0.25, drum="taiko")))
    v = next(l for l in ls if l.startswith("v_{a}"))
    assert "0\\le \\operatorname{mod}\\left(x,0.5\\right)<0.25" in v


def test_glide_and_offset():
    ls = latexes(build_state(song(seq="A3 E4", glide=0.2, offset=4)))
    v = next(l for l in ls if l.startswith("v_{a}"))
    assert "\\min" in v and "x-4" in v


def test_no_backslash_command_mashups():
    import re
    for f in sorted((ROOT / "songs").glob("*.json")):
        for l in latexes(build_state(json.loads(f.read_text()))):
            assert not re.search(r"\\cdot[a-zA-Z]", l), l


@pytest.mark.parametrize("name", [p.name for p in sorted((ROOT / "songs").glob("*.json"))])
def test_every_song_builds(name):
    state = build_state(load(name))
    ids = [e["id"] for e in state["expressions"]["list"]]
    assert len(ids) == len(set(ids))


def test_section_missing_end_is_a_song_error():
    s = song(seq="A3")
    s["sections"] = [{"name": "a", "start": 0}]
    with pytest.raises(SongError, match="needs 'start' and 'end'"):
        build_state(s)


def test_voices_must_be_a_list_of_objects():
    with pytest.raises(SongError, match="list"):
        build_state({"title": "x", "voices": {"a": 1}})
    with pytest.raises(SongError, match="object"):
        build_state({"title": "x", "voices": ["A3"]})


def test_unknown_voice_key_suggests_fix():
    with pytest.raises(SongError, match="did you mean 'timbre'"):
        build_state(song(latex="0", timber="organ"))


def test_unknown_song_key_suggests_fix():
    s = song(latex="0")
    s["bmp"] = 90
    with pytest.raises(SongError, match="did you mean 'bpm'"):
        build_state(s)


def test_song_key_enables_degrees_and_voice_key_overrides():
    s = song(seq="^1 ^3")
    s["key"] = "A3 minor"
    v = next(l for l in latexes(build_state(s)) if l.startswith("v_{a}"))
    assert "\\frac{3}{12}" in v
    s["voices"][0]["key"] = "A3 major"
    v = next(l for l in latexes(build_state(s)) if l.startswith("v_{a}"))
    assert "\\frac{4}{12}" in v


def test_transpose_shifts_any_voice_kind():
    for kind in ({"latex": "0"}, {"seq": "A3"}, {"hits": "x"}):
        v = next(l for l in latexes(build_state(song(transpose=-12, **kind))) if l.startswith("v_{a}"))
        assert v.endswith("+\\frac{-12}{12}")


def test_ghost_notes_get_an_amplitude_curve_even_without_env():
    a = next(l for l in latexes(build_state(song(seq="A3 C4?"))) if l.startswith("a_{a}"))
    assert "1\\le x<2:0.5" in a.replace("\\operatorname{mod}\\left(x,2\\right)", "x")


def test_arp_voice_is_monophonic():
    ls = latexes(build_state(song(seq="[A3m]:4 [F3]:4", arp="updown", arp_step=0.5)))
    assert any(l.startswith("v_{a}") for l in ls)
    assert not any(l.startswith("v_{a1}") for l in ls)


def test_shepard_tone_layers():
    ls = latexes(build_state(song(shepard={"layers": 3, "period": 6})))
    layers = [l for l in ls if l.startswith("v_{a")]
    assert len(layers) == 3 and "\\frac{x}{6}+0.333333" in layers[1]
    assert sum(l.startswith("a_{a") and "\\sin" in l for l in ls) == 3
    with pytest.raises(SongError, match="direction"):
        build_state(song(shepard={"direction": "sideways"}))


def test_playhead_has_stable_id():
    state = build_state(song(seq="A3"))
    t = next(e for e in state["expressions"]["list"] if e.get("latex") == "t=0")
    assert t["id"] == "playhead"


@pytest.mark.parametrize("bad", [{"vibrato": [3]}, {"vibrato": "fast"}, {"dynamics": [[0]]}, {"dynamics": 5}])
def test_malformed_options_are_song_errors(bad):
    with pytest.raises(SongError):
        build_state(song(seq="A3", **bad))
