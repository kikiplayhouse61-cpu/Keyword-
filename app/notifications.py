import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional, List

from telegram import Bot
from telegram.error import RetryAfter, TelegramError
from telegram.constants import ParseMode

from app.config import Config
from app.utils import format_time
from app import database as db

logger = logging.getLogger(__name__)


@dataclass
class NotificationPayload:
    keywords: List[str]
    sender_name: Optional[str]
    sender_username: Optional[str]
    sender_id: Optional[int]
    group_name: Optional[str]
    group_id: Optional[int]
    message_text: Optional[str]
    message_id: Optional[int]
    timestamp: str = field(default_factory=lambda: format_time())


class NotificationQueue:
    def __init__(self, bot: Bot):
        self._bot = bot
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def start(self):
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._worker())
            logger.info("Notification queue worker started")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Notification queue worker stopped")

    async def enqueue(self, payload: NotificationPayload):
        await self._queue.put(payload)

    async def _worker(self):
        while self._running:
            try:
                payload: NotificationPayload = await asyncio.wait_for(
                    self._queue.get(), timeout=1.0
                )
                await self._send_with_retry(payload)
                self._queue.task_done()
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Notification worker error: {e}")

    async def _send_with_retry(self, payload: NotificationPayload, retries: int = 5):
        # Check notifications enabled
        notif_enabled = await db.get_setting("notifications_enabled", "1")
        if notif_enabled != "1":
            return

        text = _build_notification_text(payload)

        for attempt in range(retries):
            try:
                await self._bot.send_message(
                    chat_id=Config.OWNER_ID,
                    text=text,
                    parse_mode=ParseMode.MARKDOWN_V2,
                )
                # Persist to history for each matched keyword
                for kw in payload.keywords:
                    await db.save_alert(
                        keyword=kw,
                        sender_name=payload.sender_name,
                        sender_username=payload.sender_username,
                        sender_id=payload.sender_id,
                        group_name=payload.group_name,
                        group_id=payload.group_id,
                        message_text=payload.message_text,
                        message_id=payload.message_id,
                    )
                return
            except RetryAfter as e:
                wait = e.retry_after + 1
                logger.warning(f"Rate limited — waiting {wait}s")
                await asyncio.sleep(wait)
            except TelegramError as e:
                logger.error(f"Telegram error sending notification (attempt {attempt + 1}): {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
            except Exception as e:
                logger.error(f"Unexpected error sending notification: {e}")
                break


def _build_notification_text(payload: NotificationPayload) -> str:
    def esc(s: str) -> str:
        if not s:
            return ""
        special = r'\_*[]()~`>#+-=|{}.!'
        import re
        return re.sub(r'([' + re.escape(special) + r'])', r'\\\1', s)

    keywords_str = esc(", ".join(payload.keywords))
    sender_name = esc(payload.sender_name or "Unknown")
    username = f"@{esc(payload.sender_username)}" if payload.sender_username else "_not available_"
    sender_id = str(payload.sender_id) if payload.sender_id else "_not available_"
    group_name = esc(payload.group_name or "Unknown")
    message_text = esc(payload.message_text or "")
    timestamp = esc(payload.timestamp)

    return (
        f"🔔 *NEW KEYWORD MATCH*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔑 *Keyword:* `{keywords_str}`\n"
        f"👤 *Name:* {sender_name}\n"
        f"🔗 *Username:* {username}\n"
        f"🆔 *Telegram ID:* `{sender_id}`\n"
        f"👥 *Group:* {group_name}\n"
        f"🕒 *Time:* `{timestamp}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💬 *Original Message:*\n{message_text}"
    )
