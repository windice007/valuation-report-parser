from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import (
    Column, Date, DateTime, Integer, MetaData, Numeric, String, Table,
    event, select, text,
)
from sqlalchemy.exc import IntegrityError, DataError
from sqlalchemy.dialects.postgresql import UUID

from vrp.base import CaseDict, DATASOUCE, TABLE_NAME, ValuationReportData
from vrp.excel.sink import DbSink


def record(table="positions", **fields):
    return CaseDict({TABLE_NAME: table, **fields})


def report(details=(), products=()):
    result = ValuationReportData("synthetic")
    result.details = list(details)
    result.products = list(products)
    return result


def create_positions(sink):
    table = Table(
        "positions", MetaData(),
        Column("id", Integer, primary_key=True, autoincrement=False),
        Column("day", Date, primary_key=True),
        Column("required", String(20), nullable=False),
        Column("amount", Numeric(18, 4)),
        Column("note", String(20), server_default=text("'default'")),
        Column("updated", DateTime),
    )
    table.create(sink.engine)
    return table


def read_rows(sink, table):
    with sink.engine.connect() as con:
        return [dict(row) for row in con.execute(select(table).order_by(*table.primary_key.columns)).mappings()]


DAY = date(2026, 9, 11)


def test_postgresql_matches_legacy_for_mixed_partial_updates(pg_sink):
    table = create_positions(pg_sink)
    records = [
        record(id=1, day=DAY, required="first", amount=Decimal("1.2300")),
        record(id=2, day=DAY, required="second", amount=None),
        record(id=1, day=DAY, amount=Decimal("9.8700"), updated=datetime(2026, 9, 11, 12)),
        record(id=3, day=DAY, required="third", note=None),
        record(id=1, day=DAY, note="last"),
        record(id=2, day=DAY, note=None),
    ]
    pg_sink.save(report(records[:4], records[4:]))
    actual = read_rows(pg_sink, table)
    with pg_sink.engine.begin() as con:
        con.execute(table.delete())
        for row in records:
            pg_sink.update_or_insert_record(con, row)
    assert actual == read_rows(pg_sink, table)
    assert actual[0]["required"] == "first"
    assert actual[0]["amount"] == Decimal("9.8700")
    assert actual[1]["note"] is None


@pytest.mark.parametrize("batch_size", [1, 2, 500])
def test_duplicate_keys_keep_last_update(pg_sink, batch_size):
    table = create_positions(pg_sink)
    pg_sink.batch_size = batch_size
    pg_sink.save(report([
        record(id=key, day=DAY, required=f"value{i}")
        for i, key in enumerate([1, 2, 1, 3, 2, 1])
    ]))
    assert [(r["id"], r["required"]) for r in read_rows(pg_sink, table)] == [
        (1, "value5"), (2, "value4"), (3, "value3"),
    ]


def test_casing_metadata_and_null_values(pg_sink):
    table = create_positions(pg_sink)
    pg_sink.save(report([
        CaseDict({TABLE_NAME: "positions", "ID": 1, "DAY": DAY,
                  "REQUIRED": "ok", "AMOUNT": None, DATASOUCE: ["debug"]}),
        record(id=2, day=DAY, required="ok", amount=None),
    ]))
    rows = read_rows(pg_sink, table)
    assert len(rows) == 2
    assert all(r["amount"] is None and r["note"] == "default" for r in rows)


def test_coerced_primary_keys_keep_input_order(pg_sink):
    table = create_positions(pg_sink)
    pg_sink.save(report([
        record(id=1, day=DAY, required="first"),
        record(id="1", day=DAY, required="second"),
        record(id=1, day=DAY, required="last"),
    ]))
    assert read_rows(pg_sink, table)[0]["required"] == "last"


def test_primary_key_coercion_does_not_change_update_match(pg_sink):
    table = create_positions(pg_sink)
    pg_sink.save(report([record(id=1, day=DAY, required="before")]))
    # The old UPDATE matches no row for 1.2; the subsequent integer INSERT
    # conflicts with id=1. Casting before the UPDATE would incorrectly succeed.
    with pytest.raises(IntegrityError):
        pg_sink.save(report([record(id=Decimal("1.2"), day=DAY, required="after")]))
    assert read_rows(pg_sink, table)[0]["required"] == "before"


def test_uuid_string_forms_use_database_key_comparison(pg_sink):
    table = Table("uuid_keys", MetaData(), Column("id", UUID, primary_key=True),
                  Column("note", String))
    table.create(pg_sink.engine)
    pg_sink.save(report([
        record("uuid_keys", id="12345678-1234-5678-1234-567812345678", note="first"),
        record("uuid_keys", id="12345678123456781234567812345678", note="last"),
    ]))
    rows = read_rows(pg_sink, table)
    assert len(rows) == 1 and rows[0]["note"] == "last"


