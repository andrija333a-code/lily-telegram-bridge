import asyncio
import logging
import os
from typing import Any

import httpx
from fastapi import FastAPI
from telethon import TelegramClient, events
from telethon.sessions import StringSession

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
log = logging.getLogger("lily-bridge")

API_ID = int(os.environ["TELEGRAM_API_ID"])
API_HASH = os.environ["TELEGRAM_API_HASH"]
SESSION = os.environ["TELEGRAM_SESSION"]
N8N_WEBHOOK_URL = os.environ["N8N_WEBHOOK_URL"]
N8N_SHARED_SECRET = os.environ["N8N_SHARED_SECRET"]
N8N_SECRET_HEADER = os.getenv("N8N_SECRET_HEADER", "X-Lily-Secret")

app = FastAPI()
client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)
http_client: httpx.AsyncClient | None = None
processing_lock = asyncio.Lock()


@app.get("/")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "lily-telegram-bridge"}


@app.on_event("startup")
async def startup() -> None:
    global http_client
    http_client = httpx.AsyncClient(timeout=httpx.Timeout(35.0))
    await client.connect()
    if not await client.is_user_authorized():
        raise RuntimeError("Telegram session is not authorized. Generate a valid StringSession locally.")
    log.info("Telegram client connected; bridge is running.")


@app.on_event("shutdown")
async def shutdown() -> None:
    global http_client
    if http_client:
        await http_client.aclose()
    await client.disconnect()


@client.on(events.NewMessage(incoming=True))
async def handle_incoming(event: Any) -> None:
    # Only private incoming text messages; never reply to our own/outgoing messages.
    if not event.is_private or event.out or not event.raw_text:
        return

    sender = await event.get_sender()
    if not sender or getattr(sender, "bot", False):
        return

    chat = await event.get_chat()
    payload = {
        "message_id": int(event.id),
        "chat_id": int(event.chat_id),
        "sender_id": int(event.sender_id or 0),
        "sender_name": " ".join(
            part for part in [
                getattr(sender, "first_name", None),
                getattr(sender, "last_name", None),
            ] if part
        ) or getattr(sender, "username", None) or "Telegram user",
        "text": event.raw_text,
        "is_private": True,
        "is_outgoing": False,
    }

    # Serialize requests so messages do not race through this basic bridge.
    async with processing_lock:
        try:
            assert http_client is not None
            response = await http_client.post(
                N8N_WEBHOOK_URL,
                json=payload,
                headers={N8N_SECRET_HEADER: N8N_SHARED_SECRET},
            )
            response.raise_for_status()
            result = response.json()
        except Exception:
            log.exception("Could not reach the n8n webhook or parse its response.")
            return

        if result.get("action") == "reply":
            reply = result.get("text")
            target_chat = result.get("chat_id", payload["chat_id"])
            if isinstance(reply, str) and reply.strip():
                try:
                    await client.send_message(
                        int(target_chat),
                        reply[:4096],
                        reply_to=event.id,
                    )
                except Exception:
                    log.exception("Could not send the reply to Telegram.")
        # action=skip: intentionally do nothing


async def telegram_runner() -> None:
    # Telethon's event loop is the app's event loop; connection is established on startup.
    await client.run_until_disconnected()


@app.on_event("startup")
async def start_telegram_runner() -> None:
    asyncio.create_task(telegram_runner())
