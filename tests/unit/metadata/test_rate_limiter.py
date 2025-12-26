import time
from unittest.mock import patch

import httpx
import pytest
import time_machine

from kobold.metadata.base import RateLimitedTransport


class TestRateLimitedTransport:
    @pytest.mark.asyncio
    async def test_transport_enforces_delay_between_requests(self) -> None:
        transport = RateLimitedTransport(min_delay=0.1, jitter_max=0.0)

        mock_response = httpx.Response(200, text="OK")

        async def mock_handle(request: httpx.Request) -> httpx.Response:
            return mock_response

        transport._transport.handle_async_request = mock_handle  # type: ignore[method-assign]

        with time_machine.travel(0, tick=False):
            request = httpx.Request("GET", "https://example.com")

            start = time.monotonic()
            await transport.handle_async_request(request)
            first_duration = time.monotonic() - start
            assert first_duration < 0.05

            start = time.monotonic()

            await transport.handle_async_request(request)

            second_duration = time.monotonic() - start

            assert second_duration == pytest.approx(0.1, abs=0.05)

        await transport.aclose()

    @pytest.mark.asyncio
    async def test_transport_applies_jitter(self) -> None:
        transport = RateLimitedTransport(min_delay=0.05, jitter_max=0.05)

        mock_response = httpx.Response(200, text="OK")

        async def mock_handle(request: httpx.Request) -> httpx.Response:
            return mock_response

        transport._transport.handle_async_request = mock_handle  # type: ignore[method-assign]

        with (
            time_machine.travel(0, tick=False),
            patch("random.uniform", return_value=0.03) as mock_random,
        ):
            request = httpx.Request("GET", "https://example.com")

            await transport.handle_async_request(request)

            # Manually reset last request time to current time (0) to force a wait
            transport._last_request_time = time.monotonic()

            start = time.monotonic()
            await transport.handle_async_request(request)
            duration = time.monotonic() - start

            assert duration == pytest.approx(0.08, abs=0.05)
            mock_random.assert_called_with(0, 0.05)

        await transport.aclose()
