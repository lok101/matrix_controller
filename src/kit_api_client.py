import enum
import hashlib
import json
import os
import time
from abc import ABC, abstractmethod
from enum import IntEnum

import aiohttp
from typing import Any, Optional

from dotenv import load_dotenv

BASE_URL = "https://api2.kit-invest.ru/APIService.svc"


class Endpoints(enum.StrEnum):
    GET_GOODS = 'GetGoods'
    CREATE_MATRIX = 'CreatePiecesMatrix'


class ResultCodes(IntEnum):
    SUCCESS = 0


RESULT_CODE_KEY = 'ResultCode'


class KitAPIClient(ABC):
    @abstractmethod
    async def post_request(self, endpoint: Endpoints, payload: Optional[dict[str, Any]] = None) -> dict[str, Any]: pass


class KitAPIClientImpl(KitAPIClient):
    def __init__(self):
        self._set_from_env()
        self.request_counter = int(time.time_ns())

    async def post_request(self, endpoint: Endpoints, payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        if payload is None:
            payload = {}

        full_payload = {"Auth": self._build_auth()}
        full_payload.update(payload)
        request = json.dumps(full_payload)

        async with aiohttp.ClientSession() as session:
            async with session.post(url=f"{BASE_URL}/{endpoint}", data=request) as response:
                response.raise_for_status()
                data = await response.json()
                result_code = data[RESULT_CODE_KEY]

                if result_code != ResultCodes.SUCCESS:
                    raise Exception(f'Не удалось получить данные от Kit API, код ответа - {result_code}')

                return data

    def _set_from_env(self):
        load_dotenv()
        self._company_id = os.getenv("KIT_API_COMPANY_ID")
        self._user_login = os.getenv("KIT_API_LOGIN")
        self._password = os.getenv("KIT_API_PASSWORD")

    def _generate_request_id(self) -> int:
        self.request_counter += 1
        return self.request_counter

    def _build_auth(self) -> dict[str, Any]:
        request_id = self._generate_request_id()
        sign = hashlib.md5(f"{self._company_id}{self._password}{request_id}".encode("utf-8")).hexdigest()
        return {
            "CompanyId": self._company_id,
            "RequestId": request_id,
            "UserLogin": self._user_login,
            "Sign": sign,
        }
