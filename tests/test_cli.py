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


def test_build_writes_manifest_and_console_script(in_tmp):
    main(["new", "one"])
    main(["new", "two"])
    assert main([]) == 0
    index = json.loads((in_tmp / "build" / "index.json").read_text())
    assert [e["name"] for e in index] == ["one", "two"]
    js = (in_tmp / "build" / "one.console.js").read_text()
    assert js.splitlines()[1].startswith("Calc.setState(")


def test_bad_song_exits_nonzero(in_tmp, capsys):
    (in_tmp / "songs").mkdir()
    (in_tmp / "songs" / "bad.json").write_text('{"title": "x", "voices": [{"name": "a"}]}')
    assert main([]) == 1
    assert "needs exactly one of" in capsys.readouterr().err


def test_no_songs_is_an_error(in_tmp):
    assert main([]) == 1


def test_invalid_json_reports_line(in_tmp, capsys):
    (in_tmp / "songs").mkdir()
    (in_tmp / "songs" / "bad.json").write_text('{"title": "x",\n "voices": [,]}')
    assert main([]) == 1
    assert "line 2" in capsys.readouterr().err
