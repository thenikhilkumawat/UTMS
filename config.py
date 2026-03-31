import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    SECRET_KEY = "uttam-tailors-v2-secret-2025"
    DATABASE    = os.path.join(BASE_DIR, "uttam.db")
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "order_images")
    MAX_IMAGES_PER_ORDER = 5
    # Owner session lasts 8 hours (28800 seconds)
    OWNER_SESSION_HOURS = 8
    DEFAULT_PIN = "1234"
