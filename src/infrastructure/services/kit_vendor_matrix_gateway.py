import asyncio

from src.domain.entities.matrix import Matrix
from src.domain.entities.vending_machine import VendingMachine
from src.domain.services.vendor_matrix_gateway import VendorMatrixGateway
from src.infrastructure.ex_api.kit_api_client import KitVendingAPI
from src.infrastructure.logger import logger

COMMAND_TIMEOUT = 120


class KitVendorMatrixGateway(VendorMatrixGateway):

    def __init__(self, api_client: KitVendingAPI):
        self._api_client = api_client

    async def upload_matrix(self, matrix: Matrix) -> int:
        full_name = matrix.get_matrix_full_name()
        matrix_id = await self._api_client.create_matrix(
            matrix_positions=matrix.cells,
            matrix_name=full_name,

        )

        logger.info(f"Создана матрица c именем {full_name}. Id матрицы: {matrix_id}.")

        return matrix_id

    async def apply_to_machine(self, matrix_id: int, vending_machine: VendingMachine):
        await self._api_client.bound_matrix_to_machine(
            matrix_id=matrix_id,
            machine_id=vending_machine.kit_id,
        )

        logger.info(f"Матрица {matrix_id} привязана к аппарату {vending_machine.name}.")

        await self._api_client.load_matrix(
            machine_id=vending_machine.kit_id,
        )

        logger.info(
            f"Отправлена команда на загрузку матрицы для аппарата {vending_machine.name}. "
            f"Ожидание {COMMAND_TIMEOUT} секунд."
        )

        await asyncio.sleep(COMMAND_TIMEOUT)

        # todo проверка загрузки.

        await self._api_client.apply_matrix(
            machine_id=vending_machine.kit_id,
        )
        logger.info(f"Отправлена команда на применение матрицы для аппарата {vending_machine.name}.")

        # todo проверка применения.
