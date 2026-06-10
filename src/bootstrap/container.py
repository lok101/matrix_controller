from __future__ import annotations

from types import TracebackType

import gspread

from src.application.use_cases.deploy.deploy_matrices import DeployMatricesUseCase
from src.application.use_cases.deploy.upload_and_apply_matrix import UploadAndApplyMatrixUseCase
from src.application.use_cases.orchestration.run_deployment_job import RunDeploymentJobUseCase
from src.application.use_cases.sync.sync_all_caches import SyncAllCachesUseCase
from src.application.use_cases.sync.sync_matrices_cache import SyncMatricesCache
from src.application.use_cases.sync.sync_products_cache import SyncProductsCache
from src.application.use_cases.sync.sync_vending_machines_cache import SyncVendingMachinesCache
from src.bootstrap.settings import Settings
from src.domain.entities.job_run import JobRun, JobRunTrigger
from src.domain.exceptions import JobRunError
from src.domain.ports.matrix_selection import MatrixSelectionPort
from src.infrastructure.google_sheets.adapters.get_matrices import GetAllMatricesAdapter
from src.infrastructure.google_sheets.adapters.get_products import GetAllProductsAdapter
from src.infrastructure.google_sheets.client import GoogleSheetsAPIClient
from src.infrastructure.kit_vending.adapters.apply_matrix_to_vending_machine import (
    ApplyMatrixToVendingMachineAdapter,
)
from src.infrastructure.kit_vending.adapters.bind_matrix_to_machine import BindMatrixToVendingMachineAdapter
from src.infrastructure.kit_vending.adapters.download_matrix_to_vending_machine import (
    DownloadMatrixToVendingMachineAdapter,
)
from src.infrastructure.kit_vending.adapters.get_vending_machines import GetVendingMachinesAdapter
from src.infrastructure.kit_vending.adapters.upload_matrix import UploadMatrixAdapter
from src.infrastructure.kit_vending.api.account import KitAPIAccount
from src.infrastructure.kit_vending.api.client import KitVendingAPIClient
from src.infrastructure.persistence.in_memory.job_run_repository import InMemoryJobRunRepository
from src.infrastructure.persistence.in_memory.matrix_repository import InMemoryMatrixRepository
from src.infrastructure.persistence.in_memory.product_repository import InMemoryProductRepository
from src.infrastructure.persistence.in_memory.vending_machine_repository import InMemoryVendingMachineRepository
from src.infrastructure.selection.configured_selection import ConfiguredMatrixSelection
from src.infrastructure.selection.interactive_selection import InteractiveMatrixSelection
from src.infrastructure.selection.interactive_selector import InteractiveSelector


class Container:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._matrix_selection: MatrixSelectionPort | None = None
        self._kit_client: KitVendingAPIClient | None = None

        self.product_repository = InMemoryProductRepository()
        self.matrix_repository = InMemoryMatrixRepository()
        self.vending_machine_repository = InMemoryVendingMachineRepository()
        self.job_run_repository = InMemoryJobRunRepository()

        self._sync_all: SyncAllCachesUseCase | None = None
        self._deploy_matrices: DeployMatricesUseCase | None = None

    async def __aenter__(self) -> Container:
        kit_config = self._settings.to_kit_api_config()
        account = KitAPIAccount(
            login=kit_config.login,
            password=kit_config.password,
            company_id=kit_config.company_id,
        )
        self._kit_client = KitVendingAPIClient(account=account, config=kit_config)
        await self._kit_client.__aenter__()

        if self._settings.google_application_credentials:
            sa = gspread.service_account(filename=self._settings.google_application_credentials)
        else:
            sa = gspread.service_account()
        spreadsheet = sa.open_by_key(self._settings.google_sheets_matrix_table_id)
        google_client = GoogleSheetsAPIClient(spreadsheet=spreadsheet)

        get_products = GetAllProductsAdapter(google_table_api_client=google_client)
        get_matrices = GetAllMatricesAdapter(
            google_table_api_client=google_client,
            product_repository=self.product_repository,
        )
        get_vending_machines = GetVendingMachinesAdapter(kit_api_client=self._kit_client)

        upload_matrix = UploadMatrixAdapter(kit_api_client=self._kit_client)
        bind_matrix = BindMatrixToVendingMachineAdapter(kit_api_client=self._kit_client)
        download_matrix = DownloadMatrixToVendingMachineAdapter(
            kit_api_client=self._kit_client,
            matrix_load_timeout=self._settings.matrix_load_timeout,
        )
        apply_matrix = ApplyMatrixToVendingMachineAdapter(
            kit_api_client=self._kit_client,
            matrix_apply_timeout=self._settings.matrix_apply_timeout,
        )

        upload_and_apply = UploadAndApplyMatrixUseCase(
            upload_matrix_port=upload_matrix,
            bind_matrix_to_machine_port=bind_matrix,
            download_matrix_to_machine_port=download_matrix,
            apply_matrix_to_machine_port=apply_matrix,
            validate_matrices=self._settings.validate_matrices,
        )

        self._deploy_matrices = DeployMatricesUseCase(
            matrix_repository=self.matrix_repository,
            vending_machine_repository=self.vending_machine_repository,
            upload_and_apply_matrix_uc=upload_and_apply,
        )

        self._sync_all = SyncAllCachesUseCase(
            sync_products=SyncProductsCache(
                get_products=get_products,
                product_repository=self.product_repository,
            ),
            sync_vending_machines=SyncVendingMachinesCache(
                get_vending_machines=get_vending_machines,
                vending_machine_repository=self.vending_machine_repository,
            ),
            sync_matrices=SyncMatricesCache(
                get_all_matrices=get_matrices,
                matrix_repository=self.matrix_repository,
            ),
        )

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._kit_client is not None:
            await self._kit_client.close()

    def set_matrix_selection(self, selection: MatrixSelectionPort) -> None:
        self._matrix_selection = selection

    def configure_interactive_selection(self) -> None:
        self.set_matrix_selection(
            InteractiveMatrixSelection(interactive_selector=InteractiveSelector())
        )

    def configure_scheduled_selection(self, names: str) -> None:
        self.set_matrix_selection(ConfiguredMatrixSelection(names=names))

    def _require_matrix_selection(self) -> MatrixSelectionPort:
        if self._matrix_selection is None:
            raise JobRunError("MatrixSelectionPort не задан — вызовите set_matrix_selection()")
        return self._matrix_selection

    async def run_deployment(self, trigger: JobRunTrigger) -> JobRun:
        if self._sync_all is None or self._deploy_matrices is None:
            raise JobRunError("Container не инициализирован — используйте async with")

        run_deployment = RunDeploymentJobUseCase(
            job_run_repository=self.job_run_repository,
            sync_all_caches=self._sync_all,
            matrix_selection=self._require_matrix_selection(),
            matrix_repository=self.matrix_repository,
            deploy_matrices=self._deploy_matrices,
        )
        return await run_deployment.execute(trigger)

    async def sync_only(self) -> None:
        if self._sync_all is None:
            raise JobRunError("Container не инициализирован — используйте async with")
        await self._sync_all.execute()
