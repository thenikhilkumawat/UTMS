import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    SECRET_KEY    = "uttam-tailors-v2-secret-2025"
    # PostgreSQL URL from Render environment variable
    DATABASE_URL  = os.environ.get("DATABASE_URL", "")
    # Fallback to SQLite for local testing only
    DATABASE      = os.environ.get("DATABASE_PATH") or os.path.join(BASE_DIR, "uttam.db")
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "order_images")
    MAX_IMAGES_PER_ORDER = 5
    OWNER_SESSION_HOURS  = 8
    DEFAULT_PIN          = "1234"
