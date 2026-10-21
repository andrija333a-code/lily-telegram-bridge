# Lily personal Telegram bridge

This service uses Telethon (Telegram's MTProto client API) to receive incoming private text messages and pass them to an n8n webhook. It sends back a reply only when n8n responds with `{"action":"reply", ...}`.

## Security

- Never commit `TELEGRAM_API_HASH`, `TELEGRAM_SESSION`, or `N8N_SHARED_SECRET`.
- Use a private GitHub repository if possible. This repository contains only code and no credentials.
- The session string grants access to your Telegram account. Store it only in the hosting provider's secret environment variables.
- Start with a test webhook and one consenting test contact. Do not use bulk messaging. Stop the service if Telegram warns or limits the account.

## Generate a Telegram session locally

Install Python 3.10+ on your own computer, download this repository, then run:

```bash
py -m pip install telethon
py generate_session.py
```

The script prompts for your API ID/hash and logs into your account. Copy the resulting session string into the host's `TELEGRAM_SESSION` secret. Do not share it or save it in GitHub.

## Environment variables

- `TELEGRAM_API_ID`: numeric app ID from my.telegram.org
- `TELEGRAM_API_HASH`: secret hash from my.telegram.org
- `TELEGRAM_SESSION`: StringSession created locally
- `N8N_WEBHOOK_URL`: n8n test URL while testing, production URL only after workflow is deliberately published
- `N8N_SHARED_SECRET`: the exact secret configured in n8n Header Auth
- `N8N_SECRET_HEADER`: `X-Lily-Secret`

## Important n8n behavior

The bridge expects the webhook to return a JSON object immediately. Test mode URLs generally work only while the n8n editor is listening for a test execution. A continuously running bridge normally needs a production webhook and an active/published workflow; do not switch to that until you intentionally approve going live.

Before live use, verify the webhook actually validates the shared-secret header, test duplicate and skip handling, and ensure the workflow returns the expected JSON response. This basic bridge serializes message processing but does not provide durable queuing or cross-restart deduplication.
