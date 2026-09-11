import pytest
from pyexcel import Sheet

from vrp.excel.process import ProcessContext, capture_data, merged_value
from vrp.excel.utils import Dict


@pytest.mark.parametrize("direction, target, opposite", [
    ("up", (0, 2), (4, 2)),
    ("down", (4, 2), (0, 2)),
    ("left", (2, 0), (2, 4)),
    ("right", (2, 4), (2, 0)),
])
@pytest.mark.parametrize("value", ["target", 0, None])
def test_directional_search_stays_within_sheet(direction, target, opposite, value):
    data = [[""] * 5 for _ in range(5)]
    data[opposite[0]][opposite[1]] = "wrong direction"
    if value is not None:
        data[target[0]][target[1]] = value
    context = ProcessContext(Sheet(data), Dict({"subject_code_column": "A"}))
    context.env = {}
    cell = Dict({"address": "C3", "merged_value": direction})

    assert merged_value(context, cell, 2, 2) == value
    assert capture_data(context, cell) == ("" if value is None else value)


@pytest.mark.parametrize("direction, address, start, opposite", [
    ("up", "C1", (0, 2), (4, 2)),
    ("down", "C5", (4, 2), (0, 2)),
    ("left", "A3", (2, 0), (2, 4)),
    ("right", "E3", (2, 4), (2, 0)),
])
def test_search_from_edge_does_not_wrap(direction, address, start, opposite):
    data = [[""] * 5 for _ in range(5)]
    data[opposite[0]][opposite[1]] = "opposite edge"
    context = ProcessContext(Sheet(data), Dict({"subject_code_column": "A"}))
    context.env = {}
    cell = Dict({"address": address, "merged_value": direction})

    assert merged_value(context, cell, *start) is None
    assert capture_data(context, cell) == ""
