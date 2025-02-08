import asyncio
import random
from typing import Dict, List, Optional

from deep_translator import GoogleTranslator
from pymongo import MongoClient
from pyrogram import Client, filters
from pyrogram.enums import ChatAction, ChatMemberStatus as CMS
from pyrogram.errors import MessageEmpty
from pyrogram.types import (CallbackQuery, InlineKeyboardButton,
                            InlineKeyboardMarkup, Message)

from config import MONGO_URL, OWNER_ID
from nexichat import LOGGER, db, mongo, nexichat
from nexichat.database import abuse_list, add_served_cchat, add_served_cuser, chatai
from nexichat.database.chats import add_served_chat
from nexichat.database.users import add_served_user
from nexichat.mplugin.helpers import languages

# Initialize MongoDB client
mongo_client = MongoClient(MONGO_URL)
db = mongo_client.nexichat

# Collections
lang_db = db.chat_langs
status_db = db.chat_status
abuse_words_db = db.abuse_words

# Caches
replies_cache: List[Dict] = []
abuse_cache: List[str] = []
message_counts: Dict[int, int] = {}

async def initialize_caches():
    """Initialize all caches from database"""
    await asyncio.gather(
        load_abuse_cache(),
        load_replies_cache()
    )

async def load_abuse_cache():
    """Load abuse words from database"""
    global abuse_cache
    abuse_cache = [doc["word"] async for doc in abuse_words_db.find()]
    LOGGER.info(f"Loaded {len(abuse_cache)} abuse words")

async def add_abuse_word(word: str):
    """Add word to abuse list"""
    if word.lower() not in abuse_cache:
        await abuse_words_db.insert_one({"word": word.lower()})
        abuse_cache.append(word.lower())
        LOGGER.info(f"Added abuse word: {word}")

async def is_abusive(text: str) -> bool:
    """Check if text contains abusive content"""
    text_lower = text.lower()
    return any(word in text_lower for word in abuse_cache + abuse_list)

@nexichat.on_message(filters.command("block") & filters.user(OWNER_ID))
async def block_word(client: Client, message: Message):
    """Block a word"""
    if len(message.command) < 2:
        return await message.reply("⚠️ Usage: /block <word>")
    
    word = message.command[1].lower()
    await add_abuse_word(word)
    await message.reply(f"✅ Successfully blocked word: `{word}`")

@nexichat.on_message(filters.command("unblock") & filters.user(OWNER_ID))
async def unblock_word(client: Client, message: Message):
    """Unblock a word"""
    if len(message.command) < 2:
        return await message.reply("⚠️ Usage: /unblock <word>")
    
    word = message.command[1].lower()
    if word in abuse_cache:
        await abuse_words_db.delete_one({"word": word})
        abuse_cache.remove(word)
        await message.reply(f"✅ Successfully unblocked word: `{word}`")
    else:
        await message.reply(f"❌ Word not found: `{word}`")

@nexichat.on_message(filters.command("blocked") & filters.user(OWNER_ID))
async def list_blocked_words(client: Client, message: Message):
    """List blocked words"""
    if not abuse_cache:
        return await message.reply("❌ No words blocked yet")
    
    words = "\n".join(f"• `{word}`" for word in abuse_cache)
    await message.reply(f"🚫 Blocked Words:\n{words}")

async def save_reply(original: Message, reply: Message):
    """Save reply pattern to database"""
    try:
        if await is_abusive(original.text or "") or await is_abusive(reply.text or ""):
            return

        reply_data = {
            "word": original.text,
            "text": None,
            "media_type": "text"
        }

        # Handle media types
        media_mapping = {
            "sticker": "file_id",
            "photo": "file_id",
            "video": "file_id",
            "audio": "file_id",
            "animation": "file_id",
            "voice": "file_id"
        }

        for media_type, attr in media_mapping.items():
            if media := getattr(reply, media_type, None):
                reply_data.update({
                    "text": getattr(media, attr),
                    "media_type": media_type
                })
                break
        else:
            reply_data["text"] = reply.text

        if not await chatai.find_one(reply_data):
            await chatai.insert_one(reply_data)
            replies_cache.append(reply_data)

    except Exception as e:
        LOGGER.error(f"Error saving reply: {e}")

async def load_replies_cache():
    """Load replies from database"""
    global replies_cache
    replies_cache = await chatai.find().to_list(length=None)
    LOGGER.info(f"Loaded {len(replies_cache)} replies")

async def get_chat_language(chat_id: int) -> Optional[str]:
    """Get chat language preference"""
    lang = await lang_db.find_one({"chat_id": chat_id})
    return lang.get("language") if lang else "en"

async def get_response(text: str) -> Optional[Dict]:
    """Get random matching response"""
    if not replies_cache:
        await load_replies_cache()
    
    matches = [r for r in replies_cache if r["word"] == text]
    return random.choice(matches or replies_cache)

@nexichat.on_message(filters.text & ~filters.bot & ~filters.edited)
async def handle_chat(client: Client, message: Message):
    """Handle chatbot responses"""
    try:
        chat_id = message.chat.id
        bot_id = client.me.id
        
        # Check chatbot status
        status = await status_db.find_one({"chat_id": chat_id})
        if status and status.get("status") == "disabled":
            return

        # Update user/chat stats
        if message.chat.type in ["group", "supergroup"]:
            await add_served_cchat(bot_id, chat_id)
            await add_served_chat(chat_id)
        else:
            await add_served_cuser(bot_id, chat_id)
            await add_served_user(chat_id)

        # Generate response
        response = await get_response(message.text)
        if not response:
            return await message.reply("🤖 I'm still learning, please teach me!")

        # Translate response
        lang = await get_chat_language(chat_id)
        translated = GoogleTranslator(source="auto", target=lang).translate(response["text"])

        # Send response
        media_type = response.get("media_type")
        if media_type and media_type != "text":
            await getattr(message, f"reply_{media_type}")(response["text"])
        else:
            await message.reply(translated or response["text"])

        # Save conversation pattern
        if message.reply_to_message and message.reply_to_message.from_user.is_self:
            await save_reply(message.reply_to_message, message)

    except MessageEmpty:
        pass
    except Exception as e:
        LOGGER.error(f"Chatbot error: {e}", exc_info=True)

# Initialize caches on startup
asyncio.create_task(initialize_caches())
