from src.domain.entites.matrix import Matrix
from src.domain.repositories.matrix_repository import MatrixRepository


class InMemoryMatrixRepository(MatrixRepository):
    def __init__(self):
        self._storage: dict[str, Matrix] = {}

    def get_by_name(self, matrix_name: str) -> Matrix | None:
        return self._storage.get(matrix_name)

    def get_all(self) -> list[Matrix]:
        return list(self._storage.values())

    def add(self, matrix: Matrix) -> None:
        self._storage[matrix.name] = matrix

    def get_size(self) -> int:
        return len(self._storage)

    def clear(self) -> None:
        self._storage.clear()
