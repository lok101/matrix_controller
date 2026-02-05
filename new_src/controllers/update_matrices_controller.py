from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from beartype import beartype

from new_src.application.use_cases.select_and_upload_matrices import SelectAndUploadMatricesUseCase
from new_src.domain.ports.get_all_matrices import GetAllMatricesPort
from new_src.infrastructure.interactive_matrices_selector import InteractiveSelector


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class SelectAndUpdateMatricesController:
    get_all_matrices: GetAllMatricesPort
    interactive_selector: InteractiveSelector
    select_and_upload_matrices_uc: SelectAndUploadMatricesUseCase

    async def run(self) -> None:
        now = datetime.now(tz=ZoneInfo("Asia/Yekaterinburg"))

        matrices = await self.get_all_matrices.execute()

        if not matrices:
            raise ValueError("Не найдено ни одной доступной матрицы")

        matrices_names: list[str] = [matrix.name for matrix in matrices]

        selected_names: list[str] = self.interactive_selector.select_items(matrices_names)

        if not selected_names:
            return

        await self.select_and_upload_matrices_uc.execute(selected_names, now)
