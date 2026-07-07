import os
import asyncio
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from telethon.tl.functions.account import UpdateStatusRequest

# --- CONFIGURATION FROM RAILWAY VARIABLES ---
API_ID = int(os.environ.get("API_ID", 12345))
API_HASH = os.environ.get("API_HASH", "your_hash")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

# Ab IDs seedha Railway se load hongi, kisi command ki zaroorat nahi
try:
    SOURCE_CHAT = int(os.environ.get("SOURCE_CHAT", 0))
except:
    SOURCE_CHAT = os.environ.get("SOURCE_CHAT", "")

try:
    DEST_CHAT = int(os.environ.get("DEST_CHAT", 0))
except:
    DEST_CHAT = os.environ.get("DEST_CHAT", "")

from telethon.sessions import StringSession
bot = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

print("=== TELETHON ULTRA FORWARDER STARTING ===")

# GHOST MODE FUNCTION (Hamesha Offline rakhne ke liye)
async def keep_offline():
    while True:
        try:
            await bot(UpdateStatusRequest(offline=True))
        except Exception:
            pass
        await asyncio.sleep(30)

# Safely Media Sender
async def safe_send(entity, file_path, msg_obj, is_sticker=False):
    retry = True
    while retry:
        try:
            if is_sticker:
                await bot.send_file(entity=entity, file=file_path)
            else:
                await bot.send_file(
                    entity=entity,
                    file=file_path,
                    caption=msg_obj.message,
                    formatting_entities=msg_obj.entities
                )
            retry = False
        except FloodWaitError as e:
            print(f"[FLOOD WAIT] Waiting for {e.seconds}s...")
            await asyncio.sleep(e.seconds + 2)
        except Exception as err:
            print(f"[SEND ERROR] {str(err)}")
            retry = False

# Safely Text Sender
async def safe_send_text(entity, msg_obj):
    retry = True
    while retry:
        try:
            await bot.send_message(
                entity=entity,
                message=msg_obj.message,
                formatting_entities=msg_obj.entities
            )
            retry = False
        except FloodWaitError as e:
            print(f"[FLOOD WAIT] Waiting for {e.seconds}s...")
            await asyncio.sleep(e.seconds + 2)
        except Exception as err:
            print(f"[TEXT ERROR] {str(err)}")
            retry = False

# BULK FORWARDING: Ab ye sirf SAVED MESSAGES me chalegi aur Railway ke channels use karegi
@bot.on(events.NewMessage(pattern=r",forward (\d+)", outgoing=True))
async def bulk_forward(event):
    global SOURCE_CHAT, DEST_CHAT
    
    # Check karega ki command sirf Saved Messages me maari gayi ho
    if event.chat_id != (await bot.get_me()).id:
        return

    if not SOURCE_CHAT or not DEST_CHAT:
        await event.edit("❌ **Railway variables me SOURCE_CHAT aur DEST_CHAT set nahi hai!**")
        return
        
    count = int(event.pattern_match.group(1))
    await event.edit(f"⏳ **Saved Messages Command Detected!**\nSource se pichle {count} messages target destination me bhej raha hoon...")
    
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
            
    await event.respond(f"✅ **Bulk Forwarding Complete!**\nTotal `{success_count}` messages safely copy ho gaye.")

# LIVE FORWARDER (Naye real-time messages ke liye)
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

# MAIN EXECUTION
if __name__ == "__main__":
    print("🚀 Telethon Bot Engine Successfully Activated 24/7!")
    bot.start()
    bot.loop.create_task(keep_offline())
    bot.run_until_disconnected()
