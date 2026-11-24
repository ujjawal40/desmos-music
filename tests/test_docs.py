"""Every voice snippet in the docs must build."""
import json
import re

import pytest
from conftest import ROOT

from desmos_music.build import build_state

BLOCKS = re.findall(r"```json\n(.*?)```", (ROOT / "docs" / "COOKBOOK.md").read_text(), re.S)
VOICES = [json.loads(b) for b in BLOCKS if b.lstrip().startswith("{")]


@pytest.mark.parametrize("voice", VOICES, ids=[v["name"] for v in VOICES])
def test_cookbook_voice_builds(voice):
    song = {"title": "t", "base": "A3", "key": "D3 phrygian",
            "sections": [["worm", 48, 64]], "voices": [voice]}
    build_state(song)


def test_cookbook_has_snippets():
    assert len(VOICES) >= 10
