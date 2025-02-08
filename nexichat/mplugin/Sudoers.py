from typing import Optional

from pyrogram import Client, filters
from pyrogram.types import Message

from config import MONGO_URL, OWNER_ID
from nexichat import nexichat as app, SUDOERS
from nexichat.database import add_sudo, remove_sudo
from nexichat.utils.helpers import get_user_info

# Error messages
MONGO_MISSING_MSG = (
    "**Due to bot's privacy issues, you can't manage sudo users "
    "when using the default database.\n\n"
    "Please fill your `MONGO_DB_URI` in your vars to use this feature.**"
)

async def validate_user(client: Client, message: Message, user_input: str) -> Optional[int]:
    """Validate and fetch user ID from input"""
    if not user_input:
        await message.reply_text("Please reply to a user's message or provide a username/user_id.")
        return None

    try:
        if "@" in user_input:
            user_input = user_input.replace("@", "")
        user = await client.get_users(user_input)
        return user.id
    except Exception as e:
        await message.reply_text(f"Error fetching user: {e}")
        return None

@app.on_message(filters.command("addsudo") & filters.user(OWNER_ID))
async def add_sudo_user(client: Client, message: Message):
    """Add a user to sudoers"""
    if not MONGO_URL:
        return await message.reply_text(MONGO_MISSING_MSG)

    user_id = None
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    else:
        if len(message.command) < 2:
            return await message.reply_text("Please provide a username/user_id.")
        user_id = await validate_user(client, message, message.command[1])

    if not user_id:
        return

    if user_id in SUDOERS:
        return await message.reply_text(f"{user_id} is already a sudo user.")

    if await add_sudo(user_id):
        SUDOERS.add(user_id)
        await message.reply_text(f"✅ Added {user_id} to sudo users.")
    else:
        await message.reply_text("❌ Failed to add user to sudo.")

@app.on_message(filters.command(["rmsudo", "delsudo"]) & filters.user(OWNER_ID))
async def remove_sudo_user(client: Client, message: Message):
    """Remove a user from sudoers"""
    if not MONGO_URL:
        return await message.reply_text(MONGO_MISSING_MSG)

    user_id = None
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    else:
        if len(message.command) < 2:
            return await message.reply_text("Please provide a username/user_id.")
        user_id = await validate_user(client, message, message.command[1])

    if not user_id:
        return

    if user_id not in SUDOERS:
        return await message.reply_text(f"{user_id} is not a sudo user.")

    if await remove_sudo(user_id):
        SUDOERS.discard(user_id)
        await message.reply_text(f"✅ Removed {user_id} from sudo users.")
    else:
        await message.reply_text("❌ Failed to remove user from sudo.")

@app.on_message(filters.command(["sudo", "sudolist"]))
async def list_sudoers(client: Client, message: Message):
    """List all sudo users"""
    if not SUDOERS:
        return await message.reply_text("No sudo users found.")

    owner_info = await get_user_info(client, OWNER_ID)
    sudoers_info = [await get_user_info(client, uid) for uid in SUDOERS if uid != OWNER_ID]

    text = "👑 **Owner:**\n"
    text += f"➤ {owner_info}\n\n"

    if sudoers_info:
        text += "🔧 **Sudo Users:**\n"
        text += "\n".join(f"➤ {info}" for info in sudoers_info)

    await message.reply_text(text)
