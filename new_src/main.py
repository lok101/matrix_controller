import os

import aiohttp
import gspread
from kit_api import KitVendingAPIClient

from new_src.app.use_cases.upload_machine_matrix import UploadAndApplyMatrixUseCase
from new_src.controllers.update_matrices_controller import SelectAndUpdateMatricesController
from new_src.domain.ports.get_all_matrices import GetAllMatricesPort
from new_src.domain.ports.upload_machine_matrix import UploadMatrixPort
from new_src.domain.repositories.vending_machine_repository import VendingMachineRepository
from new_src.infrastructure.adapters.google_sheets.get_matrix_data import GetAllMatricesAdapter
from new_src.infrastructure.adapters.kit_vending.upload_matrix import UploadMatrixAdapter
from new_src.infrastructure.interactive_matrices_selector import InteractiveSelector


async def main():
    async with aiohttp.ClientSession() as session:
        table_id: str | None = os.getenv("GOOGLE_SHEETS_MATRIX_TABLE_ID")

        if table_id is None:
            raise Exception("Укажите Id таблицы в .env файле (GOOGLE_SHEETS_MATRIX_TABLE_ID=...).")

        spreadsheet = gspread.service_account().open_by_key(key=table_id)

        kit_api_client = KitVendingAPIClient(session=session)

        interactive_selector: InteractiveSelector = InteractiveSelector()

        get_all_matrices: GetAllMatricesPort = GetAllMatricesAdapter(
            spreadsheet=spreadsheet,
        )

        upload_matrix_port: UploadMatrixPort = UploadMatrixAdapter(
            kit_api_client=kit_api_client
        )

        vending_machine_repository: VendingMachineRepository = ...

        upload_and_apply_matrix_uc: UploadAndApplyMatrixUseCase = UploadAndApplyMatrixUseCase(
            upload_matrix_port=upload_matrix_port
        )

        controller = SelectAndUpdateMatricesController(
            get_all_matrices=get_all_matrices,
            interactive_selector=interactive_selector,
            vending_machine_repository=vending_machine_repository,
            upload_and_apply_matrix_uc=upload_and_apply_matrix_uc,
        )
