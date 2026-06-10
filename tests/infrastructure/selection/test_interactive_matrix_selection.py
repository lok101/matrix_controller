from __future__ import annotations

from dataclasses import dataclass, field

from src.domain.entities.matrix import Matrix
from src.domain.value_objects.ids.vending_machine_id import VMId
from src.infrastructure.selection.interactive_selection import InteractiveMatrixSelection
from tests.application.conftest import make_cell


@dataclass
class FakeSelector:
    last_items: list[tuple[str, str]] = field(default_factory=list)
    return_value: list[str] = field(default_factory=list)

    def select_items(self, items: list[tuple[str, str]]) -> list[str]:
        self.last_items = items
        return self.return_value


def test_interactive_matrix_selection_returns_names() -> None:
    fake = FakeSelector(return_value=["M1"])
    selection = InteractiveMatrixSelection(selector=fake)
    matrices = [
        Matrix(
            name="M1",
            cells=[make_cell()],
            vending_machines_ids=[VMId(101), VMId(102)],
        ),
        Matrix(name="M2", cells=[make_cell()], vending_machines_ids=[]),
    ]

    result = selection.select(matrices)

    assert result == ["M1"]
    assert fake.last_items == [
        ("M1 — 101, 102", "M1"),
        ("M2 — (нет аппаратов)", "M2"),
    ]
