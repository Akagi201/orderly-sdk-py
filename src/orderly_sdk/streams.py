import asyncio
import gzip
import json
import logging
import time
from asyncio import sleep
from enum import Enum
from random import random
from socket import gaierror
from typing import Any, Callable, Dict, List, Optional

import websockets as ws
from websockets.exceptions import ConnectionClosedError

from .client import AsyncClient
from .exceptions import OrderlyWebsocketUnableToConnectException
from .helpers import get_loop
from .threaded_stream import ThreadedApiManager

KEEPALIVE_TIMEOUT = 5 * 60  # 5 minutes


class WSListenerState(Enum):
    INITIALISING = "Initialising"
    STREAMING = "Streaming"
    RECONNECTING = "Reconnecting"
    EXITING = "Exiting"


class ReconnectingWebsocket:
    MAX_RECONNECTS = 5
    MAX_RECONNECT_SECONDS = 60
    TIMEOUT = 60

    def __init__(
        self,
        url: str,
        name: Optional[str] = None,
        is_binary: bool = False,
        exit_coro=None,
    ):
        self._loop = get_loop()
        self._log = logging.getLogger(__name__)
        self._name = name
        self._url = url
        self._exit_coro = exit_coro
        self._reconnects = 0
        self._is_binary = is_binary
        self._conn = None
        self._socket = None
        self.ws: Optional[ws.client.WebSocketClientProtocol] = None  # type: ignore
        self.ws_state = WSListenerState.INITIALISING
        self._queue = asyncio.Queue()

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._exit_coro:
            await self._exit_coro(self._name)
        self.ws_state = WSListenerState.EXITING
        if self.ws:
            self.ws.fail_connection()
        if self._conn and hasattr(self._conn, "protocol"):
            await self._conn.__aexit__(exc_type, exc_val, exc_tb)
        self.ws = None

    async def connect(self):
        await self._before_connect()
        assert self._name
        self._conn = ws.connect(self._url, close_timeout=0.1)  # type: ignore
        try:
            self.ws = await self._conn.__aenter__()
        except:  # noqa
            await self._reconnect()
            return
        self.ws_state = WSListenerState.STREAMING
        self._reconnects = 0
        await self._after_connect()
        self._loop.call_soon_threadsafe(asyncio.create_task, self._read_loop())

    async def send_msg(self, msg):
        while not self.ws:
            await asyncio.sleep(0.1)
        await self.ws.send(json.dumps(msg))

    async def _before_connect(self):
        pass

    async def _after_connect(self):
        pass

    def _handle_message(self, evt):
        if self._is_binary:
            try:
                evt = gzip.decompress(evt)
            except (ValueError, OSError):
                return None
        try:
            return json.loads(evt)
        except ValueError:
            self._log.debug(f"error parsing evt json:{evt}")
            return None

    async def _read_loop(self):
        while True:
            res = None
            if not self.ws or self.ws_state != WSListenerState.STREAMING:
                await self._wait_for_reconnect()
                break
            if self.ws_state == WSListenerState.EXITING:
                break
            if self.ws.state == ws.protocol.State.CLOSING:
                break
            if self.ws.state == ws.protocol.State.CLOSED:
                try:
                    await self._reconnect()
                except Exception as e:
                    print(e)
                else:
                    break
            try:
                res = await asyncio.wait_for(self.ws.recv(), timeout=self.TIMEOUT)
            except asyncio.TimeoutError:
                logging.debug(f"no message in {self.TIMEOUT} seconds")
                await self._reconnect()
            except asyncio.CancelledError as e:
                logging.debug(f"cancelled error {e}")
                break
            except asyncio.IncompleteReadError as e:
                logging.debug(f"incomplete read error {e}")
            except Exception as e:
                logging.debug(f"exception {e}")
                await self._reconnect()
                break
            else:
                if self.ws_state in (
                    WSListenerState.EXITING,
                    WSListenerState.RECONNECTING,
                ):
                    break
                res = self._handle_message(res)
                if self.ws_state in (
                    WSListenerState.EXITING,
                    WSListenerState.RECONNECTING,
                ):
                    break

            if res and self._queue.qsize() < 100:
                await self._queue.put(res)

    async def recv(self):
        res = None
        while not res:
            try:
                res = await asyncio.wait_for(self._queue.get(), timeout=self.TIMEOUT)
            except asyncio.TimeoutError:
                logging.debug(f"no message in {self.TIMEOUT} seconds")
        return res

    async def _wait_for_reconnect(self):
        while self.ws_state == WSListenerState.RECONNECTING:
            logging.debug("reconnecting waiting for connect")
        if not self.ws:
            logging.debug("ignore message no ws")
        else:
            logging.debug(f"ignore message {self.ws_state}")

    def _get_reconnect_wait(self, attempts: int) -> int:
        expo = 2**attempts
        return round(random() * min(self.MAX_RECONNECT_SECONDS, expo - 1) + 1)

    async def before_reconnect(self):
        if self.ws:
            await self._conn.__aexit__(None, None, None)
            self.ws = None
        self._reconnects += 1

    def _no_message_received_reconnect(self):
        logging.debug("No message received, reconnecting")
        asyncio.create_task(self._reconnect())

    async def _reconnect(self):
        if self.ws_state == WSListenerState.RECONNECTING:
            return
        self.ws_state = WSListenerState.RECONNECTING
        await self.before_reconnect()
        if self._reconnects < self.MAX_RECONNECTS:
            reconnect_wait = self._get_reconnect_wait(self._reconnects)
            logging.debug(
                f"websocket reconnecting {self.MAX_RECONNECTS - self._reconnects} reconnects left - "
                f"waiting {reconnect_wait}"
            )
            await asyncio.sleep(reconnect_wait)
            await self.connect()
        else:
            logging.error(f"Max reconnections {self.MAX_RECONNECTS} reached:")
            raise "MaximumReconnectRetry"


