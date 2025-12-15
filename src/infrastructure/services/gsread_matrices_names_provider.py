#
# from src.infrastructure.ex_api.gspread_api_client import GspreadAPIClient
#
#
# class GspreadMatricesNamesProvider(MatricesNamesProvider):
#     def __init__(self, gspread_api_client: GspreadAPIClient):
#         self._gspread_api_client = gspread_api_client
#
#     async def get_all(self) -> list[str]:
#         return await self._gspread_api_client.get_matrices_names()
