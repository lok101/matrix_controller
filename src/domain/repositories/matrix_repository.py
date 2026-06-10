from abc import ABC, abstractmethod

from src.domain.entities.matrix import Matrix


class MatrixRepository(ABC):
    @abstractmethod
    def get_by_name(self, matrix_name: str) -> Matrix | None: ...

    @abstractmethod
    def get_all(self) -> list[Matrix]: ...

    @abstractmethod
    def add(self, matrix: Matrix) -> None: ...

    @abstractmethod
    def clear(self) -> None: ...

    @abstractmethod
    def get_size(self) -> int: ...
