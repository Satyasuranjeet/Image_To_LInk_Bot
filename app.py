import os
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

# Flask route to show the app is running
@app.route('/')
def home():
    return "Bot is active and running!"

def upload_to_image_upload_api(image_data, delay=False, background=None, enhance=False, width=None, height=None):
    """
    Upload image to the image upload API and return the response.
    """
    url = "https://api.apilayer.com/image_upload/upload"
    
    # Set headers with API key
    headers = {
        "apikey": IMAGE_UPLOAD_API_KEY
    }
    
    # Prepare query parameters
    params = {
        "delay": delay,
        "background": background,
        "enhance": enhance,
        "width": width,
        "height": height
    }
    
    # Send the image as a file upload
    files = {
        'image': ('image.jpg', image_data, 'image/jpeg')  # Changed field name to 'image'
    }
    
    response = requests.post(url, headers=headers, params=params, files=files)
    return response.json()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "👋 Welcome to the Image Upload Bot!\n\n"
        "Simply send me any image and I'll upload it for you."
    )
    bot.reply_to(message, welcome_text)

@bot.message_handler(content_types=['photo'])
def handle_image(message):
    try:
        processing_msg = bot.reply_to(message, "📤 Processing your image...")

        # Get the largest photo version
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        image_data = bot.download_file(file_info.file_path)

        # Upload to image service
        upload_response = upload_to_image_upload_api(image_data)
        
        if upload_response.get('success'):
            # Store data in MongoDB
            user_data = {
                'user_id': message.from_user.id,
                'username': message.from_user.username or "Unknown",
                'image_url': upload_response['data']['image_url'],
                'delete_url': upload_response['data'].get('delete_url', ''),
                'timestamp': message.date
            }
            collection.insert_one(user_data)

            # Send success message
            success_msg = (
                "✅ Image uploaded successfully!\n\n"
                f"🔗 View your image: {upload_response['data']['image_url']}\n\n"
                "📎 You can now share this link with anyone!"
            )
            bot.edit_message_text(
                success_msg,
                chat_id=processing_msg.chat.id,
                message_id=processing_msg.message_id
            )
        else:
            error_msg = "❌ Image upload failed. Please try again."
            if 'error' in upload_response:
                error_msg += f"\n\nError details: {upload_response['error']['message']}"
            bot.edit_message_text(
                error_msg,
                chat_id=processing_msg.chat.id,
                message_id=processing_msg.message_id
            )

    except Exception as e:
        bot.edit_message_text(
            f"❌ Error: {str(e)}",
            chat_id=processing_msg.chat.id,
            message_id=processing_msg.message_id
        )

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    # Run Flask and bot in separate threads
    threading.Thread(target=run_bot).start()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), use_reloader=False)