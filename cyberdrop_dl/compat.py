from __future__ import annotations

import enum
from typing import TypeVar

T = TypeVar("T")


Enum = enum.Enum
IntEnum = enum.IntEnum
StrEnum = enum.StrEnum


class MayBeUpperStrEnum(StrEnum):
    @classmethod
    def _missing_(cls, value: object):
        try:
            return cls[str(value).upper()]
        except KeyError as e:
            raise e
