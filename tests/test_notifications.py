import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("API_ID", "123456")
os.environ.setdefault("API_HASH", "test_hash")
os.environ.setdefault("BOT_TOKEN", "123:test_token")
os.environ.setdefault("OWNER_ID", "999999999")
os.environ.setdefault("TELETHON_SESSION_STRING", "test_session")
os.environ["DATABASE_PATH"] = "/tmp/test_notif.db"

from app.notifications import NotificationPayload, _build_notification_text


def test_notification_text_with_username():
    payload = NotificationPayload(
        keywords=["Need Pop"],
        sender_name="Rahul",
        sender_username="rahul123",
        sender_id=12345,
        group_name="OTT Exchange",
        group_id=99999,
        message_text="Need Pop urgently, anyone available?",
        message_id=1,
        timestamp="25-11-2026 12:30 AM",
    )
    text = _build_notification_text(payload)
    assert "Need Pop" in text
    assert "Rahul" in text
    assert "rahul123" in text
    assert "OTT Exchange" in text
    assert "Need Pop urgently" in text


def test_notification_text_without_username():
    payload = NotificationPayload(
        keywords=["Available"],
        sender_name="Unknown User",
        sender_username=None,
        sender_id=None,
        group_name="Group Name",
        group_id=1,
        message_text="Available now",
        message_id=2,
        timestamp="25-11-2026 01:00 PM",
    )
    text = _build_notification_text(payload)
    assert "not available" in text
    assert "Available" in text


def test_notification_text_multiple_keywords():
    payload = NotificationPayload(
        keywords=["Need Pop", "Available"],
        sender_name="Test",
        sender_username="test",
        sender_id=1,
        group_name="Group",
        group_id=1,
        message_text="Need Pop, Available",
        message_id=3,
        timestamp="25-11-2026 09:00 AM",
    )
    text = _build_notification_text(payload)
    assert "Need Pop" in text
    assert "Available" in text
