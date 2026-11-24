import logging
from typing import Optional

from telegram import Update, Bot
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from telegram.error import TelegramError, BadRequest

from app.config import Config
from app import database as db
from app import dashboard as dash
from app.keyboards import (
    main_dashboard_keyboard,
    keywords_keyboard,
    remove_keywords_keyboard,
    groups_keyboard,
    history_keyboard,
    settings_keyboard,
    confirm_keyboard,
    back_keyboard,
)
from app.utils import paginate

logger = logging.getLogger(__name__)

# State key for waiting on user input
AWAITING_KEYWORD = "awaiting_keyword"


def _owner_only(func):
    """Decorator: reject unauthorized users."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = None
        if update.effective_user:
            user_id = update.effective_user.id
        elif update.callback_query and update.callback_query.from_user:
            user_id = update.callback_query.from_user.id

        if user_id != Config.OWNER_ID:
            if update.callback_query:
                await update.callback_query.answer("⛔ Unauthorized", show_alert=True)
            elif update.message:
                await update.message.reply_text("⛔ Unauthorized")
            return
        return await func(update, context)
    return wrapper


class BotHandlers:
    def __init__(self, bot: Bot, userbot):
        self._bot = bot
        self._userbot = userbot

    # ─────────────────────────── DASHBOARD CORE ──────────────────────────────

    async def _send_or_update_dashboard(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE = None):
        """Either create a new dashboard message or edit the existing one."""
        text = await dash.build_dashboard_text(self._userbot.monitoring_active)
        kb = main_dashboard_keyboard(self._userbot.monitoring_active)

        state = await db.get_dashboard_state()
        if state:
            try:
                await self._bot.edit_message_text(
                    chat_id=state["chat_id"],
                    message_id=state["message_id"],
                    text=text,
                    parse_mode=ParseMode.MARKDOWN_V2,
                    reply_markup=kb,
                )
                return
            except BadRequest as e:
                if "message is not modified" in str(e).lower():
                    return
                # Dashboard message deleted — fall through to recreate
                await db.clear_dashboard_state()
            except TelegramError as e:
                logger.warning(f"Could not edit dashboard: {e}")
                await db.clear_dashboard_state()

        # Create fresh dashboard
        msg = await self._bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=kb,
        )
        await db.save_dashboard_state(msg.message_id, chat_id)

    async def _edit_dashboard(self, update: Update, text: str, keyboard):
        """Edit the static dashboard message in-place."""
        state = await db.get_dashboard_state()
        if not state:
            # Create dashboard first
            chat_id = update.effective_chat.id
            msg = await self._bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=keyboard,
            )
            await db.save_dashboard_state(msg.message_id, chat_id)
            return

        try:
            await self._bot.edit_message_text(
                chat_id=state["chat_id"],
                message_id=state["message_id"],
                text=text,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=keyboard,
            )
        except BadRequest as e:
            if "message is not modified" not in str(e).lower():
                logger.error(f"Dashboard edit error: {e}")
        except TelegramError as e:
            logger.error(f"Dashboard edit TG error: {e}")

    # ─────────────────────────── COMMAND HANDLERS ────────────────────────────

    @_owner_only
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        # Clear any old awaiting state
        if context.user_data:
            context.user_data.pop(AWAITING_KEYWORD, None)
        await self._send_or_update_dashboard(chat_id, context)

    # ─────────────────────────── MESSAGE HANDLER ─────────────────────────────

    @_owner_only
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle plain text messages — used for keyword input."""
        if not update.message or not update.message.text:
            return

        state = context.user_data.get(AWAITING_KEYWORD)
        if state == "add":
            keyword = update.message.text.strip()
            if not keyword:
                await update.message.reply_text("⚠️ Keyword cannot be empty.")
                return
            added = await db.add_keyword(keyword)
            if added:
                note = await update.message.reply_text(f"✅ Keyword added: `{keyword}`", parse_mode=ParseMode.MARKDOWN_V2)
            else:
                note = await update.message.reply_text(f"⚠️ Keyword already exists: `{keyword}`", parse_mode=ParseMode.MARKDOWN_V2)
            context.user_data.pop(AWAITING_KEYWORD, None)
            # Refresh dashboard
            await self._send_or_update_dashboard(update.effective_chat.id, context)

    # ─────────────────────────── CALLBACK ROUTER ─────────────────────────────

    @_owner_only
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data or ""

        try:
            if data == "action:dashboard":
                await self._show_main_dashboard(update, context)

            elif data == "action:refresh":
                await self._show_main_dashboard(update, context)

            elif data == "action:start":
                self._userbot.set_monitoring(True)
                await self._show_main_dashboard(update, context)

            elif data == "action:stop":
                self._userbot.set_monitoring(False)
                await self._show_main_dashboard(update, context)

            elif data == "action:add_keyword":
                await self._prompt_add_keyword(update, context)

            elif data == "action:remove_keyword":
                await self._show_remove_keywords(update, context, page=0)

            elif data.startswith("action:remove_keyword_page:"):
                page = int(data.split(":")[-1])
                await self._show_remove_keywords(update, context, page=page)

            elif data.startswith("action:keywords:"):
                page = int(data.split(":")[-1])
                await self._show_keywords(update, context, page=page)

            elif data.startswith("action:groups:"):
                page = int(data.split(":")[-1])
                await self._show_groups(update, context, page=page)

            elif data.startswith("action:history:"):
                page = int(data.split(":")[-1])
                await self._show_history(update, context, page=page)

            elif data == "action:stats":
                await self._show_stats(update, context)

            elif data == "action:settings":
                await self._show_settings(update, context)

            elif data.startswith("kw:toggle:"):
                kw_id = int(data.split(":")[-1])
                new_state = await db.toggle_keyword(kw_id)
                if new_state is None:
                    await query.answer("Keyword not found", show_alert=True)
                else:
                    state_str = "enabled" if new_state else "disabled"
                    await query.answer(f"Keyword {state_str}")
                await self._show_keywords(update, context, page=0)

            elif data.startswith("kw:delete:"):
                kw_id = int(data.split(":")[-1])
                removed = await db.remove_keyword(kw_id)
                if removed:
                    await query.answer("✅ Keyword removed")
                else:
                    await query.answer("⚠️ Not found", show_alert=True)
                await self._show_remove_keywords(update, context, page=0)

            elif data.startswith("grp:info:"):
                # Just show a toast for now — group list is read-only
                await query.answer("Group info coming soon", show_alert=True)

            elif data == "settings:toggle_notif":
                current = await db.get_setting("notifications_enabled", "1")
                new_val = "0" if current == "1" else "1"
                await db.set_setting("notifications_enabled", new_val)
                await self._show_settings(update, context)

            elif data == "settings:clear_history":
                await self._edit_dashboard(
                    update,
                    "⚠️ *Are you sure you want to clear ALL alert history?*",
                    confirm_keyboard("clear_history")
                )

            elif data == "confirm:yes:clear_history":
                async with await db.get_connection() as conn:
                    await conn.execute("DELETE FROM alert_history")
                    await conn.commit()
                await query.answer("✅ History cleared")
                await self._show_main_dashboard(update, context)

            elif data == "settings:reload_groups":
                await query.answer("Reloading groups…")
                try:
                    await self._userbot._discover_groups()
                    await query.answer("✅ Groups reloaded", show_alert=True)
                except Exception as e:
                    await query.answer(f"⚠️ Error: {e}", show_alert=True)
                await self._show_main_dashboard(update, context)

        except Exception as e:
            logger.error(f"Callback handler error ({data}): {e}", exc_info=True)
            await query.answer("⚠️ Error — please try again", show_alert=True)

    # ─────────────────────────── SCREEN BUILDERS ─────────────────────────────

    async def _show_main_dashboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = await dash.build_dashboard_text(self._userbot.monitoring_active)
        kb = main_dashboard_keyboard(self._userbot.monitoring_active)
        await self._edit_dashboard(update, text, kb)

    async def _prompt_add_keyword(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data[AWAITING_KEYWORD] = "add"
        await self._edit_dashboard(
            update,
            "➕ *Add Keyword*\n\nSend me the keyword or phrase you want to monitor\\.\nExample: `Need Pop`",
            back_keyboard()
        )

    async def _show_keywords(self, update: Update, context: ContextTypes.DEFAULT_TYPE, page: int):
        all_kw = await db.get_all_keywords()
        page_kw, total_pages, page = paginate(all_kw, page)
        text, _, _, _ = await dash.build_keywords_text(page=page)
        kb = keywords_keyboard(page_kw, page, total_pages)
        await self._edit_dashboard(update, text, kb)

    async def _show_remove_keywords(self, update: Update, context: ContextTypes.DEFAULT_TYPE, page: int):
        all_kw = await db.get_all_keywords()
        if not all_kw:
            await self._edit_dashboard(
                update,
                "🔑 *Remove Keyword*\n\nNo keywords to remove\\.",
                back_keyboard()
            )
            return
        page_kw, total_pages, page = paginate(all_kw, page)
        text = f"➖ *Remove Keyword* \\(Page {page + 1}/{total_pages}\\)\n\nTap a keyword to delete it:"
        kb = remove_keywords_keyboard(page_kw, page, total_pages)
        await self._edit_dashboard(update, text, kb)

    async def _show_groups(self, update: Update, context: ContextTypes.DEFAULT_TYPE, page: int):
        text, page_groups, total_pages, page = await dash.build_groups_text(page=page)
        kb = groups_keyboard(page_groups, page, total_pages)
        await self._edit_dashboard(update, text, kb)

    async def _show_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE, page: int):
        text, alerts, total_pages, page = await dash.build_history_text(page=page)
        kb = history_keyboard(page, total_pages)
        await self._edit_dashboard(update, text, kb)

    async def _show_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = await dash.build_stats_text()
        await self._edit_dashboard(update, text, back_keyboard())

    async def _show_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = await dash.build_settings_text()
        notif = await db.get_setting("notifications_enabled", "1")
        kb = settings_keyboard(notif == "1")
        await self._edit_dashboard(update, text, kb)
