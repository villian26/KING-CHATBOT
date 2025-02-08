import sys
import asyncio
import importlib
from flask import Flask
import threading
import signal
import config
from nexichat import ID_CHATBOT
from pyrogram import idle
from pyrogram.types import BotCommand
from config import OWNER_ID
from nexichat import LOGGER, nexichat, userbot, load_clone_owners
from nexichat.modules import ALL_MODULES
from nexichat.modules.Clone import restart_bots
from nexichat.modules.Id_Clone import restart_idchatbots

# Initialize Flask app
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running"

def run_flask():
    app.run(host="0.0.0.0", port=8000)

async def anony_boot():
    try:
        # Start the main bot
        await nexichat.start()
        LOGGER.info(f"@{nexichat.username} started.")

        # Notify the owner
        try:
            await nexichat.send_message(int(OWNER_ID), f"**{nexichat.mention} is started ✅**")
        except Exception as ex:
            LOGGER.warning(f"Failed to send start message to owner: {ex}")

        # Start additional services
        await asyncio.gather(
            restart_bots(),
            restart_idchatbots(),
            load_clone_owners()
        )

        # Start userbot if STRING1 is configured
        if config.STRING1:
            try:
                await userbot.start()
                await nexichat.send_message(int(OWNER_ID), f"**Id-Chatbot also started ✅**")
            except Exception as ex:
                LOGGER.error(f"Error in starting id-chatbot: {ex}")

        # Import all modules
        for all_module in ALL_MODULES:
            try:
                importlib.import_module("nexichat.modules." + all_module)
                LOGGER.info(f"Successfully imported: {all_module}")
            except ImportError as ex:
                LOGGER.error(f"Failed to import module {all_module}: {ex}")

        # Set bot commands
        try:
            await nexichat.set_bot_commands([
                BotCommand("start", "Start the bot"),
                BotCommand("help", "Get the help menu"),
                BotCommand("clone", "Make your own chatbot"),
                BotCommand("idclone", "Make your id-chatbot"),
                BotCommand("cloned", "Get list of all cloned bots"),
                BotCommand("ping", "Check if the bot is alive or dead"),
                BotCommand("lang", "Select bot reply language"),
                BotCommand("chatlang", "Get current using language for chat"),
                BotCommand("resetlang", "Reset to default bot reply language"),
                BotCommand("id", "Get user's user_id"),
                BotCommand("stats", "Check bot stats"),
                BotCommand("gcast", "Broadcast any message to groups/users"),
                BotCommand("chatbot", "Enable or disable chatbot"),
                BotCommand("status", "Check chatbot enable or disable in chat"),
                BotCommand("shayri", "Get random shayri for love"),
                BotCommand("ask", "Ask anything from chatgpt"),
                BotCommand("repo", "Get chatbot source code"),
            ])
            LOGGER.info("Bot commands set successfully.")
        except Exception as ex:
            LOGGER.error(f"Failed to set bot commands: {ex}")

        # Keep the bot running
        await idle()

    except Exception as ex:
        LOGGER.error(f"Failed to start nexichat: {ex}")
    finally:
        LOGGER.info("Stopping nexichat Bot...")
        await nexichat.stop()
        if config.STRING1:
            await userbot.stop()

def signal_handler(signal, frame):
    LOGGER.info("Shutting down gracefully...")
    asyncio.get_event_loop().create_task(shutdown())

async def shutdown():
    await nexichat.stop()
    if config.STRING1:
        await userbot.stop()
    sys.exit(0)

if __name__ == "__main__":
    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True  # Daemonize thread to exit when the main program exits
    flask_thread.start()

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start the bot
    try:
        asyncio.get_event_loop().run_until_complete(anony_boot())
    except Exception as ex:
        LOGGER.error(f"Error in main loop: {ex}")
    finally:
        LOGGER.info("Application stopped.")
