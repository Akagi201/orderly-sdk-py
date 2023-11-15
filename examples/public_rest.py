import logging
from asyncio import run

from configs import *

from orderly_sdk.rest import AsyncClient

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


async def main():
    orderly_client = AsyncClient(
        account_id=ACCOUNT_ID,
        endpoint=REST_ENDPOINT,
    )

    info = await orderly_client.get_maintenance_info()
    logger.info(info)
    await orderly_client.close_connection()


run(main(), debug=True)
