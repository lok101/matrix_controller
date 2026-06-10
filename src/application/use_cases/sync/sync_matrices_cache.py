import logging
from dataclasses import dataclass

from beartype import beartype

from src.domain.exceptions import SynchronizationError
from src.domain.ports.get_matrices import GetAllMatricesPort
from src.domain.repositories.matrix_repository import MatrixRepository

logger = logging.getLogger(__name__)


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class SyncMatricesCache:
    get_all_matrices: GetAllMatricesPort
    matrix_repository: MatrixRepository

    async def execute(self) -> None:
        self.matrix_repository.clear()
        matrices = self.get_all_matrices.execute()
        if not matrices:
            raise SynchronizationError("При попытке синхронизации не были получены матрицы.")
        for matrix in matrices:
            self.matrix_repository.add(matrix)
        logger.info(
            "Синхронизация матриц завершена. Матриц в репозитории: %s.",
            self.matrix_repository.get_size(),
        )
