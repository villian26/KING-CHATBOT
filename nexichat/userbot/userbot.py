import asyncio
import logging
from typing import Optional

from pyrogram import Client
from pyrogram.types import User
import config

# Configure logging
logging.basicConfig(
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    handlers=[logging.FileHandler("log.txt"), logging.StreamHandler()],
    level=logging.INFO,
)

LOGGER = logging.getLogger(__name__)

class Userbot:
    """Custom Pyrogram client for Userbot functionality"""

    def __init__(self):
        self.client: Optional[Client] = None
        self.user: Optional[User] = None

    async def start(self):
        """Start the userbot client with error handling"""
        if not config.STRING1:
            LOGGER.warning("STRING1 not found in config. Userbot will not start.")
            return

        try:
            self.client = Client(
                name="VIPAss1",
                api_id=config.API_ID,
                api_hash=config.API_HASH,
                session_string=str(config.STRING1),
                no_updates=True,  # Disable updates for better performance
                plugins=dict(root="nexichat.idchatbot"),
            )

            await self.client.start()
            self.user = await self.client.get_me()

            # Join required channels
            await self._join_channels()

            LOGGER.info(
                f"Userbot started successfully as {self.user.first_name} (ID: {self.user.id})"
            )
        except Exception as e:
            LOGGER.error(f"Failed to start userbot: {e}")
            raise

    async def _join_channels(self):
        """Join required channels/groups"""
        channels = ["ll_KINGDOM_ll", "ll_IMPERIAL_ll"]
        for channel in channels:
            try:
                await self.client.join_chat(channel)
                LOGGER.info(f"Joined channel: {channel}")
            except Exception as e:
                LOGGER.warning(f"Failed to join channel {channel}: {e}")

    async def stop(self):
        """Stop the userbot client gracefully"""
        if self.client:
            LOGGER.info("Stopping userbot...")
            try:
                await self.client.stop()
                LOGGER.info("Userbot stopped successfully")
            except Exception as e:
                LOGGER.error(f"Error stopping userbot: {e}")
        else:
            LOGGER.warning("Userbot is not running.")

    @property
    def is_initialized(self) -> bool:
        """Check if the userbot is initialized"""
        return self.client is not None and self.user is not None

    @property
    def mention(self) -> str:
        """Get the userbot's mention"""
        return self.user.mention if self.user else "Userbot"

    @property
    def username(self) -> Optional[str]:
        """Get the userbot's username"""
        return self.user.username if self.user else None

# Example usage
async def main():
    userbot = Userbot()
    try:
        await userbot.start()
        print(f"Userbot started as {userbot.mention}")
    except Exception as e:
        print(f"Failed to start userbot: {e}")
    finally:
        await userbot.stop()

if __name__ == "__main__":
    asyncio.run(main())
