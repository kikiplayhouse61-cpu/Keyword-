"""
Session Generator — Run this LOCALLY (not on Railway) to create a Telethon StringSession.

Usage:
    python scripts/generate_session.py

You need:
    pip install telethon

After running, copy the session string into Railway → Variables → TELETHON_SESSION_STRING
"""

import asyncio
import os
import sys

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def generate():
    try:
        from telethon import TelegramClient
        from telethon.sessions import StringSession
    except ImportError:
        print("Telethon not installed. Run: pip install telethon")
        sys.exit(1)

    print("=" * 50)
    print("   GC Keyword Alert — Session Generator")
    print("=" * 50)
    print()
    print("Get API_ID and API_HASH from: https://my.telegram.org/apps")
    print()

    api_id_str = input("Enter your API_ID: ").strip()
    api_hash = input("Enter your API_HASH: ").strip()

    if not api_id_str.isdigit():
        print("ERROR: API_ID must be a number")
        sys.exit(1)

    api_id = int(api_id_str)

    print()
    print("Creating Telethon client...")
    client = TelegramClient(StringSession(), api_id, api_hash)

    await client.start()

    if not await client.is_user_authorized():
        print("ERROR: Authorization failed.")
        await client.disconnect()
        sys.exit(1)

    me = await client.get_me()
    session_string = client.session.save()

    await client.disconnect()

    print()
    print("=" * 50)
    print(f"Logged in as: {me.first_name} (ID: {me.id})")
    print()
    print("Your StringSession (copy this entire line):")
    print()
    print(session_string)
    print()
    print("=" * 50)
    print()
    print("Next steps:")
    print("1. Copy the session string above")
    print("2. Go to Railway → Your Project → Variables")
    print("3. Add: TELETHON_SESSION_STRING = <paste here>")
    print("4. Never share this string with anyone")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(generate())
