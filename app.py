import os
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from pymongo import MongoClient
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

# MongoDB setup
client = MongoClient(os.getenv("MONGO_URI"))
db = client['telegram_bot']
users_collection = db['users']

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Function to handle start command
def start(update: Update, context: CallbackContext):
    user = update.message.from_user
    update.message.reply_text(f"Hello {user.first_name}, I am your image upload bot. Send me an image!")

# Function to handle image uploads
def handle_image(update: Update, context: CallbackContext):
    user = update.message.from_user
    file = update.message.photo[-1].get_file()
    file_url = file.file_url

    # Save the user data along with the image URL in MongoDB
    users_collection.update_one(
        {'user_id': user.id},
        {'$set': {'username': user.username, 'image_url': file_url}},
        upsert=True
    )

    update.message.reply_text(f"Image uploaded! Here's your link: {file_url}")

# Function to handle the command to get the generated image links
def get_links(update: Update, context: CallbackContext):
    user = update.message.from_user

    # Query MongoDB for the user's data
    user_data = users_collection.find_one({'user_id': user.id})
    
    if user_data and 'image_url' in user_data:
        update.message.reply_text(f"Your uploaded image link: {user_data['image_url']}")
    else:
        update.message.reply_text("You have not uploaded any images yet.")

# Function to handle unknown messages
def handle_unknown(update: Update, context: CallbackContext):
    update.message.reply_text("Sorry, I didn't understand that. Please send an image or use /start or /getlinks.")

# Main function to set up the bot
def main():
    # Set up the Updater and Dispatcher
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Handlers for commands and messages
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('getlinks', get_links))
    dispatcher.add_handler(MessageHandler(Filters.photo, handle_image))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_unknown))

    # Start polling for updates
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
