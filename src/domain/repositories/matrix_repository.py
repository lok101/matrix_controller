from abc import ABC, abstractmethod

from src.domain.entites.matrix import Matrix


class MatrixRepository(ABC):
    @abstractmethod
    def get_by_name(self, matrix_name: str) -> Matrix | None: pass

    @abstractmethod
    def get_all(self) -> list[Matrix]: pass
