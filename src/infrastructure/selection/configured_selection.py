from dataclasses import dataclass

from beartype import beartype

from src.domain.entities.matrix import Matrix
from src.domain.ports.matrix_selection import MatrixSelectionPort


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class ConfiguredMatrixSelection(MatrixSelectionPort):
    names: str

    def select(self, available: list[Matrix]) -> list[str]:
        if self.names.strip() == "*":
            return [m.name for m in available]
        wanted = {n.strip() for n in self.names.split(",") if n.strip()}
        return [m.name for m in available if m.name in wanted]
