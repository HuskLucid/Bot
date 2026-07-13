import os
import asyncio
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# --- DUMMY WEB SERVER FOR RENDER PING ---
class SimpleWebHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Bot Engine is Alive and Running 24/7!")
        
    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

def run_ping_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleWebHandler)
    print(f"🌍 Ping Server started on port {port}", flush=True)
    server.serve_forever()

# --- CONFIGURATION FROM RENDER ---
API_ID = int(os.environ.get("API_ID", 12345))
API_HASH = os.environ.get("API_HASH", "your_hash")
SESSION_STRING = os.environ.get("SESSION_STRING", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

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

user_client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
helper_bot = TelegramClient('helper_bot_session', API_ID, API_HASH)

print("=== TELETHON ULTRA SECURE FORWARDER STARTING ===", flush=True)

async def bot_send_media(entity, file_path, msg_obj, is_sticker=False):
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
        print(f"[BOT SEND ERROR] {str(err)}", flush=True)

async def bot_send_text(entity, msg_obj):
    try:
        await helper_bot.send_message(
            entity=entity,
            message=msg_obj.message,
            formatting_entities=msg_obj.entities
        )
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds + 2)
    except Exception as err:
        print(f"[BOT TEXT ERROR] {str(err)}", flush=True)

# BULK FORWARDING FROM DESTINATION CHANNEL
@user_client.on(events.NewMessage(pattern=r",forward (\d+)", outgoing=True))
async def bulk_forward(event):
    global SOURCE_CHAT, DEST_CHAT
    if event.chat_id != DEST_CHAT:
        return
    if not SOURCE_CHAT or not DEST_CHAT:
        await event.edit("❌ **Variables missing hain!**")
        return
        
    count = int(event.pattern_match.group(1))
    await event.edit(f"⏳ **Processing Bulk Forwarding...**\n`{count}` posts copy ho rahi hain...")
    
    messages_to_forward = []
    async_messages = user_client.iter_messages(SOURCE_CHAT, limit=count)
    async for msg in async_messages:
        messages_to_forward.append(msg)
    
    messages_to_forward.reverse()
    
    success_count = 0
    for msg in messages_to_forward:
        try:
            if msg.media and not msg.sticker:
                media_file = await user_client.download_media(msg)
                if media_file:
                    await bot_send_media(DEST_CHAT, media_file, msg, is_sticker=False)
                    try: os.remove(media_file) 
                    except: pass
                success_count += 1
            elif msg.sticker:
                sticker_file = await user_client.download_media(msg)
                if sticker_file:
                    await bot_send_media(DEST_CHAT, sticker_file, msg, is_sticker=True)
                    try: os.remove(sticker_file)
                    except: pass
                success_count += 1
            elif msg.message:
                await bot_send_text(DEST_CHAT, msg)
                success_count += 1
            await asyncio.sleep(1.5)
        except Exception as e:
            print(f"[BULK ERROR] Msg ID {msg.id}: {str(e)}", flush=True)
            
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
                    await bot_send_media(DEST_CHAT, media_file, event.message, is_sticker=False)
                    try: os.remove(media_file)
                    except: pass
            elif event.sticker:
                media_file = await user_client.download_media(event.message)
                if media_file:
                    await bot_send_media(DEST_CHAT, media_file, event.message, is_sticker=True)
                    try: os.remove(media_file)
                    except: pass
            elif event.message.message:
                await bot_send_text(DEST_CHAT, event.message)
        except Exception as e:
            print(f"[LIVE ERROR] {str(e)}", flush=True)

# HANG-PROOF STARTUP LOGIC
async def start_engines():
    print("🚀 Telethon Hybrid Engine Activating...", flush=True)
    try:
        # User client ko bina hang kiye connect karna
        await user_client.connect()
        if not await user_client.is_user_authorized():
            print("❌ [CRITICAL] SESSION_STRING EXPIRED YA GALAT HAI! Bot login nahi kar pa raha.", flush=True)
            return
        
        print("✅ User Account Successfully Connected!", flush=True)
        
        # Helper Bot start karna
        await helper_bot.start(bot_token=BOT_TOKEN)
        print("🚀 Dual Engine Successfully Activated 24/7!", flush=True)
        
        await user_client.run_until_disconnected()
    except Exception as e:
        print(f"❌ [STARTUP ERROR] {str(e)}", flush=True)

if __name__ == "__main__":
    threading.Thread(target=run_ping_server, daemon=True).start()
    asyncio.run(start_engines())
