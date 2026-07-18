# restart-trigger 1781961500
import os, sys, logging, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, session, redirect, url_for, request, g, render_template_string
from config import Config
from database import init_db, get_setting

app = Flask(__name__, template_folder="templates", static_folder="static", static_url_path="/static")
app.secret_key = Config.SECRET_KEY

# ── asset_v(): real cache-busting for static files ──────────────────────────
# Static files are served with a 1-year "immutable" Cache-Control header, which
# tells the browser to never even revalidate a given URL again once cached.
# That's fine ONLY if the URL itself changes whenever the file's content
# changes. This was previously done with a hand-typed "?v=1782918998" hardcoded
# directly in base.html — a number that never actually updated, so every
# browser that had ever loaded the page stayed stuck on that exact CSS/JS
# snapshot forever, no matter how many times the file was updated on the
# server (this is why mobile CSS fixes weren't showing up on already-visited
# devices). asset_v() now computes the version from the file's real
# last-modified time, so it changes automatically on every deploy that
# actually touches the file.
@app.template_global()
def asset_v(path):
    try:
        v = int(os.path.getmtime(os.path.join(app.static_folder, path)))
    except OSError:
        v = int(time.time())
    return f"/static/{path}?v={v}"


# ── Register blueprints ──────────────────────────────────────────────────────
from app.routes.employee import bp as employee_bp
from app.routes.owner import bp as owner_bp
app.register_blueprint(employee_bp)
app.register_blueprint(owner_bp)

# ── Cache-Control: prevent stale pages in the installed PWA ─────────────────
# No header was being set on dynamic pages before this, so mobile browsers —
# especially in installed/standalone PWA mode — could keep serving an old
# cached copy of a page even after a fresh deploy (this is why UI fixes weren't
# showing up on the phone). Static assets are left untouched: asset_v() already
# cache-busts those via a version query string, so long-lived caching there is fine.
@app.after_request
def _add_cache_headers(response):
    if not request.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

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

# restart-trigger 2026-07-18 18:43:33