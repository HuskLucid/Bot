import os
import io
import asyncio
import logging
from pyrogram import Client, filters, errors
from pyrogram.types import Message
from pyrogram.enums import MessageEntityType

# --- LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
log = logging.getLogger("Forwarder")

# --- CONFIGURATION ---
API_ID = int(os.environ.get("API_ID", 12345))
API_HASH = os.environ.get("API_HASH", "your_hash")
SESSION_STRING = os.environ.get("SESSION_STRING", "")
SOURCE_CHAT = int(os.environ.get("SOURCE_CHAT", 0))
DEST_CHAT = int(os.environ.get("DEST_CHAT", 0))
SOURCE_USERNAME = os.environ.get("SOURCE_USERNAME", "")
DEST_USERNAME = os.environ.get("DEST_USERNAME", "")

# --- CLIENT ---
app = Client(
    name="session",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
    workdir=".",
)


# --- PREMIUM EMOJI HELPERS ---

async def fetch_custom_emoji_stickers(client, emoji_ids):
    mapping = {}
    try:
        stickers = await client.get_custom_emoji_stickers(emoji_ids)
        for s in stickers:
            mapping[s.custom_emoji_id] = s.emoji or "❓"
    except Exception as e:
        log.warning(f"Emoji fetch failed: {e}")
    return mapping


async def handle_premium_emoji(client, text, entities):
    if not entities:
        return text, []

    custom_ids = [
        e.custom_emoji_id for e in entities
        if e.type == MessageEntityType.CUSTOM_EMOJI and e.custom_emoji_id
    ]
    if not custom_ids:
        return text, list(entities)

    emoji_map = await fetch_custom_emoji_stickers(client, list(set(custom_ids)))
    if not emoji_map:
        return text, list(entities)

    new_text = ""
    prev_end = 0
    new_entities = []
    shift = 0

    for ent in sorted(entities, key=lambda e: e.offset):
        new_text += text[prev_end:ent.offset]

        if ent.type == MessageEntityType.CUSTOM_EMOJI:
            emoji_char = emoji_map.get(ent.custom_emoji_id, "❓")
            new_text += emoji_char
            shift += len(emoji_char) - 1
        else:
            new_text += text[ent.offset:ent.offset + ent.length]
            new_entities.append(
                MessageEntityType(
                    type=ent.type,
                    offset=ent.offset + shift,
                    length=ent.length,
                )
            )

        prev_end = ent.offset + ent.length

    new_text += text[prev_end:]
    return new_text, new_entities


# --- CORE FORWARDER ---

async def forward_message(client, dest, message):
    try:
        if message.media:
            media_type = type(message.media).__name__
            log.info(f"[MEDIA] msg={message.id} type={media_type}")

            file_data = io.BytesIO()
            await client.download_media(message, file_name=file_data)
            file_data.seek(0)

            file_name = getattr(message, "file_name", None) or "file"

            caption = message.caption or ""
            cap_entities = list(message.caption_entities) if message.caption_entities else []
            caption, cap_entities = await handle_premium_emoji(client, caption, cap_entities)

            if message.sticker:
                await client.send_sticker(chat_id=dest, sticker=file_data)
            elif message.animation or message.video:
                await client.send_video(
                    chat_id=dest, video=file_data, caption=caption,
                    caption_entities=cap_entities or None,
                    duration=message.video.duration if message.video else None,
                    file_name=file_name,
                )
            elif message.photo:
                await client.send_photo(
                    chat_id=dest, photo=file_data, caption=caption,
                    caption_entities=cap_entities or None,
                )
            elif message.audio:
                await client.send_audio(
                    chat_id=dest, audio=file_data, caption=caption,
                    caption_entities=cap_entities or None,
                    title=message.audio.title,
                    performer=message.audio.performer,
                )
            elif message.voice:
                await client.send_voice(
                    chat_id=dest, voice=file_data, caption=caption,
                    caption_entities=cap_entities or None,
                    duration=message.voice.duration,
                )
            elif message.document:
                await client.send_document(
                    chat_id=dest, document=file_data, caption=caption,
                    caption_entities=cap_entities or None, file_name=file_name,
                )
            else:
                await client.send_media(
                    chat_id=dest, media=message.media, caption=caption,
                    caption_entities=cap_entities or None,
                )

            log.info(f"[SUCCESS] Media forwarded (msg={message.id})")

        elif message.text:
            text = message.text
            entities = list(message.entities) if message.entities else []
            text, entities = await handle_premium_emoji(client, text, entities)
            await client.send_message(chat_id=dest, text=text, entities=entities or None)
            log.info(f"[SUCCESS] Text forwarded (msg={message.id})")

        else:
            log.info(f"[SKIP] msg={message.id} unsupported type")

    except errors.FloodWait as e:
        log.warning(f"[FLOOD] Waiting {e.value}s...")
        await asyncio.sleep(e.value + 2)
        await forward_message(client, dest, message)
    except errors.Forbidden:
        log.error("[FORBIDDEN] No permission")
    except Exception as e:
        log.error(f"[ERROR] msg={message.id}: {e}")


