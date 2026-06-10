from abc import ABC, abstractmethod

from src.domain.entities.matrix import Matrix


class MatrixSelectionPort(ABC):
    @abstractmethod
    async def select(self, available: list[Matrix]) -> list[str]: ...
