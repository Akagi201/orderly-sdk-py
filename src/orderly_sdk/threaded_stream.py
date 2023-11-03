import asyncio
import threading
from typing import Callable, Dict, Optional

from .client import AsyncClient
from .helpers import get_loop


class ThreadedApiManager(threading.Thread):
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
        """Initialise the BinanceSocketManager"""
        super().__init__()
        self._loop: asyncio.AbstractEventLoop = get_loop()
        self._client: Optional[AsyncClient] = None
        self._running: bool = True
        self._socket_running: Dict[str, bool] = {}
        self._client_params = {
            "_id": _id,
            "application_id": application_id,
            "orderly_key": orderly_key,
            "orderly_secret": orderly_secret,
            "rest_endpoint": rest_endpoint,
            "ws_endpoint": ws_endpoint,
            "private_ws_endpoint": private_ws_endpoint,
        }

    async def _before_socket_listener_start(self):
        ...

    async def socket_listener(self):
        self._client = await AsyncClient.create(loop=self._loop, **self._client_params)
        await self._before_socket_listener_start()
        while self._running:
            await asyncio.sleep(0.2)
        while self._socket_running:
            await asyncio.sleep(0.2)

    async def start_listener(
        self, socket, name: str, callback, ping: Optional[Callable] = None
    ):
        async with socket as s:
            while self._socket_running[name]:
                try:
                    msg = await asyncio.wait_for(s.recv(), 3)
                except asyncio.TimeoutError:
                    ...
                    continue
                else:
                    if not msg:
                        continue
                    if "event" in msg and msg["event"] == "ping":
                        if ping is not None:
                            ping(name)
                    callback(msg)
        del self._socket_running[name]

    def run(self):
        self._loop.run_until_complete(self.socket_listener())

    def stop_socket(self, socket_name):
        if socket_name in self._socket_running:
            self._socket_running[socket_name] = False

    async def stop_client(self):
        if not self._client:
            return
        await self._client.close_connection()

    def stop(self):
        if not self._running:
            return
        self._running = False
        self._loop.call_soon(asyncio.create_task, self.stop_client())
        for socket_name in self._socket_running.keys():
            self._socket_running[socket_name] = False
