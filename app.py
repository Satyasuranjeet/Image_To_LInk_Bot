import telebot
import os
import pymongo
import datetime
import random
from flask import Flask, send_from_directory
from dotenv import load_dotenv
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import threading

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

# Generate a unique 4-digit ID
def generate_unique_id():
    return str(random.randint(1000, 9999))

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
    
    # Generate a unique 4-digit ID for the image
    unique_id = generate_unique_id()
    
    # Generate a filename using the ID and timestamp
    filename = f"{unique_id}_{message.chat.id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
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
        "image_id": unique_id,
        "timestamp": datetime.datetime.now()
    }
    collection.insert_one(image_data)
    
    # Generate a public URL for the uploaded image
    public_url = f"https://image-to-link-bot-ph5v.onrender.com/uploads/{filename}"
    bot.reply_to(message, f"✅ Image saved successfully!\nPublic URL: {public_url}\nImage ID: {unique_id}")

@bot.message_handler(func=lambda message: message.text == "📜 View My Images")
def list_images(message):
    user_id = message.chat.id
    images = collection.find({"user_id": user_id})
    response = "🖼 Your uploaded images:\n"
    for img in images:
        response += f"ID: {img['image_id']} - {img['file_path']}\n"
    bot.reply_to(message, response if response != "🖼 Your uploaded images:\n" else "No images found.")

@bot.message_handler(func=lambda message: message.text == "🗑 Delete Image")
def ask_delete_image(message):
    bot.reply_to(message, "Please send the Image ID of the image you want to delete.")

@bot.message_handler(func=lambda message: message.text.isdigit())
def delete_image(message):
    image_id = message.text
    image_data = collection.find_one({"image_id": image_id, "user_id": message.chat.id})
    if image_data:
        file_path = image_data['file_path']
        if os.path.exists(file_path):
            os.remove(file_path)
        collection.delete_one({"image_id": image_id})
        bot.reply_to(message, f"✅ Image with ID {image_id} deleted successfully.")
    else:
        bot.reply_to(message, "⚠ Image ID not found or you do not have permission to delete it.")

# Route to serve uploaded images
@app.route('/uploads/<filename>')
def serve_image(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route("/")
def home():
    return "Server is running! Telegram bot is active."

# Run Flask app in a separate thread
def run_flask():
    app.run(host="0.0.0.0", port=PORT, debug=True)

# Start the bot polling in a separate thread
def run_telegram_bot():
    bot.remove_webhook()  # Ensure that there are no conflicting webhooks
    bot.polling(none_stop=True)

if __name__ == "__main__":
    # Start both Flask and bot in separate threads
    threading.Thread(target=run_flask).start()
    threading.Thread(target=run_telegram_bot).start()
