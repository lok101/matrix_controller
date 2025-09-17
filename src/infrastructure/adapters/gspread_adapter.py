from typing import Mapping

from src.infrastructure.external_clients.gspread_client import GspreadClient
from src.ports import GspreadPort


class GspreadAdapter(GspreadPort):

    def __init__(self, gspread_client: GspreadClient):
        self._client = gspread_client

    def get_all_goods(self) -> list[Mapping]:
        return self._client.get_all_goods_data()

    def get_matrix_goods(self, range_name: str) -> list[list[int, str, int, int]]:
        return self._client.fetch_data(range_name)
