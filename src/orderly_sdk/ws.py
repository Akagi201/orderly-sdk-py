import asyncio
import base64
import datetime
import json as jsonlib
import logging
from collections import defaultdict
from typing import DefaultDict, Dict, Optional

import base58
import websockets
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from websockets import WebSocketClientProtocol

from .helpers import get_loop

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


class WsTopicManager:
    endpoint: str
    queues: DefaultDict[str, asyncio.Queue]
    websocket: WebSocketClientProtocol

    def __init__(
        self,
        _id="WS_PUBLIC",
        account_id="",
        endpoint="",
        loop=None,
    ):
        self._id = _id
        self.account_id = account_id
        self.endpoint = endpoint + self.account_id
        self.loop = loop or get_loop()
        # topic -> topic event queue
        self.queues: DefaultDict[str, asyncio.Queue] = defaultdict(asyncio.Queue)

    async def _connect(
        self,
        timeout: Optional[int | float] = None,
        **kwargs,
    ):
        async for websocket in websockets.connect(self.endpoint, **kwargs):
            try:
                self.websocket = websocket
                await self._reconnect()
                logger.debug(f"Connected to {self.endpoint}")
                while True:
                    try:
                        message = await asyncio.wait_for(
                            websocket.recv(), timeout=timeout
                        )
                        await self._handle_heartbeat(message)
                        # asyncio.create_task(self._handle_message(message))
                        await self._handle_message(message)
                    except asyncio.TimeoutError:
                        logger.warning(f"Connection to {self.endpoint} timed out")
                        break
            except websockets.ConnectionClosed:
                logger.warning(f"Disconnected from {self.endpoint}")
            except Exception as e:
                logger.exception(e)

    def start(self, timeout: Optional[int | float] = None, **kwargs):
        self.loop.call_soon_threadsafe(
            asyncio.create_task, self._connect(timeout, **kwargs)
        )

    def subscribe(self, topic):
        self.queues[topic] = asyncio.Queue()

    async def do_subscribe(self, topic):
        await self.send_json({"id": self._id, "event": "subscribe", "topic": topic})

    async def request(self, symbol: str):
        params = {"params": {"type": "orderbook", "symbol": symbol}}
        await self.send_json({"id": self._id, "event": "request", **params})

    async def unsubscribe(self, topic):
        await self.websocket.send(
            jsonlib.dumps({"id": self._id, "event": "unsubscribe", "topic": topic})
        )
        self.queues.pop(topic)

    async def send_json(self, message):
        if "event" in message and message["event"] != "pong":
            logger.debug(f"sending message to {self.endpoint}: {message}")
        await self.websocket.send(jsonlib.dumps(message))

    async def _handle_heartbeat(self, message):
        message = jsonlib.loads(message)
        if "event" in message:
            if message["event"] == "ping":
                await self.send_json({"event": "pong"})

    async def _handle_request_orderbook(self, message: Dict):
        topic = message["data"]["symbol"] + "@orderbook"
        data = message["data"]
        data["ts"] = message["ts"]
        await self.queues[topic].put(data)

    async def _handle_general_message(self, message: Dict):
        data = message["data"]
        # data["ts"] = message["ts"]
        # logger.info(f"received message from {self.endpoint}: {message}")
        await self.queues[message["topic"]].put(data)

    async def recv(self, topic, timeout=10):
        res = None
        while not res:
            try:
                res = await asyncio.wait_for(self.queues[topic].get(), timeout=timeout)
            except asyncio.TimeoutError:
                logging.info(f"no message in {timeout} seconds")
        return res

    async def _handle_message(self, message):
        message = jsonlib.loads(message)
        # logger.info(f"received message from {self.endpoint}: {message}")
        if "event" in message:
            if message["event"] not in ("ping", "pong"):
                if message["success"]:
                    if "data" in message and message["event"] == "request":
                        await self._handle_request_orderbook(message)
                    return
                else:
                    raise Exception(message)
        if "data" in message:
            await self._handle_general_message(message)

    # reconnect, resubscribe
    async def _reconnect(self):
        for topic in self.queues.keys():
            await self.do_subscribe(topic)


class OrderlyPublicWsManager(WsTopicManager):
    def __init__(
        self,
        _id="WS_PUBLIC",
        account_id="",
        endpoint="",
        loop=None,
    ):
        super().__init__(
            _id=_id,
            account_id=account_id,
            endpoint=endpoint,
            loop=loop,
        )


class OrderlyPrivateWsManager(WsTopicManager):
    def __init__(
        self,
        _id="WS_PRIVATE",
        account_id="",
        orderly_key: Optional[str] = None,
        orderly_secret: Optional[str] = None,
        endpoint="",
        loop=None,
    ):
        super().__init__(
            _id=_id,
            account_id=account_id,
            endpoint=endpoint,
            loop=loop,
        )
        self.orderly_key = orderly_key
        self.orderly_secret = orderly_secret
        if orderly_secret is not None:
            self.orderly_private_key = Ed25519PrivateKey.from_private_bytes(
                base58.b58decode(orderly_secret)[0:32]
            )

    def _signature(self, data):
        data_bytes = bytes(str(data), "utf-8")
        request_signature = base64.b64encode(
            self.orderly_private_key.sign(data_bytes)
        ).decode("utf-8")
        return request_signature

    async def _login(self) -> None:
        ts = round(datetime.datetime.now().timestamp() * 1000)
        await self.send_json(
            {
                "id": self._id,
                "event": "auth",
                "params": {
                    "orderly_key": f"ed25519:{self.orderly_key}",
                    "sign": self._signature(ts),
                    "timestamp": str(ts),
                },
            }
        )

    # reconnect, resubscribe
    async def _reconnect(self):
        for topic in self.queues.keys():
            await self._login()
            await self.do_subscribe(topic)
