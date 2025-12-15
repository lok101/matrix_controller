from dataclasses import asdict

from src.application.dto.create_matrix_dto import CreateMatrixDTO
from src.domain.entities.matrix import Matrix
from src.domain.repositories.matrix_repository import MatrixRepository


class InMemoryMatrixRepository(MatrixRepository):
    def __init__(self):
        self._storage = {}

    def create(self, dto: CreateMatrixDTO) -> Matrix:
        key = dto.name

        if key in self._storage.keys():
            raise Exception(f"Матрица \"{dto.name}\" - уже существует.")
        matrix = Matrix(
            name=dto.name,
            machine_model=dto.machine_model,
            machine_ids=dto.machine_ids,
            cells=dto.cells
        )
        self._storage[key] = matrix

        return matrix

    def get_matrices_names(self) -> list[str]:
        return list(self._storage.keys())

    def get_by_name(self, matrix_name: str) -> Matrix | None:
        return self._storage.get(matrix_name)
