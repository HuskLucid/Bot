import os
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
SOURCE_CHAT = int(os.environ.get("SOURCE_CHAT", 0))  # set via env or ,set_source
DEST_CHAT = int(os.environ.get("DEST_CHAT", 0))      # set via env or ,set_dest

# --- CLIENT ---
app = Client(
    name="session",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
    workdir=".",
)

# --- HELPERS ---

async def fetch_custom_emoji_stickers(client, emoji_ids: list[int]) -> dict[int, str]:
    """Map custom_emoji_id -> emoji_char by fetching sticker info."""
    mapping = {}
    try:
        stickers = await client.get_custom_emoji_stickers(emoji_ids)
        for s in stickers:
            mapping[s.custom_emoji_id] = s.emoji or "❓"
    except Exception as e:
        log.warning(f"Could not fetch custom emoji stickers: {e}")
    return mapping


def replace_custom_emojis(text: str, entities, emoji_map: dict[int, str]) -> tuple[str, list]:
    """Replace custom emoji entities with their base emoji characters."""
    if not entities:
        return text, []

    new_entities = []
    offset_shift = 0

    # Sort entities by offset
    sorted_ents = sorted(entities, key=lambda e: e.offset)

    for ent in sorted_ents:
        if ent.type == MessageEntityType.CUSTOM_EMOJI:
            custom_id = ent.custom_emoji_id
            emoji_char = emoji_map.get(custom_id, "❓")

            # Replace the single char with the emoji
            start = ent.offset + offset_shift
            text = text[:start] + emoji_char + text[start + ent.length:]
            # 1 char emoji replaces potentially multi-char placeholder
            offset_shift += len(emoji_char) - ent.length
        else:
            # Adjust offset for non-custom-emoji entities
            adjusted = MessageEntityType(
                type=ent.type,
                offset=ent.offset + offset_shift,
                length=ent.length,
            )
            if hasattr(ent, "custom_emoji_id"):
                adjusted.custom_emoji_id = ent.custom_emoji_id
            new_entities.append(adjusted)

    # Rebuild entities with correct offsets (for non-custom-emoji ones)
    final_entities = []
    for ent in sorted_ents:
        if ent.type == MessageEntityType.CUSTOM_EMOJI:
            continue  # replaced
        final_entities.append(ent)

    return text, final_entities


async def handle_premium_emoji_message(client: Client, message: Message, text: str, entities) -> tuple[str, list]:
    """Handle premium/custom emojis — try to keep them, fallback to base emoji."""
    custom_emoji_ids = []
    if entities:
        for e in entities:
            if e.type == MessageEntityType.CUSTOM_EMOJI and e.custom_emoji_id:
                custom_emoji_ids.append(e.custom_emoji_id)

    if not custom_emoji_ids:
        return text, entities or []

    # Fetch the sticker data to get base emoji chars
    emoji_map = await fetch_custom_emoji_stickers(client, list(set(custom_emoji_ids)))

    if emoji_map:
        # Replace custom emojis with their base characters
        new_text, new_entities = replace_custom_emojis(text, entities, emoji_map)
        return new_text, new_entities

    # Fallback: just return original text/entities
    return text, entities or []


async def forward_message(client: Client, source: int, dest: int, message: Message):
    """Forward a single message — handles media, captions, premium emojis, etc."""
    try:
        # --- MEDIA MESSAGES (photos, videos, documents, audio, voice, etc.) ---
        if message.media:
            log.info(f"[MEDIA] msg_id={message.id} type={type(message.media).__name__}")

            # Download to memory (BytesIO) to avoid disk I/O
            file_data = await client.download_media(message, in_memory=True)

            if file_data is None:
                log.error(f"[MEDIA] Download returned None for msg_id={message.id}")
                return

            # Handle premium emojis in caption
            caption_text = message.caption or ""
            caption_entities = message.caption_entities or []
            caption_text, caption_entities = await handle_premium_emoji_message(
                client, message, caption_text, caption_entities
            )

            # Re-upload to destination
            await client.send_media(
                chat_id=dest,
                media=message.media,
                file_data=file_data,
                caption=caption_text,
                caption_entities=caption_entities if caption_entities else None,
            )
            log.info(f"[SUCCESS] ✅ Media forwarded (msg_id={message.id})")

        # --- TEXT MESSAGES (with possible premium emojis) ---
        elif message.text:
            log.info(f"[TEXT] msg_id={message.id}")

            text = message.text
            entities = list(message.entities) if message.entities else []

            text, entities = await handle_premium_emoji_message(client, message, text, entities)

            await client.send_message(
                chat_id=dest,
                text=text,
                entities=entities if entities else None,
            )
            log.info(f"[SUCCESS] ✅ Text forwarded (msg_id={message.id})")

        # --- STICKER MESSAGES ---
        elif message.sticker:
            log.info(f"[STICKER] msg_id={message.id}")
            await client.send_sticker(chat_id=dest, sticker=message.sticker.file_id)
            log.info(f"[SUCCESS] ✅ Sticker forwarded (msg_id={message.id})")

        # --- OTHER TYPES (polls, contacts, etc.) ---
        else:
            log.info(f"[SKIP] msg_id={message.id} unsupported type")

    except errors.FloodWait as e:
        log.warning(f"[FLOOD] Waiting {e.value}s...")
        await asyncio.sleep(e.value)
        await forward_message(client, source, dest, message)

    except errors.Forbidden:
        log.error(f"[FORBIDDEN] Bot not allowed in source or dest")

    except Exception as e:
        log.error(f"[ERROR] Forwarding failed msg_id={message.id}: {e}")


