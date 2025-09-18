import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date


class SnackMatrixId(enum.StrEnum):
    ugmk_1stage_blue = 'угмк_kv12'
    ugmk_1stage_yellow = 'угмк_kv10'
    ugmk_3stage_blue = 'угмк_kv10'
    ugmk_3stage_green = 'угмк_kv10'
    ugmk_3stage_red = 'угмк_kv10'

    dvvs = 'дввс_tcn'
    okami_west = 'okami_vostok'
    okami_nord = 'оками_север'
    okami_metal = 'оками_металлургов'
    fok = 'фок'


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
        return f'{self.model} | {self.name} | {day.strftime('%d.%m.%y')}'


class ISnackMachineRepository(ABC):
    @abstractmethod
    def add(self, snack_machine: SnackMachine): pass

    @abstractmethod
    def get(self, snack_matrix_id: SnackMatrixId) -> SnackMachine: pass


class SnackMachineService:
    def __init__(self, snack_machine_repository: ISnackMachineRepository):
        self._snack_machine_repo = snack_machine_repository

    def register_snack_machine(self, name: str, model: SnackMachineModel, matrix_id: SnackMatrixId):
        new_instance = SnackMachine(
            name=name,
            model=model,
            snack_matrix_id=matrix_id
        )
        self._snack_machine_repo.add(new_instance)

    def get_matrix_name(self, snack_matrix_id: SnackMatrixId, day: date):
        snack_machine = self._snack_machine_repo.get(snack_matrix_id)
        matrix_name = snack_machine.get_matrix_name(day)
        return matrix_name
