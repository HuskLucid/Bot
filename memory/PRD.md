# PRD — Telegram Restricted-Content Forwarder Bot

## Original Problem Statement
User has an existing Telethon-based Telegram forwarder bot repo and wants to host it FREE and 24/7. Chosen platform: **Render free tier + UptimeRobot keep-alive ping**.

## Architecture
- Single-file Python app (`main.py`) using Telethon
- Dual engine: user account (StringSession) downloads restricted content from SOURCE_CHAT; helper bot (BOT_TOKEN) re-uploads to DEST_CHAT
- Live forwarding (event-based) + bulk command `,forward N` in dest chat
- Dummy HTTP ping server on $PORT (default 10000) to keep Render free web service awake
- Config via env vars: API_ID, API_HASH, SESSION_STRING, BOT_TOKEN, SOURCE_CHAT, DEST_CHAT

## What's Been Implemented (June 2026)
- [x] Repo scan & analysis
- [x] Cleaned requirements.txt (removed unused pyrogram/tgcrypto, added cryptg for faster downloads)
- [x] Added render.yaml blueprint (free web service, python runtime, env var placeholders)
- [x] Fixed Procfile worker→web
- [x] Fixed crash-loop: invalid SESSION_STRING now keeps process/ping-server alive with hourly log reminders instead of exiting
- [x] Lint cleanup (bare excepts → typed, import order, one-liners)
- [x] Verified locally: ping server returns 200 "Bot Engine is Alive and Running 24/7!"

## Deployment Plan (user actions)
1. Save to GitHub via Emergent "Save to GitHub"
2. Render → New → Blueprint (or Web Service) → connect repo → set 6 env vars
3. UptimeRobot monitor pinging Render URL every 5 min

## Backlog
- P2: `parse_chat_id` edge case — usernames containing digits get wrongly prefixed with -100
- P2: Helper bot uses file session (ephemeral disk on Render → re-login each restart; works but noisy)
- P3: Optional status/health command for the bot
