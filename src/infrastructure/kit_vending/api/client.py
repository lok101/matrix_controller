from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

import aiohttp
from aiohttp import ClientError as AioHTTPClientError, ContentTypeError
from beartype import beartype

from src.infrastructure.kit_vending.api.account import KitAPIAccount
from src.infrastructure.kit_vending.api.config import KitAPIConfig
from src.infrastructure.kit_vending.api.enums import ResultCode, VendingMachineCommand
from src.infrastructure.kit_vending.api.exceptions import (
    KitAPIAuthError,
    KitAPIError,
    KitAPINetworkError,
    KitAPIResponseError,
)
from src.infrastructure.kit_vending.api.models.vending_machine_state import VendingMachinesStatesCollection
from src.infrastructure.kit_vending.api.models.vending_machines import VendingMachinesCollection
from src.infrastructure.kit_vending.api.rate_limiter import GlobalBackoff, RateLimiter


class KitVendingAPIClient:
    @beartype
    def __init__(
        self,
        account: KitAPIAccount,
        config: KitAPIConfig,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self._base_url = "https://api2.kit-invest.ru/APIService.svc"
        self._session = session
        self._own_session = session is None
        self._backoff = GlobalBackoff(timeout=config.backoff_seconds)
        self._limiter = RateLimiter(config.request_per_window, config.window_seconds)

        self._login: str = account.login
        self._password: str = account.password
        self._company_id: int = account.company_id

    @beartype
    async def get_vending_machines(
        self,
        account: KitAPIAccount | None = None,
    ) -> VendingMachinesCollection:
        url = f"{self._base_url}/GetVendingMachines"

        async def build_data() -> dict[str, Any]:
            request_id = time.time_ns()
            return {"Auth": self._build_auth(request_id, account)}

        response = await self._async_send_post_request(url, build_data)
        return VendingMachinesCollection.model_validate(response)

    @beartype
    async def get_vending_machine_states(
        self,
        account: KitAPIAccount | None = None,
    ) -> VendingMachinesStatesCollection:
        url = f"{self._base_url}/GetVMStates"

        async def build_data() -> dict[str, Any]:
            request_id = time.time_ns()
            return {"Auth": self._build_auth(request_id, account)}

        response = await self._async_send_post_request(url, build_data)
        return VendingMachinesStatesCollection.model_validate(response)

    @beartype
    async def create_matrix(
        self,
        positions: list[dict[str, Any]],
        matrix_name: str,
        account: KitAPIAccount | None = None,
    ) -> int:
        url = f"{self._base_url}/CreatePiecesMatrix"

        async def build_data() -> dict[str, Any]:
            request_id = time.time_ns()
            return {
                "Auth": self._build_auth(request_id, account),
                "MatrixName": matrix_name,
                "Positions": [
                    {
                        "LineNumber": position["line_number"],
                        "ChoiceNumber": position["line_number"],
                        "GoodsName": position["product_name"],
                        "Price2": position["price"],
                        "Price": position["price"],
                    }
                    for position in positions
                ],
            }

        response = await self._async_send_post_request(url, build_data)
        return int(response["Id"])

    @beartype
    async def bound_matrix_to_vending_machine(
        self,
        matrix_id: int,
        machine_id: int,
        account: KitAPIAccount | None = None,
    ) -> ResultCode:
        url = f"{self._base_url}/ApplyMatrix"

        async def build_data() -> dict[str, Any]:
            request_id = time.time_ns()
            return {
                "Auth": self._build_auth(request_id, account),
                "MatrixId": matrix_id,
                "VendingMachineId": machine_id,
            }

        response = await self._async_send_post_request(url, build_data)
        return ResultCode(response["ResultCode"])

    @beartype
    async def send_command_to_vending_machine(
        self,
        machine_id: int,
        command: VendingMachineCommand,
        account: KitAPIAccount | None = None,
    ) -> ResultCode:
        url = f"{self._base_url}/SendCommand"

        async def build_data() -> dict[str, Any]:
            request_id = time.time_ns()
            return {
                "Auth": self._build_auth(request_id, account),
                "Command": {
                    "CommandCode": command.value,
                    "VendingMachineId": machine_id,
                },
            }

        response = await self._async_send_post_request(url, build_data)
        return ResultCode(response["ResultCode"])

    def is_authenticated(self) -> bool:
        return self._login is not None and self._password is not None and self._company_id is not None

    def _build_auth(self, request_id: int, account: KitAPIAccount | None) -> dict[str, Any]:
        if not self.is_authenticated() and account is None:
            raise KitAPIAuthError(
                "Учётные данные не установлены. Передайте данные в конструктор клиента "
                "или в аргументах метода в виде аккаунта."
            )

        if account is not None:
            login = account.login
            password = account.password
            company_id = account.company_id
        else:
            login = self._login
            password = self._password
            company_id = self._company_id

        sign = hashlib.md5(f"{company_id}{password}{request_id}".encode("utf-8")).hexdigest()
        return {
            "CompanyId": company_id,
            "RequestId": request_id,
            "UserLogin": login,
            "Sign": sign,
        }

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            self._own_session = True
        return self._session

    async def _async_send_post_request(
        self,
        url: str,
        build_data: Callable[[], Awaitable[Mapping[str, Any]]],
    ) -> Mapping[str, Any]:
        max_retries = 2

        for attempt in range(max_retries):
            await self._backoff.wait_if_blocked()
            await self._limiter.wait()

            data = await build_data()
            session = await self._get_session()

            try:
                async with session.post(url=url, data=json.dumps(data)) as response:
                    response.raise_for_status()

                    try:
                        response_data = await response.json()
                    except (ContentTypeError, json.JSONDecodeError) as exc:
                        raise KitAPIResponseError(
                            f"Не удалось разобрать JSON ответ от API: {exc}",
                            result_code=-1,
                        )

                    try:
                        result_code = response_data["ResultCode"]
                    except KeyError:
                        raise KitAPIResponseError(
                            "Ответ API не содержит поле ResultCode",
                            result_code=-1,
                        )

                    if result_code == ResultCode.TOO_MANY_REQUEST:
                        if attempt < max_retries - 1:
                            await self._backoff.trigger_backoff()
                            continue
                        raise KitAPIResponseError(
                            f"Превышен лимит запросов к API после {max_retries} попыток",
                            result_code=result_code,
                        )

                    if result_code != ResultCode.SUCCESS:
                        message = response_data.get("ErrorMessage", "Неизвестная ошибка")
                        raise KitAPIResponseError(
                            f"Не удалось получить данные от Kit API, код ответа - {result_code}, "
                            f"текст ошибки: {message}",
                            result_code=result_code,
                        )

                    return response_data

            except AioHTTPClientError as exc:
                raise KitAPINetworkError(f"Ошибка сети: {exc}") from exc
            except KitAPIResponseError:
                raise
            except Exception as exc:
                raise KitAPIError(f"Неожиданная ошибка при выполнении запроса: {exc}") from exc

        raise KitAPIError("Неожиданное завершение цикла retry")

    async def close(self) -> None:
        if self._session and not self._session.closed and self._own_session:
            await self._session.close()
            self._session = None

    async def __aenter__(self) -> KitVendingAPIClient:
        return self

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        await self.close()
