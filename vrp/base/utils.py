import os
import re
import sys


_INDICES = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _get_index(index_chars):
    length = len(index_chars)
    index_chars_length = len(_INDICES)
    if length > 1:
        index = 0
        for i in range(0, length):
            if i < (length - 1):
                index += (_INDICES.index(index_chars[i]) + 1) * (
                    index_chars_length ** (length - 1 - i)
                )
            else:
                index += _INDICES.index(index_chars[i])
        return index
    else:
        return _INDICES.index(index_chars[0])


def excel_column_index(index_chars):
    if len(index_chars) < 1:
        return -1
    else:
        return _get_index(index_chars.upper())


def is_position_str(pos: str):
    return (isinstance(pos, str) and re.match("^[A-Za-z]+[0-9]+$", pos)) is not None


def is_position_column_str(pos: str):
    return (isinstance(pos, str) and re.match("^[A-Za-z]+$", pos)) is not None and len(
        pos
    ) < 4


def search_app_file(file_name) -> str:
    p1 = os.path.join(os.getcwd(), file_name)
    p2 = os.path.join(os.path.dirname(sys.executable), file_name)
    if os.path.exists(p1):
        return p1
    if os.path.exists(p2):
        return p2
    return None
