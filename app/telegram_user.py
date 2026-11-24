import asyncio
import logging
from typing import Optional

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import (
    Channel, Chat, User,
    PeerChannel, PeerChat, PeerUser,
)
from telethon.errors import (
    SessionPasswordNeededError,
    AuthKeyUnregisteredError,
    UserDeactivatedBanError,
)

from app.config import Config
from app import database as db
from app.utils import find_matching_keywords, build_message_key
from app.notifications import NotificationPayload

logger = logging.getLogger(__name__)


class UserBot:
    def __init__(self, notification_queue):
        self._client: Optional[TelegramClient] = None
        self._notification_queue = notification_queue
        self._monitoring_active = True
        self._me = None

    @property
    def is_connected(self) -> bool:
        return self._client is not None and self._client.is_connected()

    @property
    def monitoring_active(self) -> bool:
        return self._monitoring_active

    def set_monitoring(self, active: bool):
        self._monitoring_active = active
        logger.info(f"Monitoring {'enabled' if active else 'disabled'}")

    async def start(self):
        logger.info("Starting Telethon userbot...")
        try:
            self._client = TelegramClient(
                StringSession(Config.TELETHON_SESSION_STRING),
                Config.API_ID,
                Config.API_HASH,
            )
            await self._client.connect()

            if not await self._client.is_user_authorized():
                raise RuntimeError(
                    "Telethon session is not authorized. "
                    "Run scripts/generate_session.py locally to create a fresh session, "
                    "then set TELETHON_SESSION_STRING in Railway environment variables."
                )

            self._me = await self._client.get_me()
            logger.info(f"Logged in as: {self._me.first_name} (ID: {self._me.id})")

            await self._discover_groups()
            self._register_handlers()
            logger.info("UserBot ready — listening for messages")
        except (AuthKeyUnregisteredError, UserDeactivatedBanError) as e:
            logger.critical(f"Session invalid or account banned: {e}")
            raise
        except Exception as e:
            logger.error(f"UserBot start error: {e}")
            raise

    async def stop(self):
        if self._client:
            await self._client.disconnect()
            logger.info("UserBot disconnected")

    async def run_until_disconnected(self):
        if self._client:
            await self._client.run_until_disconnected()

    async def _discover_groups(self):
        logger.info("Discovering joined groups...")
        count = 0
        try:
            async for dialog in self._client.iter_dialogs():
                entity = dialog.entity
                if isinstance(entity, (Channel, Chat)):
                    group_id = entity.id
                    group_name = entity.title or f"Group {group_id}"
                    username = getattr(entity, "username", None)
                    # Channel mega-groups / broadcast — skip broadcasts
                    if isinstance(entity, Channel) and entity.broadcast:
                        continue
                    await db.upsert_group(
                        group_id=group_id,
                        group_name=group_name,
                        group_username=username,
                    )
                    count += 1
        except Exception as e:
            logger.error(f"Group discovery error: {e}")
        logger.info(f"Discovered {count} groups")

    def _register_handlers(self):
        @self._client.on(events.NewMessage(incoming=True))
        async def on_message(event):
            await self._handle_message(event)

    async def _handle_message(self, event):
        if not self._monitoring_active:
            return

        try:
            msg = event.message
            if not msg or not msg.text:
                return

            # Skip messages from self
            if self._me and msg.sender_id == self._me.id:
                return

            # Only process group/channel messages
            chat = await event.get_chat()
            if not isinstance(chat, (Channel, Chat)):
                return

            # Dedup
            message_key = build_message_key(chat.id, msg.id)
            if await db.is_message_processed(message_key):
                return
            await db.mark_message_processed(message_key)

            # Update group record
            group_name = getattr(chat, "title", f"Group {chat.id}")
            group_username = getattr(chat, "username", None)
            await db.upsert_group(
                group_id=chat.id,
                group_name=group_name,
                group_username=group_username,
            )

            # Keyword matching
            active_keywords = await db.get_active_keywords()
            matched = find_matching_keywords(msg.text, active_keywords)
            if not matched:
                return

            # Gather sender info
            sender = await event.get_sender()
            sender_name = None
            sender_username = None
            sender_id = msg.sender_id

            if isinstance(sender, User):
                parts = [sender.first_name or "", sender.last_name or ""]
                sender_name = " ".join(p for p in parts if p).strip() or "Unknown"
                sender_username = sender.username
            elif sender:
                sender_name = getattr(sender, "title", None) or f"ID:{sender_id}"

            payload = NotificationPayload(
                keywords=matched,
                sender_name=sender_name,
                sender_username=sender_username,
                sender_id=sender_id,
                group_name=group_name,
                group_id=chat.id,
                message_text=msg.text,
                message_id=msg.id,
            )
            await self._notification_queue.enqueue(payload)
            logger.info(f"Alert queued: {matched} in {group_name}")

        except Exception as e:
            logger.error(f"Message handler error: {e}", exc_info=True)
