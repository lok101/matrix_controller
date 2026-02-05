import asyncio
import os

import gspread
from dotenv import load_dotenv
from kit_api import KitVendingAPIClient

from new_src.application.use_cases.sync.sync_vending_machines_cache import SyncVendingMachinesCache
from new_src.application.use_cases.upload_machine_matrix import UploadAndApplyMatrixUseCase
from new_src.controllers.update_matrices_controller import SelectAndUpdateMatricesController
from new_src.domain.ports.get_all_matrices import GetAllMatricesPort
from new_src.domain.ports.upload_machine_matrix import UploadMatrixPort
from new_src.infrastructure.adapters.google_sheets.get_matrix_data import GetAllMatricesAdapter
from new_src.infrastructure.adapters.kit_vending.upload_matrix import UploadMatrixAdapter
from new_src.infrastructure.interactive_matrices_selector import InteractiveSelector
from new_src.infrastructure.repositories.vending_machine_repository import InMemoryVendingMachineRepository

load_dotenv()

kit_company_id = os.getenv("KIT_API_COMPANY_ID")
kit_login = os.getenv("KIT_API_LOGIN")
kit_password = os.getenv("KIT_API_PASSWORD")


async def main():
    async with KitVendingAPIClient(login=kit_login, password=kit_password, company_id=kit_company_id) as kit_api_client:
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

        vending_machine_repository = InMemoryVendingMachineRepository()

        sync_data_vending_machines_uc: SyncVendingMachinesCache = SyncVendingMachinesCache(
            vending_machine_repository=vending_machine_repository,
            kit_api_client=kit_api_client,
        )

        upload_and_apply_matrix_uc: UploadAndApplyMatrixUseCase = UploadAndApplyMatrixUseCase(
            upload_matrix_port=upload_matrix_port
        )

        controller = SelectAndUpdateMatricesController(
            get_all_matrices=get_all_matrices,
            interactive_selector=interactive_selector,
            vending_machine_repository=vending_machine_repository,
            upload_and_apply_matrix_uc=upload_and_apply_matrix_uc,
        )

        await sync_data_vending_machines_uc.execute()
        await controller.run()
        pass



if __name__ == "__main__":
    asyncio.run(main())
