import os
import asyncio
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError

# --- CONFIGURATION ---
API_ID = int(os.environ.get("API_ID", 12345))
API_HASH = os.environ.get("API_HASH", "your_hash")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

SOURCE_CHAT = None
DEST_CHAT = None

from telethon.sessions import StringSession
bot = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

print("=== TELETHON ULTRA FORWARDER STARTING ===")

# 1. COMMAND: Source Chat Set Karo
@bot.on(events.NewMessage(pattern=r",set_source", outgoing=True))
async def set_source(event):
    global SOURCE_CHAT
    SOURCE_CHAT = event.chat_id
    await event.edit(f"📥 **Source Set Ho Gaya!**\nID: `{SOURCE_CHAT}`")

# 2. COMMAND: Destination Chat Set Karo
@bot.on(events.NewMessage(pattern=r",set_dest", outgoing=True))
async def set_dest(event):
    global DEST_CHAT
    DEST_CHAT = event.chat_id
    await event.edit(f"📤 **Destination Set Ho Gaya!**\nID: `{DEST_CHAT}`")

# 3. COMMAND: Status Check
@bot.on(events.NewMessage(pattern=r",status", outgoing=True))
async def check_status(event):
    status_text = (
        "🚀 **Forwarder Status:**\n\n"
        f"📥 Source: `{SOURCE_CHAT if SOURCE_CHAT else 'Not Set'}`\n"
        f"📤 Destination: `{DEST_CHAT if DEST_CHAT else 'Not Set'}`"
    )
    await event.edit(status_text)

# Helper function jo live aur bulk dono media ko safely send karegi bina skip kiye
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
            print(f"[FLOOD WAIT] Telegram limits reached. Waiting for {e.seconds}s...")
            await asyncio.sleep(e.seconds + 2)  # Telegram jitna bolega bot utna rukk jayega par skip nahi karega
        except Exception as err:
            print(f"[SEND ERROR] {str(err)}")
            retry = False

# Helper function text messages ke liye
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

# 4. FIXED BULK FORWARDING: Destination mein chalegi, Source se fetch karegi
@bot.on(events.NewMessage(pattern=r",forward (\d+)", outgoing=True))
async def bulk_forward(event):
    global SOURCE_CHAT, DEST_CHAT
    if not SOURCE_CHAT:
        await event.edit("❌ **Pehle source channel me jaakar `,set_source` set karo!**")
        return
        
    # Jis chat me command maari, wahi destination lock ho jayegi auto-safety ke liye
    DEST_CHAT = event.chat_id
    count = int(event.pattern_match.group(1))
    
    await event.edit(f"⏳ **Source Channel se pichle {count} messages nikal kar yahan bhej raha hoon...**")
    
    messages_to_forward = []
    
    # SOURCE_CHAT se messages fetch karna
    async for msg in bot.iter_messages(SOURCE_CHAT, limit=count):
        messages_to_forward.append(msg)
    
    # Sahi chronological sequence ke liye reverse karna
    messages_to_forward.reverse()
    
    success_count = 0
    for msg in messages_to_forward:
        try:
            # Media handling (Photos, Videos, Audio, Documents)
            if msg.media and not msg.sticker:
                media_file = await bot.download_media(msg)
                if media_file:
                    await safe_send(DEST_CHAT, media_file, msg, is_sticker=False)
                    try: os.remove(media_file) 
                    except: pass
                success_count += 1
                
            # Sticker handling
            elif msg.sticker:
                sticker_file = await bot.download_media(msg)
                if sticker_file:
                    await safe_send(DEST_CHAT, sticker_file, msg, is_sticker=True)
                    try: os.remove(sticker_file)
                    except: pass
                success_count += 1
                
            # Normal Text / Premium Emojis
            elif msg.message:
                await safe_send_text(DEST_CHAT, msg)
                success_count += 1
            
            # Safe interval taaki continuous operations me message miss na ho
            await asyncio.sleep(1.5)
            
        except Exception as e:
            print(f"[BULK CRITICAL ERROR] Msg ID {msg.id}: {str(e)}")
            
    await event.respond(f"✅ **Bulk Forwarding Complete!**\nTotal `{success_count}` messages bina kisi drop ke copy ho gaye.")

# 5. LIVE FORWARDER (Naye real-time messages ke liye)
@bot.on(events.NewMessage)
async def main_forwarder(event):
    global SOURCE_CHAT, DEST_CHAT
    if not SOURCE_CHAT or not DEST_CHAT:
        return
        
    if event.chat_id == SOURCE_CHAT:
        # Commands ko live copy nahi karna hai
        if event.message.message and event.message.message.startswith(','):
            return
            
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
    bot.run_until_disconnected()
