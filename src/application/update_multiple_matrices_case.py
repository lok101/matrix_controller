import asyncio

from src.application.dto.update_matrices_request import UpdateMatricesRequest
from src.application.update_snack_matrix_case import UpdateSnackMatrixUseCase
from src.domain.repositories.matrix_repository import MatrixRepository

TIMEOUT = 50


class UpdateMultipleMatricesUseCase:

    def __init__(self, update_matrix_uc: UpdateSnackMatrixUseCase, matrix_repo: MatrixRepository):
        self._update_matrix_uc = update_matrix_uc
        self._matrix_repo = matrix_repo

    async def execute(self, request: UpdateMatricesRequest) -> None:
        tasks = []
        timeouts = [TIMEOUT * i for i in range(len(request.matrices_names))]

        for i, matrix_name in enumerate(request.matrices_names):
            matrix = self._matrix_repo.get_by_name(matrix_name)
            task = self._update_matrix_uc.execute(matrix, timeouts[i])
            tasks.append(task)

        await asyncio.gather(*tasks)
