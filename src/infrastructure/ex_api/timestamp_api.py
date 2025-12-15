import aiohttp
import requests


class TimestampAPI:
    def __init__(self):
        self._base_url = "https://smartapp-code.sberdevices.ru/tools/api/now?tz=Europe/Moscow&format=dd/MM/yyyy"

    async def async_get_now(self) -> int:
        async with aiohttp.ClientSession() as session:
            async with session.get(url=self._base_url) as response:
                response.raise_for_status()
                data = await response.json()
                return data['timestamp']

    def get_now(self) -> int:
        response = requests.get(url=self._base_url)
        data = response.json()
        return data['timestamp']
