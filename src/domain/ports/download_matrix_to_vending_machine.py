from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.entities.vending_machine import VendingMachine
from src.domain.value_objects.command_result import CommandResult


class DownloadMatrixToVendingMachinePort(ABC):
    @abstractmethod
    async def execute(self, vending_machine: VendingMachine) -> CommandResult: ...
