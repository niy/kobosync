import asyncio
import contextlib
import time
from datetime import timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
import time_machine

from kobosync.scheduler import schedule_periodic_scans


@pytest.mark.asyncio
async def test_scheduler_runs_periodic_scans():
    mock_scanner = Mock()
    mock_scanner.scan_directories = AsyncMock()

    with time_machine.travel(0, tick=False) as traveller:
        # We need to break the infinite loop.
        mock_scanner.scan_directories.side_effect = [None, asyncio.CancelledError()]

        async def fast_forward_sleep(delay):
            traveller.shift(timedelta(seconds=delay))

        with patch("asyncio.sleep", side_effect=fast_forward_sleep):
            start_time = time.time()

            with (
                contextlib.suppress(asyncio.CancelledError),
                patch("kobosync.scheduler.RECONCILE_INTERVAL_MINUTES", 60),
            ):
                await schedule_periodic_scans(mock_scanner)

            end_time = time.time()
            elapsed = end_time - start_time

            # Loop 1: Sleep(3600) (virtual) -> Scan (ok)
            # Loop 2: Sleep(3600) (virtual) -> Scan (raise)
            # Total elapsed should be 3600 * 2 = 7200 seconds
            assert elapsed == pytest.approx(7200)
            assert mock_scanner.scan_directories.call_count == 2


@pytest.mark.asyncio
async def test_scheduler_disabled():
    mock_scanner = Mock()
    mock_scanner.scan_directories = AsyncMock()

    with patch("kobosync.scheduler.RECONCILE_INTERVAL_MINUTES", 0):
        await schedule_periodic_scans(mock_scanner)

    mock_scanner.scan_directories.assert_not_called()
