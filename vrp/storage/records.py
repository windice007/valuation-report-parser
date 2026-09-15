"""Record grouping helpers."""

from vrp.base import TABLE_NAME


def group_by_table(records: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for record in records:
        grouped.setdefault(record[TABLE_NAME], []).append(record)
    return grouped
