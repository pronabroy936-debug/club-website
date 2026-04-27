import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# The app reads MongoDB details from .env.
# For Atlas, MONGO_URI should include the database name, for example:
# mongodb+srv://USERNAME:PASSWORD@HOST/clubDB?retryWrites=true&w=majority&appName=Cluster0
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/clubDB")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "clubDB")

# SECRET_KEY signs Flask sessions. Use a long random value in production.
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key")

# Admin credentials for /admin/login. Keep real values only in .env.
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# Uploaded files are stored locally. MongoDB stores the filename and details.
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", str(BASE_DIR / "static" / "uploads"))
MAX_CONTENT_LENGTH = 100 * 1024 * 1024

# Cloudinary media storage.
# Put CLOUDINARY_URL in .env like:
# cloudinary://API_KEY:API_SECRET@CLOUD_NAME
# New uploads go to Cloudinary when this value exists.
CLOUDINARY_URL = os.getenv("CLOUDINARY_URL", "")

# Public social media links. Admin can also edit these from the dashboard.
SOCIAL_WHATSAPP = os.getenv("SOCIAL_WHATSAPP", "")
SOCIAL_FACEBOOK = os.getenv("SOCIAL_FACEBOOK", "")
SOCIAL_YOUTUBE = os.getenv("SOCIAL_YOUTUBE", "")
