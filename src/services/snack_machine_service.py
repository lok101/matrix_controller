from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date

from src.services.matrix_service import SnackMatrixId


class SnackMachineModel:
    KV_12 = 'KV-12'
    KV_10 = 'KV-10'
    TCN_720 = 'TCN-720'


@dataclass
class SnackMachine:
    name: str
    model: SnackMachineModel
    snack_matrix_id: SnackMatrixId

    def get_matrix_name(self, day: date) -> str:
        return f'{day.strftime('%d.%m.%y')} | {self.model} | {self.name}'


class ISnackMachineRepository(ABC):
    @abstractmethod
    def get(self, snack_matrix_id: SnackMatrixId) -> SnackMachine: pass


class SnackMachineService:
    def __init__(self, snack_machine_repository: ISnackMachineRepository):
        self._snack_machine_repo = snack_machine_repository

    def get_matrix_name(self, snack_matrix_id: SnackMatrixId, day: date):
        snack_machine = self._snack_machine_repo.get(snack_matrix_id)
        matrix_name = snack_machine.get_matrix_name(day)
        return matrix_name
