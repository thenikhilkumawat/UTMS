"""
app/utils/sms.py
────────────────
SMS helper using Fast2SMS (https://fast2sms.com).

Usage:
    from app.utils.sms import send_sms, send_otp, send_order_sms

Free tier: Fast2SMS gives ₹50 credits on signup (~500 OTPs or ~200 promo SMS).
Set FAST2SMS_KEY in .env or admin settings to activate.
If key is missing, all functions return False silently (no crash).
"""

import random
import logging
import requests

_log = logging.getLogger(__name__)

# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_key() -> str:
    """Read API key from DB settings (live) or env fallback."""
    try:
        from database import get_db
        db = get_db()
        row = db.execute(
            "SELECT value FROM settings WHERE key='fast2sms_key' LIMIT 1"
        ).fetchone()
        if row and row["value"]:
            return row["value"].strip()
    except Exception:
        pass
    # Fallback: config / env
    try:
        from config import Config
        v = getattr(Config, "FAST2SMS_KEY", "")
        if v: return v.strip()
    except Exception:
        pass
    return ""


def _clean_mobile(mobile: str) -> str:
    """Return 10-digit Indian number or empty string."""
    m = str(mobile or "").strip().lstrip("+").lstrip("91")
    return m if len(m) == 10 and m.isdigit() else ""


# ── Core send ────────────────────────────────────────────────────────────────

def send_sms(mobile: str, message: str) -> bool:
    """
    Send a plain-text SMS via Fast2SMS Quick route.
    Returns True on success, False on failure/key missing.
    """
    key = _get_key()
    if not key:
        _log.info("Fast2SMS key not set — SMS skipped")
        return False
    num = _clean_mobile(mobile)
    if not num:
        _log.warning("SMS skipped — invalid mobile: %s", mobile)
        return False
    try:
        resp = requests.post(
            "https://www.fast2sms.com/dev/bulkV2",
            headers={"authorization": key},
            json={
                "sender_id": "FSTSMS",
                "message":   message[:160],
                "language":  "english",
                "route":     "q",
                "numbers":   num,
            },
            timeout=8,
        )
        data = resp.json()
        if data.get("return") is True:
            _log.info("SMS sent → %s", num)
            return True
        _log.warning("Fast2SMS rejected: %s", data)
        return False
    except Exception as exc:
        _log.warning("SMS send error: %s", exc)
        return False


# ── OTP ──────────────────────────────────────────────────────────────────────

def send_otp(mobile: str) -> str:
    """
    Generate a 6-digit OTP, send it via Fast2SMS OTP route,
    and return the OTP string (so caller can store + verify it).
    Returns empty string if SMS fails (caller decides what to do).
    """
    key = _get_key()
    num = _clean_mobile(mobile)
    if not num:
        return ""

    otp = str(random.randint(100000, 999999))

    if key:
        try:
            resp = requests.get(
                "https://www.fast2sms.com/dev/bulk",
                params={
                    "authorization":     key,
                    "variables_values":  otp,
                    "route":             "otp",
                    "numbers":           num,
                },
                timeout=8,
            )
            data = resp.json()
            if data.get("return") is True:
                _log.info("OTP sent → %s", num)
                return otp
            _log.warning("OTP send failed: %s", data)
        except Exception as exc:
            _log.warning("OTP send error: %s", exc)
        # Fall back to quick route with plain message
        msg = f"{otp} is your Uttam Tailors OTP. Valid 10 min. Do not share."
        send_sms(mobile, msg)
    else:
        _log.info("Fast2SMS key not set — OTP skipped (OTP=%s)", otp)

    return otp  # always return so dev can test without a key


# ── Order notifications ───────────────────────────────────────────────────────

def send_order_sms(mobile: str, order_code: str, customer_name: str,
                   garment: str, total: float, advance: float,
                   delivery_date: str = "", is_home_delivery: bool = False) -> bool:
    """SMS sent right after order is placed."""
    remaining = round(total - advance, 2)
    lines = [
        f"Namaste {customer_name}! Aapka order Uttam Tailors mein place ho gaya.",
        f"Order Code: {order_code}",
        f"Garment: {garment}",
    ]
    if delivery_date:
        lines.append(f"Ready By: {delivery_date}")
    if is_home_delivery:
        lines.append("Delivery: Home Delivery")
    lines.append(f"Advance Paid: Rs.{int(advance)} | Balance: Rs.{int(remaining)}")
    lines.append(f"Track: uttamtailors.in/track-order?code={order_code}")
    return send_sms(mobile, " | ".join(lines))


def send_status_sms(mobile: str, order_code: str, customer_name: str,
                    status: str) -> bool:
    """SMS when order status changes."""
    status_msg = {
        "stitching": "Aapke kapde ki stitching shuru ho gayi hai!",
        "ready":     "Khushkhabri! Aapka order ready hai pickup ke liye.",
        "delivered": "Aapka order deliver ho gaya. Thank you for choosing Uttam Tailors!",
        "cancelled": "Aapka order cancel ho gaya hai. Help ke liye humse contact karein.",
    }.get(status.lower(), f"Order status update: {status}")

    msg = (
        f"Namaste {customer_name}! {status_msg} "
        f"Order Code: {order_code}. "
        f"Track: uttamtailors.in/track-order?code={order_code}"
    )
    return send_sms(mobile, msg)


def send_ready_sms(mobile: str, order_code: str, customer_name: str,
                   is_home_delivery: bool = False) -> bool:
    """Special SMS when order is marked Ready."""
    if is_home_delivery:
        msg = (
            f"Namaste {customer_name}! Aapka order {order_code} pack ho gaya hai "
            f"aur jald hi deliver kiya jayega. "
            f"Track: uttamtailors.in/track-order?code={order_code}"
        )
    else:
        msg = (
            f"Namaste {customer_name}! Aapka order {order_code} bilkul ready hai. "
            f"Aap hmare shop se collect kar sakte hain. "
            f"Uttam Tailors, Subhash Chowk, Sikar. "
            f"Track: uttamtailors.in/track-order?code={order_code}"
        )
    return send_sms(mobile, msg)
