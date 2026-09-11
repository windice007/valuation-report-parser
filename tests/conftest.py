import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.schema import CreateSchema, DropSchema

from vrp.excel.sink import DbSink


@pytest.fixture
def pg_sink():
    url = os.environ.get("VRP_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Set VRP_TEST_POSTGRES_URL to an isolated PostgreSQL test database")
    engine = create_engine(url)
    schema = "vrp_test_" + uuid4().hex
    with engine.begin() as con:
        con.execute(CreateSchema(schema))
    sink = DbSink(make_url(url).update_query_dict({"schema": schema}), batch_size=2)
    try:
        yield sink
    finally:
        sink.engine.dispose()
        with engine.begin() as con:
            con.execute(DropSchema(schema, cascade=True))
        engine.dispose()
