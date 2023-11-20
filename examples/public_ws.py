import logging
from asyncio import run

from configs import *
from orderly_sdk.ws import OrderlyPublicWsManager

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


async def main():
    orderly_ws_client = OrderlyPublicWsManager(
        account_id=ACCOUNT_ID,
        endpoint=WS_PUBLIC_ENDPOINT,
    )
    orderly_ws_client.subscribe("bbos")
    orderly_ws_client.start()
    while True:
        res = await orderly_ws_client.recv("bbos")
        logger.info("bbos: %s", res)


run(main(), debug=True)
