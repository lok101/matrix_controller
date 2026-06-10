from __future__ import annotations

from dataclasses import dataclass

from src.domain.entities.matrix import Matrix
from src.domain.entities.vending_machine import VendingMachine


@dataclass(frozen=True, slots=True, kw_only=True)
class MatrixDeployItem:
    matrix: Matrix
    machines: list[VendingMachine]
