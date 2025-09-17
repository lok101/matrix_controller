from src.services.matrix_service import SnackMatrixId
from src.services.snack_machine_service import ISnackMachineRepository, SnackMachine, SnackMachineModel


class SnackMachineRepository(ISnackMachineRepository):
    def __init__(self):
        self._storage = {}
        self.__post_init__()

    def __post_init__(self):
        snack = SnackMachine(
            name='Тестовый СНЭК УГМК',
            model=SnackMachineModel.KV_12,
            snack_matrix_id=SnackMatrixId.ugmk_1stage_blue
        )

        self._storage[snack.snack_matrix_id] = snack

    def get(self, snack_matrix_id: SnackMatrixId) -> SnackMachine:
        return self._storage.get(snack_matrix_id)
