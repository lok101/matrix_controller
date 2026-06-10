import logging
from dataclasses import dataclass
from datetime import datetime

from src.application.services.matrix_validator import MatrixValidator
from src.domain.entites.matrix import Matrix
from src.domain.entites.vending_machine import VendingMachine
from src.domain.exceptions import UploadMatrixError
from src.domain.ports.apply_matrix_to_vending_machine import ApplyMatrixToVendingMachinePort
from src.domain.ports.bind_matrix_to_vending_machine import BindMatrixToVendingMachinePort
from src.domain.ports.download_matrix_to_vending_machine import DownloadMatrixToVendingMachinePort
from src.domain.ports.upload_machine_matrix import UploadMatrixPort
from src.domain.value_objects.command_result import CommandResult
from src.domain.value_objects.ids.matrix_kit_id import MatrixKitId

logger = logging.getLogger()


@dataclass(frozen=True, slots=True, kw_only=True)
class UploadAndApplyMatrixUseCase:
    upload_matrix_port: UploadMatrixPort
    bind_matrix_to_machine_port: BindMatrixToVendingMachinePort
    download_matrix_to_machine_port: DownloadMatrixToVendingMachinePort
    apply_matrix_to_machine_port: ApplyMatrixToVendingMachinePort
    matrix_validator: MatrixValidator

    timeout_before_applying: int = 120

    async def execute(self, matrix: Matrix, machines: list[VendingMachine], timestamp: datetime) -> None:
        if not machines:
            raise UploadMatrixError("Не переданы аппараты для применения матрицы.")

        logger.warning(
            "Валидация матрицы '%s' отключена намеренно (MatrixValidator.validate не вызывается).",
            matrix.name,
        )

        matrix_id: MatrixKitId | None = await self.upload_matrix_port.execute(matrix, timestamp)

        if matrix_id is None:
            raise UploadMatrixError("Не удалось создать матрицу.")

        success_count = 0
        failure_count = 0

        for machine in machines:
            is_success: bool = await self.bind_matrix_to_machine_port.execute(machine, matrix_id)

            if not is_success:
                failure_count += 1
                logger.critical(
                    f"Не удалось привязать матрицу к аппарату. "
                    f"Матрица: {matrix.name}, аппарат: {machine.name}."
                )
                continue

            download_result: CommandResult = await self.download_matrix_to_machine_port.execute(machine)

            if not download_result.success:
                failure_count += 1
                logger.critical(
                    f"Не удалось загрузить матрицу. "
                    f"Матрица: {matrix.name}, аппарат: {machine.name}, "
                    f"шаг: {download_result.step}, попытка: {download_result.attempts}, "
                    f"причина: {download_result.message}."
                )
                continue

            apply_result: CommandResult = await self.apply_matrix_to_machine_port.execute(machine)

            if not apply_result.success:
                failure_count += 1
                logger.critical(
                    f"Не удалось применить матрицу. "
                    f"Матрица: {matrix.name}, аппарат: {machine.name}, "
                    f"шаг: {apply_result.step}, попытка: {apply_result.attempts}, "
                    f"причина: {apply_result.message}."
                )
                continue

            success_count += 1

        if failure_count == 0:
            logger.info(
                f"Матрица '{matrix.name}': все {success_count} аппаратов обработаны успешно."
            )
        elif success_count == 0:
            logger.critical(
                f"Матрица '{matrix.name}': полный провал — 0 из {len(machines)} аппаратов."
            )
        else:
            logger.warning(
                f"Матрица '{matrix.name}': частичный успех — "
                f"{success_count} из {len(machines)} аппаратов, ошибок: {failure_count}."
            )
