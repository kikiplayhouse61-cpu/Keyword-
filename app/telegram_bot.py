import logging

from telegram import Bot
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from app.config import Config
from app.handlers import BotHandlers

logger = logging.getLogger(__name__)


def build_application(bot: Bot, userbot) -> Application:
    """Build and return a fully configured PTB Application."""
    app = (
        Application.builder()
        .token(Config.BOT_TOKEN)
        .build()
    )

    handlers_obj = BotHandlers(bot, userbot)

    # Command
    app.add_handler(CommandHandler("start", handlers_obj.cmd_start))

    # Callbacks
    app.add_handler(CallbackQueryHandler(handlers_obj.handle_callback))

    # Text messages (for keyword input)
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handlers_obj.handle_text
        )
    )

    logger.info("Bot application configured")
    return app


async def validate_bot_token(token: str) -> bool:
    """Validate bot token by calling getMe."""
    try:
        bot = Bot(token=token)
        me = await bot.get_me()
        logger.info(f"Bot validated: @{me.username}")
        return True
    except Exception as e:
        logger.error(f"Bot token validation failed: {e}")
        return False
