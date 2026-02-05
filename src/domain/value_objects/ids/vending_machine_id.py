from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VMId:
    value: int
