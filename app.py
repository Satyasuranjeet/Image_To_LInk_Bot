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

# Load environment variables
load_dotenv()

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

# Check if all required environment variables are set
if not all([TELEGRAM_TOKEN, MONGODB_URI, GOOGLE_CREDENTIALS_JSON]):
    raise ValueError("Missing required environment variables. Please check your .env file.")

# Initialize MongoDB client
try:
    client = MongoClient(MONGODB_URI)
    db = client['image_bot_db']
    users_collection = db['users']
    # Test the connection
    client.server_info()
    logger.info("Successfully connected to MongoDB")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    raise

def get_google_drive_service():
    """Get Google Drive service using credentials from environment variable."""
    try:
        # Parse the credentials JSON from environment variable
        credentials_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
        
        # Create credentials object
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict,
            scopes=['https://www.googleapis.com/auth/drive.file']
        )
        
        # Build and return the service
        return build('drive', 'v3', credentials=credentials)
    except json.JSONDecodeError:
        logger.error("Failed to parse Google credentials JSON")
        raise
    except Exception as e:
        logger.error(f"Error creating Drive service: {e}")
        raise

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    try:
        user = update.effective_user
        welcome_message = (
            f"Hi {user.first_name}! 👋\n\n"
            "I can help you store images and generate public links.\n"
            "Just send me any image and I'll upload it to Google Drive.\n"
            "Use /history to see your previously uploaded images."
        )
        await update.message.reply_text(welcome_message)
        logger.info(f"New user started the bot: {user.id}")
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await update.message.reply_text("Sorry, something went wrong. Please try again later.")

async def upload_to_drive(file_content: bytes, filename: str):
    """Upload file to Google Drive and return the shareable link."""
    try:
        service = get_google_drive_service()
        
        # Create file metadata
        file_metadata = {
            'name': filename,
            'mimeType': 'image/jpeg'
        }
        
        # Create media
        fh = io.BytesIO(file_content)
        media = MediaIoBaseUpload(fh, mimetype='image/jpeg', resumable=True)
        
        # Upload file
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()
        
        # Make the file publicly accessible
        permission = {
            'type': 'anyone',
            'role': 'reader'
        }
        service.permissions().create(
            fileId=file.get('id'),
            body=permission
        ).execute()
        
        return file.get('webViewLink')
        
    except Exception as e:
        logger.error(f"Error uploading to Drive: {e}")
        raise

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle received photos."""
    try:
        # Get user information
        user = update.effective_user
        user_data = {
            'user_id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name
        }
        
        # Send processing message
        processing_message = await update.message.reply_text(
            "Processing your image... 🔄\n"
            "This might take a few seconds..."
        )
        
        # Get photo file
        photo = update.message.photo[-1]  # Get the highest quality photo
        file = await context.bot.get_file(photo.file_id)
        
        # Download photo content
        photo_content = await file.download_as_bytearray()
        
        # Generate filename
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"{user.id}_{timestamp}.jpg"
        
        # Upload to Google Drive
        drive_link = await upload_to_drive(photo_content, filename)
        
        # Store in MongoDB
        upload_data = {
            'user_id': user.id,
            'image_link': drive_link,
            'filename': filename,
            'upload_date': datetime.utcnow(),
            'user_details': user_data,
            'file_size': len(photo_content)
        }
        users_collection.insert_one(upload_data)
        
        # Send success message
        await processing_message.edit_text(
            f"✅ Image uploaded successfully!\n\n"
            f"🔗 Here's your link:\n{drive_link}\n\n"
            f"Use /history to see all your uploads."
        )
        
        logger.info(f"Successfully processed image for user {user.id}")
        
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        error_message = (
            "Sorry, there was an error processing your image. 😕\n"
            "Please try again later or contact support if the problem persists."
        )
        if processing_message:
            await processing_message.edit_text(error_message)
        else:
            await update.message.reply_text(error_message)

async def get_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send user's upload history."""
    try:
        user_id = update.effective_user.id
        
        # Fetch user's uploads from MongoDB
        user_uploads = users_collection.find({'user_id': user_id}).sort('upload_date', -1)
        
        if users_collection.count_documents({'user_id': user_id}) == 0:
            await update.message.reply_text("You haven't uploaded any images yet! 📭")
            return
        
        history_message = "🗂 Your upload history:\n\n"
        for upload in user_uploads:
            date_str = upload['upload_date'].strftime('%Y-%m-%d %H:%M:%S')
            history_message += f"📅 {date_str}\n🔗 {upload['image_link']}\n\n"
        
        await update.message.reply_text(history_message)
        logger.info(f"History retrieved for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error retrieving history: {e}")
        await update.message.reply_text(
            "Sorry, there was an error retrieving your history. Please try again later."
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors in the telegram bot."""
    logger.error(f"Update {update} caused error {context.error}")
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "Sorry, something went wrong. Please try again later."
            )
    except:
        pass

def main():
    """Start the bot."""
    try:
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