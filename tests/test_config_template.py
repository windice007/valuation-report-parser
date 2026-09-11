import json
from types import SimpleNamespace

import pytest
from sqlalchemy import Column, MetaData, Numeric, String, Table

from vrp.entry import config_template
from vrp.excel.sink import DbSink


@pytest.mark.parametrize("position_tables, product_tables", [
    (None, "products"),
    ("positions", None),
    ("positions", "products"),
])
def test_template_table_options(tmp_path, monkeypatch, position_tables, product_tables):
    sink = DbSink("sqlite://")
    metadata = MetaData()
    for name in ("positions", "products"):
        Table(name, metadata,
              Column("code", String, primary_key=True),
              Column("amount", Numeric, nullable=False),
              Column("note", String))
    metadata.create_all(sink.engine)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(config_template, "check_db_settings", lambda args: sink)
    try:
        config_template.process(SimpleNamespace(
            position_tables=position_tables, product_tables=product_tables,
            connection_url=None,
        ))
    finally:
        sink.engine.dispose()

    config = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert config["subject_code_column"] == "A"
    expected_values = {"code": "", "amount": 0, "note": None}
    if product_tables:
        assert config["products"] == [{"table": "products", "values": expected_values}]
    else:
        assert "products" not in config
    if position_tables:
        assert config["positions"][0]["table"] == "positions"
        handler = config["positions"][0]["groups"][0]["handlers"][0]
        assert handler == {"subject_filter_regex": ".+", "values": expected_values}
    else:
        assert "positions" not in config
