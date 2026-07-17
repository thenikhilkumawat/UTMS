import os, sys, logging, base64
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, session, redirect, url_for, request, g, render_template_string, Response
from config import Config
from database import init_db, get_setting

app = Flask(__name__, template_folder="templates", static_folder="static", static_url_path="/static")
app.secret_key = Config.SECRET_KEY
from datetime import timedelta
app.config["SESSION_COOKIE_HTTPONLY"]=True
app.config["SESSION_COOKIE_SAMESITE"]="Lax"
app.config["SESSION_COOKIE_SECURE"]=os.environ.get("FLASK_ENV")!="development"
app.config["PERMANENT_SESSION_LIFETIME"]=timedelta(days=7)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20MB max upload

# ── Gzip compression (reduces page size ~70%) ────────────────────────────────
try:
    from flask_compress import Compress as _Compress
    _Compress(app)
except ImportError:
    pass  # flask-compress not installed yet — run pip install flask-compress



# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Auto-close DB connections after every request ─────────────────────────────
@app.teardown_appcontext
def close_db_on_teardown(exception):
    """Safety net: close any DB connection stored in g to prevent leaks."""
    conn = g.pop("_db_conn", None)
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass

# ── Error handlers — prevent worker crashes ───────────────────────────────────
@app.errorhandler(500)
def handle_500(e):
    logger.error(f"500 error: {e}")
    return render_template_string("""
    <html><head><meta name="viewport" content="width=device-width,initial-scale=1">
    <style>body{font-family:sans-serif;text-align:center;padding:60px 20px;background:#1a1a2e;color:#fff}
    h1{font-size:3em;color:#e94560}a{color:#0f3460;background:#e94560;padding:12px 24px;border-radius:8px;
    text-decoration:none;color:#fff;display:inline-block;margin-top:20px}</style></head>
    <body><h1>Something went wrong</h1><p>Please try again.</p>
    <a href="/">← Go Home</a></body></html>
    """), 500

@app.errorhandler(502)
def handle_502(e):
    return render_template_string("""
    <html><head><meta name="viewport" content="width=device-width,initial-scale=1">
    <style>body{font-family:sans-serif;text-align:center;padding:60px 20px;background:#1a1a2e;color:#fff}
    h1{font-size:3em;color:#e94560}a{color:#fff;background:#e94560;padding:12px 24px;border-radius:8px;
    text-decoration:none;display:inline-block;margin-top:20px}</style></head>
    <body><h1>Service Starting...</h1><p>Please wait a moment and refresh.</p>
    <a href="javascript:location.reload()">↻ Refresh</a></body></html>
    """), 502

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled exception: {e}", exc_info=True)
    return render_template_string("""
    <html><head><meta name="viewport" content="width=device-width,initial-scale=1">
    <style>body{font-family:sans-serif;text-align:center;padding:60px 20px;background:#1a1a2e;color:#fff}
    h1{font-size:3em;color:#e94560}a{color:#fff;background:#e94560;padding:12px 24px;border-radius:8px;
    text-decoration:none;display:inline-block;margin-top:20px}</style></head>
    <body><h1>Oops!</h1><p>Something went wrong. Please try again.</p>
    <a href="/">← Go Home</a></body></html>
    """), 500

# ── Health check for uptime monitors ──────────────────────────────────────────
@app.route("/health")
def health_check():
    """Lightweight health check - no DB hit."""
    return jsonify({"status": "ok"}), 200

@app.route("/health/db")
def health_db():
    """Health check with DB ping."""
    try:
        from database import get_db
        conn = get_db()
        conn.execute("SELECT 1")
        conn.close()
        return jsonify({"status": "ok", "db": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "error", "db": str(e)}), 503

