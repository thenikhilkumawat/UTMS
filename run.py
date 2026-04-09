import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, session, redirect, url_for, request
from config import Config
from database import init_db, get_setting
from app.routes.employee import bp as employee_bp
from app.routes.owner import bp as owner_bp

app = Flask(__name__, template_folder="templates", static_folder="static", static_url_path="/static")
app.secret_key = Config.SECRET_KEY

# Ensure static files are served with proper headers
@app.after_request
def add_header(response):
    if request.path.startswith("/static/"):
        response.headers["Cache-Control"] = "public, max-age=86400"
    return response


app.register_blueprint(employee_bp)
app.register_blueprint(owner_bp)

# ── Run DB init on every startup (works with gunicorn on Render too) ──────
import os as _os
_os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
init_db()
# Ensure order code starts at 3600 minimum
from database import set_setting as _set_setting, get_setting as _get_setting
_cur = int(_get_setting("last_order_code", "0"))
if _cur < 3599:
    _set_setting("last_order_code", "3599")

@app.after_request
def add_ngrok_header(response):
    response.headers["ngrok-skip-browser-warning"] = "true"
    return response

@app.route("/api/settings/logo")
def api_logo():
    from database import get_setting
    return jsonify({"value": get_setting("shop_logo","")})

# Redirect /api/owner/... to owner blueprint
@app.route("/api/owner/earnings-7days")
def api_earnings():
    if not session.get("owner_logged_in"):
        return jsonify({"error":"unauthorized"}), 403
    from app.routes.owner import earnings_7days
    return earnings_7days()

# Placeholder stubs for future modules
# work-log routes registered via employee blueprint

# work_log registered via employee blueprint

# /pickup registered via employee blueprint

# /finance registered via employee blueprint

# /customers registered via employee blueprint

# /owner/inventory registered via owner blueprint

# /owner/finance registered via owner blueprint

# /owner/customers registered via owner blueprint

# measurement-fields registered via owner blueprint

# /owner/whatsapp registered via owner blueprint

if __name__ == "__main__":
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    init_db()
    # Ensure default order code starts at 3600 if not already set above that
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

@app.route("/export/orders")
def export_orders_root():
    from flask import session, redirect, url_for
    if not session.get("owner_logged_in"):
        return redirect(url_for("owner.login"))
    from app.routes.owner import export_orders as _exp
    return _exp()
