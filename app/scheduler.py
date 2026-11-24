import asyncio
import logging

from app import database as db

logger = logging.getLogger(__name__)


async def run_periodic_cleanup():
    """Run every 6 hours: prune old dedup records."""
    while True:
        try:
            await asyncio.sleep(6 * 3600)
            await db.cleanup_old_processed(days=7)
            logger.info("Periodic cleanup complete")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Scheduler error: {e}")


async def run_periodic_group_refresh(userbot, interval_hours: int = 2):
    """Refresh joined groups every N hours."""
    while True:
        try:
            await asyncio.sleep(interval_hours * 3600)
            if userbot.is_connected:
                await userbot._discover_groups()
                logger.info("Periodic group refresh complete")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Group refresh error: {e}")
