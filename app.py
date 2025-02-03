from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from pymongo import MongoClient
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import logging
from datetime import datetime
import json
import os
import io
from dotenv import load_dotenv
from flask import Flask
import threading

# Load environment variables
load_dotenv()

# Flask app for keeping the bot alive
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration from environment variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
MONGODB_URI = os.getenv('MONGODB_URI')
GOOGLE_CREDENTIALS_JSON = os.getenv('GOOGLE_CREDENTIALS_JSON')
PORT = int(os.getenv('PORT', 8080))  # Get port from environment variable or default to 8080

# [Previous bot code remains exactly the same until the main() function]

def run_flask():
    """Run Flask app"""
    app.run(host='0.0.0.0', port=PORT)

def main():
    """Start the bot and the web server."""
    try:
        # Start Flask in a separate thread
        flask_thread = threading.Thread(target=run_flask)
        flask_thread.start()
        logger.info(f"Flask web server started on port {PORT}")

        # Create application and add handlers
        application = Application.builder().token(TELEGRAM_TOKEN).build()

        # Add command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("history", get_history))
        
        # Add photo handler
        application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        
        # Add error handler
        application.add_error_handler(error_handler)

        # Start the bot
        logger.info("Starting bot...")
        application.run_polling()
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise

if __name__ == '__main__':
    main()