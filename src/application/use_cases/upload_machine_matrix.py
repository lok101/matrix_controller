import logging
from dataclasses import dataclass
from datetime import datetime

from src.domain.entites.matrix import Matrix
from src.domain.entites.vending_machine import VendingMachine
from src.domain.exceptions import UploadMatrixError
from src.application.services.matrix_validator import MatrixValidator
from src.domain.ports.apply_matrix_to_vending_machine import ApplyMatrixToVendingMachinePort
from src.domain.ports.bind_matrix_to_vending_machine import BindMatrixToVendingMachinePort
from src.domain.ports.download_matrix_to_vending_machine import DownloadMatrixToVendingMachinePort
from src.domain.ports.upload_machine_matrix import UploadMatrixPort
from src.domain.value_objects.ids.matrix_kit_id import MatrixKitId

logger = logging.getLogger("__main__")

@dataclass(frozen=True, slots=True, kw_only=True)
class UploadAndApplyMatrixUseCase:
    upload_matrix_port: UploadMatrixPort
    bind_matrix_to_machine_port: BindMatrixToVendingMachinePort
    download_matrix_to_machine_port: DownloadMatrixToVendingMachinePort
    apply_matrix_to_machine_port: ApplyMatrixToVendingMachinePort
    matrix_validator: MatrixValidator

    async def execute(self, matrix: Matrix, machines: list[VendingMachine], timestamp: datetime):
        if not machines:
            raise UploadMatrixError('Не переданы аппараты для применения матрицы.')

        self.matrix_validator.validate(matrix)

        matrix_id: MatrixKitId | None = await self.upload_matrix_port.execute(matrix, timestamp)

        if matrix_id is None:
            raise UploadMatrixError("Не удалось создать матрицу.")

        for machine in machines:

            is_success: bool = await self.bind_matrix_to_machine_port.execute(machine, matrix_id)

            if not is_success:
                logger.critical(
                    f"Не удалось привязать матрицу к аппарату. "
                    f"Матрица: {matrix.name}, аппарат: {machine.name}."
                )
                continue

            is_success: bool = await self.download_matrix_to_machine_port.execute(machine)

            if not is_success:
                logger.critical(
                    f"Не удалось загрузить матрицу. "
                    f"Матрица: {matrix.name}, аппарат: {machine.name}."
                )
                continue

            is_success: bool = await self.apply_matrix_to_machine_port.execute(machine)

            if not is_success:
                logger.critical(
                    f"Не удалось применить матрицу. "
                    f"Матрица: {matrix.name}, аппарат: {machine.name}."
                )
                continue

            # проверить
