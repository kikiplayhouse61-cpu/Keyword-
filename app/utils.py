
import re
import logging
from datetime import datetime
from typing import List

import pytz

from app.config import Config

logger = logging.getLogger(__name__)


# ─────────────────────────── TIMEZONE ────────────────────────────────────────

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


# ─────────────────────────── TEXT NORMALIZATION ──────────────────────────────

def normalize_text(text: str) -> str:
    """
    Normalize text for case-insensitive matching.
    """

    if not text:
        return ""

    text = text.casefold()

    # Normalize repeated spaces
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ─────────────────────────── KEYWORD MATCHING ────────────────────────────────

def find_matching_keywords(
    text: str,
    keywords: List[str]
) -> List[str]:
    """
    Flexible manual keyword matching.

    Features:
    - No compulsory 'Need' word.
    - Case-insensitive matching.
    - Supports English, Hindi and Hinglish.
    - Supports extra words around keywords.
    - Supports numbers and amounts such as 10K, 100K, 1M, 15M.
    - Supports Pop and Popularity.
    - Uses keywords added by the owner.
    - Different new messages from the same sender can alert.
    """

    if not text or not keywords:
        return []

    message = normalize_text(text)

    matched = []
    seen = set()

    for keyword in keywords:

        if not keyword:
            continue

        keyword_normalized = normalize_text(keyword)

        if not keyword_normalized:
            continue

        # Avoid duplicate keyword entries
        if keyword_normalized in seen:
            continue

        seen.add(keyword_normalized)

        # Match the complete saved phrase inside the message.
        # Extra text before and after is allowed.
        if keyword_normalized in message:
            matched.append(keyword)

    return matched


# ─────────────────────────── MESSAGE DEDUPLICATION ───────────────────────────

def build_message_key(
    group_id: int,
    message_id: int
) -> str:
    """
    Unique key for each message in each group.

    Different messages from the same sender
    will have different message IDs.
    """

    return f"{group_id}:{message_id}"


# ─────────────────────────── TEXT UTILITIES ──────────────────────────────────

def truncate(
    text: str,
    max_len: int = 200
) -> str:

    if not text:
        return ""

    return text[:max_len] + (
        "…" if len(text) > max_len else ""
    )


# ─────────────────────────── PAGINATION ─────────────────────────────────────

def paginate(
    items: list,
    page: int,
    page_size: int = 10
):
    """
    Return:
    (page_items, total_pages, current_page)
    """

    total = len(items)

    total_pages = max(
        1,
        (total + page_size - 1) // page_size
    )

    page = max(
        0,
        min(page, total_pages - 1)
    )

    start = page * page_size

    return (
        items[start:start + page_size],
        total_pages,
        page
    )


# ─────────────────────────── MARKDOWN ESCAPING ───────────────────────────────

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
    
