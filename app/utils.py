import re
import logging
from datetime import datetime
from typing import List

import pytz

from app.config import Config

logger = logging.getLogger(__name__)


def get_tz() -> pytz.BaseTzInfo:
    try:
        return pytz.timezone(Config.TIMEZONE)
    except Exception:
        logger.warning(
            f"Invalid timezone {Config.TIMEZONE}, "
            "falling back to Asia/Kolkata"
        )
        return pytz.timezone("Asia/Kolkata")


def format_time(dt: datetime = None) -> str:
    """Format datetime in local timezone."""
    tz = get_tz()

    if dt is None:
        dt = datetime.now(tz)
    elif dt.tzinfo is None:
        dt = pytz.utc.localize(dt).astimezone(tz)
    else:
        dt = dt.astimezone(tz)

    return dt.strftime("%d-%m-%Y %I:%M %p")


def now_local() -> datetime:
    return datetime.now(get_tz())


# ─────────────────────────── SMART KEYWORD MATCHING ─────────────────────────

def normalize_text(text: str) -> str:
    """Normalize text for case-insensitive matching."""
    text = text.casefold()
    text = re.sub(r"[_\-]+", " ", text)
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _keyword_pattern(keyword: str):
    """
    Build flexible keyword pattern.
    Allows partial phrase matching with extra words and amounts.
    """

    keyword = normalize_text(keyword)

    # Remove optional Need prefix from saved keyword.
    keyword = re.sub(r"^need\s+", "", keyword)

    tokens = keyword.split()

    if not tokens:
        return None

    # Allow small spelling variations in words of 4+ characters.
    patterns = []

    for token in tokens:
        if len(token) >= 4:
            patterns.append(re.escape(token) + r"\w*")
        else:
            patterns.append(re.escape(token))

    phrase = r"[\W_]+".join(patterns)

    return re.compile(
        r"(?<!\w)" + phrase + r"(?!\w)",
        re.IGNORECASE
    )


def find_matching_keywords(text: str, keywords: List[str]) -> List[str]:
    if not text or not keywords:
        return []

    text_normalized = re.sub(r"\s+", " ", text.casefold()).strip()
    matched = []

    for keyword in keywords:
        if not keyword:
            continue

        keyword_normalized = re.sub(
            r"\s+", " ", keyword.casefold()
        ).strip()

        if keyword_normalized and keyword_normalized in text_normalized:
            matched.append(keyword)

    return matched


# ─────────────────────────── MESSAGE DEDUPLICATION ──────────────────────────

def build_message_key(group_id: int, message_id: int) -> str:
    """Unique key for each message in each group."""
    return f"{group_id}:{message_id}"


# ─────────────────────────── TEXT UTILITIES ─────────────────────────────────

def truncate(text: str, max_len: int = 200) -> str:
    if not text:
        return ""

    return text[:max_len] + (
        "…" if len(text) > max_len else ""
    )


# ─────────────────────────── PAGINATION ─────────────────────────────────────

def paginate(items: list, page: int, page_size: int = 10):
    """Return (page_items, total_pages, current_page)."""

    total = len(items)
    total_pages = max(1, (total + page_size - 1) // page_size)

    page = max(0, min(page, total_pages - 1))
    start = page * page_size

    return items[start:start + page_size], total_pages, page


# ─────────────────────────── MARKDOWN ESCAPING ──────────────────────────────

def escape_md(text: str) -> str:
    """Escape MarkdownV2 special characters."""

    if not text:
        return ""

    special = r'\_*[]()~`>#+-=|{}.!'

    return re.sub(
        r'([' + re.escape(special) + r'])',
        r'\\\1',
        text
    )
    
