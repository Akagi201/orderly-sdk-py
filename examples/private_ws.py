from asyncio import run

from configs import *

from orderly_sdk.log import logger
from orderly_sdk.ws import OrderlyPrivateWsManager


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
        logger.info("position: {}", res)


run(main(), debug=True)
