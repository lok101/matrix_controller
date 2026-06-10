from dataclasses import dataclass

from beartype import beartype

from src.domain.entities.matrix import Matrix
from src.domain.exceptions import MatrixValidationError


@beartype
@dataclass(frozen=True, slots=True, kw_only=True)
class MatrixValidator:

    @classmethod
    def validate(cls, matrix: Matrix) -> None:
        if not matrix.cells:
            raise MatrixValidationError(
                f"Матрица '{matrix.name}' не содержит ни одной ячейки."
            )

        bad_price_cells: list[str] = []
        bad_purchase_price_cells: list[str] = []

        for cell in matrix.cells:
            price_rub: float = cell.price.as_ruble()
            purchase_price_rub: float = cell.product.purchase_price.as_ruble()

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
            messages.append(
                "Неверная цена продажи (ниже закупочной): " + "; ".join(bad_price_cells)
            )

        if bad_purchase_price_cells:
            messages.append(
                "Неверная закупочная цена (<= 0): " + "; ".join(bad_purchase_price_cells)
            )

        raise MatrixValidationError(
            f"Матрица '{matrix.name}' не прошла валидацию.\n" + "\n".join(messages)
        )