# ── Static file headers ──────────────────────────────────────────────────────
@app.after_request
def add_header(response):
    if request.path.startswith("/static/"):
        ext = request.path.rsplit(".", 1)[-1].lower() if "." in request.path else ""
        if ext in ("css", "js", "woff", "woff2", "ttf", "otf"):
            response.headers["Cache-Control"] = "public, max-age=604800"  # 7 days
        elif ext in ("jpg", "jpeg", "png", "webp", "gif", "svg", "ico"):
            response.headers["Cache-Control"] = "public, max-age=2592000"  # 30 days
        else:
            response.headers["Cache-Control"] = "public, max-age=86400"
    response.headers["ngrok-skip-browser-warning"]="true"
    response.headers["X-Frame-Options"]="SAMEORIGIN"
    response.headers["X-Content-Type-Options"]="nosniff"
    response.headers["Referrer-Policy"]="strict-origin-when-cross-origin"
    # Content Security Policy — blocks XSS from untrusted sources
    # 'unsafe-inline' needed for Jinja2 inline styles/scripts; tighten further if you add nonces
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
            "https://cdn.razorpay.com https://checkout.razorpay.com "
            "https://cdnjs.cloudflare.com https://nominatim.openstreetmap.org "
            "https://www.gstatic.com https://*.gstatic.com "
            "https://www.googletagmanager.com https://tagmanager.google.com "
            "https://www.google-analytics.com https://ssl.google-analytics.com "
            "https://connect.facebook.net; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://tagmanager.google.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data: blob: https:; "
        "connect-src 'self' "
            "https://*.razorpay.com https://api.replicate.com "
            "https://www.google-analytics.com https://analytics.google.com "
            "https://nominatim.openstreetmap.org "
            "https://fcm.googleapis.com https://*.googleapis.com "
            "https://www.googletagmanager.com "
            "https://*.firebaseio.com wss://*.firebaseio.com "
            "https://firestore.googleapis.com; "
        "frame-src https://*.razorpay.com https://checkout.razorpay.com "
            "https://www.googletagmanager.com; "
        "object-src 'none'; base-uri 'self';"
    )
    return response

# ── Custom 404 ───────────────────────────────────────────────────────────────
@app.errorhandler(404)
def page_not_found(e):
    from flask import render_template as _rt
    return _rt("website/404.html"), 404

# ── Register blueprints ──────────────────────────────────────────────────────
from app.routes.employee import bp as employee_bp
from app.routes.owner import bp as owner_bp
from app.routes.website import website_bp
from app.routes.features import features_bp

# Employee dashboard under /manage, website at root
app.register_blueprint(employee_bp, url_prefix="/manage")
app.register_blueprint(owner_bp)
app.register_blueprint(website_bp)
app.register_blueprint(features_bp)
try:
    from app.extensions import limiter as _lim,LIMITER_AVAILABLE as _LA
    if _LA and _lim: _lim.init_app(app)
except Exception: pass

# ── Inject ann_items into every website template ──────────────────────────────

@app.context_processor
def inject_nav_services():
    """Inject garment categories + items into every template for mega drawer."""
    try:
        from database import get_db
        from app.routes.website import get_item_media
        db = get_db()
        cats = db.execute("SELECT * FROM web_service_categories ORDER BY sort_order, id").fetchall()
        items = db.execute("SELECT * FROM web_service_items ORDER BY sort_order, id").fetchall()
        items_by_cat = {}
        for item in items:
            cid = item["category_id"]
            if cid not in items_by_cat:
                items_by_cat[cid] = []
            items_by_cat[cid].append(item)
        media = get_item_media()
        nav_cats = [(cat, items_by_cat.get(cat["id"], []), media) for cat in cats]
        return {"nav_services": nav_cats}
    except:
        pass
    return {"nav_services": []}

@app.context_processor
def inject_ann_items():
    try:
        from database import get_db
        db = get_db()
        raw = db.execute("SELECT value FROM settings WHERE key='web_ann_items'").fetchone()
        speed_row = db.execute("SELECT value FROM settings WHERE key='web_ann_speed'").fetchone()
        ann_speed = speed_row["value"] if speed_row and speed_row["value"] else "55"
        items = []
        if raw and raw["value"]:
            items = [x.strip() for x in raw["value"].split("||") if x.strip()]
        return {"ann_items": items, "ann_speed": ann_speed}
    except:
        pass
    return {"ann_items": [], "ann_speed": "55"}

