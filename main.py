import asyncio
import os

from dotenv import load_dotenv

from src.application.update_multiple_matrices_case import UpdateMultipleMatricesUseCase
from src.application.update_snack_matrix_case import UpdateSnackMatrixUseCase
from src.application.user_select_matrices_use_case import GetMatricesWithSelectionUseCase
from src.controllers.update_snacks_matrices import UpdateSnackMatricesController

from src.infrastructure.ex_api.gspread_api_client import GspreadAPIClient
from src.infrastructure.ex_api.kit_api_client import KitVendingAPI
from src.infrastructure.ex_api.timestamp_api import TimestampAPI
from src.infrastructure.interactive_matrices_selector import ColorfulInteractiveSelector
from src.infrastructure.repositories.matrix_repository import InMemoryMatrixRepository
from src.infrastructure.repositories.product_repository import InMemoryProductRepository
from src.infrastructure.repositories.vending_machine_repository import InMemoryVendingMachineRepository

from src.infrastructure.services.kit_vendor_matrix_gateway import KitVendorMatrixGateway
from src.infrastructure.services.sync_data_service import SyncDataService

load_dotenv()


async def main():
    kit_company_id = os.getenv("KIT_API_COMPANY_ID")
    kit_login = os.getenv("KIT_API_LOGIN")
    kit_password = os.getenv("KIT_API_PASSWORD")

    timestamp_api = TimestampAPI()

    gspread_api_client = GspreadAPIClient()
    kit_api_client = KitVendingAPI(
        login=kit_login,
        password=kit_password,
        company_id=kit_company_id,
        timestamp_provider=timestamp_api
    )

    selector = ColorfulInteractiveSelector()

    product_repo = InMemoryProductRepository()
    matrix_repo = InMemoryMatrixRepository()
    vending_machine_repo = InMemoryVendingMachineRepository()

    vendor_matrix_gateway = KitVendorMatrixGateway(api_client=kit_api_client)

    get_matrices_uc = GetMatricesWithSelectionUseCase(selector=selector, matrix_repo=matrix_repo)
    update_matrix_uc = UpdateSnackMatrixUseCase(
        vending_machine_repo=vending_machine_repo,
        vendor_matrix_gateway=vendor_matrix_gateway,
    )
    update_matrices_uc = UpdateMultipleMatricesUseCase(
        update_matrix_uc=update_matrix_uc,
        matrix_repo=matrix_repo
    )

    update_matrices_controller = UpdateSnackMatricesController(
        update_multiple_matrices_uc=update_matrices_uc,
        select_matrices_use_case=get_matrices_uc,

    )

    sync_service = SyncDataService(
        vending_machine_repo=vending_machine_repo,
        product_repo=product_repo,
        gs_api_client=gspread_api_client,
        kit_api_client=kit_api_client,
        matrix_repo=matrix_repo
    )

    sync_service.sync_all_data()
    result = await update_matrices_controller.execute()
    print(result)
    pass


if __name__ == "__main__":
    asyncio.run(main())
