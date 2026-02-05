from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from beartype import beartype

from src.application.use_cases.select_and_upload_matrices import SelectAndUploadMatricesUseCase
from src.domain.repositories.matrix_repository import MatrixRepository
from src.infrastructure.interactive_matrices_selector import InteractiveSelector


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class SelectAndUpdateMatricesController:
    matrix_repository: MatrixRepository
    interactive_selector: InteractiveSelector
    select_and_upload_matrices_uc: SelectAndUploadMatricesUseCase

    async def run(self) -> None:
        now = datetime.now(tz=ZoneInfo("Asia/Yekaterinburg"))

        matrices = self.matrix_repository.get_all()

        if not matrices:
            raise ValueError("Не найдено ни одной доступной матрицы")

        matrices_names: list[str] = [matrix.name for matrix in matrices]

        selected_names: list[str] = self.interactive_selector.select_items(matrices_names)

        if not selected_names:
            return

        await self.select_and_upload_matrices_uc.execute(selected_names, now)
