import json

from desmos_music.__main__ import main


def test_new_scaffolds_a_buildable_song(in_tmp):
    assert main(["new", "demo"]) == 0
    song = json.loads((in_tmp / "songs" / "demo.json").read_text())
    assert song["title"] == "demo"
    assert main([]) == 0
    assert (in_tmp / "build" / "demo.json").exists()


def test_new_refuses_to_overwrite(in_tmp):
    assert main(["new", "demo"]) == 0
    assert main(["new", "demo"]) == 1
