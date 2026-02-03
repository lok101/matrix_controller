import hashlib
import json
from enum import IntEnum
from typing import Mapping, Any

import aiohttp
import requests

from src.application.dto.create_vending_machine_dto import CreateVendingMachineDTO
from src.domain.entities.matrix import MatrixCell
from src.infrastructure.ex_api.models.vending_machine import VendingMachinesCollection
from src.infrastructure.ex_api.timestamp_api import TimestampAPI
from src.infrastructure.rate_limiter import rate_limit


class ResultCodes(IntEnum):
    SUCCESS = 0
    TOO_MANY_REQUEST = 27


class APILimitError(Exception):
    pass


@rate_limit(1, 15)
class KitVendingAPI:
    def __init__(self, login: str, password: str, company_id: str, timestamp_provider: TimestampAPI):
        self._timestamp_provider = timestamp_provider
        self._login = login
        self._password = password
        self._company_id = int(company_id)
        self._base_url = "https://api2.kit-invest.ru/APIService.svc"

    async def create_matrix(self, matrix_positions: list[MatrixCell], matrix_name: str) -> int:
        request_id = await self._timestamp_provider.async_get_now()
        url = f"{self._base_url}/CreatePiecesMatrix"
        auth = self._build_auth(request_id)

        request_data = {
            "Auth": auth,
            "MatrixName": matrix_name,
            "Positions": [
                {
                    'LineNumber': item.line_number,
                    'ChoiceNumber': item.line_number,
                    'GoodsName': item.product_full_name,
                    'Price2': item.price,
                    'Price': item.price,
                    'MaxCount': item.product_capacity,
                } for item in matrix_positions
            ]
        }
        response = await self._async_send_post_request(url, request_data)
        return int(response["Id"])

    async def bound_matrix_to_machine(self, matrix_id: int, machine_id: int):
        request_id = await self._timestamp_provider.async_get_now()
        url = f"{self._base_url}/ApplyMatrix"
        auth = self._build_auth(request_id)

        request_data = {
            "Auth": auth,
            "MatrixId": matrix_id,
            "VendingMachineId": machine_id

        }
        await self._async_send_post_request(url, request_data)

    async def apply_matrix(self, machine_id: int):
        request_id = await self._timestamp_provider.async_get_now()
        url = f"{self._base_url}/SendCommand"
        auth = self._build_auth(request_id)

        request_data = {
            "Auth": auth,
            "Command": {
                "CommandCode": 4,
                "VendingMachineId": machine_id,
            }
        }
        await self._async_send_post_request(url, request_data)

    async def load_matrix(self, machine_id: int):
        request_id = await self._timestamp_provider.async_get_now()
        url = f"{self._base_url}/SendCommand"
        auth = self._build_auth(request_id)

        request_data = {
            "Auth": auth,
            "Command": {
                "CommandCode": 3,
                "VendingMachineId": machine_id,
            }
        }
        await self._async_send_post_request(url, request_data)

    def get_vending_machines(self) -> list[CreateVendingMachineDTO]:
        request_id = self._timestamp_provider.get_now()
        url = f"{self._base_url}/GetVendingMachines"
        auth = self._build_auth(request_id)

        request_data = {
            "Auth": auth,
        }
        response = self._send_post_request(url, request_data)
        collection = VendingMachinesCollection.model_validate(response)

        return collection.as_dtos()

    def _build_auth(self, request_id: int) -> dict[str, Any]:
        sign = hashlib.md5(f"{self._company_id}{self._password}{request_id}".encode("utf-8")).hexdigest()
        return {
            "CompanyId": self._company_id,
            "RequestId": request_id,
            "UserLogin": self._login,
            "Sign": sign,
        }

    @staticmethod
    async def _async_send_post_request(url: str, data: Mapping) -> Mapping:

        try:

            async with aiohttp.ClientSession() as session:
                async with session.post(url=url, data=json.dumps(data)) as response:
                    response.raise_for_status()
                    response_data = await response.json()
                    result_code = response_data['ResultCode']

                    if result_code == ResultCodes.TOO_MANY_REQUEST:
                        raise APILimitError("Лимит запросов превышен.")

                    if result_code != ResultCodes.SUCCESS:
                        message = response_data["ErrorMessage"]
                        raise Exception(
                            f'Не удалось получить данные от Kit API, код ответа - {result_code}, текст ошибки: {message}')

                    return response_data

        except aiohttp.ClientError as e:
            print(f"Ошибка сети: {e}")

    @staticmethod
    def _send_post_request(url: str, data: Mapping) -> Mapping:
        response = requests.post(url, data=json.dumps(data))
        response_data = response.json()
        result_code = response_data['ResultCode']

        if result_code != ResultCodes.SUCCESS:
            message = response_data["ErrorMessage"]
            raise Exception(
                f'Не удалось получить данные от Kit API, код ответа - {result_code}, текст ошибки: {message}')

        return response_data
