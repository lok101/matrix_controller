import logging
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from beartype import beartype

from src.application.exceptions import SynchronizationError
from src.domain.entites.matrix import Matrix
from src.domain.ports.get_all_matrices import GetAllMatricesPort

logger = logging.getLogger("__main__")

@runtime_checkable
class MatrixCache(Protocol):
    def add(self, matrix: Matrix) -> None: pass

    def get_size(self) -> int: pass

    def clear(self) -> None: pass


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class SyncMatricesCache:
    get_all_matrices: GetAllMatricesPort
    matrix_repository: MatrixCache

    async def execute(self) -> None:
        self.matrix_repository.clear()
        matrices_quantity: int = self.matrix_repository.get_size()
        logger.info(f"Репозиторий матриц очищен. Матриц в репозитории: {matrices_quantity}.")

        matrices: list[Matrix] = await self.get_all_matrices.execute()

        if not matrices:
            raise SynchronizationError("При попытке синхронизации не были получены матрицы.")

        for matrix in matrices:
            self.matrix_repository.add(matrix)

        matrices_quantity: int = self.matrix_repository.get_size()
        logger.info(f"Синхронизация матриц завершена. Матриц в репозитории: {matrices_quantity}.")
