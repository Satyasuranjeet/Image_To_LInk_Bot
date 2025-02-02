import os
import threading
import telebot
import requests
from dotenv import load_dotenv
from pymongo import MongoClient
from flask import Flask

# Initialize Flask app
app = Flask(__name__)

# Load environment variables
load_dotenv()

# Configure environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
IMAGE_UPLOAD_API_KEY = os.getenv('IMAGE_UPLOAD_API_KEY')
MONGO_URI = os.getenv('MONGO_URI')
DB_NAME = os.getenv('DB_NAME', 'image_uploads')
COLLECTION_NAME = os.getenv('COLLECTION_NAME', 'users')

# Initialize bot and database
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

@app.route('/')
def home():
    return "Bot is active and running!"

def upload_to_image_upload_api(image_data):
    """
    Modified to handle API parameters correctly
    """
    url = "https://api.apilayer.com/image_upload/upload"

    headers = {
        "apikey": IMAGE_UPLOAD_API_KEY
    }

    # Prepare form data parameters
    params = {
        "enhance": "true",  # API typically expects string values
        "delay": "false"
    }

    files = {
        # Try different field names if this doesn't work
        'image': ('image.jpg', image_data, 'image/jpeg')
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            data=params,
            files=files,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API Request Error: {str(e)}")
        return {"success": False, "error": str(e)}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "👋 Welcome! Send me an image to upload.")

@bot.message_handler(content_types=['photo'])
def handle_image(message):
    try:
        msg = bot.reply_to(message, "⏳ Processing your image...")

        # Get image file
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        image_data = bot.download_file(file_info.file_path)

        # Upload to API
        result = upload_to_image_upload_api(image_data)

        if isinstance(result, dict) and result.get('success'):
            # Store in database
            collection.insert_one({
                "user_id": message.from_user.id,
                "image_url": result.get('data', {}).get('image_url', ''),
                "timestamp": message.date
            })

            # Send response
            bot.edit_message_text(
                f"✅ Upload successful!\n{result.get('data', {}).get('image_url', '')}",
                chat_id=msg.chat.id,
                message_id=msg.message_id
            )
        else:
            error = result.get('error', {}).get('message', 'Unknown error')
            bot.edit_message_text(
                f"❌ Upload failed: {error}",
                chat_id=msg.chat.id,
                message_id=msg.message_id
            )

    except Exception as e:
        bot.reply_to(message, f"🔥 Critical error: {str(e)}")

def run_bot():
    print("🤖 Bot started polling...")
    bot.infinity_polling()

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), use_reloader=False)