class OrderlySocketManager:
    def __init__(
        self,
        client: AsyncClient,
    ):
        self._conns = {}
        self._loop = get_loop()
        self._client = client
        self._log = logging.getLogger("OrderlySocketManager")
        self.ws_endpoint = client.ws_endpoint
        self.private_ws_endpoint = client.private_ws_endpoint
        self.application_id = client.application_id
        self._init_stream_url()

    def _init_stream_url(self):
        # TODO
        self.ws_url = (self.ws_endpoint or "") + (self.application_id or "")
        self.private_ws_url = (self.private_ws_endpoint or "") + (
            self.application_id or ""
        )

    def _get_socket(
        self, socket_name: str, is_binary: bool = False, auth: bool = False
    ) -> str:
        conn_id = f"{socket_name}"
        if auth:
            url = self.private_ws_url
        else:
            url = self.ws_url
        if conn_id not in self._conns:
            self._conns[conn_id] = ReconnectingWebsocket(
                name=socket_name,
                url=url,
                exit_coro=self._exit_socket,
                is_binary=is_binary,
            )

        return self._conns[conn_id]

    async def subscribe(self, socket_name: str, **params):
        try:
            await self._conns[socket_name].send_msg(params)
        except KeyError:
            self._log.warning(f"Connection name: <{socket_name}> not create and start!")

    async def _exit_socket(self, name: str):
        await self._stop_socket(name)

    def get_socket(self, socket_name, auth: bool = False):
        return self._get_socket(socket_name, auth=auth)

    async def _stop_socket(self, conn_key):
        if conn_key not in self._conns:
            return

        del self._conns[conn_key]


class ThreadedWebsocketManager(ThreadedApiManager):
    def __init__(
        self,
        _id="websocket_client",
        application_id: Optional[str] = None,
        orderly_key: Optional[str] = None,
        orderly_secret: Optional[str] = None,
        rest_endpoint: Optional[str] = None,
        ws_endpoint: Optional[str] = None,
        private_ws_endpoint: Optional[str] = None,
    ):
        super().__init__(
            _id="websocket_client",
            application_id=application_id,
            orderly_key=orderly_key,
            orderly_secret=orderly_secret,
            rest_endpoint=rest_endpoint,
            ws_endpoint=ws_endpoint,
            private_ws_endpoint=private_ws_endpoint,
        )
        self._bsm: Optional[OrderlySocketManager] = None
        self._id = _id
        self.application_id = application_id
        self.orderly_key = orderly_key
        self.orderly_secret = orderly_secret
        self.rest_endpoint = rest_endpoint
        self.ws_endpoint = ws_endpoint
        self.private_ws_endpoint = private_ws_endpoint

    async def _before_socket_listener_start(self):
        assert self._client
        self._bsm = OrderlySocketManager(client=self._client)

    def _start_socket(
        self,
        callback: Callable,
        socket_name: str,
        auth: bool = False,
    ) -> str:
        while not self._bsm:
            time.sleep(0.1)

        socket = getattr(self._bsm, "get_socket")(socket_name, auth=auth)
        name = socket._name
        self._socket_running[name] = True
        self._loop.call_soon_threadsafe(
            asyncio.create_task,
            self.start_listener(socket, socket._name, callback, self.ping),
        )

        return socket

    def start_socket(
        self,
        callback: Callable,
        socket_name: str,
        auth: bool = False,
    ) -> str:
        return self._start_socket(
            callback=callback,
            socket_name=socket_name,
            auth=auth,
        )

    def subscribe(self, socket_name: str, **params):
        while not self._bsm:
            time.sleep(0.1)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            loop.create_task(self._bsm.subscribe(socket_name, **params))
        else:
            asyncio.run(self._bsm.subscribe(socket_name, **params))

    def authentication(self, socket_name="private_connection"):
        # TODO
        # ts = str(int(time.time() * 1000))
        # sign = signature(ts, self.secret)
        params = {}
        params["apikey"] = ""
        params["sign"] = ""
        params["timestamp"] = ""
        self.subscribe(
            socket_name=socket_name,
            id=socket_name,
            event="auth",
            params=params,
        )

    def ping(self, name):
        self.subscribe(name, event="pong")
