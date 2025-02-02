import os
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from dotenv import load_dotenv
from flask import Flask

# Load environment variables
load_dotenv()

# Your Telegram bot token from BotFather
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Initialize Flask app
app = Flask(__name__)

# Command to start the bot
def start(update: Update, context: CallbackContext):
    user = update.message.from_user
    update.message.reply_text(f"Hello {user.first_name}, I'm your Python bot! How can I assist you today?")

# Command to echo the user's message
def echo(update: Update, context: CallbackContext):
    update.message.reply_text(update.message.text)

# Command for an example custom message
def custom_message(update: Update, context: CallbackContext):
    update.message.reply_text("This is a custom message!")

# Flask home route
@app.route('/')
def home():
    return "Welcome to the Telegram Bot Home Page!"

# Main function to set up the bot and Flask server
def main():
    # Set up the Updater and Dispatcher for the Telegram bot
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Add command handlers for Telegram Bot
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('custom', custom_message))

    # Add message handler for all text messages (echo functionality)
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

    # Start the bot polling in the background
    updater.start_polling()

    # Start the Flask web server
    app.run(port=5000)

if __name__ == '__main__':
    main()
