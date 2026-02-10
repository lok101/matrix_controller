from dataclasses import dataclass
from beartype import beartype


@beartype
@dataclass(frozen=True, slots=True)
class Money:
    value: int  # всегда в копейках

    def __init__(self, *, rubles: int | float | None = None, kopecks: int | None = None) -> None:
        # Разрешаем указать ровно один аргумент
        if (rubles is None) == (kopecks is None):
            raise ValueError("Нужно указать либо rubles, либо kopecks, но не оба и не ни одного")

        if rubles is not None:
            raw_value = int(rubles * 100)
        else:
            raw_value = int(kopecks)

        object.__setattr__(self, "value", raw_value)

    def as_ruble(self) -> float:
        return self.value / 100
