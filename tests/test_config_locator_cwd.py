from vrp.config.locator import locate_config


def test_config_locator_falls_back_to_current_directory(tmp_path, monkeypatch):
    work = tmp_path / "work"
    work.mkdir()
    config = tmp_path / "config.json"
    config.write_text("{}", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert locate_config("config.json", str(work)) == str(config)
