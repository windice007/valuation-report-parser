"""PostgreSQL backend detection."""


POSTGRES_BACKENDS = {"postgresql", "opengauss"}


def supports_schema_query(backend: str) -> bool:
    return backend in POSTGRES_BACKENDS
