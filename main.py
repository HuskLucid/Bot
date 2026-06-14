import os
import asyncio
from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler

# --- CONFIGURATION ---
# Railway ke dashboard se automatic load hone ke liye variables
API_ID = int(os.environ.get("API_ID", 12345))          # Apni API ID se badlein agar locally chala rahe hain
API_HASH = os.environ.get("API_HASH", "your_hash")    # Apne API HASH se badlein
SESSION_STRING = os.environ.get("SESSION_STRING", "") # Telegram Account String Session

# Global variables jo live commands se set honge (Code me ID badalne ki zaroorat nahi)
SOURCE_CHAT = None
DEST_CHAT = None

# Pure Pyrogram Client Initialize karna
if SESSION_STRING:
    app = Client("my_forwarder_bot", session_string=SESSION_STRING)
else:
    app = Client("my_forwarder_bot", api_id=API_ID, api_hash=API_HASH)

print("=== FRESH START: PURE PYROGRAM FORWARDER COMPILING ===")

# 1. COMMAND: Source Channel Set Karne Ke Liye (,set_source)
@app.on_message(filters.command("set_source", prefixes=",") & filters.me)
async def set_source_channel(client, message):
    global SOURCE_CHAT
    SOURCE_CHAT = message.chat.id
    await message.edit(f"📥 **Source Set Ho Gaya!**\nAb is channel/group ke saare naye messages track honge.\nID: `{SOURCE_CHAT}`")

# 2. COMMAND: Destination Channel Set Karne Ke Liye (,set_dest)
@app.on_message(filters.command("set_dest", prefixes=",") & filters.me)
async def set_destination_channel(client, message):
    global DEST_CHAT
    DEST_CHAT = message.chat.id
    await message.edit(f"📤 **Destination Set Ho Gaya!**\nSaare messages ab yahan bhejenge.\nID: `{DEST_CHAT}`")

# 3. COMMAND: Bot Ka Status Check Karne Ke Liye (,status)
@app.on_message(filters.command("status", prefixes=",") & filters.me)
async def check_status(client, message):
    status_msg = (
        "🚀 **Custom Forwarder Status:**\n\n"
        f"📥 Source: `{SOURCE_CHAT if SOURCE_CHAT else 'Not Set (Use ,set_source)'}`\n"
        f"📤 Destination: `{DEST_CHAT if DEST_CHAT else 'Not Set (Use ,set_dest)'}`"
    )
    await message.edit(status_msg)

# 4. MAIN FORWARDER FUNCTION (Anti-Restrict Protection & Direct Media)
async def automatic_forwarder_logic(client, message):
    global SOURCE_CHAT, DEST_CHAT
    
    # Agar dono me se ek bhi set nahi hai, toh kuch nahi karega
    if not SOURCE_CHAT or not DEST_CHAT:
        return
        
    # Sirf hamare target source chat se aaye messages ko process karega
    if message.chat.id == SOURCE_CHAT:
        try:
            caption_text = message.text or message.caption or ""
            
            # STICKER BYPASS (Premium & Normal)
            if message.sticker:
                sticker_file = await client.download_media(message)
                if sticker_file:
                    await client.send_sticker(chat_id=DEST_CHAT, sticker=sticker_file)
                    os.remove(sticker_file)
                    
            # DIRECT PHOTO BYPASS
            elif message.photo:
                photo_file = await client.download_media(message)
                if photo_file:
                    await client.send_photo(chat_id=DEST_CHAT, photo=photo_file, caption=caption_text)
                    os.remove(photo_file)
                    
            # DIRECT VIDEO BYPASS
            elif message.video:
                video_file = await client.download_media(message)
                if video_file:
                    await client.send_video(chat_id=DEST_CHAT, video=video_file, caption=caption_text)
                    os.remove(video_file)
                    
            # ANIMATION / GIF BYPASS
            elif message.animation:
                gif_file = await client.download_media(message)
                if gif_file:
                    await client.send_animation(chat_id=DEST_CHAT, animation=gif_file, caption=caption_text)
                    os.remove(gif_file)
                    
            # PURE TEXT & PREMIUM EMOJIS BYPASS
            elif caption_text:
                await client.send_message(chat_id=DEST_CHAT, text=caption_text)
                
        except Exception as e:
            print(f"[ERROR] Forward failed: {str(e)}")

# Raw/Normal dono updates ko listen karne ke liye handler attach karna
app.add_handler(MessageHandler(automatic_forwarder_logic), group=1)

if __name__ == "__main__":
    print("🚀 24/7 Custom Forwarder Engine Started Successfully!")
    app.run()
