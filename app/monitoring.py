import asyncio
import logging

logger = logging.getLogger(__name__)


class MonitoringManager:
    """Thin wrapper that owns the monitoring active/paused state."""

    def __init__(self):
        self._active = True

    @property
    def active(self) -> bool:
        return self._active

    def start(self):
        self._active = True
        logger.info("Monitoring started")

    def stop(self):
        self._active = False
        logger.info("Monitoring paused")
