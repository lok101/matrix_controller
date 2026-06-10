from __future__ import annotations

import asyncio
import json
from typing import Any

import aiohttp
from aiohttp import ClientError as AioHTTPClientError, ContentTypeError

from src.infrastructure.kit_vending.api.exceptions import KitAPIError, KitAPINetworkError


class TimestampAPI:
    """Класс для получения текущего timestamp с внешнего сервиса."""

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url: str = (
            base_url
            or "https://smartapp-code.sberdevices.ru/tools/api/now?tz=Europe/Moscow&format=dd/MM/yyyy"
        )

    async def async_get_now(self) -> int:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url=self._base_url) as response:
                    response.raise_for_status()
                    try:
                        data: dict[str, Any] = await response.json()
                    except (ContentTypeError, json.JSONDecodeError) as exc:
                        raise KitAPIError(
                            f"Не удалось разобрать JSON ответ от timestamp API: {exc}"
                        ) from exc

                    try:
                        return data["timestamp"]
                    except KeyError:
                        raise KitAPIError(
                            f"Ответ timestamp API не содержит поле 'timestamp'. Данные: {data}"
                        )
        except AioHTTPClientError as exc:
            raise KitAPINetworkError(f"Ошибка сети при получении timestamp: {exc}") from exc

    def get_now(self) -> int:
        return asyncio.run(self.async_get_now())
