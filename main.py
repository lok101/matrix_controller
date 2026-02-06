import asyncio
import os

import gspread
from dotenv import load_dotenv
from kit_api import KitVendingAPIClient
from kit_api.client import KitAPIAccount

from src.application.repositories.product_repository import ProductRepository
from src.application.use_cases.select_and_upload_matrices import SelectAndUploadMatricesUseCase
from src.application.use_cases.sync.sync_matrices_cache import SyncMatricesCache
from src.application.use_cases.sync.sync_products_cache import SyncProductsCache
from src.application.use_cases.sync.sync_vending_machines_cache import SyncVendingMachinesCache
from src.application.use_cases.upload_machine_matrix import UploadAndApplyMatrixUseCase
from src.controllers.update_matrices_controller import SelectAndUpdateMatricesController
from src.domain.ports.apply_matrix_to_vending_machine import ApplyMatrixToVendingMachinePort
from src.domain.ports.bind_matrix_to_vending_machine import BindMatrixToVendingMachinePort
from src.domain.ports.download_matrix_to_vending_machine import DownloadMatrixToVendingMachinePort
from src.domain.ports.get_matrices import GetAllMatricesPort
from src.domain.ports.get_products import GetAllProductsPort
from src.domain.ports.upload_machine_matrix import UploadMatrixPort
from src.infrastructure.adapters.google_sheets.get_matrices import GetAllMatricesAdapter
from src.infrastructure.adapters.google_sheets.get_products import GetAllProductsAdapter
from src.infrastructure.adapters.kit_vending.apply_matrix_to_vending_machine import \
    ApplyMatrixToVendingMachineAdapter
from src.infrastructure.adapters.kit_vending.bind_matrix_to_machine import BindMatrixToVendingMachineAdapter
from src.infrastructure.adapters.kit_vending.download_matrix_to_vending_machine import \
    DownloadMatrixToVendingMachineAdapter
from src.infrastructure.adapters.kit_vending.upload_matrix import UploadMatrixAdapter
from src.infrastructure.google_sheets_api_client import GoogleSheetsAPIClient
from src.infrastructure.interactive_matrices_selector import InteractiveSelector
from src.infrastructure.repositories.matrix_repository import InMemoryMatrixRepository
from src.infrastructure.repositories.product_repository import InMemoryProductRepository
from src.infrastructure.repositories.vending_machine_repository import InMemoryVendingMachineRepository

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
        google_table_api_client: GoogleSheetsAPIClient = GoogleSheetsAPIClient(spreadsheet=spreadsheet)

        interactive_selector: InteractiveSelector = InteractiveSelector()

        product_repository: ProductRepository = InMemoryProductRepository()

        get_all_matrices: GetAllMatricesPort = GetAllMatricesAdapter(
            google_table_api_client=google_table_api_client,
            product_repository=product_repository,
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

        get_products_port: GetAllProductsPort = GetAllProductsAdapter(
            google_table_api_client=google_table_api_client
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

        sync_products_cache_uc: SyncProductsCache = SyncProductsCache(
            get_products=get_products_port,
            product_repository=product_repository,
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
        sync_products_cache_uc.execute()
        await sync_data_vending_machines_uc.execute()
        await sync_matrices_cache_uc.execute()

        await controller.run()
        pass


if __name__ == "__main__":
    asyncio.run(main())