# ── Redirect shortcuts so original UTMS template links still work ─────────────
from flask import redirect as _rd

@app.route("/api/settings/all_rates")
def api_all_rates():
    from database import get_db
    db = get_db()
    rows = db.execute("SELECT key, value FROM settings WHERE key LIKE 'customer_rate_%'").fetchall()
    data = {}
    for r in rows:
        k = r["key"].replace("customer_rate_", "")
        data[k] = r["value"]
    from flask import jsonify
    return jsonify(data)
@app.route("/print-slip/<order_code>")
def _r_print_slip(order_code): return _rd(f"/manage/print-slip/{order_code}", 302)

@app.route("/order-status")
def _r_order_status(): return _rd("/manage/order-status", 301)
@app.route("/new-order")
def _r_new_order(): return _rd("/manage/new-order", 301)
@app.route("/work-log")
def _r_work_log(): return _rd("/manage/work-log", 301)
@app.route("/pickup")
def _r_pickup(): return _rd("/manage/pickup", 301)
@app.route("/finance")
def _r_finance(): return _rd("/manage/finance", 301)
@app.route("/customers")
def _r_customers(): return _rd("/manage/customers", 301)
@app.route("/measurements")
def _r_measurements(): return _rd("/manage/measurements", 301)
@app.route("/gallery")
def _r_gallery(): return _rd("/manage/gallery", 301)

# ── DB init on startup ───────────────────────────────────────────────────────
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
init_db()
from database import run_seo_migrations
run_seo_migrations()  # Adds SEO columns and auto-generates slugs
from database import run_account_migrations
run_account_migrations()  # Adds email/Google login, addresses, wishlist, payment refs, order link

# ── Style options column migrations ──────────────────────────────────────────
try:
    from database import get_db
    _db = get_db()
    _style_alters = [
        "ALTER TABLE garment_style_options ADD COLUMN is_required INTEGER DEFAULT 0",
        "ALTER TABLE garment_style_options ADD COLUMN sort_order INTEGER DEFAULT 0",
        "ALTER TABLE garment_style_values ADD COLUMN sort_order INTEGER DEFAULT 0",
        "ALTER TABLE garment_style_values ADD COLUMN value_key TEXT DEFAULT ''",
        "ALTER TABLE garment_style_values ADD COLUMN image_url TEXT DEFAULT ''",
        "ALTER TABLE garment_style_values ADD COLUMN ai_prompt TEXT DEFAULT ''",
    ]
    for _stmt in _style_alters:
        try:
            _db.execute(_stmt)
        except Exception:
            pass  # Column already exists
    _db.commit()
except Exception:
    pass

# ── Daily Craft table migration ───────────────────────────────────────────────
try:
    from database import get_db as _gdb2
    _dc = _gdb2()
    _dc.execute("""
        CREATE TABLE IF NOT EXISTS web_daily_craft (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_url TEXT DEFAULT '',
            caption TEXT DEFAULT '',
            tag TEXT DEFAULT '',
            posted_date TEXT DEFAULT (date('now','localtime')),
            created_at TEXT DEFAULT (datetime('now','localtime')),
            is_published INTEGER DEFAULT 1
        )
    """)
    _dc.commit()
except Exception:
    pass
# ── OTP log table migration ───────────────────────────────────────────────────
try:
    from database import get_db as _gdb3
    _otpdb = _gdb3()
    _otpdb.execute("""
        CREATE TABLE IF NOT EXISTS otp_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mobile TEXT NOT NULL,
            otp TEXT NOT NULL,
            purpose TEXT DEFAULT 'login',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            expires_at TEXT DEFAULT (datetime('now','localtime','+10 minutes')),
            used INTEGER DEFAULT 0
        )
    """)
    _otpdb.commit()
except Exception:
    pass
