from vrp.storage.postgres import supports_schema_query


def test_schema_query_backends_are_explicit():
    assert supports_schema_query("postgresql")
    assert supports_schema_query("opengauss")
    assert not supports_schema_query("mysql")
