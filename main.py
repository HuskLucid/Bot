import os
import asyncio
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from telethon.tl.functions.account import UpdateStatusRequest

# --- CONFIGURATION ---
API_ID = int(os.environ.get("API_ID", 12345))
API_HASH = os.environ.get("API_HASH", "your_hash")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

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
bot = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

print("=== TELETHON ULTRA FORWARDER STARTING ===")

# STRICT GHOST MODE: Har 2 second me offline status force karega
async def keep_offline_loop():
    while True:
        try:
            await bot(UpdateStatusRequest(offline=True))
        except:
            pass
        await asyncio.sleep(2)

# Safely Media Sender (Bypasses restriction by uploading fresh)
async def safe_send(entity, file_path, msg_obj, is_sticker=False):
    try:
        await bot(UpdateStatusRequest(offline=True)) # Action se pehle offline push
        if is_sticker:
            await bot.send_file(entity=entity, file=file_path)
        else:
            await bot.send_file(
                entity=entity,
                file=file_path,
                caption=msg_obj.message,
                formatting_entities=msg_obj.entities
            )
        await bot(UpdateStatusRequest(offline=True)) # Action ke turant baad offline push
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds + 2)
    except Exception as err:
        print(f"[SEND ERROR] {str(err)}")

# Safely Text Sender
async def safe_send_text(entity, msg_obj):
    try:
        await bot(UpdateStatusRequest(offline=True))
        await bot.send_message(
            entity=entity,
            message=msg_obj.message,
            formatting_entities=msg_obj.entities
        )
        await bot(UpdateStatusRequest(offline=True))
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds + 2)
    except Exception as err:
        print(f"[TEXT ERROR] {str(err)}")

# BULK FORWARDING FROM SAVED MESSAGES (Anti-Restrict Version)
@bot.on(events.NewMessage(pattern=r",forward (\d+)", outgoing=True))
async def bulk_forward(event):
    global SOURCE_CHAT, DEST_CHAT
    
    # Target Saved Messages Check
    me = await bot.get_me()
    if event.chat_id != me.id:
        return

    if not SOURCE_CHAT or not DEST_CHAT:
        await event.edit("❌ **Railway Variables missing hain!**")
        return
        
    count = int(event.pattern_match.group(1))
    await event.edit(f"⏳ **Anti-Restrict Bulk Active!**\nDownloading & re-uploading `{count}` posts...")
    
    messages_to_forward = []
    async for msg in bot.iter_messages(SOURCE_CHAT, limit=count):
        messages_to_forward.append(msg)
    
    messages_to_forward.reverse()
    
    success_count = 0
    for msg in messages_to_forward:
        try:
            if msg.media and not msg.sticker:
                media_file = await bot.download_media(msg)
                if media_file:
                    await safe_send(DEST_CHAT, media_file, msg, is_sticker=False)
                    try: os.remove(media_file) 
                    except: pass
                success_count += 1
            elif msg.sticker:
                sticker_file = await bot.download_media(msg)
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
            print(f"[BULK ERROR] Msg ID {msg.id}: {str(e)}")
            
    await event.respond(f"✅ **Done!** `{success_count}` restricted messages successfully re-uploaded.")

# LIVE FORWARDER (Anti-Restrict Version)
@bot.on(events.NewMessage)
async def main_forwarder(event):
    global SOURCE_CHAT, DEST_CHAT
    if not SOURCE_CHAT or not DEST_CHAT:
        return
        
    if event.chat_id == SOURCE_CHAT:
        try:
            if event.media and not event.sticker:
                media_file = await bot.download_media(event.message)
                if media_file:
                    await safe_send(DEST_CHAT, media_file, event.message, is_sticker=False)
                    try: os.remove(media_file)
                    except: pass
            elif event.sticker:
                media_file = await bot.download_media(event.message)
                if media_file:
                    await safe_send(DEST_CHAT, media_file, event.message, is_sticker=True)
                    try: os.remove(media_file)
                    except: pass
            elif event.message.message:
                await safe_send_text(DEST_CHAT, event.message)
                
        except Exception as e:
            print(f"[LIVE ERROR] {str(e)}")

if __name__ == "__main__":
    print("🚀 Telethon Bot Engine Successfully Activated 24/7!")
    bot.start()
    bot.loop.create_task(keep_offline_loop())
    bot.run_until_disconnected()
