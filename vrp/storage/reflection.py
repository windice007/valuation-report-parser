"""Case-insensitive SQLAlchemy column lookup."""


def find_column(table, name: str):
    if name in table.columns:
        return table.columns[name]
    lowered = name.lower()
    return next((column for key, column in table.columns.items() if key.lower() == lowered), None)
