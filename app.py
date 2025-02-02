import os
import telebot
import requests
from dotenv import load_dotenv
from pymongo import MongoClient
import base64
from flask import Flask
import threading

# Initialize Flask app
app = Flask(__name__)

# Load environment variables
load_dotenv()

# Configure environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
IMAGE_UPLOAD_API_KEY = os.getenv('IMAGE_UPLOAD_API_KEY')  # API key for the new image upload API
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
    Upload image to the new image upload API and return the response.
    """
    url = "https://api.apilayer.com/image_upload/upload"
    
    # Preparing payload with required and optional parameters
    payload = {
        "apikey": IMAGE_UPLOAD_API_KEY,
        "delay": delay,
        "background": background,
        "enhance": enhance,
        "width": width,
        "height": height
    }
    
    # Sending the image as part of the body
    files = {
        'upload': ('image.jpg', image_data, 'image/jpeg')  # Adjust content type based on the image format
    }
    
    response = requests.post(url, params=payload, files=files)
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
        # Send processing message
        processing_msg = bot.reply_to(message, "📤 Processing your image...")

        # Get the largest version of the photo
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        
        # Download the image
        image_data = bot.download_file(file_info.file_path)
        
        # Upload to the new Image Upload API
        imgbb_response = upload_to_image_upload_api(image_data)
        
        if imgbb_response.get('success'):
            # Extract relevant data from the response
            data = imgbb_response['data']
            image_url = data['image_url']
            delete_url = data['delete_url']
            
            # Store in MongoDB
            user_data = {
                'user_id': message.from_user.id,
                'username': message.from_user.username or "Unknown",
                'image_url': image_url,
                'delete_url': delete_url,
                'timestamp': message.date
            }
            collection.insert_one(user_data)
            
            # Send success message
            success_message = (
                "✅ Image uploaded successfully!\n\n"
                f"🔗 View your image: {image_url}\n\n"
                "📎 You can now share this link with anyone!"
            )
            bot.edit_message_text(
                success_message,
                chat_id=processing_msg.chat.id,
                message_id=processing_msg.message_id
            )
            
        else:
            raise Exception("Image upload failed")
            
    except Exception as e:
        error_message = f"❌ Sorry, an error occurred: {str(e)}"
        bot.edit_message_text(
            error_message,
            chat_id=processing_msg.chat.id,
            message_id=processing_msg.message_id
        )

def bot_polling():
    print("🤖 Telegram Bot started polling...")
    bot.infinity_polling()

if __name__ == "__main__":
    # Start the bot polling in a separate thread
    bot_thread = threading.Thread(target=bot_polling)
    bot_thread.start()
    
    # Get port from environment variable (Render sets this)
    port = int(os.getenv('PORT', 5000))
    
    # Run Flask app
    print(f"🚀 Starting Flask server on port {port}...")
    app.run(host='0.0.0.0', port=port)
