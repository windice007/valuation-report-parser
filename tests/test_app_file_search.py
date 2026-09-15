from vrp.base.utils import search_app_file


def test_app_file_search_accepts_absolute_path(tmp_path):
    file = tmp_path / "settings.ini"
    file.write_text("", encoding="utf-8")
    assert search_app_file(str(file), str(tmp_path / "unused")) == str(file)
