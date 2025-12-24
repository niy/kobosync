from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from .logging_config import get_logger

if TYPE_CHECKING:
    from .scanner import ScannerService

logger = get_logger(__name__)

RECONCILE_INTERVAL_MINUTES = 60


async def schedule_periodic_scans(scanner: ScannerService) -> None:
    interval_minutes = RECONCILE_INTERVAL_MINUTES

    if interval_minutes <= 0:
        logger.info("Periodic reconcile disabled (interval=0)")
        return

    logger.info(
        "Periodic reconcile enabled",
        interval_minutes=interval_minutes,
    )

    interval_seconds = interval_minutes * 60

    try:
        while True:
            await asyncio.sleep(interval_seconds)

            logger.info("Starting scheduled reconcile scan...")
            try:
                await scanner.scan_directories()
            except Exception as e:
                logger.error(
                    "Reconcile scan failed",
                    error=str(e),
                )

    except asyncio.CancelledError:
        logger.debug("Reconcile scheduler cancelled")
        raise
