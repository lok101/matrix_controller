from dataclasses import dataclass

from beartype import beartype

from src.application.exceptions import MatrixValidationError
from src.domain.entites.matrix import Matrix


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class MatrixValidator:

    @classmethod
    def validate(cls, matrix: Matrix):
        cells_count: int = len(matrix.cells)

        if cells_count == 0:
            raise MatrixValidationError(f"Матрица '{matrix.name}' не содержит ни одной ячейки.")

        bad_price_cells: list[str] = []
        bad_purchase_price_cells: list[str] = []

        for cell in matrix.cells:
            price_rub: int = cell.price.as_ruble()
            purchase_price_rub: int = cell.product.purchase_price.as_ruble()

            if price_rub < purchase_price_rub:
                bad_price_cells.append(
                    f"строка={cell.line_number}, товар='{cell.product.name}', цена={price_rub}"
                )

            if purchase_price_rub <= 0:
                bad_purchase_price_cells.append(
                    f"строка={cell.line_number}, товар='{cell.product.name}', "
                    f"закупочная_цена={purchase_price_rub}"
                )

        if not bad_price_cells and not bad_purchase_price_cells:
            return

        messages: list[str] = []

        if bad_price_cells:
            details_price: str = "; ".join(bad_price_cells)
            messages.append(
                f"Неверная цена продажи (ниже закупочной): {details_price}"
            )

        if bad_purchase_price_cells:
            details_purchase: str = "; ".join(bad_purchase_price_cells)
            messages.append(
                f"Неверная закупочная цена (<= 0): {details_purchase}"
            )

        full_message: str = (
            f"Матрица '{matrix.name}' не прошла валидацию.\n" + "\n".join(messages)
        )
        raise MatrixValidationError(full_message)