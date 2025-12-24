import time

import httpx
import pytest

from kobosync.metadata.base import RateLimitedTransport


class TestRateLimitedTransport:
    @pytest.mark.asyncio
    async def test_transport_enforces_delay_between_requests(self) -> None:
        transport = RateLimitedTransport(min_delay=0.1, jitter_max=0.0)

        mock_response = httpx.Response(200, text="OK")

        async def mock_handle(request: httpx.Request) -> httpx.Response:
            return mock_response

        transport._transport.handle_async_request = mock_handle  # type: ignore[method-assign]

        request = httpx.Request("GET", "https://example.com")
        start = time.monotonic()
        await transport.handle_async_request(request)
        first_duration = time.monotonic() - start
        assert first_duration < 0.05

        start = time.monotonic()
        await transport.handle_async_request(request)
        second_duration = time.monotonic() - start
        assert second_duration >= 0.1
        assert second_duration < 0.15

        await transport.aclose()

    @pytest.mark.asyncio
    async def test_transport_applies_jitter(self) -> None:
        transport = RateLimitedTransport(min_delay=0.05, jitter_max=0.05)

        mock_response = httpx.Response(200, text="OK")

        async def mock_handle(request: httpx.Request) -> httpx.Response:
            return mock_response

        transport._transport.handle_async_request = mock_handle  # type: ignore[method-assign]

        request = httpx.Request("GET", "https://example.com")

        await transport.handle_async_request(request)

        delays = []
        for _ in range(5):
            start = time.monotonic()
            await transport.handle_async_request(request)
            delays.append(time.monotonic() - start)

        assert all(d >= 0.05 for d in delays)
        assert any(d > 0.06 for d in delays)

        await transport.aclose()
