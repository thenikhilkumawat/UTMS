"""
app/utils/fcm.py
────────────────
Firebase Cloud Messaging (FCM) push notification helper.
Service account + web config are hardcoded as defaults (can be overridden from DB).
"""

import json
import logging

_log = logging.getLogger(__name__)


# ── Hardcoded Firebase config ─────────────────────────────────────────────────

_DEFAULT_SERVICE_ACCOUNT = {
    "type": "service_account",
    "project_id": "uttam-tailors",
    "private_key_id": "c584969ecdd378335939a93cc06297725d9b1468",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQDBiLBOWjzNZrsa\nN/T90IIMtQ8vzFF4Zlssc9yUT7CIONGF9AZ5s9YmJcZD+0q/g2nzUOYVHiZDWVEB\n7X6BDzbbC8LXReL6B/fKpSCYIWgAowv1iupVq72VnqhtOy0MRbNTDzosBFpFr6Ao\n1+x72rnD9YpMwpH4adXRtP4QF4MG2+g+z3Gfl0nXE2GZbi35NqRfTPVmP0lgmKBG\nebLM49HhOr0HjMjP2XzJbQFaW3vuYpHFmnucVtZFw6PHh0Y5HaYuTFgvbcGG0jLx\nzxfomAHc8D/3c95JEZGtroNcZJaSvFCZ/fXjQfwF1MHETmYQvV3kx5r9YeWR357b\n5iO4x/ZnAgMBAAECggEAAYHNUFQ25FPoIb8ieEDXEmmX3FkXSqcOugeORdViXDKH\nvHxMT0b4OZnSXmsm3NuVcqCZpLvJs9KOj+5H2DzEbOuS29bzz9tKBwOcKl3Fj+O1\nJHdYIHdS5ZxeVri+6WPi4+2wF/GnZk2EzhdIWc/ijG/CtkWkRK6bofi/1bjpJfTY\nRNjlbRqvASZJ6ub2fPtqn1MuMpKrS5U6p8+IIBKcvelBQo3F4yJbCNhgoigKKh1S\nUuvwu5GWKBHlfYBO3gSVmaLy702QReOc9ylL8TW/nY+3YA+VK8Xt51DPyPEytoIe\nXuFGAjVEhY7lc7XzUvY09hf+Yg9ZJvFKDIjkn7IfsQKBgQD6bvZdjNgwyZhonVuU\n/9Pxr0FWUtvdvNLRvsGpF2dZ3ARiNFumDr4NxGBKPu/N8dT91Cslggt0UfZ2qXA5\nLXOV3n2WO1o9jWX6MHb8CI9lYlPDOB06ueHrwX1fNQPYT4V3+SeNJj98apPaGxaq\na7Wo/JK71r3hbOtNUX8afEp9KQKBgQDF1fOx65BkNs006uju8r6x+zjXNxI42S8y\ngJojqGh/HXWkU5fqnjSZDl+/CFr2+vi1GJjPk7Ja70KcnXBS8YUibUu2ShtrgGtK\nl76OqYLDSJ2whwJqXKNaYzjIT68rxA0arWPCHzDzki6BsTWKsiQBASS/Wpxio9A0\niMJrwzi5DwKBgH2/8h2Pd48n60u8mBv9SeN16Qz7lkOFaSbA7mWFxvOsMtdNCygb\nBvvKu78MU0XKRPUf8HppDm9eKK/07NEJLZz3l4A0VV/K/IXgiB6N/dMeyIiiSKsQ\nY40KH3YLHN8lLxPLHD0YE5DZw1wldgAlDZbJHLUNY1Mqagzs+zHFb3HhAoGAUnrH\ntebK9Szv0t8ZK/3iSRu+7+MS4saRadG58aHVpyFmGZOMY5F/xkv62Q8ntY6ewAm4\nM9qU4lqb/+WXncz5v4enqCEvW1tX3+px1NKRJM+ShrVS6Xsj05xIYSLvmiSLfhLJ\n43XTl8jbQNDbzK5GWnDanDivuGQpeq2FuR3T+TsCgYA/CtPkrFiE7IBLIv3SU/TA\n05dJxV2yC9BJ2QAHaf+Cw2cUqkD4NXtBCeI+aj9eeWnrkoY4hoB8uwprVIH+QPQa\nOtQP7I5VkrDaYFHk5O3RhRka3m3myj8Y0YdHRO0vBOwVmjkLYO1BKKLyxxO/umSQ\nkrQ+mLSbpYaxbIH02W9CWw==\n-----END PRIVATE KEY-----\n",
    "client_email": "firebase-adminsdk-fbsvc@uttam-tailors.iam.gserviceaccount.com",
    "client_id": "101224224109482309504",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40uttam-tailors.iam.gserviceaccount.com",
    "universe_domain": "googleapis.com"
}

_DEFAULT_WEB_CONFIG = {
    "apiKey": "AIzaSyCpKrqgMz0QdOtsF-cd80-gSzJy1IRBr1U",
    "authDomain": "uttam-tailors.firebaseapp.com",
    "projectId": "uttam-tailors",
    "storageBucket": "uttam-tailors.firebasestorage.app",
    "messagingSenderId": "696453691951",
    "appId": "1:696453691951:web:e3e44fe2e6a4b46cdb64da",
    "measurementId": "G-3PFZZHYL1J"
}