try:
    from database import get_db as _gdb4
    _fcmdb = _gdb4()
    _fcmdb.execute("""
        CREATE TABLE IF NOT EXISTS fcm_tokens (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER,
            token      TEXT NOT NULL UNIQUE,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    # Also add email column to customers if missing
    try:
        _fcmdb.execute("ALTER TABLE customers ADD COLUMN email TEXT DEFAULT ''")
    except Exception:
        pass
    _fcmdb.commit()
except Exception:
    pass
# ─────────────────────────────────────────────────────────────────────────────
from database import set_setting as _set_setting, get_setting as _get_setting
_cur = int(_get_setting("last_order_code", "0"))
if _cur < 3599:
    _set_setting("last_order_code", "3599")

# ── Auto-backup at 9:00 PM daily ─────────────────────────────────────────────
import threading, time as _time
def _auto_backup_worker():
    """Background thread: checks every 30 min, runs backup at 9PM IST."""
    last_backup_date = ""
    while True:
        try:
            _time.sleep(1800)  # Check every 30 minutes
            from datetime import datetime, timedelta, timezone
            ist = timezone(timedelta(hours=5, minutes=30))
            now = datetime.now(ist)
            today_str = now.strftime("%Y-%m-%d")
            if now.hour == 21 and last_backup_date != today_str:
                # Run backup
                last_backup_date = today_str
                from database import get_db as _bdb
                conn = _bdb()
                import json as _bj
                tables = ["customers","orders","order_items","order_images","work_logs",
                          "finance","employees","settings","measurement_fields","inventory",
                          "salary_advances","notify_log","web_accounts","web_addresses",
                          "web_wishlist","web_payment_methods"]
                backup = {}
                for t in tables:
                    try:
                        rows = conn.execute(f"SELECT * FROM {t}").fetchall()
                        backup[t] = [dict(r) for r in rows]
                    except: pass
                conn.close()
                backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups")
                os.makedirs(backup_dir, exist_ok=True)
                fname = os.path.join(backup_dir, f"auto_backup_{today_str}.json")
                with open(fname, "w") as f:
                    _bj.dump(backup, f, default=str)
                # Keep only last 7 backups
                import glob
                files = sorted(glob.glob(os.path.join(backup_dir, "auto_backup_*.json")))
                for old in files[:-7]:
                    try: os.remove(old)
                    except: pass
                from database import set_setting
                set_setting("last_backup_at", now.strftime("%d-%m-%Y %I:%M %p"))
                logger.info(f"Auto-backup saved: {fname}")
        except Exception as e:
            logger.error(f"Auto-backup error: {e}")

_backup_thread = threading.Thread(target=_auto_backup_worker, daemon=True)
_backup_thread.start()

# ── API routes ───────────────────────────────────────────────────────────────
@app.route("/api/settings/logo")
def api_logo():
    from database import get_setting
    return jsonify({"value": get_setting("shop_logo","")})

@app.route("/api/owner/earnings-7days")
def api_earnings():
    if not session.get("owner_logged_in"):
        return jsonify({"error":"unauthorized"}), 403
    from app.routes.owner import earnings_7days
    return earnings_7days()

@app.route("/export/orders")
def export_orders_root():
    if not session.get("owner_logged_in"):
        return redirect(url_for("owner.login"))
    from app.routes.owner import export_orders as _exp
    return _exp()


@app.context_processor
def inject_web_settings():
    result = {"web_settings": {}, "footer_pages": [], "footer_make_items": []}
    try:
        from database import get_db
        db = get_db()
        result["web_settings"] = {r["key"]: r["value"] for r in db.execute("SELECT key,value FROM settings").fetchall()}
    except Exception:
        pass
        pass
    try:
        from database import get_db
        db = get_db()
        result["footer_pages"] = db.execute("SELECT * FROM web_pages WHERE show_in_footer=1 ORDER BY sort_order,id").fetchall()
    except Exception:
        pass
        pass
    try:
        from database import get_db
        db = get_db()
        result["footer_make_items"] = db.execute("SELECT * FROM web_footer_make ORDER BY sort_order").fetchall()
    except Exception:
        pass
    return result

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)

