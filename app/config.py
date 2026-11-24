import os
import sys
import logging

logger = logging.getLogger(__name__)


def get_required(key: str) -> str:
    val = os.environ.get(key, "").strip()
    if not val:
        logger.critical(f"Missing required environment variable: {key}")
        sys.exit(1)
    return val


def get_optional(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


class Config:
    # Telegram developer credentials
    API_ID: int = int(get_required("API_ID"))
    API_HASH: str = get_required("API_HASH")

    # Bot credentials
    BOT_TOKEN: str = get_required("BOT_TOKEN")
    OWNER_ID: int = int(get_required("OWNER_ID"))

    # Telethon session (StringSession format)
    TELETHON_SESSION_STRING: str = get_required("TELETHON_SESSION_STRING")

    # Database path — Railway persistent volume
    DATABASE_PATH: str = get_optional("DATABASE_PATH", "/data/keyword_alert.db")

    # Timezone
    TIMEZONE: str = get_optional("TIMEZONE", "Asia/Kolkata")

    # Logging
    LOG_LEVEL: str = get_optional("LOG_LEVEL", "INFO")

    # Health check port
    HEALTH_PORT: int = int(get_optional("PORT", "8080"))

    # Webhook URL (optional — if set, use webhook instead of polling)
    WEBHOOK_URL: str = get_optional("WEBHOOK_URL", "")

    @classmethod
    def validate(cls):
        """Final sanity checks after loading."""
        if cls.API_ID <= 0:
            logger.critical("API_ID must be a positive integer")
            sys.exit(1)
        logger.info("Config validated successfully")
