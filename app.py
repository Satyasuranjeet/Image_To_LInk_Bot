import telebot
import requests
import base64
import os
import dotenv
from pymongo import MongoClient

# Load environment variables
dotenv.load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
IMG_API_KEY = os.getenv("IMG_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "image_uploads")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "users")

# Initialize bot and database
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

def get_ip():
    try:
        return requests.get("https://api64.ipify.org?format=json").json().get("ip")
    except:
        return "Unknown"

@bot.message_handler(content_types=['photo'])
def handle_image(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    username = message.from_user.username if message.from_user.username else "Unknown"
    user_ip = get_ip()
    file_id = message.photo[-1].file_id
    
    # Get the file path
    file_info = bot.get_file(file_id)
    file_path = file_info.file_path
    
    # Download the image
    image_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
    response = requests.get(image_url)
    
    if response.status_code != 200:
        bot.send_message(chat_id, "Failed to download the image.")
        return
    
    encoded_image = base64.b64encode(response.content).decode("utf-8")
    
    # Upload to ImgBB
    img_response = requests.post(
        "https://api.imgbb.com/1/upload",
        data={"key": IMG_API_KEY, "image": encoded_image}
    )
    
    if img_response.status_code != 200:
        bot.send_message(chat_id, "Image upload failed.")
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
    
    bot.send_message(chat_id, f"✅ Image uploaded successfully!\n🔗 {image_url}")

bot.polling()
