"""
Database unit tests — run with: python -m pytest tests/ -v
Requires: pip install pytest pytest-asyncio
"""
import asyncio
import os
import pytest
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Override database path for testing
os.environ.setdefault("API_ID", "123456")
os.environ.setdefault("API_HASH", "test_hash")
os.environ.setdefault("BOT_TOKEN", "123:test_token")
os.environ.setdefault("OWNER_ID", "999999999")
os.environ.setdefault("TELETHON_SESSION_STRING", "test_session")
os.environ["DATABASE_PATH"] = "/tmp/test_keyword_alert.db"

from app import database as db


@pytest.fixture(autouse=True)
async def setup_db():
    await db.init_database()
    # Clean slate
    import aiosqlite
    async with await db.get_connection() as conn:
        await conn.execute("DELETE FROM keywords")
        await conn.execute("DELETE FROM groups")
        await conn.execute("DELETE FROM alert_history")
        await conn.execute("DELETE FROM processed_messages")
        await conn.execute("DELETE FROM settings")
        await conn.commit()
    yield


@pytest.mark.asyncio
async def test_add_keyword():
    result = await db.add_keyword("Need Pop")
    assert result is True


@pytest.mark.asyncio
async def test_add_duplicate_keyword():
    await db.add_keyword("Need Pop")
    result = await db.add_keyword("Need Pop")
    assert result is False


@pytest.mark.asyncio
async def test_get_all_keywords():
    await db.add_keyword("Need Pop")
    await db.add_keyword("Need Netflix")
    kws = await db.get_all_keywords()
    assert len(kws) == 2


@pytest.mark.asyncio
async def test_remove_keyword():
    await db.add_keyword("Need Pop")
    kws = await db.get_all_keywords()
    removed = await db.remove_keyword(kws[0]["id"])
    assert removed is True
    kws2 = await db.get_all_keywords()
    assert len(kws2) == 0


@pytest.mark.asyncio
async def test_toggle_keyword():
    await db.add_keyword("Need Pop")
    kws = await db.get_all_keywords()
    kw_id = kws[0]["id"]
    new_state = await db.toggle_keyword(kw_id)
    assert new_state is False
    new_state2 = await db.toggle_keyword(kw_id)
    assert new_state2 is True


@pytest.mark.asyncio
async def test_get_active_keywords():
    await db.add_keyword("Need Pop")
    await db.add_keyword("Need Netflix")
    kws = await db.get_all_keywords()
    await db.toggle_keyword(kws[0]["id"])  # disable first
    active = await db.get_active_keywords()
    assert len(active) == 1


@pytest.mark.asyncio
async def test_keyword_persistence():
    await db.add_keyword("Need Prime")
    # Re-init DB (simulates restart)
    await db.init_database()
    kws = await db.get_all_keywords()
    assert any(k["keyword"] == "Need Prime" for k in kws)


@pytest.mark.asyncio
async def test_upsert_group():
    await db.upsert_group(123456, "Test Group", "testgroup")
    groups = await db.get_all_groups()
    assert len(groups) == 1
    assert groups[0]["group_name"] == "Test Group"
    # Upsert again with updated name
    await db.upsert_group(123456, "Updated Group", "testgroup")
    groups2 = await db.get_all_groups()
    assert len(groups2) == 1
    assert groups2[0]["group_name"] == "Updated Group"


@pytest.mark.asyncio
async def test_save_and_retrieve_alert():
    await db.save_alert(
        keyword="Need Pop",
        sender_name="Rahul",
        sender_username="rahul123",
        sender_id=12345,
        group_name="OTT Exchange",
        group_id=99999,
        message_text="Need Pop urgently",
        message_id=1,
    )
    alerts = await db.get_alert_history()
    assert len(alerts) == 1
    assert alerts[0]["keyword"] == "Need Pop"


@pytest.mark.asyncio
async def test_dedup_processing():
    key = "123:456"
    assert not await db.is_message_processed(key)
    await db.mark_message_processed(key)
    assert await db.is_message_processed(key)


@pytest.mark.asyncio
async def test_settings():
    await db.set_setting("notifications_enabled", "0")
    val = await db.get_setting("notifications_enabled", "1")
    assert val == "0"


@pytest.mark.asyncio
async def test_dashboard_state():
    await db.save_dashboard_state(message_id=777, chat_id=999999999)
    state = await db.get_dashboard_state()
    assert state is not None
    assert state["message_id"] == 777
    await db.clear_dashboard_state()
    state2 = await db.get_dashboard_state()
    assert state2 is None


@pytest.mark.asyncio
async def test_alert_counts():
    for i in range(3):
        await db.save_alert(
            keyword="Available",
            sender_name=f"User{i}",
            sender_username=None,
            sender_id=i,
            group_name="Group",
            group_id=1,
            message_text="Available",
            message_id=i,
        )
    total = await db.get_total_alert_count()
    assert total == 3


@pytest.mark.asyncio
async def test_top_keywords():
    for _ in range(3):
        await db.save_alert("Need Pop", "U", None, 1, "G", 1, "msg", 1)
    for _ in range(1):
        await db.save_alert("Need Netflix", "U", None, 2, "G", 1, "msg", 2)
    top = await db.get_top_keywords(5)
    assert top[0]["keyword"] == "Need Pop"
    assert top[0]["hits"] == 3
