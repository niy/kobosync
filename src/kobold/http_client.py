import asyncio
from typing import Self

import httpx

from .logging_config import get_logger

logger = get_logger(__name__)

# Default HTTP client limits
HTTP_TIMEOUT = 30.0
HTTP_MAX_CONNECTIONS = 100


class HttpClientManager:
    _instance: Self | None = None
    _client: httpx.AsyncClient | None = None
    _lock: asyncio.Lock | None = None

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._lock = asyncio.Lock()
        return cls._instance

    @classmethod
    async def get_client(cls) -> httpx.AsyncClient:
        instance = cls()

        if instance._lock is None:
            instance._lock = asyncio.Lock()

        async with instance._lock:
            if instance._client is None or instance._client.is_closed:
                instance._client = httpx.AsyncClient(
                    timeout=httpx.Timeout(HTTP_TIMEOUT),
                    follow_redirects=True,
                    limits=httpx.Limits(
                        max_connections=HTTP_MAX_CONNECTIONS,
                        max_keepalive_connections=HTTP_MAX_CONNECTIONS // 2,
                    ),
                )
                logger.debug(
                    "HTTP client initialized",
                    timeout=HTTP_TIMEOUT,
                    max_connections=HTTP_MAX_CONNECTIONS,
                )

            return instance._client

    @classmethod
    async def close(cls) -> None:
        instance = cls()

        if instance._lock is None:
            return

        async with instance._lock:
            if instance._client is not None and not instance._client.is_closed:
                await instance._client.aclose()
                logger.debug("HTTP client closed")
            instance._client = None
