# Telegram Image Upload Bot 📸

This is a Telegram bot that allows users to upload images and receive a shareable link. It uses the ImgBB API for image hosting and MongoDB for storing user details.

## Features 🚀
- Upload images via Telegram
- Store uploaded images in ImgBB
- Save user details (username & IP) in MongoDB
- Retrieve uploaded image links

## Installation 🛠️
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/telegram-imgbb-bot.git
   cd telegram-imgbb-bot
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file and add your environment variables:
   ```
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   IMG_API_KEY=your_imgbb_api_key
   MONGO_URI=your_mongo_connection_string
   ```

4. Run the bot:
   ```bash
   python bot.py
   ```

## Deployment 🚀
This bot can be deployed on Jercel using the provided `jercel.json` configuration.

## License 🐟
This project is licensed under the MIT License.

## Bot Link 📱
You can interact with the bot here: [🔗BOT_LINK](https://t.me/Imagelinksatya_bot)
