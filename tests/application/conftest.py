from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from src.application.use_cases.deploy.deploy_matrices import DeployMatricesUseCase
from src.application.use_cases.deploy.upload_and_apply_matrix import UploadAndApplyMatrixUseCase
from src.application.use_cases.sync.sync_all_caches import SyncAllCachesUseCase
from src.domain.exceptions import SynchronizationError
from src.domain.entities.cell import MatrixCell
from src.domain.entities.matrix import Matrix
from src.domain.entities.product import Product
from src.domain.entities.vending_machine import VendingMachine
from src.domain.ports.apply_matrix_to_vending_machine import ApplyMatrixToVendingMachinePort
from src.domain.ports.bind_matrix_to_vending_machine import BindMatrixToVendingMachinePort
from src.domain.ports.download_matrix_to_vending_machine import DownloadMatrixToVendingMachinePort
from src.domain.ports.get_matrices import GetAllMatricesPort
from src.domain.ports.get_products import GetAllProductsPort
from src.domain.ports.get_vending_machines import GetVendingMachinesPort
from src.domain.ports.upload_machine_matrix import UploadMatrixPort
from src.domain.value_objects.command_result import CommandResult
from src.domain.value_objects.ids.matrix_kit_id import MatrixKitId
from src.domain.value_objects.ids.product_id import ProductId
from src.domain.value_objects.ids.vending_machine_id import VMId
from src.domain.value_objects.ids.vending_machine_kit_id import VMKitId
from src.domain.value_objects.money import Money


def make_product() -> Product:
    return Product(id=ProductId(1), name="Cola", purchase_price=Money(rubles=50))


def make_cell() -> MatrixCell:
    return MatrixCell(line_number=1, product=make_product(), price=Money(rubles=100))


def make_matrix(name: str = "M1") -> Matrix:
    return Matrix(name=name, cells=[make_cell()], vending_machines_ids=[VMId(101)])


def make_machine(name: str = "VM-1") -> VendingMachine:
    return VendingMachine(id=VMId(101), kit_id=VMKitId(1001), name=name)


@dataclass
class FakeUploadPort(UploadMatrixPort):
    result: MatrixKitId | None = MatrixKitId(999)
    calls: list[tuple[Matrix, datetime]] = field(default_factory=list)

    async def execute(self, matrix: Matrix, timestamp: datetime) -> MatrixKitId | None:
        self.calls.append((matrix, timestamp))
        return self.result


@dataclass
class FakeBindPort(BindMatrixToVendingMachinePort):
    result: bool = True
    calls: int = 0

    async def execute(self, vending_machine: VendingMachine, matrix_kit_id: MatrixKitId) -> bool:
        self.calls += 1
        return self.result


@dataclass
class FakeDownloadPort(DownloadMatrixToVendingMachinePort):
    result: CommandResult = CommandResult(success=True, step="verify_status", message="ok", attempts=1)
    calls: int = 0

    async def execute(self, vending_machine: VendingMachine) -> CommandResult:
        self.calls += 1
        return self.result


@dataclass
class FakeApplyPort(ApplyMatrixToVendingMachinePort):
    result: CommandResult = CommandResult(success=True, step="verify_status", message="ok", attempts=1)
    calls: int = 0

    async def execute(self, vending_machine: VendingMachine) -> CommandResult:
        self.calls += 1
        return self.result


class FakeProductsPort(GetAllProductsPort):
    def execute(self) -> list[Product]:
        return [make_product()]


class FakeProductsPortEmpty(GetAllProductsPort):
    def execute(self) -> list[Product]:
        return []


class FakeMatricesPort(GetAllMatricesPort):
    def execute(self) -> list[Matrix]:
        return [make_matrix()]


class FakeVendingMachinesPort(GetVendingMachinesPort):
    async def execute(self) -> list[VendingMachine]:
        return [make_machine()]


class FakeUploadAndApply(UploadAndApplyMatrixUseCase):
    def __init__(self, side_effects: list[tuple[int, int]]) -> None:
        super().__init__(
            upload_matrix_port=FakeUploadPort(),
            bind_matrix_to_machine_port=FakeBindPort(),
            download_matrix_to_machine_port=FakeDownloadPort(),
            apply_matrix_to_machine_port=FakeApplyPort(),
            validate_matrices=False,
        )
        object.__setattr__(self, "_side_effects", list(side_effects))
        object.__setattr__(self, "_index", 0)

    async def execute(self, matrix, machines, timestamp) -> tuple[int, int]:
        index: int = self._index
        object.__setattr__(self, "_index", index + 1)
        return self._side_effects[index]


class FakeDeployMatrices(DeployMatricesUseCase):
    def __init__(
        self,
        return_value: tuple[int, int, int],
        matrix_repository,
        vending_machine_repository,
        upload_and_apply_matrix_uc,
    ) -> None:
        super().__init__(
            matrix_repository=matrix_repository,
            vending_machine_repository=vending_machine_repository,
            upload_and_apply_matrix_uc=upload_and_apply_matrix_uc,
        )
        object.__setattr__(self, "_return_value", return_value)

    async def execute(self, selected_matrix_names: list[str], timestamp: datetime) -> tuple[int, int, int]:
        return self._return_value


class FakeSyncAllRaises(SyncAllCachesUseCase):
    def __init__(self) -> None:
        pass

    async def execute(self) -> None:
        raise SynchronizationError("sync failed")
