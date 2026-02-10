from dataclasses import dataclass

from beartype import beartype

from src.application.exceptions import SynchronizationError
from src.application.repositories.product_repository import ProductRepository
from src.domain.entites.cell import MatrixCell
from src.domain.entites.matrix import Matrix
from src.domain.entites.product import Product
from src.domain.value_objects.ids.vending_machine_id import VMId
from src.domain.value_objects.money import Money
from src.infrastructure.google_sheets_api_client import GoogleSheetsAPIClient, MatrixModel, MatrixCellModel


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class GetAllMatricesAdapter:
    google_table_api_client: GoogleSheetsAPIClient
    product_repository: ProductRepository

    def execute(self) -> list[Matrix]:
        res: list[Matrix] = []
        matrices_data: list[MatrixModel] = self.google_table_api_client.get_all_matrices()

        for matrix_dto in matrices_data:
            matrix_name: str = matrix_dto.matrix_name
            vending_machines_ids: list[VMId] = [VMId(item) for item in matrix_dto.vending_machine_ids]
            cells: list[MatrixCell] = self._get_matrix_cells(matrix_dto.cells_data, matrix_name)

            matrix = Matrix(
                name=matrix_name,
                cells=cells,
                vending_machines_ids=vending_machines_ids,
            )

            res.append(matrix)

        return res

    def _get_matrix_cells(self, cells_data: list[MatrixCellModel], matrix_name: str) -> list[MatrixCell]:
        res: list[MatrixCell] = []

        for cell_dto in cells_data:
            cell_number: int | None = cell_dto.number

            if cell_number is None:
                continue

            product_name: str = cell_dto.product_name
            product_price: float | None = cell_dto.product_price

            if product_price is None:
                price: Money = Money(rubles=0)

            else:
                price: Money = Money(rubles=cell_dto.product_price)

            if product_name is None and product_price is None:
                continue

            if product_name is None and product_price is not None:
                raise SynchronizationError(
                    f"Для товара не передано имя, но указана цена. "
                    f"Матрица: {matrix_name}, товар номер {cell_number}."
                )

            if product_name is not None and product_price is None:
                raise SynchronizationError(
                    f"Для товара не указана цена. "
                    f"Матрица: {matrix_name}, товар номер {cell_number}."
                )

            product: Product | None = self.product_repository.get_by_name(product_name)

            if product is None:
                raise SynchronizationError(f"Товар \"{product_name}\" не был найден в репозитории.")

            cell = MatrixCell(
                line_number=cell_number,
                product=product,
                price=price
            )

            res.append(cell)

        return res
