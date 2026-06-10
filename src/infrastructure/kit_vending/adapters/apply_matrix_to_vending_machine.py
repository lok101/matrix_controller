from __future__ import annotations

import logging
from dataclasses import dataclass

from beartype import beartype

from src.domain.entities.vending_machine import VendingMachine
from src.domain.ports.apply_matrix_to_vending_machine import ApplyMatrixToVendingMachinePort
from src.domain.value_objects.command_result import CommandResult
from src.infrastructure.kit_vending.api.client import KitVendingAPIClient
from src.infrastructure.kit_vending.api.enums import VendingMachineCommand, VendingMachineStatus
from src.infrastructure.kit_vending.matrix_command_workflow import MatrixCommandWorkflow

logger = logging.getLogger(__name__)


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class ApplyMatrixToVendingMachineAdapter(ApplyMatrixToVendingMachinePort):
    kit_api_client: KitVendingAPIClient
    matrix_apply_timeout: int = 120
    max_retry_attempts: int = 3
    retry_send_command_timeout: int = 10

    async def execute(self, vending_machine: VendingMachine) -> CommandResult:
        workflow = MatrixCommandWorkflow(
            kit_api_client=self.kit_api_client,
            command=VendingMachineCommand.APPLY_MATRIX,
            status_predicate=lambda statuses: VendingMachineStatus.MATRIX_LOADED not in statuses,
            wait_timeout_seconds=self.matrix_apply_timeout,
            max_retry_attempts=self.max_retry_attempts,
            max_command_send_attempts=3,
            retry_send_command_timeout_seconds=self.retry_send_command_timeout,
        )
        result = await workflow.run(
            machine_kit_id=vending_machine.kit_id.value,
            machine_name=vending_machine.name,
        )
        if not result.success:
            logger.error(
                "Применение матрицы не удалось для %s: шаг=%s, попытка=%s, %s",
                vending_machine.name,
                result.step,
                result.attempts,
                result.message,
            )
        return result
