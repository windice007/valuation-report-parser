from vrp.base import TABLE_NAME
from vrp.storage.records import group_by_table


def test_records_are_grouped_by_target_table():
    records = [{TABLE_NAME: "a", "id": 1}, {TABLE_NAME: "b", "id": 2}, {TABLE_NAME: "a", "id": 3}]
    grouped = group_by_table(records)
    assert [item["id"] for item in grouped["a"]] == [1, 3]
