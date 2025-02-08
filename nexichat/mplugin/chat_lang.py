import asyncio
import re
from typing import Dict, List, Optional

import aiohttp
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery

from nexichat import nexichat, db
from config import LANG_DETECTION_API
from nexichat.utils.helpers import get_chat_language, set_chat_language

# Message cache with TTL (300 seconds = 5 minutes)
message_cache: Dict[int, List[Message]] = {}
CACHE_SIZE = 30
CACHE_TTL = 300

@nexichat.on_message(filters.command("chatlang"))
async def chat_lang_handler(client: Client, message: Message):
    """Get current chat language"""
    chat_id = message.chat.id
    lang = await get_chat_language(chat_id)
    await message.reply(f"🌐 Current chat language: {lang or 'Not set!'}")

@nexichat.on_callback_query(filters.regex("^choose_lang$"))
async def lang_callback_handler(client: Client, query: CallbackQuery):
    """Handle language selection callback"""
    await query.answer()
    await query.message.edit_text(
        "Please choose your preferred language:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("English 🇺🇸", callback_data="lang_en"),
             InlineKeyboardButton("Hindi 🇮🇳", callback_data="lang_hi")],
            [InlineKeyboardButton("Cancel ❌", callback_data="lang_cancel")]
        ])
    )

@nexichat.on_callback_query(filters.regex("^lang_(.*)$"))
async def set_lang_handler(client: Client, query: CallbackQuery):
    """Set language from callback"""
    lang_code = query.data.split("_")[1]
    if lang_code == "cancel":
        await query.message.delete()
        return
    
    chat_id = query.message.chat.id
    await set_chat_language(chat_id, lang_code)
    await query.answer(f"Language set to {lang_code.upper()}!")
    await query.message.edit_text(f"✅ Successfully set language to {lang_code.upper()}")

async def detect_language(messages: List[str]) -> Optional[str]:
    """Detect language using external API"""
    try:
        history = "\n".join([f"- {msg}" for msg in messages])
        prompt = f"""
        Analyze these messages and identify the dominant language (ISO 639-1 code):
        {history}
        Respond ONLY with the 2-letter language code.
        """
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                LANG_DETECTION_API,
                params={"chat": prompt},
                timeout=10
            ) as response:
                result = await response.text()
                return re.search(r"[a-z]{2}", result.strip(), re.I).group().lower()
                
    except Exception as e:
        print(f"Language detection error: {e}")
        return None

async def process_message_batch(chat_id: int):
    """Process cached messages for a chat"""
    if chat_id not in message_cache:
        return
    
    messages = [msg.text for msg in message_cache[chat_id] if msg.text]
    if len(messages) < 5:  # Minimum messages for reliable detection
        return
    
    lang_code = await detect_language(messages)
    if not lang_code:
        return
    
    # Send detection result with action buttons
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Set Automatically", callback_data=f"lang_{lang_code}"),
         InlineKeyboardButton("🗣 Choose Manually", callback_data="choose_lang")]
    ])
    
    await nexichat.send_message(
        chat_id,
        f"🌍 Detected dominant language: {lang_code.upper()}\n"
        "Choose an option:",
        reply_markup=markup
    )
    message_cache.pop(chat_id, None)

@nexichat.on_message(filters.text & ~filters.bot & ~filters.command)
async def message_store_handler(client: Client, message: Message):
    """Store messages and trigger language detection"""
    chat_id = message.chat.id
    
    # Check existing language
    current_lang = await get_chat_language(chat_id)
    if current_lang and current_lang != "nolang":
        return
    
    # Initialize cache
    if chat_id not in message_cache:
        message_cache[chat_id] = []
        # Schedule cache cleanup
        asyncio.get_event_loop().call_later(
            CACHE_TTL, 
            lambda: message_cache.pop(chat_id, None)
        )
    
    # Add message to cache
    message_cache[chat_id].append(message)
    
    # Process when cache reaches threshold
    if len(message_cache[chat_id]) >= CACHE_SIZE:
        await process_message_batch(chat_id)
