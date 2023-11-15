import logging
from asyncio import run

from configs import *

from orderly_sdk.rest import AsyncClient
from orderly_sdk.ws import OrderlyPrivateWsManager

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


async def main():
    orderly_client = AsyncClient(
        account_id=ACCOUNT_ID,
        orderly_key=ORDERLY_KEY,
        orderly_secret=ORDERLY_SECRET,
        endpoint=REST_ENDPOINT,
    )

    info = await orderly_client.get_maintenance_info()
    logger.info(info)
    stats = await orderly_client.get_user_statistics()
    logger.info(stats)
    await orderly_client.close_connection()

    # orderly_ws_client = OrderlyPublicWsManager(
    #     account_id=ACCOUNT_ID,
    #     endpoint=WS_PUBLIC_ENDPOINT,
    # )
    # await orderly_ws_client.subscribe("bbos")
    # orderly_ws_client.start()
    # while True:
    #     res = await orderly_ws_client.recv("bbos")
    #     logger.info("bbos: %s", res)

    orderly_private_ws_client = OrderlyPrivateWsManager(
        account_id=ACCOUNT_ID,
        orderly_key=ORDERLY_KEY,
        orderly_secret=ORDERLY_SECRET,
        endpoint=WS_PRIVATE_ENDPOINT,
    )
    await orderly_private_ws_client.subscribe("position")
    orderly_private_ws_client.start()
    while True:
        res = await orderly_private_ws_client.recv("position")
        logger.info("balance: %s", res)


run(main(), debug=True)
