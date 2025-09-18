import asyncio

from src.external_clients.kit_api_client import KitAPIClientImpl, Endpoints

client = KitAPIClientImpl()


async def main():
    res = await client.post_request(endpoint=Endpoints.GET_GOODS)
    pass


asyncio.run(main())
