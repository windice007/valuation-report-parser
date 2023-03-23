import decimal
import json
from sqlalchemy import CursorResult, Engine, Table, create_engine, text
from urllib.parse import quote_plus


class MySQLTableSink:
    def __init__(self, engine: Engine, table: str) -> None:
        self._engine = engine
        self.table = table
        self.schema = self._engine.url.database
        self.table_schema = self._fetch_table_schema()
        self._primary_columns = None

    def _fetch_table_schema(self):
        sql = f"SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = '{self.schema}' AND TABLE_NAME ='{self.table}'"
        with self._engine.connect() as con:
            rs: CursorResult = con.execute(text(sql))
            rows = rs.mappings().fetchall()
            dic = {}
            for row in rows:
                dic[row['COLUMN_NAME']] = row
            return dic

    def column_schema(self, column: str):
        return self.table_schema.get(column)

    @property
    def primary_columns(self):
        if self._primary_columns is None:
            self._primary_columns = []
            for k, column in self.table_schema.items():
                if column['COLUMN_KEY'] == 'PRI':
                    self._primary_columns.append(k)
        return self._primary_columns

    def display(self):
        print(self.table_schema)


__sinks__: dict[str, MySQLTableSink] = {}


def get_table_sink(table: str):
    if table not in __sinks__:
        __sinks__[table] = MySQLTableSink(DB_ENGINE, table)
    return __sinks__.get(table)


DB_ENGINE: Engine = None


def init_db(connection_url: str):
    global DB_ENGINE
    DB_ENGINE = create_engine(connection_url)
