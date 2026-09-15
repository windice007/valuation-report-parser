from vrp.config.locator import locate_config


def test_config_locator_prefers_work_directory(tmp_path, monkeypatch):
    work = tmp_path / "work"
    cwd = tmp_path / "cwd"
    work.mkdir()
    cwd.mkdir()
    (work / "config.json").write_text("work", encoding="utf-8")
    (cwd / "config.json").write_text("cwd", encoding="utf-8")
    monkeypatch.chdir(cwd)
    assert locate_config("config.json", str(work)) == str(work / "config.json")
