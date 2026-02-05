import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Awaitable
from zoneinfo import ZoneInfo

from beartype import beartype

from new_src.application.use_cases.upload_machine_matrix import UploadAndApplyMatrixUseCase
from new_src.domain.entites.matrix import Matrix
from new_src.domain.entites.vending_machine import VendingMachine
from new_src.domain.ports.get_all_matrices import GetAllMatricesPort
from new_src.domain.repositories.vending_machine_repository import VendingMachineRepository
from new_src.domain.value_objects.ids.vending_machine_id import VMId
from new_src.infrastructure.interactive_matrices_selector import InteractiveSelector

logger = logging.getLogger("__main__")


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class SelectAndUpdateMatricesController:
    get_all_matrices: GetAllMatricesPort
    interactive_selector: InteractiveSelector

    vending_machine_repository: VendingMachineRepository

    upload_and_apply_matrix_uc: UploadAndApplyMatrixUseCase

    async def run(self):
        now = datetime.now(tz=ZoneInfo("Asia/Yekaterinburg"))

        matrices: list[Matrix] = await self.get_all_matrices.execute()
        matrices_map: dict[str, Matrix] = {matrix.name: matrix for matrix in matrices}

        if not matrices:
            raise NotImplementedError()

        matrices_names: list[str] = [matrix.name for matrix in matrices]

        selected_names: list[str] = self.interactive_selector.select_items(matrices_names)

        if not selected_names:
            raise NotImplementedError()

        tasks: list[Awaitable] = []

        for name in selected_names:
            matrix: Matrix | None = matrices_map.get(name)

            if matrix is None:
                raise NotImplementedError()

            machines: list[VendingMachine] = self._get_vending_machines(matrix.vending_machines_ids)

            task = self.upload_and_apply_matrix_uc.execute(matrix, machines, now)

            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        errors: list[Exception] = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                errors.append(result)
                logger.error(f"Ошибка при загрузке матрицы '{selected_names[i]}': {result}")

        if errors:
            logger.warning(f"Завершено с {len(errors)} ошибками из {len(results)} задач")
        else:
            logger.info("Загрузка матриц завершена успешно.")

    def _get_vending_machines(self, machines_ids: list[VMId]) -> list[VendingMachine]:
        res: list[VendingMachine] = []

        for _id in machines_ids:
            vm: VendingMachine | None = self.vending_machine_repository.get_by_id(_id)

            if vm is None:
                logger.error(f"Не была получена машина с Id: {_id.value}.")
                continue

            res.append(vm)

        return res
