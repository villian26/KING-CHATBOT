import logging
import signal
import time
from typing import Dict, Optional

from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient as MongoCli
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
import config
import uvloop

from Abg import patch  # Remove if unused
from nexichat.userbot.userbot import Userbot

# Initialize uvloop for better async performance
uvloop.install()

# Configure logging
logging.basicConfig(
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    handlers=[logging.FileHandler("log.txt"), logging.StreamHandler()],
    level=logging.INFO,
)

logging.getLogger("pyrogram").setLevel(logging.ERROR)
LOGGER = logging.getLogger(__name__)

# Global variables
ID_CHATBOT: Optional[int] = None
SUDOERS = filters.user()
CLONE_OWNERS: Dict[int, int] = {}
boot_time = time.time()

# MongoDB connections
mongo_client = MongoCli(config.MONGO_URL)
db = mongo_client.Anonymous
clone_db = mongo_client.VIP.clone_owners

class NexiChat(Client):
    """Custom Pyrogram client for NexiChat bot"""
    
    def __init__(self):
        super().__init__(
            name="nexichat",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            bot_token=config.BOT_TOKEN,
            in_memory=True,
            parse_mode=ParseMode.DEFAULT,
        )
        self.id: Optional[int] = None
        self.name: Optional[str] = None
        self.username: Optional[str] = None
        self.mention: Optional[str] = None

    async def start(self):
        """Start the bot client with error handling"""
        try:
            await super().start()
            me = await self.get_me()
            self.id = me.id
            self.name = f"{me.first_name} {me.last_name or ''}".strip()
            self.username = me.username
            self.mention = me.mention
            LOGGER.info(f"Bot started successfully: {self.mention}")
        except Exception as e:
            LOGGER.error(f"Failed to start bot: {e}")
            raise

    async def stop(self):
        """Stop the bot client gracefully"""
        await super().stop()
        LOGGER.info("Bot stopped successfully")

async def load_sudoers():
    """Load sudo users from database"""
    global SUDOERS
    try:
        sudoers = await clone_db.find_one({"sudo": "sudo"}) or {"sudoers": []}
        SUDOERS.add(config.OWNER_ID)
        for user_id in sudoers.get("sudoers", []):
            SUDOERS.add(user_id)
        LOGGER.info(f"Loaded {len(SUDOERS)} sudoers")
    except Exception as e:
        LOGGER.error(f"Error loading sudoers: {e}")

async def load_clone_owners():
    """Load clone bot owners from database"""
    global CLONE_OWNERS
    try:
        async for entry in clone_db.find({"bot_id": {"$exists": True}}):
            CLONE_OWNERS[entry["bot_id"]] = entry["user_id"]
        LOGGER.info(f"Loaded {len(CLONE_OWNERS)} clone owners")
    except Exception as e:
        LOGGER.error(f"Error loading clone owners: {e}")

async def save_clone_owner(bot_id: int, user_id: int):
    """Save clone bot owner to database"""
    try:
        await clone_db.update_one(
            {"bot_id": bot_id},
            {"$set": {"user_id": user_id}},
            upsert=True
        )
        CLONE_OWNERS[bot_id] = user_id
    except Exception as e:
        LOGGER.error(f"Error saving clone owner: {e}")

async def delete_clone_owner(bot_id: int):
    """Delete clone bot owner from database"""
    try:
        await clone_db.delete_one({"bot_id": bot_id})
        CLONE_OWNERS.pop(bot_id, None)
    except Exception as e:
        LOGGER.error(f"Error deleting clone owner: {e}")

def get_readable_time(seconds: int) -> str:
    """Convert seconds to human-readable time format"""
    periods = [
        ('day', 86400),
        ('hour', 3600),
        ('minute', 60),
        ('second', 1)
    ]
    
    result = []
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            plural = 's' if period_value > 1 else ''
            result.append(f"{period_value} {period_name}{plural}")
    
    return ", ".join(result) if result else "0 seconds"

async def graceful_shutdown(signal, loop):
    """Handle graceful shutdown"""
    LOGGER.info("Starting graceful shutdown...")
    await nexichat.stop()
    if userbot.is_initialized:
        await userbot.stop()
    mongo_client.close()
    loop.stop()
    LOGGER.info("Shutdown completed")

# Initialize clients
nexichat = NexiChat()
userbot = Userbot()

async def main():
    """Main application entry point"""
    try:
        # Initialize components
        await load_sudoers()
        await load_clone_owners()
        
        # Start clients
        await asyncio.gather(
            nexichat.start(),
            userbot.start()
        )
        
        # Send startup notification
        if config.OWNER_ID:
            try:
                await nexichat.send_message(
                    config.OWNER_ID,
                    f"🚀 **{nexichat.name} started successfully!**\n"
                    f"⏰ Uptime: {get_readable_time(int(time.time() - boot_time))}"
                )
            except Exception as e:
                LOGGER.warning(f"Failed to send startup message: {e}")

        # Set bot commands
        commands = [
            ("start", "Start the bot"),
            ("help", "Get help menu"),
            ("clone", "Create your chatbot"),
            ("stats", "View bot statistics"),
            ("ping", "Check bot latency"),
            ("gcast", "Broadcast message"),
            ("repo", "Get source code")
        ]
        
        await nexichat.set_bot_commands([
            BotCommand(cmd, desc) for cmd, desc in commands
        ])
        
        # Add signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(
                sig, 
                lambda: asyncio.create_task(graceful_shutdown(sig, loop))
            )
        
        # Keep running
        LOGGER.info("Bot is now running...")
        await idle()

    except Exception as e:
        LOGGER.error(f"Fatal error: {e}", exc_info=True)
    finally:
        await graceful_shutdown(None, asyncio.get_event_loop())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        LOGGER.info("Bot stopped by user")
