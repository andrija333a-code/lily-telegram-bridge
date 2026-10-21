"""
Run locally on your own computer, not on GitHub or Render:
  py -m pip install telethon
  py generate_session.py

Enter your phone number and Telegram login code when prompted.
If Telegram asks for your two-step verification password, enter it in the local terminal.
Keep the printed TELEGRAM_SESSION secret. Never share it or commit it to GitHub.
"""
import asyncio
import getpass
import os
from telethon import TelegramClient
from telethon.sessions import StringSession

async def main():
    api_id = int(input("Telegram api_id: ").strip())
    api_hash = getpass.getpass("Telegram api_hash (hidden): ").strip()
    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.start()
    print("\nCopy this value into Render as TELEGRAM_SESSION. Keep it private:\n")
    print(client.session.save())
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
