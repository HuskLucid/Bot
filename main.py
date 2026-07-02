import os
import asyncio
from telethon import TelegramClient, events

# --- CONFIGURATION ---
API_ID = int(os.environ.get("API_ID", 12345))
API_HASH = os.environ.get("API_HASH", "your_hash")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

SOURCE_CHAT = None
DEST_CHAT = None

from telethon.sessions import StringSession
bot = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

print("=== TELETHON ULTRA FORWARDER STARTING ===")

@bot.on(events.NewMessage(pattern=r",set_source", outgoing=True))
async def set_source(event):
    global SOURCE_CHAT
    SOURCE_CHAT = event.chat_id
    await event.edit(f"📥 **Source Set Ho Gaya!**\nID: `{SOURCE_CHAT}`")

@bot.on(events.NewMessage(pattern=r",set_dest", outgoing=True))
async def set_dest(event):
    global DEST_CHAT
    DEST_CHAT = event.chat_id
    await event.edit(f"📤 **Destination Set Ho Gaya!**\nID: `{DEST_CHAT}`")

@bot.on(events.NewMessage(pattern=r",status", outgoing=True))
async def check_status(event):
    status_text = (
        "🚀 **Forwarder Status:**\n\n"
        f"📥 Source: `{SOURCE_CHAT if SOURCE_CHAT else 'Not Set'}`\n"
        f"📤 Destination: `{DEST_CHAT if DEST_CHAT else 'Not Set'}`"
    )
    await event.edit(status_text)

# 4. MAIN ANTI-RESTRICT FORWARDER (With Premium Emoji Support)
@bot.on(events.NewMessage)
async def main_forwarder(event):
    global SOURCE_CHAT, DEST_CHAT
    if not SOURCE_CHAT or not DEST_CHAT:
        return
        
    if event.chat_id == SOURCE_CHAT:
        try:
            # 1. AGAR MESSAGE ME MEDIA HAI (Photo, Video, GIF)
            if event.media and not event.sticker:
                print(f"[MEDIA] Downloading restricted media...")
                media_file = await bot.download_media(event.message)
                
                if media_file:
                    # send_file me direct event.message bhejne se text, caption aur PREMIUM EMOJIS sab sath chale jaate hain
                    await bot.send_file(
                        entity=DEST_CHAT,
                        file=media_file,
                        caption=event.message
                    )
                    os.remove(media_file)
                    print("[SUCCESS] ✅ Media with Premium Emojis Sent!")
            
            # 2. AGAR STICKER HAI
            elif event.sticker:
                sticker_file = await bot.download_media(event.message)
                if sticker_file:
                    await bot.send_file(entity=DEST_CHAT, file=sticker_file)
                    os.remove(sticker_file)
                    print("[SUCCESS] ✅ Sticker Sent!")
            
            # 3. AGAR SIRF NORMAL TEXT HAI (With Premium Emojis)
            elif event.message.message:
                # Direct event.message object ko send karne se premium custom emojis 100% work karenge
                await bot.send_message(entity=DEST_CHAT, message=event.message)
                print("[SUCCESS] ✅ Text with Premium Emojis Sent!")
                
        except Exception as e:
            print(f"[ERROR] Forwarding failed: {str(e)}")

if __name__ == "__main__":
    print("🚀 Telethon Bot Engine Successfully Activated 24/7!")
    bot.start()
    bot.run_until_disconnected()
