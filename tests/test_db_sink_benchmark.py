"""Opt-in benchmark; uses only the disposable schema supplied by pg_sink."""
import json
import os
from statistics import median
from time import perf_counter

import pytest
from sqlalchemy import event, text

from test_db_sink import DAY, create_positions, read_rows, record, report


@pytest.mark.skipif(
    os.environ.get("VRP_RUN_BENCHMARK") != "1",
    reason="Set VRP_RUN_BENCHMARK=1 to run the PostgreSQL benchmark",
)
@pytest.mark.parametrize("workload", ["new", "existing", "mixed"])
def test_postgresql_benchmark(pg_sink, workload):
    table = create_positions(pg_sink)
    pg_sink.batch_size = 500
    pg_sink.get_table(table.name)  # Exclude initial reflection for both writers.
    data = report([
        record(id=i, day=DAY, required="after", amount=i, note=None)
        for i in range(10000)
    ])
    existing = {"new": 0, "existing": 10000, "mixed": 5000}[workload]
    seed = [{"id": i, "day": DAY, "required": "before"} for i in range(existing)]
    samples = {"legacy": [], "batch": []}
    sql_counts = {"legacy": [], "batch": []}
    count = 0

    def on_execute(con, cursor, statement, parameters, context, executemany):
        nonlocal count
        if context.isinsert or context.isupdate:
            count += 1

    event.listen(pg_sink.engine, "before_cursor_execute", on_execute)
    expected = None
    for _ in range(3):
        for mode in samples:
            with pg_sink.engine.begin() as con:
                con.execute(table.delete())
                if seed:
                    con.execute(table.insert(), seed)
            count = 0
            start = perf_counter()
            if mode == "legacy":
                with pg_sink.engine.begin() as con:
                    for row in data.details:
                        pg_sink.update_or_insert_record(con, row)
            else:
                pg_sink.save(data)
            samples[mode].append(perf_counter() - start)
            sql_counts[mode].append(count)
            rows = read_rows(pg_sink, table)
            if expected is None:
                expected = rows
            assert rows == expected
            assert len(rows) == 10000

    with pg_sink.engine.connect() as con:
        version = con.execute(text("SHOW server_version")).scalar()
    timings = {mode: round(median(runs), 4) for mode, runs in samples.items()}
    result = {
        "postgresql": version, "workload": workload, "rows": 10000,
        "median_seconds": timings, "dml_statements": sql_counts,
        "median_rows_per_second": {
            mode: round(10000 / median(runs)) for mode, runs in samples.items()
        },
        "speedup": round(median(samples["legacy"]) / median(samples["batch"]), 2),
    }
    print(json.dumps(result))
    assert all(count == 40 for count in sql_counts["batch"])
