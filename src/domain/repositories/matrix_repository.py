from abc import ABC, abstractmethod

from src.application.dto.create_matrix_dto import CreateMatrixDTO
from src.domain.entities.matrix import Matrix


class MatrixRepository(ABC):
    @abstractmethod
    def get_matrices_names(self) -> list[str]: pass

    @abstractmethod
    def create(self, dto: CreateMatrixDTO) -> Matrix: pass

    @abstractmethod
    def get_by_name(self, matrix_name: str) -> Matrix | None: pass