# --- COMMANDS ---

@app.on_message(filters.command("set_source", prefixes=",") & filters.me)
async def cmd_set_source(client: Client, message: Message):
    global SOURCE_CHAT
    SOURCE_CHAT = message.chat.id
    await message.edit_text(f"📥 **Source Set Ho Gaya!**\nID: `{SOURCE_CHAT}`")
    log.info(f"Source set to {SOURCE_CHAT}")


@app.on_message(filters.command("set_dest", prefixes=",") & filters.me)
async def cmd_set_dest(client: Client, message: Message):
    global DEST_CHAT
    DEST_CHAT = message.chat.id
    await message.edit_text(f"📤 **Destination Set Ho Gaya!**\nID: `{DEST_CHAT}`")
    log.info(f"Destination set to {DEST_CHAT}")


@app.on_message(filters.command("status", prefixes=",") & filters.me)
async def cmd_status(client: Client, message: Message):
    src = f"`{SOURCE_CHAT}`" if SOURCE_CHAT else "❌ Not Set"
    dst = f"`{DEST_CHAT}`" if DEST_CHAT else "❌ Not Set"
    await message.edit_text(
        f"🚀 **Forwarder Status**\n\n"
        f"📥 Source: {src}\n"
        f"📤 Destination: {dst}\n\n"
        f"Premium Emoji: ✅ Enabled"
    )


@app.on_message(filters.command("start_fwd", prefixes=",") & filters.me)
async def cmd_start_fwd(client: Client, message: Message):
    if not SOURCE_CHAT or not DEST_CHAT:
        await message.edit_text("⚠️ Pehle `,set_source` aur `,set_dest` command se channels set karo!")
        return
    await message.edit_text(
        f"🔄 **Forwarder Active!**\n\n"
        f"📥 `{SOURCE_CHAT}` → 📤 `{DEST_CHAT}`\n"
        f"Premium Emojis: ✅\n"
        f"Media + Captions: ✅\n"
        f"Anti-Restrict: ✅"
    )
    log.info("Forwarder manually started")


@app.on_message(filters.command("stop_fwd", prefixes=",") & filters.me)
async def cmd_stop_fwd(client: Client, message: Message):
    global SOURCE_CHAT, DEST_CHAT
    SOURCE_CHAT = 0
    DEST_CHAT = 0
    await message.edit_text("⏹️ **Forwarder Stopped!**")
    log.info("Forwarder stopped")


# --- MAIN FORWARDER HANDLER ---

@app.on_message(~filters.me & ~filters.command(
    ["set_source", "set_dest", "status", "start_fwd", "stop_fwd"],
    prefixes=","
))
async def main_forwarder(client: Client, message: Message):
    if not SOURCE_CHAT or not DEST_CHAT:
        return
    if message.chat.id != SOURCE_CHAT:
        return

    log.info(f"[RECV] New msg from source: id={message.id}")
    await forward_message(client, SOURCE_CHAT, DEST_CHAT, message)


# --- MAIN ---

if __name__ == "__main__":
    log.info("🚀 Telegram Forwarder Starting (Pyrogram + TgCrypto)...")

    # Start + keep alive
    async def run():
        async with app:
            me = await app.get_me()
            log.info(f"✅ Bot logged in as: {me.first_name} (@{me.username})")
            log.info("🔄 Listening for new messages...")
            await asyncio.Event().wait()  # block forever

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        log.info("⛔ Stopped by user")
    except Exception as e:
        log.critical(f"💥 Fatal: {e}")