def test_source_alias_does_not_conflict_with_target(pg_sink):
    table = Table("vrp_source", MetaData(), Column("id", Integer, primary_key=True))
    table.create(pg_sink.engine)
    pg_sink.save(report([record("vrp_source", id=1), record("vrp_source", id=2)]))
    assert read_rows(pg_sink, table) == [{"id": 1}, {"id": 2}]


def test_details_finish_before_products_on_same_table(pg_sink):
    create_positions(pg_sink)
    statements = []

    def count(con, cursor, statement, parameters, context, executemany):
        if context.isinsert or context.isupdate:
            statements.append(statement.split()[0])

    event.listen(pg_sink.engine, "before_cursor_execute", count)
    pg_sink.save(report(
        [record(id=1, day=DAY, required="detail")],
        [record(id=2, day=DAY, required="product")],
    ))
    assert statements == ["UPDATE", "INSERT", "UPDATE", "INSERT"]


def test_non_primary_unique_constraint_failure_rolls_back(pg_sink):
    table = Table("unique_values", MetaData(), Column("id", Integer, primary_key=True),
                  Column("code", String, unique=True))
    table.create(pg_sink.engine)
    with pytest.raises(IntegrityError):
        pg_sink.save(report([
            record("unique_values", id=1, code="duplicate"),
            record("unique_values", id=2, code="duplicate"),
        ]))
    assert read_rows(pg_sink, table) == []


def test_only_primary_key_and_no_primary_key(pg_sink):
    metadata = MetaData()
    keys = Table("keys_only", metadata, Column("id", Integer, primary_key=True))
    logs = Table("logs", metadata, Column("value", Integer, server_default=text("7")))
    metadata.create_all(pg_sink.engine)
    pg_sink.save(report([
        record("keys_only", id=1), record("keys_only", id=2), record("keys_only", id=1),
        record("logs", value=3), record("logs", value=3), record("logs"), record("logs"),
    ]))
    assert read_rows(pg_sink, keys) == [{"id": 1}, {"id": 2}]
    with pg_sink.engine.connect() as con:
        assert sorted(con.execute(select(logs.c.value)).scalars()) == [3, 3, 7, 7]


@pytest.mark.parametrize("failure", ["later_batch", "product", "missing_key", "too_long"])
def test_failure_rolls_back_entire_file(pg_sink, failure):
    table = create_positions(pg_sink)
    pg_sink.save(report([record(id=0, day=DAY, required="before")]))
    details = [record(id=i, day=DAY, required="after") for i in range(3)]
    products = []
    error = IntegrityError
    if failure == "later_batch":
        details.append(record(id=3, day=DAY, required=None))
    elif failure == "product":
        products.append(record(id=4, day=DAY, required=None))
    elif failure == "missing_key":
        details.append(record(day=DAY, required="missing"))
        error = KeyError
    else:
        details.append(record(id=3, day=DAY, required="x" * 21))
        error = DataError
    with pytest.raises(error):
        pg_sink.save(report(details, products))
    rows = read_rows(pg_sink, table)
    assert len(rows) == 1 and rows[0]["required"] == "before"


def test_ten_thousand_rows_use_forty_dml_statements(pg_sink):
    table = create_positions(pg_sink)
    pg_sink.batch_size = 500
    counts = []

    def count(con, cursor, statement, parameters, context, executemany):
        if context.isinsert or context.isupdate:
            counts.append(statement.split()[0])

    event.listen(pg_sink.engine, "before_cursor_execute", count)
    data = report([record(id=i, day=DAY, required="ok") for i in range(10000)])
    pg_sink.save(data)
    assert counts.count("UPDATE") == 20
    assert counts.count("INSERT") == 20
    counts.clear()
    pg_sink.save(data)
    assert len(counts) == 40
    assert len(read_rows(pg_sink, table)) == 10000


def test_batch_bind_parameter_limit_and_shape_boundaries():
    sink = DbSink("sqlite:///:memory:", batch_size=10000)
    Table("wide", sink.meta_data, Column("id", Integer, primary_key=True),
          *(Column(f"c{i}", Integer) for i in range(60)))
    full = {f"c{i}": i for i in range(60)}
    rows = [record("wide", id=i, **full) for i in range(1000)]
    rows.extend([record("wide", id=1001), record("wide", id=1002, **full)])
    batches = list(sink._postgresql_batches(rows))
    assert [len(batch) for _, batch in batches] == [491, 491, 18, 1, 1]
    assert all(len(batch) * len(batch[0]) <= 30000 for _, batch in batches)


def test_non_postgresql_fallback_and_empty_input():
    sink = DbSink("sqlite:///:memory:")
    table = create_positions(sink)
    sink.save(report())
    sink.save(report([record(id=1, day=DAY, required="first")]))
    sink.save(report([], [record(id=1, day=DAY, required="last")]))
    assert read_rows(sink, table)[0]["required"] == "last"


@pytest.mark.parametrize("batch_size", [0, -1, 1.5, True, "500"])
def test_invalid_batch_size(batch_size):
    with pytest.raises(ValueError, match="batch_size"):
        DbSink("sqlite:///:memory:", batch_size=batch_size)