# --- COMMANDS ---

@app.on_message(filters.command("set_source", prefixes=",") & filters.me)
async def cmd_set_source(client, message):
    global SOURCE_CHAT
    SOURCE_CHAT = message.chat.id
    await message.edit_text(f"Source Set!\n`{SOURCE_CHAT}`")
    log.info(f"Source set to {SOURCE_CHAT}")


@app.on_message(filters.command("set_dest", prefixes=",") & filters.me)
async def cmd_set_dest(client, message):
    global DEST_CHAT
    DEST_CHAT = message.chat.id
    await message.edit_text(f"Destination Set!\n`{DEST_CHAT}`")
    log.info(f"Dest set to {DEST_CHAT}")


@app.on_message(filters.command("status", prefixes=",") & filters.me)
async def cmd_status(client, message):
    src = f"`{SOURCE_CHAT}`" if SOURCE_CHAT else "Not Set"
    dst = f"`{DEST_CHAT}`" if DEST_CHAT else "Not Set"
    await message.edit_text(
        f"Forwarder Status\n\n"
        f"Source: {src}\n"
        f"Destination: {dst}\n"
        f"Premium Emoji: ON\n"
        f"Anti-Restrict: ON"
    )


@app.on_message(filters.command("stop_fwd", prefixes=",") & filters.me)
async def cmd_stop_fwd(client, message):
    global SOURCE_CHAT, DEST_CHAT
    SOURCE_CHAT = 0
    DEST_CHAT = 0
    await message.edit_text("Forwarder Stopped!")
    log.info("Forwarder stopped")


# --- MAIN FORWARDER HANDLER ---

@app.on_message(~filters.me)
async def main_forwarder(client, message):
    if not SOURCE_CHAT or not DEST_CHAT:
        return
    if message.chat.id != SOURCE_CHAT:
        return

    log.info(f"[RECV] msg={message.id} from source")
    await forward_message(client, DEST_CHAT, message)


# --- MAIN ---

if __name__ == "__main__":
    log.info("Starting Forwarder...")

    async def run():
        global SOURCE_CHAT, DEST_CHAT

        async with app:
            me = await app.get_me()
            log.info(f"Logged in as: {me.first_name} (@{me.username})")

            # CRITICAL: Cache ALL dialogs first — this populates Pyrogram's
            # internal peer cache so it can resolve chat IDs from updates
            log.info("Caching all dialogs (this fixes Peer id invalid errors)...")
            dialog_count = 0
            async for dialog in app.get_dialogs():
                dialog_count += 1
            log.info(f"Cached {dialog_count} dialogs")

            # Now resolve source and dest
            if SOURCE_USERNAME:
                try:
                    chat = await app.get_chat(SOURCE_USERNAME)
                    SOURCE_CHAT = chat.id
                    log.info(f"Source resolved: @{SOURCE_USERNAME} -> {chat.id}")
                except Exception as e:
                    log.error(f"Source username failed: {e}")
            elif SOURCE_CHAT:
                try:
                    chat = await app.get_chat(SOURCE_CHAT)
                    SOURCE_CHAT = chat.id
                    log.info(f"Source resolved: {chat.id} ({chat.title})")
                except Exception as e:
                    log.error(f"Source ID failed: {e}")

            if DEST_USERNAME:
                try:
                    chat = await app.get_chat(DEST_USERNAME)
                    DEST_CHAT = chat.id
                    log.info(f"Dest resolved: @{DEST_USERNAME} -> {chat.id}")
                except Exception as e:
                    log.error(f"Dest username failed: {e}")
            elif DEST_CHAT:
                try:
                    chat = await app.get_chat(DEST_CHAT)
                    DEST_CHAT = chat.id
                    log.info(f"Dest resolved: {chat.id} ({chat.title})")
                except Exception as e:
                    log.error(f"Dest ID failed: {e}")

            if SOURCE_CHAT and DEST_CHAT:
                log.info(f"Source: {SOURCE_CHAT}")
                log.info(f"Dest: {DEST_CHAT}")
                log.info("Listening for new messages...")
            else:
                log.error("SOURCE_CHAT or DEST_CHAT not resolved!")
                log.info("Use env vars or commands: ,set_source / ,set_dest")

            await asyncio.Event().wait()

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        log.info("Stopped")
    except Exception as e:
        log.critical(f"Fatal: {e}")
