from dataclasses import dataclass
from numbers import Real
from beartype import beartype


@beartype
@dataclass(frozen=True, slots=True)
class Money:
    value: int

    def __init__(self, value: Real) -> None:
        object.__setattr__(self, "value", int(value))

    def as_ruble(self) -> int:
        return self.value