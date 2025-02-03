import telebot
import os
import pymongo
import datetime
from flask import Flask
from dotenv import load_dotenv
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# Load environment variables
load_dotenv()

TOKEN = os.getenv("TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
PORT = int(os.getenv("PORT", 5000))

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Ensure upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Connect to MongoDB
client = pymongo.MongoClient(MONGO_URI)
db = client["telegram_bot"]
collection = db["images"]

# Start command with options menu
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("📤 Upload Image"))
    markup.add(KeyboardButton("📜 View My Images"))
    markup.add(KeyboardButton("🗑 Delete Image"))
    bot.send_message(message.chat.id, "Welcome to the Image Bot! Choose an option:", reply_markup=markup)

@bot.message_handler(content_types=['photo'])
def handle_image(message):
    file_info = bot.get_file(message.photo[-1].file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    # Generate a unique filename
    filename = f"{message.chat.id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    
    # Save the image locally
    with open(file_path, 'wb') as new_file:
        new_file.write(downloaded_file)
    
    # Store in MongoDB
    image_data = {
        "user_id": message.chat.id,
        "username": message.chat.username,
        "first_name": message.chat.first_name,
        "last_name": message.chat.last_name,
        "file_path": file_path,
        "timestamp": datetime.datetime.now()
    }
    collection.insert_one(image_data)
    
    bot.reply_to(message, f"✅ Image saved locally at: {file_path}")

@bot.message_handler(func=lambda message: message.text == "📜 View My Images")
def list_images(message):
    user_id = message.chat.id
    images = collection.find({"user_id": user_id})
    response = "🖼 Your uploaded images:\n"
    for img in images:
        response += f"{img['file_path']}\n"
    bot.reply_to(message, response if response != "🖼 Your uploaded images:\n" else "No images found.")

@bot.message_handler(func=lambda message: message.text == "🗑 Delete Image")
def ask_delete_image(message):
    bot.reply_to(message, "Please send the file path of the image you want to delete.")

@bot.message_handler(func=lambda message: message.text.startswith("/delete") or os.path.exists(message.text))
def delete_image(message):
    file_path = message.text.split(' ')[1] if message.text.startswith("/delete") else message.text
    image_data = collection.find_one({"file_path": file_path, "user_id": message.chat.id})
    if image_data:
        if os.path.exists(file_path):
            os.remove(file_path)
        collection.delete_one({"file_path": file_path})
        bot.reply_to(message, "✅ Image deleted successfully.")
    else:
        bot.reply_to(message, "⚠ Image not found.")

@app.route("/")
def home():
    return "Server is running! Telegram bot is active."

if __name__ == "__main__":
    import threading
    bot_thread = threading.Thread(target=lambda: bot.polling(none_stop=True))
    bot_thread.start()
    app.run(host="0.0.0.0", port=PORT, debug=True)
