import asyncio
import logging
from typing import Awaitable

from new_src.app.use_cases.upload_machine_matrix import UploadAndApplyMatrixUseCase
from new_src.domain.entites.matrix import Matrix
from new_src.domain.entites.vending_machine import VendingMachine
from new_src.domain.ports.get_matrix_data import GetMatricesPort
from new_src.domain.repositories.vending_machine_repository import VendingMachineRepository
from new_src.domain.value_objects.ids.vending_machine_id import VMId
from new_src.infrastructure.interactive_matrices_selector import InteractiveSelector

logger = logging.getLogger("__main__")


class SelectAndUpdateMatricesController:
    get_all_matrices: GetMatricesPort
    interactive_selector: InteractiveSelector

    vending_machine_repository: VendingMachineRepository

    upload_and_apply_matrix_uc: UploadAndApplyMatrixUseCase

    async def run(self):

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

            task = self.upload_and_apply_matrix_uc.execute(matrix, machines)

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