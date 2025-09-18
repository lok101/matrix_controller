from src.services.snack_machine_service import ISnackMachineRepository, SnackMachine, SnackMatrixId


class SnackMachineRepository(ISnackMachineRepository):
    def __init__(self):
        self._storage = {}

    def add(self, snack_machine: SnackMachine):
        self._storage[snack_machine.snack_matrix_id] = snack_machine

    def get(self, snack_matrix_id: SnackMatrixId) -> SnackMachine:
        return self._storage.get(snack_matrix_id)
