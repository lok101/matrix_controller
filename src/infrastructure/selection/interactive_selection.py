from dataclasses import dataclass

from beartype import beartype

from src.domain.entities.matrix import Matrix
from src.domain.ports.matrix_selection import MatrixSelectionPort
from src.infrastructure.selection.interactive_selector import InteractiveSelector


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class InteractiveMatrixSelection(MatrixSelectionPort):
    interactive_selector: InteractiveSelector

    def select(self, available: list[Matrix]) -> list[str]:
        names = [m.name for m in available]
        return self.interactive_selector.select_items(names)
