import os
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from pymongo import MongoClient
from dotenv import load_dotenv
from urllib.parse import quote as url_quote  # ✅ Correct replacement for url_quote

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
    file_url = file.file_path

    # Save the user data along with the image URL in MongoDB
    users_collection.update_one(
        {'user_id': user.id},
        {'$set': {'username': user.username, 'image_url': file_url}},
        upsert=True
    )

    await update.message.reply_text(f"Image uploaded! Here's your link: {file_url}")

# Function to retrieve stored image links
async def get_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_data = users_collection.find_one({'user_id': user.id})

    if user_data and 'image_url' in user_data:
        await update.message.reply_text(f"Your uploaded image link: {user_data['image_url']}")
    else:
        await update.message.reply_text("You have not uploaded any images yet.")

# Function to handle unknown messages
async def handle_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Sorry, I didn't understand that. Please send an image or use /start or /getlinks.")

# Main function to run the bot
def run_bot():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('getlinks', get_links))
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))  # ✅ Corrected import
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_unknown))  # ✅ Corrected import

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    from threading import Thread
    
    # Run Flask and Telegram bot simultaneously
    Thread(target=run_bot).start()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
