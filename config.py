import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    SECRET_KEY = "uttam-tailors-v2-secret-2025"
    # Use DATABASE_PATH env var if set (for Render persistent disk at /data/uttam.db)
    # Otherwise fall back to local file
    DATABASE    = os.environ.get("DATABASE_PATH") or os.path.join(BASE_DIR, "uttam.db")
    UPLOAD_FOLDER = os.environ.get("UPLOAD_PATH") or os.path.join(BASE_DIR, "static", "order_images")
    MAX_IMAGES_PER_ORDER = 5
    OWNER_SESSION_HOURS = 8
    DEFAULT_PIN = "1234"
