# tests/domain/test_matrix_validator.py
import pytest

from src.domain.entities.cell import MatrixCell
from src.domain.entities.matrix import Matrix
from src.domain.entities.product import Product
from src.domain.exceptions import MatrixValidationError
from src.domain.services.matrix_validator import MatrixValidator
from src.domain.value_objects.ids.product_id import ProductId
from src.domain.value_objects.ids.vending_machine_id import VMId
from src.domain.value_objects.money import Money


def _product(name: str = "Cola", purchase: float = 50.0) -> Product:
    return Product(id=ProductId(1), name=name, purchase_price=Money(rubles=purchase))


def _matrix(cells: list[MatrixCell]) -> Matrix:
    return Matrix(name="Test", cells=cells, vending_machines_ids=[VMId(1)])


def test_validate_passes_when_prices_ok():
    cell = MatrixCell(line_number=1, product=_product(), price=Money(rubles=100))
    MatrixValidator.validate(_matrix([cell]))


def test_validate_raises_when_sale_below_purchase():
    cell = MatrixCell(line_number=1, product=_product(purchase=100), price=Money(rubles=50))
    with pytest.raises(MatrixValidationError, match="Неверная цена продажи"):
        MatrixValidator.validate(_matrix([cell]))


def test_validate_raises_when_purchase_zero():
    cell = MatrixCell(line_number=2, product=_product(purchase=0), price=Money(rubles=10))
    with pytest.raises(MatrixValidationError, match="Неверная закупочная цена"):
        MatrixValidator.validate(_matrix([cell]))


def test_validate_raises_when_no_cells():
    with pytest.raises(MatrixValidationError, match="не содержит ни одной ячейки"):
        MatrixValidator.validate(_matrix([]))
