import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext
from telegram.ext.filters import Photo, Text
from pymongo import MongoClient
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

# Load environment variables
load_dotenv()

# MongoDB setup
client = MongoClient(os.getenv("MONGO_URI"))
db = client['telegram_bot']
users_collection = db['users']

# Initialize Flask app
app = Flask(__name__)

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Function to handle the /start command
async def start(update: Update, context: CallbackContext):
    user = update.message.from_user
    await update.message.reply_text(f"Hello {user.first_name}, I am your image upload bot. Send me an image!")

# Function to handle image uploads and store the data
async def handle_image(update: Update, context: CallbackContext):
    user = update.message.from_user
    file = await update.message.photo[-1].get_file()  # Get the largest photo (usually last in the list)
    file_url = file.file_url

    # Save the user data along with the image URL in MongoDB
    users_collection.update_one(
        {'user_id': user.id},
        {'$set': {'username': user.username, 'image_url': file_url}},
        upsert=True
    )

    await update.message.reply_text(f"Image uploaded successfully! Here's your link: {file_url}")

# Function to handle the /getlinks command to retrieve image URLs
async def get_links(update: Update, context: CallbackContext):
    user = update.message.from_user

    # Query MongoDB for the user's data
    user_data = users_collection.find_one({'user_id': user.id})
    
    if user_data and 'image_url' in user_data:
        await update.message.reply_text(f"Your uploaded image link: {user_data['image_url']}")
    else:
        await update.message.reply_text("You have not uploaded any images yet.")

# Function to handle unknown messages
async def handle_unknown(update: Update, context: CallbackContext):
    await update.message.reply_text("Sorry, I didn't understand that. Please send an image or use /start or /getlinks.")

# Flask home route
@app.route('/')
def home():
    return "Welcome to the Telegram Image Upload Bot API!"

# Main function to set up the bot and Flask server
def run_flask():
    # Start Flask web server
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))

async def run_bot():
    # Set up the Application (formerly Updater) for the Telegram bot
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Handlers for commands and messages
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('getlinks', get_links))
    application.add_handler(MessageHandler(Photo, handle_image))
    application.add_handler(MessageHandler(Text & ~Command, handle_unknown))

    # Start the bot polling
    await application.run_polling()

def main():
    # Run Flask and Telegram bot in parallel using threading
    flask_thread = Thread(target=run_flask)
    flask_thread.start()

    # Run the bot asynchronously
    asyncio.run(run_bot())

if __name__ == '__main__':
    main()
