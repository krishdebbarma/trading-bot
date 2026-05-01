import hashlib
import hmac
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

from .logging_config import get_logger

logger = get_logger(__name__)

DEFAULT_BASE_URL = "https://testnet.binancefuture.com"
DEFAULT_TIMEOUT = 10
DEFAULT_RECV_WINDOW = 5000


class BinanceAPIError(Exception):
    def __init__(self, status_code: int, code: Optional[int], message: str, payload: Any = None):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.payload = payload
        super().__init__(f"[HTTP {status_code}] code={code} msg={message}")


class BinanceNetworkError(Exception):
    pass


class BinanceFuturesClient:
    def __init__(self, api_key: str, api_secret: str,
                 base_url: str = DEFAULT_BASE_URL,
                 timeout: int = DEFAULT_TIMEOUT,
                 recv_window: int = DEFAULT_RECV_WINDOW) -> None:
        if not api_key or not api_secret:
            raise ValueError("api_key and api_secret are required")
        self.api_key = api_key
        self.api_secret = api_secret.encode("utf-8")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.recv_window = recv_window
        self._session = requests.Session()
        self._session.headers.update({"X-MBX-APIKEY": self.api_key})
        self._time_offset_ms = 0

    def _sign(self, query: str) -> str:
        return hmac.new(self.api_secret, query.encode("utf-8"), hashlib.sha256).hexdigest()

    def _timestamp(self) -> int:
        return int(time.time() * 1000) + self._time_offset_ms

    @staticmethod
    def _redact(params: Dict[str, Any]) -> Dict[str, Any]:
        return {k: v for k, v in params.items() if k != "signature"}

    def _request(self, method: str, path: str,
                 params: Optional[Dict[str, Any]] = None, signed: bool = False) -> Any:
        url = f"{self.base_url}{path}"
        params = dict(params or {})

        if signed:
            params["timestamp"] = self._timestamp()
            params["recvWindow"] = self.recv_window
            params["signature"] = self._sign(urlencode(params, doseq=True))

        logger.info("REQUEST  %s %s params=%s signed=%s",
                    method, path, self._redact(params), signed)

        try:
            resp = self._session.request(method=method, url=url, params=params,
                                         timeout=self.timeout)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError,
                requests.exceptions.RequestException) as e:
            logger.error("NETWORK  %s %s -> %s", method, path, e)
            raise BinanceNetworkError(str(e)) from e

        try:
            data = resp.json()
        except ValueError:
            data = {"raw": resp.text}

        logger.info("RESPONSE %s %s status=%s body=%s",
                    method, path, resp.status_code, data)

        if resp.status_code >= 400:
            code = data.get("code") if isinstance(data, dict) else None
            msg = data.get("msg") if isinstance(data, dict) else str(data)
            raise BinanceAPIError(resp.status_code, code, msg or "Unknown API error", data)

        if isinstance(data, dict) and data.get("code", 0) and data.get("code", 0) < 0:
            raise BinanceAPIError(resp.status_code, data["code"], data.get("msg", ""), data)

        return data

    def ping(self) -> Dict[str, Any]:
        return self._request("GET", "/fapi/v1/ping")

    def sync_time(self) -> int:
        data = self._request("GET", "/fapi/v1/time")
        self._time_offset_ms = int(data["serverTime"]) - int(time.time() * 1000)
        return self._time_offset_ms

    def account(self) -> Dict[str, Any]:
        return self._request("GET", "/fapi/v2/account", signed=True)

    def new_order(self, **params: Any) -> Dict[str, Any]:
        return self._request("POST", "/fapi/v1/order", params=params, signed=True)
