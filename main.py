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

# STEALTH MODE: Is baar interval 2 second hai aur har action se pehle trigger hoga
async def force_offline():
    try:
        await bot(UpdateStatusRequest(offline=True))
    except:
        pass

async def keep_offline_loop():
    while True:
        await force_offline()
        await asyncio.sleep(3)

# 4. FIXED BULK FORWARDING (Direct Server Forwarding - Zero Uploading, Fully Invisible)
@bot.on(events.NewMessage(pattern=r",forward (\d+)", outgoing=True))
async def bulk_forward(event):
    global SOURCE_CHAT, DEST_CHAT
    
    if not SOURCE_CHAT or not DEST_CHAT:
        await event.edit("❌ **Railway Variables check karo! SOURCE_CHAT/DEST_CHAT missing hai.**")
        return
        
    count = int(event.pattern_match.group(1))
    await event.edit(f"⏳ **Direct Server-Side Copy Active!**\nPichle `{count}` messages bina online aaye bhej raha hoon...")
    
    # Source chat se saare message IDs nikalna
    msg_ids = []
    async for msg in bot.iter_messages(SOURCE_CHAT, limit=count):
        msg_ids.append(msg.id)
    
    # Purane se naye sequence me karne ke liye reverse
    msg_ids.reverse()
    
    # Chunk me forward karna taaki flood wait na aaye
    success_count = 0
    chunk_size = 10  # Ek baar me 10 message
    
    for i in range(0, len(msg_ids), chunk_size):
        await force_offline() # Send karne se theek pehle offline push karna
        chunk = msg_ids[i:i+chunk_size]
        try:
            # Direct server forward logic (Isme download/upload nahi hota, direct copy hota hai)
            await bot.forward_messages(DEST_CHAT, chunk, SOURCE_CHAT)
            success_count += len(chunk)
            await asyncio.sleep(2)  # Safe delay
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds + 2)
        except Exception as e:
            print(f"[BULK CHUNK ERROR] {str(e)}")
            
    await event.respond(f"✅ **Done!** `{success_count}` messages safely copied via server.")

# 5. LIVE FORWARDER (With Anti-Online Guard)
@bot.on(events.NewMessage)
async def main_forwarder(event):
    global SOURCE_CHAT, DEST_CHAT
    if not SOURCE_CHAT or not DEST_CHAT:
        return
        
    if event.chat_id == SOURCE_CHAT:
        await force_offline() # Live message aate hi pehle offline force karo
        try:
            # Direct forward single message to prevent downloading overhead
            await bot.forward_messages(DEST_CHAT, event.message)
        except Exception as e:
            print(f"[LIVE ERROR] {str(e)}")

if __name__ == "__main__":
    print("🚀 Telethon Bot Engine Successfully Activated 24/7!")
    bot.start()
    bot.loop.create_task(keep_offline_loop())
    bot.run_until_disconnected()
