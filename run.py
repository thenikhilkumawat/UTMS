import os, sys, logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, session, redirect, url_for, request, g, render_template_string
from config import Config
from database import init_db, get_setting

app = Flask(__name__, template_folder="templates", static_folder="static", static_url_path="/static")
app.secret_key = Config.SECRET_KEY

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
        response.headers["Cache-Control"] = "public, max-age=86400"
    response.headers["ngrok-skip-browser-warning"] = "true"
    return response

# ── Register blueprints ──────────────────────────────────────────────────────
from app.routes.employee import bp as employee_bp
from app.routes.owner import bp as owner_bp
app.register_blueprint(employee_bp)
app.register_blueprint(owner_bp)

# ── DB init on startup ───────────────────────────────────────────────────────
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
init_db()
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
                          "salary_advances","notify_log"]
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

if __name__ == "__main__":
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    init_db()
    cur_code = int(get_setting("last_order_code","0"))
    if cur_code < 3599:
        from database import set_setting
        set_setting("last_order_code","3599")
    print("\n" + "="*50)
    print("  Uttam Tailors Management System v2")
    print("  Running at: http://localhost:5000")
    print("  Owner PIN:  " + get_setting("owner_pin","1234"))
    print("  Next order: #" + str(int(get_setting("last_order_code","3599")) + 1))
    print("="*50 + "\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
