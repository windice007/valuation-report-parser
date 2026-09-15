from sqlalchemy import Column, Integer, MetaData, Table

from vrp.storage.reflection import find_column


def test_column_lookup_is_case_insensitive():
    table = Table("items", MetaData(), Column("ItemId", Integer))
    assert find_column(table, "itemid") is table.c.ItemId
