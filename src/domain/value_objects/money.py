from dataclasses import dataclass, field

from beartype import beartype


@beartype
@dataclass(frozen=True, slots=True)
class Money:
    value: int | float = field(default_factory=lambda val: int(val))
