import datetime

from src.services.matrix_service import MatrixService
from src.services.positions_service import ProductPositionsService
from src.services.product_service import ProductService
from src.services.snack_machine_service import SnackMachineService, SnackMatrixId


class CreateMatrixController:
    def __init__(
            self,
            matrix_service: MatrixService,
            product_service: ProductService,
            snack_machine_service: SnackMachineService,
            positions_service: ProductPositionsService
    ):
        self._matrix_service = matrix_service
        self._product_service = product_service
        self._snack_machine_service = snack_machine_service
        self._positions_service = positions_service

    async def execute(self, matrix_type: SnackMatrixId, day: datetime = datetime.date.today()):
        cells = self._positions_service.get_cells(matrix_type)
        matrix_name = self._snack_machine_service.get_matrix_name(matrix_type, day)
        await self._product_service.sync_products()
        await self._matrix_service.create_matrix(matrix_name, matrix_cells=cells)
