from collections import defaultdict
from typing import Dict, Optional

import aiohttp
import requests

from .exceptions import OrderlyAPIException, OrderlyValueException
from .helpers import get_loop


class BaseClient:
    _id: str
    application_id: Optional[str]
    orderly_key: Optional[str]
    orderly_secret: Optional[str]
    rest_endpoint: Optional[str]
    ws_endpoint: Optional[str]
    private_ws_endpoint: Optional[str]
    api_version: str = "v1"
    timeout = 30

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
        self._id = _id
        self.application_id = application_id
        self.orderly_key = orderly_key
        self.orderly_secret = orderly_secret
        self.rest_endpoint = rest_endpoint
        self.ws_endpoint = ws_endpoint
        self.private_ws_endpoint = private_ws_endpoint

    def _get_headers(self) -> Dict:
        headers = {
            "Accept": "application/json",
            "x-api-key": "",
            "x-api-signature": "",
            "x-api-timestamp": "",
        }
        if self.orderly_key:
            headers["x-api-key"] = self.orderly_key
        return headers

    def _init_session(self):
        raise NotImplementedError

    def _init_url(self, application_id: str):
        raise NotImplementedError

    def _handle_response(self, response):
        code = response.status_code
        if code == 200:
            return response.json()
        else:
            try:
                resp_json = response.json()
                raise OrderlyAPIException(resp_json, code)
            except ValueError as exc:
                raise OrderlyValueException(response) from exc


class Client(BaseClient):
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
            _id=_id,
            application_id=application_id,
            orderly_key=orderly_key,
            orderly_secret=orderly_secret,
            rest_endpoint=rest_endpoint,
            ws_endpoint=ws_endpoint,
            private_ws_endpoint=private_ws_endpoint,
        )
        self.headers = self._get_headers()
        self.session = self._init_session()
        self.response = None

    def _init_session(self) -> requests.Session:
        self.headers = self._get_headers()
        session = requests.session()
        session.headers.update(self.headers)
        return session

    def _init_url(self, application_id: str):
        raise NotImplementedError

    def _create_rest_uri(self, ep: str, v: str = ""):
        if not v:
            v = self.api_version
        return f"{self.rest_endpoint}/{v}/{ep}"

    def _request(self, method, uri: str, signed: bool, **kwargs):
        try:
            k = kwargs
            k["timeout"] = self.timeout
            sorted_arg = {key: value for key, value in sorted(kwargs.items())}
            if signed:
                # TODO
                self.headers["x-api-signature"] = ""
                self.headers["x-api-timestamp"] = ""
                self.session.headers.update(self.headers)
            self.response = getattr(self.session, method)(uri, params=sorted_arg)
            return self._handle_response(self.response)
        except Exception as exc:
            print("Request Exception: ", exc)

    def _request_api(self, method, ep: str, signed: bool, v: str = "", **kwargs):
        uri = self._create_rest_uri(ep, v)
        return self._request(method, uri, signed, **kwargs)

    def _get(self, ep: str, signed: bool, v: str = "", **kwargs):
        return self._request_api("get", ep, signed, v, **kwargs)

    def _post(self, ep: str, signed: bool, v: str = "", **kwargs):
        return self._request_api("post", ep, signed, v, **kwargs)

    def _put(self, ep: str, signed: bool, v: str = "", **kwargs):
        return self._request_api("put", ep, signed, v, **kwargs)

    def _delete(self, ep: str, signed: bool, v: str = "", **kwargs):
        return self._request_api("delete", ep, signed, v, **kwargs)


class AsyncClient(BaseClient):
    def __init__(
        self,
        _id="websocket_client",
        application_id: Optional[str] = None,
        orderly_key: Optional[str] = None,
        orderly_secret: Optional[str] = None,
        rest_endpoint: Optional[str] = None,
        ws_endpoint: Optional[str] = None,
        private_ws_endpoint: Optional[str] = None,
        loop=None,
    ):
        super().__init__(
            _id=_id,
            application_id=application_id,
            orderly_key=orderly_key,
            orderly_secret=orderly_secret,
            rest_endpoint=rest_endpoint,
            ws_endpoint=ws_endpoint,
            private_ws_endpoint=private_ws_endpoint,
        )
        self.loop = loop or get_loop()
        self.session = self._init_session()
        self.headers: Dict[str, str] = defaultdict(str)
        self.response = None

    @classmethod
    async def create(
        cls,
        _id="websocket_client",
        application_id: Optional[str] = None,
        orderly_key: Optional[str] = None,
        orderly_secret: Optional[str] = None,
        rest_endpoint: Optional[str] = None,
        ws_endpoint: Optional[str] = None,
        private_ws_endpoint: Optional[str] = None,
        loop=None,
    ):
        self = cls(
            _id=_id,
            application_id=application_id,
            orderly_key=orderly_key,
            orderly_secret=orderly_secret,
            rest_endpoint=rest_endpoint,
            ws_endpoint=ws_endpoint,
            private_ws_endpoint=private_ws_endpoint,
            loop=loop,
        )
        return self

    def _init_session(self) -> aiohttp.ClientSession:
        return aiohttp.ClientSession(loop=self.loop, headers=self._get_headers())

    async def close_connection(self):
        if self.session:
            assert self.session
            await self.session.close()

    async def _request(self, method, uri: str, signed: bool, **kwargs):
        sorted_arg = {key: value for key, value in sorted(kwargs.items())}
        if signed:
            # TODO
            self.headers["x-api-signature"] = ""
            self.headers["x-api-timestamp"] = ""
            self.session.headers.update(self.headers)

        async with getattr(self.session, method)(uri, params=sorted_arg) as response:
            self.response = response
            return await self._handle_response(response)

    async def _handle_response(self, response: requests.Response):
        code = response.status_code
        if code == 200:
            return response.json()
        else:
            try:
                resp_json = response.json()
                raise OrderlyAPIException(resp_json, code)
            except ValueError:
                raise OrderlyValueException(response)

    def _create_rest_uri(self, ep: str, v: str = ""):
        if not v:
            v = self.api_version
        return f"{self.rest_endpoint}/{v}/{ep}"

    async def _request_api(self, method, ep: str, signed: bool, v: str = "", **kwargs):
        uri = self._create_rest_uri(ep, v)
        return self._request(method, uri, signed, **kwargs)

    async def _get(self, ep, signed=False, v: str = "", **kwargs):
        return await self._request_api("get", ep, signed, v, **kwargs)

    async def _post(self, ep, signed=False, v: str = "", **kwargs):
        return await self._request_api("post", ep, signed, v, **kwargs)

    async def _put(self, ep, signed=False, v: str = "", **kwargs):
        return await self._request_api("put", ep, signed, v, **kwargs)

    async def _delete(self, ep, signed=False, v: str = "", **kwargs):
        return await self._request_api("delete", ep, signed, v, **kwargs)
