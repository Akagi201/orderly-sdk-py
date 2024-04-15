from asyncio import run

from configs import *

from orderly_sdk.log import logger
from orderly_sdk.rest import AsyncClient


async def main():
    orderly_client = AsyncClient(
        account_id=ACCOUNT_ID,
        endpoint=REST_ENDPOINT,
    )

    info = await orderly_client.get_maintenance_info()
    logger.info(info)

    liquidation = await orderly_client.get_liquidation(params=None)
    logger.info(liquidation)

    await orderly_client.close_connection()


run(main(), debug=True)
