from __future__ import annotations

from src.domain.entities.matrix import Matrix
from src.domain.value_objects.ids.vending_machine_id import VMId
from src.interfaces.cli.matrix_choice_label import format_matrix_choice_label
from tests.application.conftest import make_cell


def test_format_matrix_choice_label_with_machines() -> None:
    matrix = Matrix(
        name="Матрица_А",
        cells=[make_cell()],
        vending_machines_ids=[VMId(101), VMId(102)],
    )
    assert format_matrix_choice_label(matrix) == "Матрица_А — 101, 102"


def test_format_matrix_choice_label_no_machines() -> None:
    matrix = Matrix(
        name="Матрица_А",
        cells=[make_cell()],
        vending_machines_ids=[],
    )
    assert format_matrix_choice_label(matrix) == "Матрица_А — (нет аппаратов)"
