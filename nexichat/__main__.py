import sys
import asyncio
import importlib
from flask import Flask
import threading
import config
from nexichat import ID_CHATBOT
from pyrogram import idle
from pyrogram.types import BotCommand
from config import OWNER_ID
from nexichat import LOGGER, nexichat, userbot, load_clone_owners
from nexichat.modules import ALL_MODULES
from nexichat.modules.Clone import restart_bots
from nexichat.modules.Id_Clone import restart_idchatbots
import random

# Function to start the bot and set up commands
async def anony_boot():
    try:
        # Start the bot
        await nexichat.start()

        # Notify the owner that the bot has started
        try:
            await nexichat.send_message(int(OWNER_ID), f"**{nexichat.mention} Is started✅**")
        except Exception as ex:
            LOGGER.info(f"@{nexichat.username} Started, please start the bot from the owner ID.")
        
        # Restart cloned bots and ID chatbots
        asyncio.create_task(restart_bots())
        asyncio.create_task(restart_idchatbots())

        # Load clone owners
        await load_clone_owners()

        # Start the userbot if STRING1 is configured
        if config.STRING1:
            try:
                await userbot.start()
                try:
                    await nexichat.send_message(int(OWNER_ID), f"**Id-Chatbot Also Started✅**")
                except Exception as ex:
                    LOGGER.info(f"@{nexichat.username} Started, please start the bot from the owner ID.")
            except Exception as ex:
                LOGGER.error(f"Error in starting ID-chatbot: {ex}")
                pass

    except Exception as ex:
        LOGGER.error(ex)

    # Import all modules
    for all_module in ALL_MODULES:
        importlib.import_module("nexichat.modules." + all_module)
        LOGGER.info(f"Successfully imported: {all_module}")

    # Set bot commands
    try:
        await nexichat.set_bot_commands(
            commands=[
                BotCommand("start", "Start the bot"),
                BotCommand("help", "Get the help menu"),
                BotCommand("clone", "Make your own chatbot"),
                BotCommand("idclone", "Make your ID-chatbot"),
                BotCommand("cloned", "Get a list of all cloned bots"),
                BotCommand("ping", "Check if the bot is alive or dead"),
                BotCommand("lang", "Select bot reply language"),
                BotCommand("chatlang", "Get current chat language"),
                BotCommand("resetlang", "Reset to default bot language"),
                BotCommand("id", "Get user ID"),
                BotCommand("stats", "Check bot stats"),
                BotCommand("gcast", "Broadcast a message to groups/users"),
                BotCommand("chatbot", "Enable or disable chatbot"),
                BotCommand("status", "Check chatbot status"),
                BotCommand("shayri", "Get a random shayri"),
                BotCommand("ask", "Ask anything from ChatGPT"),
                BotCommand("repo", "Get chatbot source code"),
                BotCommand("weather", "Get the current weather"),
                BotCommand("guess", "Play a number guessing game"),
                BotCommand("bowling", "Play a bowling game"),
                BotCommand("football", "Play a football game"),
                BotCommand("basketball", "Play a basketball game"),
                BotCommand("dart", "Play a dart game"),
                BotCommand("dice", "Roll a dice"),
                BotCommand("tic_tac_toe", "Play Tic Tac Toe"),
            ]
        )
        LOGGER.info("Bot commands set successfully.")
    except Exception as ex:
        LOGGER.error(f"Failed to set bot commands: {ex}")

    LOGGER.info(f"@{nexichat.username} Started.")
    await idle()

# Define the Flask app
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running"

def run_flask():
    app.run(host="0.0.0.0", port=8000)

# Game: Bowling
async def bowling(update, context):
    score = random.randint(0, 300)
    await update.message.reply(f'You scored {score} in bowling!')

# Game: Football
async def football(update, context):
    result = random.choice(['Goal!', 'Miss!', 'Save!'])
    await update.message.reply(f'Football result: {result}')

# Game: Basketball
async def basketball(update, context):
    score = random.choice(['2 points!', '3 points!', 'Miss!'])
    await update.message.reply(f'Basketball result: {score}')

# Game: Dart
async def dart(update, context):
    score = random.randint(0, 180)
    await update.message.reply(f'You scored {score} in darts!')

# Game: Dice
async def dice(update, context):
    roll = random.randint(1, 6)
    await update.message.reply(f'You rolled a {roll}!')

# Game: Tic Tac Toe
async def tic_tac_toe(update, context):
    board = [' ' for _ in range(9)]
    display_board(update, board)
    context.user_data['tic_tac_toe_board'] = board
    context.user_data['tic_tac_toe_turn'] = 'X'
    await update.message.reply('Tic Tac Toe started! You are X. Send your move as a number (1-9)')

def display_board(update, board):
    board_display = f"""
    {board[0]} | {board[1]} | {board[2]}
    ---------
    {board[3]} | {board[4]} | {board[5]}
    ---------
    {board[6]} | {board[7]} | {board[8]}
    """
    update.message.reply(board_display)

async def tic_tac_toe_move(update, context):
    board = context.user_data.get('tic_tac_toe_board', None)
    turn = context.user_data.get('tic_tac_toe_turn', None)
    if not board or not turn:
        await update.message.reply('Please start a new game using /tic_tac_toe')
        return

    try:
        move = int(update.message.text) - 1
        if board[move] != ' ':
            await update.message.reply('Invalid move, try again.')
            return

        board[move] = turn
        display_board(update, board)

        if check_winner(board, turn):
            await update.message.reply(f'{turn} wins!')
            context.user_data.pop('tic_tac_toe_board')
            context.user_data.pop('tic_tac_toe_turn')
        elif ' ' not in board:
            await update.message.reply('It\'s a draw!')
            context.user_data.pop('tic_tac_toe_board')
            context.user_data.pop('tic_tac_toe_turn')
        else:
            context.user_data['tic_tac_toe_turn'] = 'O' if turn == 'X' else 'X'
            await update.message.reply(f'It\'s {context.user_data["tic_tac_toe_turn"]}\'s turn.')

    except (ValueError, IndexError):
        await update.message.reply('Please enter a valid move (1-9).')

def check_winner(board, turn):
    win_conditions = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]
    for condition in win_conditions:
        if board[condition[0]] == board[condition[1]] == board[condition[2]] == turn:
            return True
    return False

# Main function to start the bot and Flask server
if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    asyncio.get_event_loop().run_until_complete(anony_boot())
    LOGGER.info("Stopping nexichat Bot...")
