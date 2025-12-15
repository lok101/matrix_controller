from src.application.dto.update_matrices_request import UpdateMatricesRequest
from src.application.update_multiple_matrices_case import UpdateMultipleMatricesUseCase
from src.application.user_select_matrices_use_case import GetMatricesWithSelectionUseCase


class UpdateSnackMatricesController:

    def __init__(
            self,
            update_multiple_matrices_uc: UpdateMultipleMatricesUseCase,
            select_matrices_use_case: GetMatricesWithSelectionUseCase
    ):
        self._update_multiple_matrices_uc = update_multiple_matrices_uc
        self._select_matrices_use_case = select_matrices_use_case

    async def execute(self) -> dict:
        matrices_names = self._select_matrices_use_case.execute()
        request = UpdateMatricesRequest(matrices_names=matrices_names)
        await self._update_multiple_matrices_uc.execute(request)

        return {
            "success": True,
            "updated_machines": matrices_names,
            "message": f"Матрицы успешно обновлены для {len(matrices_names)} аппаратов"
        }
