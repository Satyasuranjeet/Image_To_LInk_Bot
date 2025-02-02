import os
import telebot
import requests
import base64
import dotenv
from flask import Flask
from pymongo import MongoClient

# Load environment variables
dotenv.load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
IMG_API_KEY = os.getenv("IMG_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "image_uploads")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "users")

# Initialize Flask app
app = Flask(__name__)

# Initialize bot and database
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

# Home route to check if the server is active
@app.route('/')
def home():
    return "Hello, Active Server!"

# Function to get user's IP address
def get_ip():
    try:
        return requests.get("https://api64.ipify.org?format=json").json().get("ip")
    except:
        return "Unknown"

# Handle incoming /start command
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Hello! Please send me an image to upload.")

# Handle incoming photo messages
@bot.message_handler(content_types=['photo'])
def handle_image(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    username = message.from_user.username if message.from_user.username else "Unknown"
    user_ip = get_ip()
    file_id = message.photo[-1].file_id
    
    # Send loading message to indicate processing
    bot.send_message(chat_id, "🔄 Processing your image... Please wait.")
    
    try:
        # Get the file path
        file_info = bot.get_file(file_id)
        file_path = file_info.file_path
        
        # Download the image
        image_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
        response = requests.get(image_url)
        
        if response.status_code != 200:
            bot.send_message(chat_id, "❌ Failed to download the image.")
            return
        
        encoded_image = base64.b64encode(response.content).decode("utf-8")
        
        # Upload to ImgBB
        img_response = requests.post(
            "https://api.imgbb.com/1/upload",
            data={"key": IMG_API_KEY, "image": encoded_image}
        )
        
        if img_response.status_code != 200:
            bot.send_message(chat_id, "❌ Image upload failed.")
            return
        
        img_data = img_response.json().get("data")
        image_url = img_data.get("url")
        delete_url = img_data.get("delete_url")
        
        # Store in MongoDB
        collection.insert_one({
            "user_id": user_id,
            "username": username,
            "ip": user_ip,
            "image_url": image_url,
            "delete_url": delete_url
        })
        
        # Send success message with the image URL
        bot.send_message(chat_id, f"✅ Image uploaded successfully!\n🔗 {image_url}")
    
    except Exception as e:
        bot.send_message(chat_id, f"❌ An error occurred: {e}")

# Run Flask app
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))  # Render provides a PORT environment variable
    app.run(host="0.0.0.0", port=port)

    # Start bot polling in the background
    bot.polling(non_stop=True)
