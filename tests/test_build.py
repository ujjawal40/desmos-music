import json
from pathlib import Path

import pytest

from desmos_music.build import SongError, build_state, notes_to_latex

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    return json.loads((ROOT / "songs" / name).read_text())


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
