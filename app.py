import os
import logging
import asyncio
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Flask App
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running"

# MongoDB setup
client = MongoClient(os.getenv("MONGO_URI"))
db = client['telegram_bot']
users_collection = db['users']

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Function to handle /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    await update.message.reply_text(f"Hello {user.first_name}, I am your image upload bot. Send me an image!")

# Function to handle image uploads
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    file = await update.message.photo[-1].get_file()

    # Download the image locally
    file_path = f"uploads/{user.id}_{file.file_id}.jpg"
    os.makedirs("uploads", exist_ok=True)
    await file.download(custom_path=file_path)

    # Store the image reference in MongoDB
    users_collection.update_one(
        {'user_id': user.id},
        {'$set': {'username': user.username, 'image_path': file_path}},
        upsert=True
    )

    await update.message.reply_text(f"Image uploaded! You can access it later using /getlinks.")

# Function to retrieve stored image links
async def get_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_data = users_collection.find_one({'user_id': user.id})

    if user_data and 'image_path' in user_data:
        await update.message.reply_text(f"Your uploaded image is stored at: {user_data['image_path']}")
    else:
        await update.message.reply_text("You have not uploaded any images yet.")

# Function to handle unknown messages
async def handle_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Sorry, I didn't understand that. Please send an image or use /start or /getlinks.")

# Run Telegram bot asynchronously
async def run_bot():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('getlinks', get_links))
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_unknown))

    logging.info("Bot is running...")
    await app.run_polling()

# Run both Flask and Telegram Bot together
async def main():
    bot_task = asyncio.create_task(run_bot())  # Runs the Telegram bot asynchronously
    flask_task = asyncio.to_thread(app.run, host='0.0.0.0', port=int(os.getenv('PORT', 5000)))  # Runs Flask in a separate thread
    await asyncio.gather(bot_task, flask_task)  # Runs both tasks concurrently

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())  # Start the event loop
