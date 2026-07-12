import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

class Config:
    SECRET_KEY    = "uttam-tailors-v2-secret-2025"
    # SQLite database (local)
    DATABASE      = os.environ.get("DATABASE_PATH") or os.path.join(BASE_DIR, "uttam.db")
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "order_images")
    MAX_IMAGES_PER_ORDER = 5
    OWNER_SESSION_HOURS  = 8
    DEFAULT_PIN          = "1234"

    # Google OAuth (customer "Continue with Google" login) — set these as env
    # vars once you create an OAuth Client ID in Google Cloud Console. Until
    # set, the Google-login button gracefully tells customers it isn't ready.
    GOOGLE_CLIENT_ID     = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

    # Outbound email (wishlist price-drop / back-in-stock alerts) — set these as
    # env vars to activate. Until set, alert emails are skipped silently (the
    # in-app wishlist badges still work without this).
    SMTP_HOST     = os.environ.get("SMTP_HOST", "")
    SMTP_PORT     = int(os.environ.get("SMTP_PORT", "587") or 587)
    SMTP_USER     = os.environ.get("SMTP_USER", "")
    SMTP_PASS     = os.environ.get("SMTP_PASS", "")
    ALERT_FROM_NAME = os.environ.get("ALERT_FROM_NAME", "Uttam Tailors")
    SITE_URL      = os.environ.get("SITE_URL", "https://uttamtailors.in")

    # Fast2SMS — OTP + transactional SMS for India
    # Get free API key at https://fast2sms.com  (Settings → Dev API)
    # Can also be set live via Admin → Settings → "Fast2SMS API Key"
    FAST2SMS_KEY  = os.environ.get("FAST2SMS_KEY", "")
    # Razorpay — set these in .env on the server
    RAZORPAY_KEY_ID     = os.environ.get("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")
    RAZORPAY_ADVANCE_PCT = float(os.environ.get("RAZORPAY_ADVANCE_PCT", "30"))  # % advance to collect
