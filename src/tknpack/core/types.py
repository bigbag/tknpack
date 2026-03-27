from dataclasses import dataclass
from enum import Enum


class Format(Enum):
    TOON = "toon"
    PLOON = "ploon"


@dataclass
class ToonOptions:
    indent: int = 2
    delimiter: str = ","


@dataclass
class PloonOptions:
    field_delimiter: str = "|"
    path_separator: str = ":"
    compact: bool = False