_DEFAULT_VAPID_KEY = "BBDoz7BM-M-ul22v9SjMztaaO-3RVjijIghmaFjruU9tdU7rUsTHjKGkP_5_lgI7HJ8e2xvMxcS-8GhREOzUGhw"


# ── Config loaders ────────────────────────────────────────────────────────────

def _get_service_account():
    try:
        from database import get_db
        db = get_db()
        row = db.execute(
            "SELECT value FROM settings WHERE key='fcm_service_account' LIMIT 1"
        ).fetchone()
        if row and row["value"] and row["value"].strip().startswith("{"):
            return json.loads(row["value"])
    except Exception:
        pass
    return _DEFAULT_SERVICE_ACCOUNT


def _get_app():
    try:
        import firebase_admin
        from firebase_admin import credentials
        try:
            return firebase_admin.get_app("uttam")
        except ValueError:
            pass
        sa = _get_service_account()
        if not sa:
            return None
        cred = credentials.Certificate(sa)
        return firebase_admin.initialize_app(cred, name="uttam")
    except ImportError:
        _log.warning("firebase-admin not installed. Run: pip install firebase-admin")
        return None
    except Exception as exc:
        _log.warning("FCM init error: %s", exc)
        return None


# ── Token management ──────────────────────────────────────────────────────────

def save_token(account_id, token):
    if not token:
        return False
    try:
        from database import get_db
        from datetime import datetime
        db = get_db()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        existing = db.execute(
            "SELECT id FROM fcm_tokens WHERE token=?", (token,)
        ).fetchone()
        if existing:
            db.execute(
                "UPDATE fcm_tokens SET account_id=?, updated_at=? WHERE token=?",
                (account_id, now, token)
            )
        else:
            db.execute(
                "INSERT INTO fcm_tokens(account_id, token, created_at, updated_at) VALUES(?,?,?,?)",
                (account_id, token, now, now)
            )
        db.commit()
        return True
    except Exception as exc:
        _log.warning("FCM save token error: %s", exc)
        return False


def get_tokens_for_account(account_id):
    try:
        from database import get_db
        db = get_db()
        rows = db.execute(
            "SELECT token FROM fcm_tokens WHERE account_id=? ORDER BY updated_at DESC LIMIT 5",
            (account_id,)
        ).fetchall()
        return [r["token"] for r in rows]
    except Exception:
        return []


# ── Core push sender ──────────────────────────────────────────────────────────

def send_push(tokens, title, body, data=None, icon="/static/img/logo.png"):
    if not tokens:
        return False
    app = _get_app()
    if not app:
        _log.info("FCM not configured - push skipped")
        return False
    try:
        from firebase_admin import messaging
        messages = []
        for token in tokens:
            track_url = (data.get("url") if data else None) or "https://uttamtailors.in/track-order"
            msg = messaging.Message(
                notification=messaging.Notification(title=title, body=body, image=icon),
                webpush=messaging.WebpushConfig(
                    notification=messaging.WebpushNotification(
                        title=title, body=body, icon=icon,
                        badge="/static/img/badge.png",
                        vibrate=[200, 100, 200],
                        actions=[messaging.WebpushNotificationAction(
                            action="track", title="Track Order"
                        )],
                    ),
                    fcm_options=messaging.WebpushFCMOptions(link=track_url),
                ),
                data={k: str(v) for k, v in (data or {}).items()},
                token=token,
            )
            messages.append(msg)
        if not messages:
            return False
        resp = messaging.send_each(messages, app=app)
        success = sum(1 for r in resp.responses if r.success)
        _log.info("FCM push: %d/%d sent", success, len(messages))
        return success > 0
    except Exception as exc:
        _log.warning("FCM send error: %s", exc)
        return False


# ── Convenience wrappers ──────────────────────────────────────────────────────

def push_order_placed(account_id, order_code, garment):
    tokens = get_tokens_for_account(account_id)
    return send_push(
        tokens,
        title="Order Confirmed",
        body="Your " + garment + " order (" + order_code + ") has been placed. We'll craft it with love!",
        data={"order_code": order_code, "url": "https://uttamtailors.in/track-order?code=" + order_code},
    )


def push_status_update(account_id, order_code, status):
    tokens = get_tokens_for_account(account_id)
    sl = status.lower()
    titles = {
        "stitching": "Stitching In Progress",
        "ready":     "Your Order is Ready",
        "delivered": "Order Delivered",
        "cancelled": "Order Cancelled",
    }
    bodies = {
        "stitching": "Stitching started on order " + order_code,
        "ready":     "Order " + order_code + " is ready for pickup!",
        "delivered": "Order " + order_code + " delivered. Enjoy!",
        "cancelled": "Order " + order_code + " has been cancelled.",
    }
    return send_push(
        tokens,
        title=titles.get(sl, "Order Update - " + order_code),
        body=bodies.get(sl, "Order " + order_code + " status: " + status),
        data={"order_code": order_code, "url": "https://uttamtailors.in/track-order?code=" + order_code},
    )
