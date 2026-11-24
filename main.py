"""
GC Keyword Alert System — main entry point
"""
import asyncio
import logging
import os
import signal
import sys

import aiohttp
from aiohttp import web
from telegram import Bot
from telegram.ext import Application

from app.config import Config
from app import database as db
from app.notifications import NotificationQueue
from app.telegram_user import UserBot
from app.telegram_bot import build_application, validate_bot_token
from app.scheduler import run_periodic_cleanup, run_periodic_group_refresh

# ─────────────────────────── LOGGING ─────────────────────────────────────────

def setup_logging():
    level = getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Silence noisy libraries
    logging.getLogger("telethon").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)


logger = logging.getLogger(__name__)

# ─────────────────────────── HEALTH CHECK ────────────────────────────────────

async def health_check(request):
    return web.Response(text="OK", status=200)


async def start_health_server(port: int):
    app_web = web.Application()
    app_web.router.add_get("/", health_check)
    app_web.router.add_get("/health", health_check)
    runner = web.AppRunner(app_web)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Health check server on port {port}")
    return runner


# ─────────────────────────── MAIN ────────────────────────────────────────────

async def main():
    setup_logging()
    Config.validate()

    logger.info("=== GC Keyword Alert System starting ===")

    # Validate bot token before anything else
    if not await validate_bot_token(Config.BOT_TOKEN):
        logger.critical("Invalid BOT_TOKEN — exiting")
        sys.exit(1)

    # Initialize database
    await db.init_database()

    # Build components
    bot = Bot(token=Config.BOT_TOKEN)
    notification_queue = NotificationQueue(bot)
    userbot = UserBot(notification_queue)

    # Build PTB application
    ptb_app: Application = build_application(bot, userbot)

    # Start notification queue
    notification_queue.start()

    # Start userbot
    try:
        await userbot.start()
    except Exception as e:
        logger.critical(f"Failed to start userbot: {e}")
        await notification_queue.stop()
        sys.exit(1)

    # Health check server
    health_runner = await start_health_server(Config.HEALTH_PORT)

    # Background tasks
    tasks = [
        asyncio.create_task(run_periodic_cleanup()),
        asyncio.create_task(run_periodic_group_refresh(userbot)),
    ]

    # Graceful shutdown handler
    stop_event = asyncio.Event()

    def _handle_signal():
        logger.info("Shutdown signal received")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _handle_signal)
        except (NotImplementedError, ValueError):
            pass  # Windows doesn't support add_signal_handler

    # Initialize PTB (drop pending updates to avoid duplicate processing after restart)
    await ptb_app.initialize()
    await ptb_app.bot.delete_webhook(drop_pending_updates=True)
    await ptb_app.start()

    # Start polling in background
    polling_task = asyncio.create_task(
        ptb_app.updater.start_polling(
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query"],
        )
    )

    # Telethon run-until-disconnected in background
    telethon_task = asyncio.create_task(userbot.run_until_disconnected())

    logger.info("=== System fully operational ===")

    # Wait for shutdown signal
    await stop_event.wait()

    logger.info("Shutting down gracefully…")

    # Cancel background tasks
    for t in tasks:
        t.cancel()

    polling_task.cancel()
    telethon_task.cancel()

    await asyncio.gather(*tasks, polling_task, telethon_task, return_exceptions=True)

    # Stop components in order
    await ptb_app.updater.stop()
    await ptb_app.stop()
    await ptb_app.shutdown()
    await notification_queue.stop()
    await userbot.stop()
    await health_runner.cleanup()

    logger.info("=== Shutdown complete ===")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
