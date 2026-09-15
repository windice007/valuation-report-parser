"""Batch-size calculations for database writes."""


MAX_BIND_PARAMETERS = 30000


def rows_per_batch(column_count: int, requested: int) -> int:
    if column_count < 1 or requested < 1:
        raise ValueError("column_count and requested must be positive")
    return max(1, min(requested, MAX_BIND_PARAMETERS // column_count))


def chunks(items: list, size: int):
    if size < 1:
        raise ValueError("size must be positive")
    for index in range(0, len(items), size):
        yield items[index:index + size]
