from __future__ import annotations

from enum import IntEnum


class ResultCode(IntEnum):
    SUCCESS = 0
    TOO_MANY_REQUEST = 27


class VendingMachineCommand(IntEnum):
    LOAD_MATRIX = 3
    APPLY_MATRIX = 4


class VendingMachineStatus(IntEnum):
    MATRIX_LOADED = 21
    NO_CONNECTION = 1
