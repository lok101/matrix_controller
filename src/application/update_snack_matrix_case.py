import asyncio

from src.domain.entities.matrix import Matrix
from src.domain.repositories.vending_machine_repository import VendingMachineRepository
from src.domain.services.vendor_matrix_gateway import VendorMatrixGateway
from src.infrastructure.logger import logger


class UpdateSnackMatrixUseCase:

    def __init__(
            self,
            vending_machine_repo: VendingMachineRepository,
            vendor_matrix_gateway: VendorMatrixGateway
    ):
        self._vending_machine_repo = vending_machine_repo
        self._vendor_matrix_gateway = vendor_matrix_gateway

    async def execute(self, matrix: Matrix, delay_before_start: int) -> None:

        await asyncio.sleep(delay_before_start)

        ex_matrix_id = await self._vendor_matrix_gateway.upload_matrix(matrix)

        tasks = []

        for machine_id in matrix.machine_ids:
            vending_machine = self._vending_machine_repo.get_by_id(machine_id)

            if vending_machine is None:
                logger.error(f"Не найден аппарата с кодом {machine_id}!")
                continue

            task = self._vendor_matrix_gateway.apply_to_machine(ex_matrix_id, vending_machine)
            tasks.append(task)

        await asyncio.gather(*tasks)
