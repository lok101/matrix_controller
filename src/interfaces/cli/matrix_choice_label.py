from __future__ import annotations

from beartype import beartype

from src.domain.entities.matrix import Matrix


@beartype
def format_matrix_choice_label(matrix: Matrix) -> str:
    if not matrix.vending_machines_ids:
        return f"{matrix.name} — (нет аппаратов)"
    numbers = ", ".join(str(vm.value) for vm in matrix.vending_machines_ids)
    return f"{matrix.name} — {numbers}"
