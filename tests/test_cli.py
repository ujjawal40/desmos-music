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


def test_stats_command(in_tmp, capsys):
    main(["new", "demo"])
    assert main(["stats"]) == 0
    out = capsys.readouterr().out
    assert "tones" in out and "drone" in out


def test_import_midi(in_tmp, capsys):
    from test_midi import note_track, smf
    (in_tmp / "My Tune.mid").write_bytes(smf(note_track("lead", [(0, 480, 69)])))
    assert main(["import-midi", "My Tune.mid"]) == 0
    assert (in_tmp / "songs" / "my_tune.json").exists()
    assert main(["import-midi", "My Tune.mid"]) == 1
    assert main(["import-midi", "My Tune.mid", "--force"]) == 0
    assert main([]) == 0
    (in_tmp / "junk.mid").write_bytes(b"nope")
    assert main(["import-midi", "junk.mid"]) == 1
