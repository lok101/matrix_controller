from src.domain.services.matrix_data_provider import MatrixDataProvider, MatrixData
from src.infrastructure.ex_api.gspread_api_client import GspreadAPIClient


class GspreadMatrixDataSProvider(MatrixDataProvider):

    def __init__(self, api_client: GspreadAPIClient):
        self._api_client = api_client

    def get_by_name(self, matrix_name_range: str) -> MatrixData:
        cells_data = self._api_client.get_snack_cells(matrix_name_range)
        machine_model = self._api_client.get_machine_model(matrix_name_range)
        machine_ids = self._api_client.get_machine_ids(matrix_name_range)

        return MatrixData(
            cells=cells_data,
            machine_model=machine_model,
            machine_ids=machine_ids
        )
