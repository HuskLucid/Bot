import os
import asyncio
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError

# --- CONFIGURATION FROM RAILWAY ---
API_ID = int(os.environ.get("API_ID", 12345))
API_HASH = os.environ.get("API_HASH", "your_hash")
SESSION_STRING = os.environ.get("SESSION_STRING", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")  # Bot token jo upload ka kaam karega

def parse_chat_id(env_value):
    if not env_value:
        return None
    val = str(env_value).strip()
    if val.startswith('-100') or val.startswith('-') or val.isalpha():
        try: return int(val)
        except: return val
    else:
        try: return int(f"-100{val}")
        except: return val

SOURCE_CHAT = parse_chat_id(os.environ.get("SOURCE_CHAT", ""))
DEST_CHAT = parse_chat_id(os.environ.get("DEST_CHAT", ""))

from telethon.sessions import StringSession

# 1. Tumhara Personal Account (Sirf read karega, hamesha offline rahega)
user_client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
# 2. Helper Robot Bot (Yeh upload karega, isliye tum online nahi dikhoge)
helper_bot = TelegramClient('helper_bot_session', API_ID, API_HASH)

print("=== TELETHON ULTRA SECURE FORWARDER STARTING ===")

# Helper: Media Sender (Yeh kaam ab ROBOT bot karega, tum nahi!)
async def safe_send(entity, file_path, msg_obj, is_sticker=False):
    try:
        if is_sticker:
            await helper_bot.send_file(entity=entity, file=file_path)
        else:
            await helper_bot.send_file(
                entity=entity,
                file=file_path,
                caption=msg_obj.message,
                formatting_entities=msg_obj.entities
            )
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds + 2)
    except Exception as err:
        print(f"[SEND ERROR] {str(err)}")

# Helper: Text Sender (Yeh bhi robot bot karega)
async def safe_send_text(entity, msg_obj):
    try:
        await helper_bot.send_message(
            entity=entity,
            message=msg_obj.message,
            formatting_entities=msg_obj.entities
        )
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds + 2)
    except Exception as err:
        print(f"[TEXT ERROR] {str(err)}")

# BULK FORWARDING: Ab ye tab chalegi jab tum DESTINATION CHANNEL me command likhoge
@user_client.on(events.NewMessage(pattern=r",forward (\d+)", outgoing=True))
async def bulk_forward(event):
    global SOURCE_CHAT, DEST_CHAT
    
    # Check ki command usi destination channel me maari gayi ho jo variable me set hai
    if event.chat_id != DEST_CHAT:
        return

    if not SOURCE_CHAT or not DEST_CHAT:
        await event.edit("❌ **Railway Variables me SOURCE_CHAT/DEST_CHAT nahi mila!**")
        return
        
    count = int(event.pattern_match.group(1))
    await event.edit(f"⏳ **Processing Bulk Forwarding...**\n`{count}` restricted posts copy ho rahi hain (Tu 100% offline hai)...")
    
    messages_to_forward = []
    # User account chupchaap restricted channel se message read karega (Isme online nahi dikhte)
    async for msg in user_client.iter_messages(SOURCE_CHAT, limit=count):
        messages_to_forward.append(msg)
    
    messages_to_forward.reverse()
    
    success_count = 0
    for msg in messages_to_forward:
        try:
            if msg.media and not msg.sticker:
                media_file = await user_client.download_media(msg)
                if media_file:
                    # Helper bot ko bolenge ki tu post kar destination me
                    await safe_send(DEST_CHAT, media_file, msg, is_sticker=False)
                    try: os.remove(media_file) 
                    except: pass
                success_count += 1
            elif msg.sticker:
                sticker_file = await user_client.download_media(msg)
                if sticker_file:
                    await safe_send(DEST_CHAT, sticker_file, msg, is_sticker=True)
                    try: os.remove(sticker_file)
                    except: pass
                success_count += 1
            elif msg.message:
                await safe_send_text(DEST_CHAT, msg)
                success_count += 1
            
            await asyncio.sleep(1.5)
            
        except Exception as e:
            print(f"[BULK ERROR] {str(e)}")
            
    await event.respond(f"✅ **Done!** `{success_count}` restricted messages successfully copied.")

# LIVE FORWARDER
@user_client.on(events.NewMessage)
async def main_forwarder(event):
    global SOURCE_CHAT, DEST_CHAT
    if not SOURCE_CHAT or not DEST_CHAT:
        return
        
    if event.chat_id == SOURCE_CHAT:
        try:
            if event.media and not event.sticker:
                media_file = await user_client.download_media(event.message)
                if media_file:
                    await safe_send(DEST_CHAT, media_file, event.message, is_sticker=False)
                    try: os.remove(media_file)
                    except: pass
            elif event.sticker:
                media_file = await user_client.download_media(event.message)
                if media_file:
                    await safe_send(DEST_CHAT, media_file, event.message, is_sticker=True)
                    try: os.remove(media_file)
                    except: pass
            elif event.message.message:
                await safe_send_text(DEST_CHAT, event.message)
                
        except Exception as e:
            print(f"[LIVE ERROR] {str(e)}")

async def main():
    # Dono clients ko ek sath chalana
    await user_client.start()
    await helper_bot.start(bot_token=BOT_TOKEN)
    print("🚀 Dual Engine (User + Robot Bot) Successfully Activated 24/7!")
    await user_client.run_until_disconnected()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
