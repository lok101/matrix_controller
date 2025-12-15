from dataclasses import asdict

from src.application.dto.create_matrix_dto import CreateMatrixDTO
from src.application.dto.create_product_dto import CreateProductDTO
from src.domain.entities.matrix import MatrixCell
from src.domain.repositories.matrix_repository import MatrixRepository
from src.domain.repositories.product_repository import ProductRepository
from src.domain.repositories.vending_machine_repository import VendingMachineRepository
from src.infrastructure.ex_api.gspread_api_client import GspreadAPIClient
from src.infrastructure.ex_api.kit_api_client import KitVendingAPI
from src.infrastructure.logger import logger


class SyncDataService:
    def __init__(
            self,
            gs_api_client: GspreadAPIClient,
            kit_api_client: KitVendingAPI,
            product_repo: ProductRepository,
            vending_machine_repo: VendingMachineRepository,
            matrix_repo: MatrixRepository,
    ):
        self._gs_api_client = gs_api_client
        self._kit_api_client = kit_api_client
        self._product_repo = product_repo
        self._vending_machine_repo = vending_machine_repo
        self._matrix_repo = matrix_repo

    def sync_all_data(self):
        self._sync_vending_machine_data()
        self._sync_product_data()
        self._sync_matrix_data()

    def _sync_product_data(self):
        products = self._gs_api_client.get_products()

        for item in products:
            dto = CreateProductDTO(**asdict(item))
            self._product_repo.create(dto)

        logger.info("Данные о товарах синхронизированы.")

    def _sync_vending_machine_data(self):
        machines = self._kit_api_client.get_vending_machines()

        for dto in machines:
            self._vending_machine_repo.create(dto)

        logger.info("Данные об аппаратах синхронизированы.")

    def _sync_matrix_data(self):
        matrices = self._gs_api_client.get_matrices()

        for item in matrices:
            cells = []
            for cell in item.cells:
                product = self._product_repo.get_by_name(cell.product_name)

                if product is None:
                    raise Exception(f"Не найден товар с именем {cell.product_name} для матрицы {item.matrix_name}.")

                cells.append(
                    MatrixCell(
                        product=product,
                        line_number=cell.line,
                        price=cell.price
                    )
                )
            dto = CreateMatrixDTO(
                cells=cells,
                machine_ids=item.machine_ids,
                machine_model=item.machine_model,
                name=item.matrix_name
            )
            self._matrix_repo.create(dto)

        logger.info("Данные о матрицах синхронизированы.")
