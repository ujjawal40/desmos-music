import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_song(name):
    return json.loads((ROOT / "songs" / name).read_text())


def one_voice(**voice):
    return {"title": "x", "base": "A3", "voices": [{"name": "a", **voice}]}


def latexes(state):
    return [e.get("latex", "") for e in state["expressions"]["list"]]


@pytest.fixture
def in_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path
