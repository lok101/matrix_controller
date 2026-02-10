import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Awaitable

from beartype import beartype

from src.application.use_cases.upload_machine_matrix import UploadAndApplyMatrixUseCase
from src.domain.entites.matrix import Matrix
from src.domain.entites.vending_machine import VendingMachine
from src.domain.exceptions import UploadMatrixError
from src.domain.repositories.matrix_repository import MatrixRepository
from src.domain.repositories.vending_machine_repository import VendingMachineRepository
from src.domain.value_objects.ids.vending_machine_id import VMId

logger = logging.getLogger()


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class SelectAndUploadMatricesUseCase:
    matrix_repository: MatrixRepository
    vending_machine_repository: VendingMachineRepository
    upload_and_apply_matrix_uc: UploadAndApplyMatrixUseCase

    async def execute(self, selected_matrix_names: list[str], timestamp: datetime) -> None:
        if not selected_matrix_names:
            raise UploadMatrixError("Не выбрано ни одной матрицы для загрузки")

        tasks: list[Awaitable] = []
        task_matrix_names: list[str] = []

        for name in selected_matrix_names:
            matrix: Matrix | None = self.matrix_repository.get_by_name(name)

            if matrix is None:
                logger.error(f"Матрица с именем '{name}' не найдена")
                continue

            machines: list[VendingMachine] = self._get_vending_machines(matrix.vending_machines_ids)

            if not machines:
                logger.warning(f"Не найдено ни одной машины для матрицы '{name}'")
                continue

            task = self.upload_and_apply_matrix_uc.execute(matrix, machines, timestamp)
            tasks.append(task)
            task_matrix_names.append(name)

        if not tasks:
            raise UploadMatrixError("Не удалось создать ни одной задачи для загрузки матриц")

        results = await asyncio.gather(*tasks, return_exceptions=True)

        errors: list[Exception] = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                errors.append(result)
                logger.error(f"Ошибка при загрузке матрицы '{task_matrix_names[i]}': {result}")

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
