import os
import asyncio
from telethon import TelegramClient, events

# --- CONFIGURATION ---
API_ID = int(os.environ.get("API_ID", 12345))
API_HASH = os.environ.get("API_HASH", "your_hash")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

# Live target variables
SOURCE_CHAT = None
DEST_CHAT = None

# Telethon Client string session ke sath initialize karna
from telethon.sessions import StringSession
bot = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

print("=== TELETHON ULTRA FORWARDER STARTING ===")

# 1. COMMAND: Source Channel Set Karo (,set_source)
@bot.on(events.NewMessage(pattern=r",set_source", outgoing=True))
async def set_source(event):
    global SOURCE_CHAT
    SOURCE_CHAT = event.chat_id
    await event.edit(f"📥 **Source Set Ho Gaya!**\nID: `{SOURCE_CHAT}`")

# 2. COMMAND: Destination Channel Set Karo (,set_dest)
@bot.on(events.NewMessage(pattern=r",set_dest", outgoing=True))
async def set_dest(event):
    global DEST_CHAT
    DEST_CHAT = event.chat_id
    await event.edit(f"📤 **Destination Set Ho Gaya!**\nID: `{DEST_CHAT}`")

# 3. COMMAND: Status Check (,status)
@bot.on(events.NewMessage(pattern=r",status", outgoing=True))
async def check_status(event):
    status_text = (
        "🚀 **Forwarder Status:**\n\n"
        f"📥 Source: `{SOURCE_CHAT if SOURCE_CHAT else 'Not Set'}`\n"
        f"📤 Destination: `{DEST_CHAT if DEST_CHAT else 'Not Set'}`"
    )
    await event.edit(status_text)

# 4. MAIN ANTI-RESTRICT FORWARDER (Photos, Videos, Captions & Premium Emojis)
@bot.on(events.NewMessage)
async def main_forwarder(event):
    global SOURCE_CHAT, DEST_CHAT
    if not SOURCE_CHAT or not DEST_CHAT:
        return
        
    # Check agar message target source se aaya hai
    if event.chat_id == SOURCE_CHAT:
        try:
            # Telethon me restricted bypass karne ke liye direct download/upload helper
            if event.media:
                print(f"[MEDIA] Downloading restricted media from message {event.id}...")
                media_file = await bot.download_media(event.message)
                
                if media_file:
                    print(f"[MEDIA] Uploading direct file to destination...")
                    await bot.send_file(
                        entity=DEST_CHAT,
                        file=media_file,
                        caption=event.message.message or ""
                    )
                    os.remove(media_file)
                    print("[SUCCESS] ✅ Media and caption forwarded directly!")
            
            # Agar sirf normal text message hai premium emojis ke sath
            elif event.message.message:
                await bot.send_message(entity=DEST_CHAT, message=event.message.message)
                print("[SUCCESS] ✅ Text message forwarded!")
                
        except Exception as e:
            print(f"[ERROR] Forwarding failed: {str(e)}")

if __name__ == "__main__":
    print("🚀 Telethon Bot Engine Successfully Activated 24/7!")
    bot.start()
    bot.run_until_disconnected()
