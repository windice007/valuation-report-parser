"""
valuation report parser
"""
__version__ = "0.2.15"


from typing import Protocol


class Args(Protocol):
    debug: bool
    dir: str
    nofile: bool
    config: str
    connection_url: str
