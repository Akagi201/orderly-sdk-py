from asyncio import run

from configs import *
from orderly_sdk.log import logger
from orderly_sdk.rest import AsyncClient


async def main():
    orderly_client = AsyncClient(
        account_id=ACCOUNT_ID,
        orderly_key=ORDERLY_KEY,
        orderly_secret=ORDERLY_SECRET,
        endpoint=REST_ENDPOINT,
    )
    stats = await orderly_client.get_user_statistics()
    logger.info(stats)
    await orderly_client.close_connection()


run(main(), debug=True)
