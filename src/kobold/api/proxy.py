from typing import Any

import orjson
from fastapi import Request, Response

from ..http_client import HttpClientManager
from ..logging_config import get_logger
from ..utils.kobo_token import KoboSyncToken

logger = get_logger(__name__)


class KoboProxyService:
    KOBO_API_BASE = "https://storeapi.kobo.com"

    PASSTHROUGH_HEADERS = frozenset(
        {
            "authorization",
            "user-agent",
            "accept",
            "accept-language",
        }
    )

    async def proxy_request(
        self,
        request: Request,
        path: str,
        *,
        include_sync_token: bool = False,
    ) -> Response:
        url = f"{self.KOBO_API_BASE}{path}"
        query_params = dict(request.query_params)

        log = logger.bind(
            method=request.method,
            path=path,
            url=url,
        )

        headers: dict[str, str] = {}

        for key, value in request.headers.items():
            key_lower = key.lower()
            is_passthrough = key_lower in self.PASSTHROUGH_HEADERS
            is_kobo_header = key_lower.startswith("x-kobo-")
            is_sync_token = key_lower == "x-kobo-synctoken"

            if (is_passthrough or is_kobo_header) and not is_sync_token:
                headers[key] = value

        headers["Content-Type"] = "application/json"

        sync_token_obj: KoboSyncToken | None = None
        if include_sync_token:
            sync_token_obj = KoboSyncToken.from_request(request)
            if sync_token_obj.rawKoboSyncToken:
                headers["X-Kobo-SyncToken"] = sync_token_obj.rawKoboSyncToken

        log.debug("Proxying request to Kobo")

        try:
            client = await HttpClientManager.get_client()
            content = await request.body()

            response = await client.request(
                method=request.method,
                url=url,
                params=query_params,
                headers=headers,
                content=content,
                timeout=60.0,
            )

            resp_headers: dict[str, str] = {}
            for key, value in response.headers.items():
                key_lower = key.lower()
                if key_lower.startswith("x-kobo-") or key_lower == "content-type":
                    resp_headers[key] = value

            if include_sync_token and sync_token_obj:
                upstream_token = response.headers.get("X-Kobo-SyncToken")
                if upstream_token:
                    sync_token_obj.rawKoboSyncToken = upstream_token
                    resp_headers.update(sync_token_obj.to_headers())
                    log.debug("Updated composite sync token")

            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=resp_headers,
                media_type=response.headers.get("content-type"),
            )

        except Exception as e:
            log.error("Proxy request failed", error=str(e), exc_info=True)
            return Response(
                content=orjson.dumps({"error": "Proxy failed", "detail": str(e)}),
                status_code=502,
                media_type="application/json",
            )

    async def fetch_kobo_sync(
        self,
        request: Request,
    ) -> tuple[int, dict[str, str], list[dict[str, Any]]]:
        response = await self.proxy_request(
            request,
            "/v1/library/sync",
            include_sync_token=True,
        )

        entitlements: list[dict[str, Any]] = []

        if response.status_code == 200:
            try:
                data = orjson.loads(bytes(response.body))
                if isinstance(data, list):
                    entitlements = data
            except (orjson.JSONDecodeError, TypeError) as e:
                logger.warning(
                    "Failed to parse Kobo sync response",
                    error=str(e),
                )

        return response.status_code, dict(response.headers), entitlements
