import asyncio
import os

import gspread
from dotenv import load_dotenv
from kit_api import KitVendingAPIClient
from kit_api.client import KitAPIAccount

from new_src.application.use_cases.select_and_upload_matrices import SelectAndUploadMatricesUseCase
from new_src.application.use_cases.sync.sync_matrices_cache import SyncMatricesCache
from new_src.application.use_cases.sync.sync_vending_machines_cache import SyncVendingMachinesCache
from new_src.application.use_cases.upload_machine_matrix import UploadAndApplyMatrixUseCase
from new_src.controllers.update_matrices_controller import SelectAndUpdateMatricesController
from new_src.domain.ports.apply_matrix_to_vending_machine import ApplyMatrixToVendingMachinePort
from new_src.domain.ports.bind_matrix_to_vending_machine import BindMatrixToVendingMachinePort
from new_src.domain.ports.download_matrix_to_vending_machine import DownloadMatrixToVendingMachinePort
from new_src.domain.ports.get_all_matrices import GetAllMatricesPort
from new_src.domain.ports.upload_machine_matrix import UploadMatrixPort
from new_src.infrastructure.adapters.google_sheets.get_matrix_data import GetAllMatricesAdapter
from new_src.infrastructure.adapters.kit_vending.apply_matrix_to_vending_machine import \
    ApplyMatrixToVendingMachineAdapter
from new_src.infrastructure.adapters.kit_vending.bind_matrix_to_machine import BindMatrixToVendingMachineAdapter
from new_src.infrastructure.adapters.kit_vending.download_matrix_to_vending_machine import \
    DownloadMatrixToVendingMachineAdapter
from new_src.infrastructure.adapters.kit_vending.upload_matrix import UploadMatrixAdapter
from new_src.infrastructure.interactive_matrices_selector import InteractiveSelector
from new_src.infrastructure.repositories.matrix_repository import InMemoryMatrixRepository
from new_src.infrastructure.repositories.vending_machine_repository import InMemoryVendingMachineRepository

load_dotenv()

kit_company_id = int(os.getenv("KIT_API_COMPANY_ID"))
kit_login = os.getenv("KIT_API_LOGIN")
kit_password = os.getenv("KIT_API_PASSWORD")


async def main():
    account = KitAPIAccount(
        login=kit_login,
        password=kit_password,
        company_id=kit_company_id
    )

    async with KitVendingAPIClient(account=account) as kit_api_client:
        table_id: str | None = os.getenv("GOOGLE_SHEETS_MATRIX_TABLE_ID")

        if table_id is None:
            raise Exception("Укажите Id таблицы в .env файле (GOOGLE_SHEETS_MATRIX_TABLE_ID=...).")

        spreadsheet = gspread.service_account().open_by_key(key=table_id)

        interactive_selector: InteractiveSelector = InteractiveSelector()

        get_all_matrices: GetAllMatricesPort = GetAllMatricesAdapter(
            spreadsheet=spreadsheet,
        )

        upload_matrix_port: UploadMatrixPort = UploadMatrixAdapter(
            kit_api_client=kit_api_client
        )

        bind_matrix_to_machine_port: BindMatrixToVendingMachinePort = BindMatrixToVendingMachineAdapter(
            kit_api_client=kit_api_client,
        )

        download_matrix_to_machine_port: DownloadMatrixToVendingMachinePort = DownloadMatrixToVendingMachineAdapter(
            kit_api_client=kit_api_client,
        )

        apply_matrix_to_machine_port: ApplyMatrixToVendingMachinePort = ApplyMatrixToVendingMachineAdapter(
            kit_api_client=kit_api_client,
        )

        vending_machine_repository = InMemoryVendingMachineRepository()
        matrix_repository = InMemoryMatrixRepository()

        sync_data_vending_machines_uc: SyncVendingMachinesCache = SyncVendingMachinesCache(
            vending_machine_repository=vending_machine_repository,
            kit_api_client=kit_api_client,
        )

        sync_matrices_cache_uc: SyncMatricesCache = SyncMatricesCache(
            get_all_matrices=get_all_matrices,
            matrix_repository=matrix_repository,
        )

        upload_and_apply_matrix_uc: UploadAndApplyMatrixUseCase = UploadAndApplyMatrixUseCase(
            upload_matrix_port=upload_matrix_port,
            bind_matrix_to_machine_port=bind_matrix_to_machine_port,
            download_matrix_to_machine_port=download_matrix_to_machine_port,
            apply_matrix_to_machine_port=apply_matrix_to_machine_port,
        )

        select_and_upload_matrices_uc: SelectAndUploadMatricesUseCase = SelectAndUploadMatricesUseCase(
            matrix_repository=matrix_repository,
            vending_machine_repository=vending_machine_repository,
            upload_and_apply_matrix_uc=upload_and_apply_matrix_uc,
        )

        controller = SelectAndUpdateMatricesController(
            matrix_repository=matrix_repository,
            interactive_selector=interactive_selector,
            select_and_upload_matrices_uc=select_and_upload_matrices_uc,
        )

        await sync_data_vending_machines_uc.execute()
        await sync_matrices_cache_uc.execute()
        await controller.run()
        pass


if __name__ == "__main__":
    asyncio.run(main())
