import logging
from asyncio import run

from configs import *
from orderly_sdk.ws import OrderlyPrivateWsManager

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


async def main():
    orderly_private_ws_client = OrderlyPrivateWsManager(
        account_id=ACCOUNT_ID,
        orderly_key=ORDERLY_KEY,
        orderly_secret=ORDERLY_SECRET,
        endpoint=WS_PRIVATE_ENDPOINT,
    )
    orderly_private_ws_client.subscribe("position")
    orderly_private_ws_client.start()
    while True:
        res = await orderly_private_ws_client.recv("position")
        logger.info("position: %s", res)


run(main(), debug=True)
