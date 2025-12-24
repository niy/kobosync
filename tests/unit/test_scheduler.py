import asyncio
import contextlib
from unittest.mock import AsyncMock, Mock, patch

import pytest

from kobosync.scheduler import schedule_periodic_scans


@pytest.mark.asyncio
async def test_scheduler_runs_periodic_scans():
    mock_scanner = Mock()
    mock_scanner.scan_directories = AsyncMock()

    with (
        patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        patch("kobosync.scheduler.RECONCILE_INTERVAL_MINUTES", 1),
    ):
        # Make sleep raise CancelledError after 2 calls to break the infinite loop
        # First call: sleep(60) -> returns
        # Second call: sleep(60) -> raises CancelledError
        mock_sleep.side_effect = [None, asyncio.CancelledError()]

        with contextlib.suppress(asyncio.CancelledError):
            await schedule_periodic_scans(mock_scanner)

        assert mock_scanner.scan_directories.call_count == 1
        mock_sleep.assert_called_with(60)


@pytest.mark.asyncio
async def test_scheduler_disabled():
    mock_scanner = Mock()
    mock_scanner.scan_directories = AsyncMock()

    with patch("kobosync.scheduler.RECONCILE_INTERVAL_MINUTES", 0):
        await schedule_periodic_scans(mock_scanner)

    mock_scanner.scan_directories.assert_not_called()
