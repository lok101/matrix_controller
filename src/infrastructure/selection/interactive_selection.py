from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from beartype import beartype

from src.domain.entities.matrix import Matrix
from src.domain.ports.matrix_selection import MatrixSelectionPort
from src.interfaces.cli.matrix_choice_label import format_matrix_choice_label


@runtime_checkable
class MatrixItemSelector(Protocol):
    def select_items(self, items: list[tuple[str, str]]) -> list[str]: ...


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class InteractiveMatrixSelection(MatrixSelectionPort):
    selector: MatrixItemSelector

    def select(self, available: list[Matrix]) -> list[str]:
        choices = [(format_matrix_choice_label(m), m.name) for m in available]
        return self.selector.select_items(choices)
