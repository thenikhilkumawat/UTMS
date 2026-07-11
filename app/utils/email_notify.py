"""
app/utils/email_notify.py
─────────────────────────
Email notification helper using GoDaddy SMTP (smtpout.secureserver.net).

From: order@uttamtailors.in  → order confirmations
From: update@uttamtailors.in → status updates, OTP

If SMTP credentials are missing, all functions return False silently.
"""

import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

_log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

SMTP_HOST = "smtpout.secureserver.net"
SMTP_PORT = 587
SMTP_USER = "info@uttamtailors.in"
SMTP_PASS = "L&m5$w8S*R*jB.G"

FROM_ORDER  = "Uttam Tailors <info@uttamtailors.in>"
FROM_UPDATE = "Uttam Tailors <info@uttamtailors.in>"
SHOP_NAME   = "Uttam Tailors"
SHOP_ADDR   = "Subhash Chowk, Sikar, Rajasthan"
SHOP_PHONE  = "+91 98765 43210"
TRACK_BASE  = "https://uttamtailors.in/track-order?code="

# ── Core sender ───────────────────────────────────────────────────────────────

def _send(to: str, subject: str, html: str, from_addr: str = FROM_ORDER) -> bool:
    """Send an HTML email. Returns True on success."""
    if not to or "@" not in to:
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = from_addr
        msg["To"]      = to
        msg.attach(MIMEText(html, "html", "utf-8"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, [to], msg.as_string())
        _log.info("Email sent → %s | %s", to, subject)
        return True
    except Exception as exc:
        _log.warning("Email send error: %s", exc)
        return False


# ── HTML base template ────────────────────────────────────────────────────────

def _wrap(body_html: str, preheader: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Uttam Tailors</title>
<style>
  body{{margin:0;padding:0;background:#f5f0ea;font-family:Georgia,serif;color:#2c1a0e;}}
  .wrap{{max-width:600px;margin:0 auto;background:#fff;}}
  .header{{background:#1a0a00;padding:28px 32px;text-align:center;}}
  .header img{{height:48px;}}
  .header h1{{margin:8px 0 0;color:#C8903A;font-size:22px;letter-spacing:2px;font-weight:normal;}}
  .header p{{margin:4px 0 0;color:#a87a50;font-size:12px;letter-spacing:1px;}}
  .body{{padding:36px 32px;}}
  .greeting{{font-size:18px;color:#1a0a00;margin-bottom:8px;}}
  .subtitle{{font-size:13px;color:#7a5c3a;margin-bottom:28px;}}
  .card{{background:#fdf8f3;border:1px solid #e8d5b7;border-radius:8px;padding:24px;margin-bottom:24px;}}
  .card-row{{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #efe0c8;font-size:14px;}}
  .card-row:last-child{{border-bottom:none;}}
  .card-label{{color:#7a5c3a;}}
  .card-value{{color:#1a0a00;font-weight:bold;text-align:right;}}
  .order-code{{font-size:28px;font-weight:bold;color:#C8903A;text-align:center;letter-spacing:3px;margin:16px 0;}}
  .badge{{display:inline-block;background:#C8903A;color:#fff;padding:4px 14px;border-radius:20px;font-size:12px;font-weight:bold;letter-spacing:1px;}}
  .cta-btn{{display:block;background:#C8903A;color:#fff;text-align:center;text-decoration:none;padding:14px 28px;border-radius:6px;font-size:15px;font-weight:bold;letter-spacing:1px;margin:24px 0;}}
  .steps{{counter-reset:step;}}
  .step{{display:flex;align-items:flex-start;margin-bottom:16px;font-size:14px;}}
  .step-num{{background:#C8903A;color:#fff;width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:bold;flex-shrink:0;margin-right:12px;margin-top:2px;}}
  .divider{{border:none;border-top:1px solid #e8d5b7;margin:24px 0;}}
  .footer{{background:#1a0a00;padding:24px 32px;text-align:center;}}
  .footer p{{color:#a87a50;font-size:11px;margin:4px 0;}}
  .footer a{{color:#C8903A;text-decoration:none;}}
  .status-icon{{font-size:48px;text-align:center;margin:16px 0;}}
  .highlight{{color:#C8903A;font-weight:bold;}}
</style>
</head>
<body>
{'<div style="display:none;max-height:0;overflow:hidden;">'+preheader+'</div>' if preheader else ''}
<div class="wrap">
  <div class="header">
    <h1>✂ UTTAM TAILORS</h1>
    <p>MASTER TAILORS · SIKAR, RAJASTHAN</p>
  </div>
  <div class="body">
    {body_html}
  </div>
  <div class="footer">
    <p>{SHOP_ADDR}</p>
    <p><a href="tel:{SHOP_PHONE}">{SHOP_PHONE}</a> &nbsp;|&nbsp; <a href="https://uttamtailors.in">uttamtailors.in</a></p>
    <p style="margin-top:12px;color:#5a3a1a;font-size:10px;">© Uttam Tailors. This is an automated notification.</p>
  </div>
</div>
</body>
</html>"""


# ── Order confirmation email ──────────────────────────────────────────────────

def send_order_email(
    to: str,
    order_code: str,
    customer_name: str,
    garment: str,
    total: float,
    advance: float = 0.0,
    delivery_date: str = "",
    is_home_delivery: bool = False,
) -> bool:
    if not to:
        return False

    remaining = round(total - advance, 2)
    delivery_line = (
        "<div class='card-row'><span class='card-label'>Delivery Type</span>"
        "<span class='card-value'>🏠 Home Delivery</span></div>"
        if is_home_delivery else
        "<div class='card-row'><span class='card-label'>Pickup</span>"
        "<span class='card-value'>From Our Shop</span></div>"
    )
    date_line = (
        f"<div class='card-row'><span class='card-label'>Ready By</span>"
        f"<span class='card-value'>{delivery_date}</span></div>"
        if delivery_date else ""
    )
    advance_line = (
        f"<div class='card-row'><span class='card-label'>Advance Paid</span>"
        f"<span class='card-value'>₹{int(advance)}</span></div>"
        f"<div class='card-row'><span class='card-label'>Balance Due</span>"
        f"<span class='card-value highlight'>₹{int(remaining)}</span></div>"
        if advance > 0 else
        f"<div class='card-row'><span class='card-label'>Amount Due</span>"
        f"<span class='card-value highlight'>₹{int(total)}</span></div>"
    )

    body = f"""
<p class="greeting">Namaste, {customer_name}! 🙏</p>
<p class="subtitle">Your order has been placed successfully. We'll craft it with love.</p>

<p style="text-align:center;"><span class="badge">ORDER CONFIRMED</span></p>
<div class="order-code">{order_code}</div>

<div class="card">
  <div class="card-row"><span class="card-label">Garment</span><span class="card-value">{garment}</span></div>
  <div class="card-row"><span class="card-label">Total Amount</span><span class="card-value">₹{int(total)}</span></div>
  {advance_line}
  {date_line}
  {delivery_line}
</div>

<a href="{TRACK_BASE}{order_code}" class="cta-btn">📍 Track Your Order</a>

<hr class="divider">
<p style="font-size:13px;color:#7a5c3a;text-align:center;">
  Questions? Reply to this email or call us at <strong>{SHOP_PHONE}</strong>
</p>
"""
    html = _wrap(body, preheader=f"Order {order_code} confirmed — {garment} is being crafted for you.")
    return _send(to, f"Order Confirmed ✓ — {order_code} | Uttam Tailors", html, FROM_ORDER)


# ── Status update email ───────────────────────────────────────────────────────

_STATUS_META = {
    "stitching": {
        "icon": "🧵",
        "badge": "STITCHING IN PROGRESS",
        "title": "Your order is being stitched!",
        "msg": "Our master tailor has started working on your garment. We'll notify you when it's ready.",
        "color": "#2980b9",
    },
    "ready": {
        "icon": "✅",
        "badge": "READY FOR PICKUP",
        "title": "Your order is ready!",
        "msg": "Your garment has been crafted and is ready. Come pick it up at our shop or we'll deliver it to you.",
        "color": "#27ae60",
    },
    "delivered": {
        "icon": "🎉",
        "badge": "DELIVERED",
        "title": "Order delivered — enjoy your new outfit!",
        "msg": "Thank you for choosing Uttam Tailors. We hope you love your new garment. See you again!",
        "color": "#8e44ad",
    },
    "cancelled": {
        "icon": "❌",
        "badge": "ORDER CANCELLED",
        "title": "Your order has been cancelled",
        "msg": "Your order has been cancelled. If this was unexpected, please contact us immediately.",
        "color": "#c0392b",
    },
}

def send_status_email(
    to: str,
    order_code: str,
    customer_name: str,
    status: str,
) -> bool:
    if not to:
        return False

    meta = _STATUS_META.get(status.lower(), {
        "icon": "📋", "badge": status.upper(),
        "title": f"Order status update: {status}",
        "msg": f"Your order {order_code} status has been updated to: {status}.",
        "color": "#C8903A",
    })

    body = f"""
<p class="greeting">Namaste, {customer_name}! 🙏</p>

<div class="status-icon">{meta['icon']}</div>
<p style="text-align:center;"><span class="badge" style="background:{meta['color']};">{meta['badge']}</span></p>
<h2 style="text-align:center;font-size:18px;color:#1a0a00;margin:16px 0 8px;">{meta['title']}</h2>
<p style="text-align:center;font-size:14px;color:#7a5c3a;margin-bottom:24px;">{meta['msg']}</p>

<div class="card">
  <div class="card-row"><span class="card-label">Order Code</span><span class="card-value">{order_code}</span></div>
  <div class="card-row"><span class="card-label">Status</span><span class="card-value">{meta['badge']}</span></div>
</div>

<a href="{TRACK_BASE}{order_code}" class="cta-btn">📍 Track Your Order</a>

<hr class="divider">
<p style="font-size:13px;color:#7a5c3a;text-align:center;">
  Need help? Call us at <strong>{SHOP_PHONE}</strong> or visit {SHOP_ADDR}
</p>
"""
    subj_map = {
        "stitching": f"Stitching Started 🧵 — Order {order_code}",
        "ready":     f"Your Order is Ready ✅ — {order_code} | Uttam Tailors",
        "delivered": f"Order Delivered 🎉 — {order_code} | Uttam Tailors",
        "cancelled": f"Order Cancelled — {order_code} | Uttam Tailors",
    }
    subject = subj_map.get(status.lower(), f"Order Update — {order_code} | Uttam Tailors")
    html = _wrap(body, preheader=meta["msg"])
    return _send(to, subject, html, FROM_UPDATE)


# ── OTP email ─────────────────────────────────────────────────────────────────

def send_otp_email(to: str, otp: str, name: str = "") -> bool:
    if not to:
        return False
    greeting = f"Namaste{', ' + name if name else ''}!"
    body = f"""
<p class="greeting">{greeting} 🙏</p>
<p class="subtitle">Here is your one-time verification code for Uttam Tailors.</p>

<div class="card" style="text-align:center;">
  <p style="font-size:13px;color:#7a5c3a;margin-bottom:8px;">YOUR OTP</p>
  <div style="font-size:42px;font-weight:bold;color:#C8903A;letter-spacing:8px;">{otp}</div>
  <p style="font-size:12px;color:#a87a50;margin-top:8px;">Valid for 10 minutes. Do not share with anyone.</p>
</div>

<p style="font-size:13px;color:#7a5c3a;text-align:center;margin-top:16px;">
  If you did not request this OTP, please ignore this email.
</p>
"""
    html = _wrap(body, preheader=f"Your Uttam Tailors OTP is {otp}. Valid for 10 minutes.")
    return _send(to, f"Your OTP: {otp} — Uttam Tailors", html, FROM_UPDATE)


# ── Home delivery notification ────────────────────────────────────────────────

def send_delivery_email(
    to: str,
    order_code: str,
    customer_name: str,
    address: str = "",
) -> bool:
    if not to:
        return False
    addr_line = f"<div class='card-row'><span class='card-label'>Delivery Address</span><span class='card-value'>{address}</span></div>" if address else ""
    body = f"""
<p class="greeting">Namaste, {customer_name}! 🙏</p>
<p class="subtitle">Great news — your order is on its way to you!</p>

<div class="status-icon">🚚</div>
<p style="text-align:center;"><span class="badge" style="background:#27ae60;">OUT FOR DELIVERY</span></p>

<div class="card">
  <div class="card-row"><span class="card-label">Order Code</span><span class="card-value">{order_code}</span></div>
  {addr_line}
  <div class="card-row"><span class="card-label">Status</span><span class="card-value">Out for Delivery</span></div>
</div>

<a href="{TRACK_BASE}{order_code}" class="cta-btn">📍 Track Your Order</a>

<p style="font-size:13px;color:#7a5c3a;text-align:center;">
  Questions? Call us at <strong>{SHOP_PHONE}</strong>
</p>
"""
    html = _wrap(body, preheader=f"Your order {order_code} is out for delivery!")
    return _send(to, f"Out for Delivery 🚚 — Order {order_code} | Uttam Tailors", html, FROM_UPDATE)



# ── Support chat notifications ─────────────────────────────────────────────────

def send_support_owner_email(chat_id, customer_name, message, customer_email=""):
    email_line = "<div class=\'card-row\'><span class=\'card-label\'>Customer Email</span><span class=\'card-value\'>{}</span></div>".format(customer_email) if customer_email else ""
    body = """
<p class="greeting">New Support Message</p>
<p class="subtitle">A customer sent a message on the support chat.</p>
<div class="card">
  <div class="card-row"><span class="card-label">Chat ID</span><span class="card-value">#{}</span></div>
  <div class="card-row"><span class="card-label">Customer</span><span class="card-value">{}</span></div>
  {}
  <div class="card-row"><span class="card-label">Message</span><span class="card-value">{}</span></div>
</div>
<a href="https://dashboard.uttamtailors.in" class="cta-btn">Reply on Dashboard</a>
""".format(chat_id, customer_name, email_line, message)
    html = _wrap(body, preheader="New message from {}".format(customer_name))
    return _send("info@uttamtailors.in", "New Support Message from {} — Uttam Tailors".format(customer_name), html, FROM_UPDATE)


def send_support_customer_email(to, customer_name, message):
    if not to:
        return False
    body = """
<p class="greeting">Namaste, {}!</p>
<p class="subtitle">Uttam Tailors has replied to your support message.</p>
<div class="card">
  <div class="card-row"><span class="card-label">Reply</span><span class="card-value">{}</span></div>
</div>
<a href="https://uttamtailors.in" class="cta-btn">Continue Chat</a>
<p style="font-size:13px;color:#7a5c3a;text-align:center;">You can also call us at <strong>{}</strong></p>
""".format(customer_name, message, SHOP_PHONE)
    html = _wrap(body, preheader="Uttam Tailors replied to your message")
    return _send(to, "Uttam Tailors replied to your message", html, FROM_UPDATE)
