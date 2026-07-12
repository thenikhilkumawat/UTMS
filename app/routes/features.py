"""
features.py — Uttam Tailors new premium features
  • Live Stitch Tracker
  • Measurement Locker
  • Occasions / Countdown
  • Style Requests ("Bring Your Inspo") — chat system
  • Support Chat
  • Gifting Flow metadata
"""

from flask import Blueprint, request, jsonify, session, render_template
from database import get_db
from datetime import datetime, timedelta
import os, uuid

features_bp = Blueprint("features", __name__)

# ── DB bootstrap ──────────────────────────────────────────────────────────────
_tables_ready = False

def ensure_tables():
    global _tables_ready
    if _tables_ready:
        return
    try:
        db = get_db()
        db.executescript("""
        CREATE TABLE IF NOT EXISTS order_stages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            order_code  TEXT NOT NULL UNIQUE,
            stage       INTEGER DEFAULT 1,
            note        TEXT DEFAULT '',
            updated_at  TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS saved_measurements (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id  INTEGER NOT NULL,
            label       TEXT DEFAULT 'My Measurements',
            chest       REAL, shoulder REAL, sleeve REAL,
            waist       REAL, hip      REAL, inseam  REAL,
            neck        REAL, thigh    REAL, height  REAL, weight REAL,
            notes       TEXT DEFAULT '',
            created_at  TEXT DEFAULT (datetime('now','localtime')),
            updated_at  TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS occasions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id   INTEGER NOT NULL,
            name         TEXT NOT NULL,
            event_date   TEXT NOT NULL,
            garment_type TEXT DEFAULT '',
            created_at   TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS style_requests (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id      INTEGER,
            session_key     TEXT DEFAULT '',
            customer_name   TEXT DEFAULT '',
            customer_mobile TEXT DEFAULT '',
            garment_type    TEXT DEFAULT '',
            stitching_type  TEXT DEFAULT 'standard',
            style_notes     TEXT DEFAULT '',
            image_url       TEXT DEFAULT '',
            status          TEXT DEFAULT 'pending',
            created_at      TEXT DEFAULT (datetime('now','localtime')),
            updated_at      TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS style_request_messages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id  INTEGER NOT NULL,
            sender      TEXT NOT NULL,
            message     TEXT DEFAULT '',
            image_url   TEXT DEFAULT '',
            created_at  TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS support_chats (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id      INTEGER,
            session_key     TEXT DEFAULT '',
            customer_name   TEXT DEFAULT '',
            customer_mobile TEXT DEFAULT '',
            customer_email  TEXT DEFAULT '',
            status          TEXT DEFAULT 'open',
            created_at      TEXT DEFAULT (datetime('now','localtime')),
            updated_at      TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS support_messages (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id   INTEGER NOT NULL,
            sender    TEXT NOT NULL,
            message   TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
        """)
        # migrate: add customer_email if missing
        try:
            db.execute("ALTER TABLE support_chats ADD COLUMN customer_email TEXT DEFAULT ''")
        except Exception:
            pass
        # migrate: add attachment columns to support_messages
        try:
            db.execute("ALTER TABLE support_messages ADD COLUMN attachment_url TEXT DEFAULT ''")
        except Exception:
            pass
        try:
            db.execute("ALTER TABLE support_messages ADD COLUMN attachment_type TEXT DEFAULT ''")
        except Exception:
            pass
        db.commit()
        _tables_ready = True
    except Exception:
        pass


# ── Helpers ───────────────────────────────────────────────────────────────────
STITCH_STAGES = [
    (1, "Order Received",  "Your order is confirmed and in our queue."),
    (2, "Fabric Cut",      "We have cut the fabric to your measurements."),
    (3, "Stitching",       "Your garment is being stitched by our tailor."),
    (4, "Quality Check",   "Final fit and finish check before dispatch."),
    (5, "Ready",           "Your garment is ready — delivery or pickup arranged."),
]

def _get_account():
    acc_id = session.get("web_account_id")
    if not acc_id:
        return None
    return get_db().execute(
        "SELECT * FROM web_accounts WHERE id=? AND is_active=1", (acc_id,)
    ).fetchone()

def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _ensure_addresses_table():
    db = get_db()
    db.execute("""CREATE TABLE IF NOT EXISTS web_addresses (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id INTEGER NOT NULL,
        label      TEXT DEFAULT 'Home',
        full_name  TEXT DEFAULT '',
        mobile     TEXT DEFAULT '',
        line1      TEXT DEFAULT '',
        line2      TEXT DEFAULT '',
        city       TEXT DEFAULT '',
        state      TEXT DEFAULT '',
        pincode    TEXT DEFAULT '',
        is_default INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )""")
    db.commit()

def _ensure_payment_methods_table():
    db = get_db()
    db.execute("""CREATE TABLE IF NOT EXISTS web_payment_methods (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id   INTEGER NOT NULL,
        method_type  TEXT DEFAULT '',
        label        TEXT DEFAULT '',
        masked_detail TEXT DEFAULT '',
        last4        TEXT DEFAULT '',
        expiry_month TEXT DEFAULT '',
        expiry_year  TEXT DEFAULT '',
        upi_id       TEXT DEFAULT '',
        is_default   INTEGER DEFAULT 0,
        created_at   TEXT DEFAULT (datetime('now','localtime'))
    )""")
    # Migrate existing table
    for col in ["last4 TEXT DEFAULT ''", "expiry_month TEXT DEFAULT ''",
                "expiry_year TEXT DEFAULT ''", "upi_id TEXT DEFAULT ''"]:
        try:
            db.execute(f"ALTER TABLE web_payment_methods ADD COLUMN {col}")
        except Exception:
            pass
    db.commit()

def _save_upload(file_obj, prefix="img"):
    if not file_obj:
        return ""
    ext = os.path.splitext(file_obj.filename)[1].lower() or ".jpg"
    if ext not in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
        return ""
    fname = f"{prefix}_{uuid.uuid4().hex[:10]}{ext}"
    save_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "static", "website", "img", "inspo"
    )
    os.makedirs(save_dir, exist_ok=True)
    _ip = os.path.join(save_dir, fname); file_obj.save(_ip)
    from app.utils.image_optimize import optimize_image as _oi; _ip = _oi(_ip); fname = os.path.basename(_ip)
    return "/static/website/img/inspo/" + fname


# ═══════════════════════════════════════════════════════════════════════════════
# LIVE STITCH TRACKER
# ═══════════════════════════════════════════════════════════════════════════════

@features_bp.route("/api/order/stage/<order_code>")
def order_stage_get(order_code):
    ensure_tables()
    db = get_db()
    row = db.execute(
        "SELECT stage, note, updated_at FROM order_stages WHERE order_code=?",
        (order_code,)
    ).fetchone()
    # Fetch full order + customer details (garments from order_items)
    order = db.execute(
        """SELECT o.order_code, o.status, o.is_urgent, o.note as order_note,
                  o.delivery_date, o.payable_amount, o.advance_paid, o.remaining,
                  c.name as cname, c.mobile, c.address
           FROM orders o LEFT JOIN customers c ON c.id=o.customer_id
           WHERE o.order_code=?""",
        (order_code,)
    ).fetchone()
    order_data = {}
    if order:
        order_data = dict(order)
        # Get garments from order_items
        items = db.execute(
            """SELECT oi.garment_type, oi.quantity, oi.measurements, oi.notes
               FROM order_items oi
               JOIN orders o ON o.id = oi.order_id
               WHERE o.order_code=?""",
            (order_code,)
        ).fetchall()
        order_data["garments"] = [
            {"name": it["garment_type"], "qty": it["quantity"],
             "measurements": it["measurements"] or "", "notes": it["notes"] or ""}
            for it in items
        ]
    stage_val = row["stage"] if row else 1
    note_val  = row["note"] or "" if row else ""
    updated   = row["updated_at"] if row else ""
    return jsonify({"ok": True, "stage": stage_val, "note": note_val,
                    "updated_at": updated, "order": order_data,
                    "stages": [{"num": s[0], "name": s[1], "desc": s[2]} for s in STITCH_STAGES]})

@features_bp.route("/api/admin/order/stage", methods=["POST"])
def order_stage_set():
    if not session.get("owner_logged_in"):
        return jsonify({"ok": False}), 403
    ensure_tables()
    d = request.get_json(force=True, silent=True) or {}
    code  = d.get("order_code", "").strip()
    stage = int(d.get("stage", 1))
    note  = d.get("note", "").strip()
    if not code or not (1 <= stage <= 5):
        return jsonify({"ok": False, "error": "Invalid"})
    db  = get_db()
    now = _now()
    existing = db.execute("SELECT id FROM order_stages WHERE order_code=?", (code,)).fetchone()
    if existing:
        db.execute("UPDATE order_stages SET stage=?, note=?, updated_at=? WHERE order_code=?",
                   (stage, note, now, code))
    else:
        db.execute("INSERT INTO order_stages(order_code, stage, note, updated_at) VALUES(?,?,?,?)",
                   (code, stage, note, now))
    db.commit()

    # ── Email notification on key stage changes ───────────────────────────────
    STAGE_TO_STATUS = {3: "stitching", 5: "ready"}
    if stage in STAGE_TO_STATUS:
        try:
            email_status = STAGE_TO_STATUS[stage]
            _ord = db.execute(
                """SELECT o.web_account_id, c.name as cust_name,
                          COALESCE(c.email,'') as cust_email, c.mobile
                   FROM orders o
                   LEFT JOIN customers c ON c.id=o.customer_id
                   WHERE o.order_code=?""", (code,)
            ).fetchone()
            if _ord:
                _email_to = (_ord["cust_email"] or "").strip()
                _web_acc  = _ord["web_account_id"]
                _cname    = _ord["cust_name"] or "Customer"
                if not _email_to and _web_acc:
                    _acc = db.execute(
                        "SELECT email FROM web_accounts WHERE id=? LIMIT 1", (_web_acc,)
                    ).fetchone()
                    if _acc:
                        _email_to = (_acc["email"] or "").strip()
                if not _email_to and (_ord["mobile"] or "").strip():
                    _acc = db.execute(
                        "SELECT email FROM web_accounts WHERE mobile=? LIMIT 1",
                        (_ord["mobile"],)
                    ).fetchone()
                    if _acc:
                        _email_to = (_acc["email"] or "").strip()
                if _email_to:
                    from app.utils.email_notify import send_status_email as _se
                    _se(_email_to, code, _cname, email_status)
                if stage == 5:
                    db.execute(
                        "UPDATE orders SET status=\'ready\' WHERE order_code=? AND status=\'pending\'",
                        (code,)
                    )
                    db.commit()
        except Exception:
            pass

    return jsonify({"ok": True})

def ensure_order_stage(order_code):
    """Call this right after creating an order to seed stage=1."""
    ensure_tables()
    db = get_db()
    if not db.execute("SELECT id FROM order_stages WHERE order_code=?", (order_code,)).fetchone():
        db.execute("INSERT OR IGNORE INTO order_stages(order_code, stage) VALUES(?,1)", (order_code,))
        db.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# MEASUREMENT LOCKER
# ═══════════════════════════════════════════════════════════════════════════════

@features_bp.route("/api/measurements")
def measurements_list():
    acc = _get_account()
    if not acc:
        return jsonify({"ok": False, "error": "Login required"}), 401
    ensure_tables()
    rows = get_db().execute(
        "SELECT * FROM saved_measurements WHERE account_id=? ORDER BY updated_at DESC",
        (acc["id"],)
    ).fetchall()
    return jsonify({"ok": True, "measurements": [dict(r) for r in rows]})

@features_bp.route("/api/measurements/save", methods=["POST"])
def measurements_save():
    acc = _get_account()
    if not acc:
        return jsonify({"ok": False, "error": "Login required"}), 401
    ensure_tables()
    d     = request.get_json(force=True, silent=True) or {}
    label = (d.get("label") or "My Measurements").strip()
    notes = (d.get("notes") or "").strip()
    flds  = ["chest","shoulder","sleeve","waist","hip","inseam","neck","thigh","height","weight"]
    vals  = [d.get(f) for f in flds]
    now   = _now()
    mid   = d.get("id")
    db    = get_db()
    if mid:
        db.execute(
            "UPDATE saved_measurements SET label=?,notes=?,updated_at=?,"
            "chest=?,shoulder=?,sleeve=?,waist=?,hip=?,inseam=?,neck=?,thigh=?,height=?,weight=? "
            "WHERE id=? AND account_id=?",
            [label, notes, now] + vals + [mid, acc["id"]]
        )
    else:
        cur = db.execute(
            "INSERT INTO saved_measurements"
            "(account_id,label,notes,created_at,updated_at,"
            "chest,shoulder,sleeve,waist,hip,inseam,neck,thigh,height,weight)"
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [acc["id"], label, notes, now, now] + vals
        )
        mid = cur.lastrowid
    db.commit()
    return jsonify({"ok": True, "id": mid})

@features_bp.route("/api/measurements/<int:mid>/delete", methods=["POST"])
def measurements_delete(mid):
    acc = _get_account()
    if not acc:
        return jsonify({"ok": False}), 401
    ensure_tables()
    db = get_db()
    db.execute("DELETE FROM saved_measurements WHERE id=? AND account_id=?", (mid, acc["id"]))
    db.commit()
    return jsonify({"ok": True})


# ═══════════════════════════════════════════════════════════════════════════════
# OCCASIONS / COUNTDOWN
# ═══════════════════════════════════════════════════════════════════════════════

@features_bp.route("/api/occasions")
def occasions_list():
    acc = _get_account()
    if not acc:
        return jsonify({"ok": False, "error": "Login required"}), 401
    ensure_tables()
    rows = get_db().execute(
        "SELECT * FROM occasions WHERE account_id=? ORDER BY event_date ASC",
        (acc["id"],)
    ).fetchall()
    return jsonify({"ok": True, "occasions": [dict(r) for r in rows]})

@features_bp.route("/api/occasions/save", methods=["POST"])
def occasions_save():
    acc = _get_account()
    if not acc:
        return jsonify({"ok": False, "error": "Login required"}), 401
    ensure_tables()
    d    = request.get_json(force=True, silent=True) or {}
    name = d.get("name","").strip()
    date = d.get("event_date","").strip()
    gtype = d.get("garment_type","").strip()
    if not name or not date:
        return jsonify({"ok": False, "error": "Name and date required"})
    db  = get_db()
    cur = db.execute(
        "INSERT INTO occasions(account_id,name,event_date,garment_type) VALUES(?,?,?,?)",
        (acc["id"], name, date, gtype)
    )
    db.commit()
    return jsonify({"ok": True, "id": cur.lastrowid})

@features_bp.route("/api/occasions/<int:oid>/delete", methods=["POST"])
def occasions_delete(oid):
    acc = _get_account()
    if not acc:
        return jsonify({"ok": False}), 401
    ensure_tables()
    db = get_db()
    db.execute("DELETE FROM occasions WHERE id=? AND account_id=?", (oid, acc["id"]))
    db.commit()
    return jsonify({"ok": True})

@features_bp.route("/api/occasions/upcoming")
def occasions_upcoming():
    acc = _get_account()
    if not acc:
        return jsonify({"ok": False})
    ensure_tables()
    today = datetime.now().strftime("%Y-%m-%d")
    limit = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
    row = get_db().execute(
        "SELECT * FROM occasions WHERE account_id=? AND event_date>=? AND event_date<=? "
        "ORDER BY event_date ASC LIMIT 1",
        (acc["id"], today, limit)
    ).fetchone()
    if not row:
        return jsonify({"ok": False})
    days = (datetime.strptime(row["event_date"], "%Y-%m-%d") - datetime.now()).days
    return jsonify({"ok": True, "name": row["name"], "event_date": row["event_date"],
                    "days_left": max(days, 0), "garment_type": row["garment_type"]})


# ═══════════════════════════════════════════════════════════════════════════════
# STYLE REQUESTS — "BRING YOUR INSPO" CHAT
# ═══════════════════════════════════════════════════════════════════════════════

@features_bp.route("/style-request")
def style_request_page():
    page_meta = {
        "title": "Bring Your Inspo — Uttam Tailors",
        "desc":  "Share your style inspiration image and we'll stitch it exactly for you.",
        "robots": "noindex", "og_image": "",
    }
    return render_template("website/style_request.html", page_meta=page_meta)

@features_bp.route("/api/style-request/start", methods=["POST"])
def style_request_start():
    import traceback
    try:
        ensure_tables()
        db  = get_db()
        acc = _get_account()

        # Session key for guest ownership
        sess_key = session.get("style_session_key") or uuid.uuid4().hex
        session["style_session_key"] = sess_key

        image_url = _save_upload(request.files.get("image"), "inspo")
        name      = request.form.get("customer_name","").strip()
        mobile    = request.form.get("customer_mobile","").strip()
        garment   = request.form.get("garment_type","").strip()
        stitch    = request.form.get("stitching_type","standard").strip()
        notes     = request.form.get("style_notes","").strip()
        now       = _now()

        cur = db.execute(
            "INSERT INTO style_requests"
            " (account_id,session_key,customer_name,customer_mobile,"
            "garment_type,stitching_type,style_notes,image_url,status,created_at,updated_at)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (acc["id"] if acc else None, sess_key, name, mobile,
             garment, stitch, notes, image_url, "pending", now, now)
        )
        req_id = cur.lastrowid

        # First message = the customer's notes + image
        first_msg = notes or "Hi! I'd like a custom garment based on my inspo image."
        db.execute(
            "INSERT INTO style_request_messages(request_id,sender,message,image_url,created_at)"
            " VALUES(?,?,?,?,?)",
            (req_id, "customer", first_msg, image_url, now)
        )
        db.commit()
        session[f"sr_{req_id}"] = True
        return jsonify({"ok": True, "request_id": req_id})
    except Exception as e:
        import traceback as _tb
        print("style_request_start ERROR:", _tb.format_exc())
        return jsonify({"ok": False, "error": "Submission failed. Please try again."}), 500

@features_bp.route("/api/style-request/<int:req_id>/messages")
def style_request_messages(req_id):
    ensure_tables()
    db  = get_db()
    req = db.execute("SELECT * FROM style_requests WHERE id=?", (req_id,)).fetchone()
    if not req:
        return jsonify({"ok": False}), 404
    acc      = _get_account()
    is_admin = session.get("owner_logged_in")
    is_mine  = (
        (acc and req["account_id"] == acc["id"])
        or session.get(f"sr_{req_id}")
        or session.get("style_session_key") == req["session_key"]
    )
    if not is_mine and not is_admin:
        return jsonify({"ok": False}), 403
    msgs = db.execute(
        "SELECT * FROM style_request_messages WHERE request_id=? ORDER BY id ASC",
        (req_id,)
    ).fetchall()
    return jsonify({"ok": True, "status": req["status"],
                    "messages": [dict(m) for m in msgs]})

@features_bp.route("/api/style-request/<int:req_id>/send", methods=["POST"])
def style_request_send(req_id):
    ensure_tables()
    db  = get_db()
    req = db.execute("SELECT * FROM style_requests WHERE id=?", (req_id,)).fetchone()
    if not req:
        return jsonify({"ok": False}), 404
    acc      = _get_account()
    is_admin = session.get("owner_logged_in")
    is_mine  = (
        (acc and req["account_id"] == acc["id"])
        or session.get(f"sr_{req_id}")
        or session.get("style_session_key") == req["session_key"]
    )
    if not is_mine and not is_admin:
        return jsonify({"ok": False}), 403

    # Accept both JSON and form-data (for image uploads in chat)
    if request.content_type and "multipart" in request.content_type:
        message   = request.form.get("message","").strip()
        image_url = _save_upload(request.files.get("image"), "chat")
    else:
        d         = request.get_json(force=True, silent=True) or {}
        message   = d.get("message","").strip()
        image_url = ""

    if not message and not image_url:
        return jsonify({"ok": False, "error": "Empty message"})

    sender     = "admin" if is_admin else "customer"
    now        = _now()
    db.execute(
        "INSERT INTO style_request_messages(request_id,sender,message,image_url,created_at)"
        "VALUES(?,?,?,?,?)",
        (req_id, sender, message, image_url, now)
    )
    new_status = "active" if (sender == "admin" and req["status"] == "pending") else req["status"]
    db.execute("UPDATE style_requests SET status=?, updated_at=? WHERE id=?",
               (new_status, now, req_id))
    db.commit()
    return jsonify({"ok": True})


# ── Admin: list all style requests ───────────────────────────────────────────
@features_bp.route("/api/admin/style-requests/list")
def admin_style_requests_list():
    if not session.get("owner_logged_in"):
        return jsonify({"ok": False}), 403
    ensure_tables()
    db   = get_db()
    reqs = db.execute(
        "SELECT * FROM style_requests ORDER BY updated_at DESC LIMIT 200"
    ).fetchall()
    result = []
    for r in reqs:
        last = db.execute(
            "SELECT message, sender, image_url FROM style_request_messages "
            "WHERE request_id=? ORDER BY id DESC LIMIT 1", (r["id"],)
        ).fetchone()
        unread = db.execute(
            "SELECT COUNT(*) c FROM style_request_messages "
            "WHERE request_id=? AND sender='customer'", (r["id"],)
        ).fetchone()["c"]
        result.append({
            **dict(r),
            "last_message": last["message"] if last else "",
            "last_sender":  last["sender"]  if last else "",
            "last_image":   last["image_url"] if last else "",
            "unread": unread,
        })
    return jsonify({"ok": True, "requests": result})


# ═══════════════════════════════════════════════════════════════════════════════
# ACCOUNT ME (lightweight — returns logged-in state for widget use)
# ═══════════════════════════════════════════════════════════════════════════════

@features_bp.route("/api/account/me")
def account_me():
    acc = _get_account()
    if acc:
        k = acc.keys()
        def _g(field, default=""):
            return acc[field] if field in k else default
        # Load default address from web_addresses
        addr = {}
        try:
            _ensure_addresses_table()
            row = get_db().execute(
                "SELECT * FROM web_addresses WHERE account_id=? ORDER BY is_default DESC, id DESC LIMIT 1",
                (acc["id"],)
            ).fetchone()
            if row:
                addr = dict(row)
        except Exception:
            pass
        return jsonify({
            "ok": True, "logged_in": True,
            "name":            _g("name"),
            "mobile":          _g("mobile"),
            "email":           _g("email"),
            "preview_count":   _g("preview_count", 0) or 0,
            "profile_image":   _g("profile_image"),
            "address_line1":   addr.get("line1",""),
            "address_line2":   addr.get("line2",""),
            "address_city":    addr.get("city",""),
            "address_state":   addr.get("state",""),
            "address_pincode": addr.get("pincode",""),
        })
    return jsonify({"ok": True, "logged_in": False})

# ═══════════════════════════════════════════════════════════════════════════════
# SUPPORT CHAT
# ═══════════════════════════════════════════════════════════════════════════════

@features_bp.route("/api/support/start", methods=["POST"])
def support_start():
    ensure_tables()
    db   = get_db()
    acc  = _get_account()
    d    = request.get_json(force=True, silent=True) or {}

    sess_key = session.get("support_session_key") or uuid.uuid4().hex
    session["support_session_key"] = sess_key

    # Reuse existing open chat
    existing = None
    if acc:
        existing = db.execute(
            "SELECT id FROM support_chats WHERE account_id=? AND status='open' "
            "ORDER BY id DESC LIMIT 1", (acc["id"],)
        ).fetchone()
    if not existing:
        existing = db.execute(
            "SELECT id FROM support_chats WHERE session_key=? AND status='open' "
            "ORDER BY id DESC LIMIT 1", (sess_key,)
        ).fetchone()
    if existing:
        return jsonify({"ok": True, "chat_id": existing["id"], "existing": True})

    name   = (d.get("name")   or (acc["name"]   if acc else "")).strip()
    mobile = (d.get("mobile") or (acc["mobile"] if acc else "")).strip()
    acc_email = ""
    if acc and "email" in acc.keys():
        acc_email = acc["email"] or ""
    email  = (d.get("email")  or acc_email).strip()
    cur    = db.execute(
        "INSERT INTO support_chats(account_id,session_key,customer_name,customer_mobile,customer_email,status)"
        "VALUES(?,?,?,?,?,?)",
        (acc["id"] if acc else None, sess_key, name, mobile, email, "open")
    )
    db.commit()
    return jsonify({"ok": True, "chat_id": cur.lastrowid, "existing": False})

@features_bp.route("/api/support/<int:chat_id>/messages")
def support_messages(chat_id):
    ensure_tables()
    db   = get_db()
    chat = db.execute("SELECT * FROM support_chats WHERE id=?", (chat_id,)).fetchone()
    if not chat:
        return jsonify({"ok": False}), 404
    acc     = _get_account()
    is_admin = session.get("owner_logged_in")
    is_mine = (
        (acc and chat["account_id"] == acc["id"])
        or session.get("support_session_key") == chat["session_key"]
    )
    if not is_mine and not is_admin:
        return jsonify({"ok": False}), 403
    msgs = db.execute(
        "SELECT * FROM support_messages WHERE chat_id=? ORDER BY id ASC",
        (chat_id,)
    ).fetchall()
    return jsonify({"ok": True, "status": chat["status"],
                    "messages": [dict(m) for m in msgs]})

@features_bp.route("/api/admin/support/<int:chat_id>/reply", methods=["POST"])
def admin_support_reply(chat_id):
    if not session.get("owner_logged_in"):
        return jsonify({"ok": False}), 403
    ensure_tables()
    db   = get_db()
    chat = db.execute("SELECT * FROM support_chats WHERE id=?", (chat_id,)).fetchone()
    if not chat:
        return jsonify({"ok": False}), 404
    d       = request.get_json(force=True, silent=True) or {}
    message = d.get("message","").strip()
    if not message:
        return jsonify({"ok": False, "error": "Empty message"})
    now = _now()
    db.execute("INSERT INTO support_messages(chat_id,sender,message,created_at) VALUES(?,?,?,?)",
        (chat_id, "admin", message, now))
    db.execute("UPDATE support_chats SET updated_at=? WHERE id=?", (now, chat_id))
    db.commit()
    import threading
    _cd = dict(chat)
    def _notify():
        try:
            if _cd.get("customer_email"):
                from app.utils.email_notify import send_support_customer_email
                send_support_customer_email(_cd["customer_email"], _cd.get("customer_name") or "Customer", message)
            if _cd.get("account_id"):
                from app.utils.fcm import get_tokens_for_account, send_push
                tokens = get_tokens_for_account(_cd["account_id"])
                if tokens:
                    send_push(tokens, title="Uttam Tailors replied", body=message[:100], data={"url": "https://uttamtailors.in"})
        except Exception as e:
            import logging; logging.getLogger(__name__).warning("Admin reply notify: %s", e)
    threading.Thread(target=_notify, daemon=True).start()
    return jsonify({"ok": True})


@features_bp.route("/api/support/<int:chat_id>/send", methods=["POST"])
def support_send(chat_id):
    ensure_tables()
    db   = get_db()
    chat = db.execute("SELECT * FROM support_chats WHERE id=?", (chat_id,)).fetchone()
    if not chat:
        return jsonify({"ok": False}), 404
    acc      = _get_account()
    is_mine  = (
        (acc and chat["account_id"] == acc["id"])
        or session.get("support_session_key") == chat["session_key"]
    )
    if not is_mine:
        return jsonify({"ok": False}), 403
    d       = request.get_json(force=True, silent=True) or {}
    message = d.get("message","").strip()
    if not message:
        return jsonify({"ok": False, "error": "Empty message"})
    sender  = "customer"
    now     = _now()
    db.execute(
        "INSERT INTO support_messages(chat_id,sender,message,created_at) VALUES(?,?,?,?)",
        (chat_id, sender, message, now)
    )
    db.execute("UPDATE support_chats SET updated_at=? WHERE id=?", (now, chat_id))
    db.commit()

    # ── Notifications ────────────────────────────────────────────────────────
    import threading
    _cd = dict(chat)
    customer_name  = _cd.get("customer_name") or "Customer"
    customer_email = _cd.get("customer_email") or ""
    account_id     = _cd.get("account_id")

    if sender == "customer":
        def _notify_owner():
            try:
                from app.utils.email_notify import send_support_owner_email
                send_support_owner_email(chat_id, customer_name, message, customer_email)
            except Exception as e:
                import logging; logging.getLogger(__name__).warning("Support owner email error: %s", e)
            try:
                from app.utils.fcm import get_tokens_for_account, send_push
                owner_tokens = get_tokens_for_account(0)
                if owner_tokens:
                    send_push(owner_tokens, title="New Support Message",
                        body=customer_name + ": " + message[:80],
                        data={"url": "https://dashboard.uttamtailors.in"})
            except Exception as e:
                import logging; logging.getLogger(__name__).warning("Owner push error: %s", e)
        threading.Thread(target=_notify_owner, daemon=True).start()

    elif sender == "admin":
        def _notify_customer():
            try:
                if customer_email:
                    from app.utils.email_notify import send_support_customer_email
                    send_support_customer_email(customer_email, customer_name, message)
                if account_id:
                    from app.utils.fcm import get_tokens_for_account, send_push
                    tokens = get_tokens_for_account(account_id)
                    if tokens:
                        send_push(tokens,
                            title="Uttam Tailors replied 💬",
                            body=message[:100],
                            data={"url": "https://uttamtailors.in"})
            except Exception as e:
                import logging; logging.getLogger(__name__).warning("Support customer notify error: %s", e)
        threading.Thread(target=_notify_customer, daemon=True).start()

    return jsonify({"ok": True})

@features_bp.route("/api/support/<int:chat_id>/close", methods=["POST"])
def support_close(chat_id):
    if not session.get("owner_logged_in"):
        return jsonify({"ok": False}), 403
    ensure_tables()
    db = get_db()
    db.execute("UPDATE support_chats SET status='closed' WHERE id=?", (chat_id,))
    db.commit()
    return jsonify({"ok": True})

@features_bp.route("/api/support/<int:chat_id>/upload", methods=["POST"])
def support_upload(chat_id):
    ensure_tables()
    db   = get_db()
    chat = db.execute("SELECT * FROM support_chats WHERE id=?", (chat_id,)).fetchone()
    if not chat:
        return jsonify({"ok": False}), 404
    acc      = _get_account()
    is_mine  = (
        (acc and chat["account_id"] == acc["id"])
        or session.get("support_session_key") == chat["session_key"]
    )
    if not is_mine:
        return jsonify({"ok": False}), 403
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"ok": False, "error": "No file"})
    ext  = os.path.splitext(f.filename)[1].lower()
    mime = (f.content_type or "").lower()
    if mime.startswith("image/") or ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif"):
        att_type = "image"
    elif mime == "application/pdf" or ext == ".pdf":
        att_type = "pdf"
    elif mime.startswith("video/") or ext in (".mp4", ".mov", ".avi", ".webm", ".mkv"):
        att_type = "video"
    else:
        return jsonify({"ok": False, "error": "Only images, PDFs, and videos are allowed"})
    save_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "static", "uploads", "support"
    )
    os.makedirs(save_dir, exist_ok=True)
    fname = "supp_" + uuid.uuid4().hex[:12] + ext
    fpath = os.path.join(save_dir, fname)
    f.save(fpath)
    if att_type == "image":
        from app.utils.image_optimize import optimize_image as _oi
        fpath = _oi(fpath)
        fname = os.path.basename(fpath)
    url    = "/static/uploads/support/" + fname
    sender = "admin" if is_admin else "customer"
    now    = _now()
    db.execute(
        "INSERT INTO support_messages(chat_id,sender,message,attachment_url,attachment_type,created_at)"
        " VALUES(?,?,?,?,?,?)",
        (chat_id, sender, "", url, att_type, now)
    )
    db.execute("UPDATE support_chats SET updated_at=? WHERE id=?", (now, chat_id))
    db.commit()
    return jsonify({"ok": True, "url": url, "type": att_type})

@features_bp.route("/api/admin/support/list")
def admin_support_list():
    if not session.get("owner_logged_in"):
        return jsonify({"ok": False}), 403
    ensure_tables()
    db    = get_db()
    chats = db.execute(
        "SELECT * FROM support_chats ORDER BY updated_at DESC LIMIT 200"
    ).fetchall()
    result = []
    for c in chats:
        last = db.execute(
            "SELECT message, sender FROM support_messages "
            "WHERE chat_id=? ORDER BY id DESC LIMIT 1", (c["id"],)
        ).fetchone()
        unread = db.execute(
            "SELECT COUNT(*) c FROM support_messages "
            "WHERE chat_id=? AND sender='customer'", (c["id"],)
        ).fetchone()["c"]
        result.append({
            **dict(c),
            "last_message": last["message"] if last else "",
            "last_sender":  last["sender"]  if last else "",
            "unread": unread,
        })
    return jsonify({"ok": True, "chats": result})


# ═══════════════════════════════════════════════════════════════════════════════
# CUSTOMER AUTH — OTP LOGIN / SIGNUP
# ═══════════════════════════════════════════════════════════════════════════════

def _ensure_auth_tables():
    """Create web_accounts and web_otp_store if not present."""
    db = get_db()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS web_accounts (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        name          TEXT DEFAULT '',
        mobile        TEXT UNIQUE NOT NULL,
        email         TEXT DEFAULT '',
        password_hash TEXT DEFAULT '',
        preview_count INTEGER DEFAULT 0,
        tryon_count   INTEGER DEFAULT 0,
        is_active     INTEGER DEFAULT 1,
        created_at    TEXT DEFAULT (datetime('now','localtime'))
    );
    CREATE TABLE IF NOT EXISTS web_otp_store (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        mobile     TEXT NOT NULL,
        otp        TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        used       INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    );
    """)
    db.commit()
    # Migrate: add profile_image column if it doesn't exist yet
    try:
        db.execute("ALTER TABLE web_accounts ADD COLUMN profile_image TEXT DEFAULT ''")
        db.commit()
    except Exception:
        pass


def _generate_otp():
    import random
    return str(random.randint(100000, 999999))


def _send_otp_whatsapp(mobile, otp):
    """Log OTP; replace with real SMS/WhatsApp API in production."""
    import logging
    logging.getLogger(__name__).info("OTP for %s: %s", mobile, otp)


@features_bp.route("/api/auth/send-otp", methods=["POST"])
def auth_send_otp():
    """Send OTP to mobile number for passwordless login."""
    _ensure_auth_tables()
    d      = request.get_json(force=True, silent=True) or {}
    mobile = (d.get("mobile") or "").strip().lstrip("0")
    name   = (d.get("name") or "").strip()
    if not mobile or len(mobile) < 10:
        return jsonify({"ok": False, "error": "Enter a valid mobile number"})

    db  = get_db()
    now = _now()
    otp = _generate_otp()

    from datetime import timedelta
    expires_at = (datetime.now() + timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")

    db.execute("UPDATE web_otp_store SET used=1 WHERE mobile=? AND used=0", (mobile,))
    db.execute(
        "INSERT INTO web_otp_store(phone, mobile, otp, expires_at) VALUES(?,?,?,?)",
        (mobile, mobile, otp, expires_at)
    )
    db.commit()

    existing = db.execute("SELECT id FROM web_accounts WHERE mobile=?", (mobile,)).fetchone()
    if not existing and name:
        db.execute(
            "INSERT INTO web_accounts(mobile, name, created_at) VALUES(?,?,?)",
            (mobile, name, now)
        )
        db.commit()

    _send_otp_whatsapp(mobile, otp)

    import os
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    resp = {"ok": True, "message": "OTP sent to your WhatsApp"}
    if debug_mode:
        resp["_debug_otp"] = otp
    return jsonify(resp)


@features_bp.route("/api/auth/verify-otp", methods=["POST"])
def auth_verify_otp():
    """Verify OTP and log the customer in."""
    _ensure_auth_tables()
    d      = request.get_json(force=True, silent=True) or {}
    mobile = (d.get("mobile") or "").strip().lstrip("0")
    otp    = (d.get("otp") or "").strip()
    name   = (d.get("name") or "").strip()
    email  = (d.get("email") or "").strip()

    if not mobile or not otp:
        return jsonify({"ok": False, "error": "Mobile and OTP are required"})

    db  = get_db()
    now = _now()

    row = db.execute(
        """SELECT * FROM web_otp_store
           WHERE mobile=? AND otp=? AND used=0
             AND expires_at >= datetime('now','localtime')
           ORDER BY id DESC LIMIT 1""",
        (mobile, otp)
    ).fetchone()

    if not row:
        return jsonify({"ok": False, "error": "Invalid or expired OTP"})

    db.execute("UPDATE web_otp_store SET used=1 WHERE id=?", (row["id"],))

    acc = db.execute("SELECT * FROM web_accounts WHERE mobile=?", (mobile,)).fetchone()
    if acc:
        acc_id = acc["id"]
        updates, vals = [], []
        if name and not (acc["name"] or "").strip():
            updates.append("name=?"); vals.append(name)
        if email and not (acc["email"] or "").strip():
            updates.append("email=?"); vals.append(email)
        if updates:
            vals.append(acc_id)
            db.execute(f"UPDATE web_accounts SET {', '.join(updates)} WHERE id=?", vals)
    else:
        db.execute(
            "INSERT INTO web_accounts(mobile, name, email, is_active, created_at) VALUES(?,?,?,1,?)",
            (mobile, name, email, now)
        )
        acc_id = db.execute(
            "SELECT id FROM web_accounts WHERE mobile=? ORDER BY id DESC LIMIT 1", (mobile,)
        ).fetchone()["id"]

    db.commit()
    session["web_account_id"] = acc_id
    session.permanent = True

    acc_row = db.execute("SELECT * FROM web_accounts WHERE id=?", (acc_id,)).fetchone()
    return jsonify({
        "ok": True,
        "account": {
            "id":     acc_id,
            "name":   acc_row["name"]  or "",
            "mobile": acc_row["mobile"] or "",
            "email":  acc_row["email"] if "email" in acc_row.keys() else "",
        }
    })


@features_bp.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    """Log out the current customer (OTP flow)."""
    session.pop("web_account_id", None)
    return jsonify({"ok": True})


# ── Password-based account routes (used by account.html) ──────────────────────

@features_bp.route("/api/account/signup", methods=["POST"])
def account_signup():
    """Create a new customer account with password."""
    from werkzeug.security import generate_password_hash
    _ensure_auth_tables()
    d        = request.get_json(force=True, silent=True) or {}
    name     = (d.get("name")     or "").strip()
    mobile   = (d.get("mobile")   or "").strip().lstrip("0")
    email    = (d.get("email")    or "").strip()
    password = (d.get("password") or "").strip()

    if not mobile or len(mobile) < 10:
        return jsonify({"ok": False, "error": "Enter a valid 10-digit mobile number"})
    if not password or len(password) < 6:
        return jsonify({"ok": False, "error": "Password must be at least 6 characters"})

    db  = get_db()
    now = _now()
    existing = db.execute("SELECT id FROM web_accounts WHERE mobile=?", (mobile,)).fetchone()
    if existing:
        return jsonify({"ok": False, "error": "This mobile is already registered — please log in"})

    pw_hash = generate_password_hash(password)
    db.execute(
        "INSERT INTO web_accounts(mobile, name, email, password_hash, is_active, created_at) VALUES(?,?,?,?,1,?)",
        (mobile, name, email, pw_hash, now)
    )
    db.commit()
    acc = db.execute("SELECT * FROM web_accounts WHERE mobile=?", (mobile,)).fetchone()
    session["web_account_id"] = acc["id"]
    session.permanent = True
    return jsonify({"ok": True, "account": {"id": acc["id"], "name": name, "mobile": mobile, "email": email}})


@features_bp.route("/api/account/login", methods=["POST"])
def account_login():
    """Log in with mobile/email + password."""
    from werkzeug.security import check_password_hash
    _ensure_auth_tables()
    d          = request.get_json(force=True, silent=True) or {}
    identifier = (d.get("identifier") or "").strip().lstrip("0")
    password   = (d.get("password")   or "").strip()

    if not identifier or not password:
        return jsonify({"ok": False, "error": "Mobile/email and password are required"})

    db  = get_db()
    acc = db.execute(
        "SELECT * FROM web_accounts WHERE (mobile=? OR email=?) AND is_active=1",
        (identifier, identifier)
    ).fetchone()

    if not acc:
        return jsonify({"ok": False, "error": "No account found with that mobile or email"})

    pw_hash = acc["password_hash"] if "password_hash" in acc.keys() else ""
    if not pw_hash or not check_password_hash(pw_hash, password):
        return jsonify({"ok": False, "error": "Incorrect password"})

    session["web_account_id"] = acc["id"]
    session.permanent = True
    return jsonify({
        "ok": True,
        "account": {
            "id":     acc["id"],
            "name":   acc["name"]  or "",
            "mobile": acc["mobile"] or "",
            "email":  acc["email"] if "email" in acc.keys() else "",
        }
    })


@features_bp.route("/api/account/logout", methods=["POST"])
def account_logout():
    """Log out customer."""
    session.pop("web_account_id", None)
    return jsonify({"ok": True})


# ═══════════════════════════════════════════════════════════════════════════════
# ACCOUNT DASHBOARD ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@features_bp.route("/api/account/profile", methods=["POST"])
def account_profile_update():
    """Update name / email + default address on the account."""
    acc = _get_account()
    if not acc:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    d     = request.get_json(force=True, silent=True) or {}
    name  = (d.get("name")  or "").strip()
    email = (d.get("email") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "Name required"})
    line1   = (d.get("address_line1")   or "").strip()
    line2   = (d.get("address_line2")   or "").strip()
    city    = (d.get("address_city")    or "").strip()
    state   = (d.get("address_state")   or "").strip()
    pincode = (d.get("address_pincode") or "").strip()
    db = get_db()
    db.execute("UPDATE web_accounts SET name=?, email=? WHERE id=?", (name, email, acc["id"]))
    # Save/update default address in web_addresses
    if line1 and city:
        try:
            _ensure_addresses_table()
            existing = db.execute(
                "SELECT id FROM web_addresses WHERE account_id=? AND is_default=1 LIMIT 1",
                (acc["id"],)
            ).fetchone()
            if existing:
                db.execute(
                    "UPDATE web_addresses SET full_name=?,line1=?,line2=?,city=?,state=?,pincode=? WHERE id=?",
                    (name, line1, line2, city, state, pincode, existing["id"])
                )
            else:
                mobile = acc["mobile"] if "mobile" in acc.keys() else ""
                db.execute(
                    """INSERT INTO web_addresses
                       (account_id,label,full_name,mobile,line1,line2,city,state,pincode,is_default)
                       VALUES(?,?,?,?,?,?,?,?,?,1)""",
                    (acc["id"], "Home", name, mobile, line1, line2, city, state, pincode)
                )
        except Exception:
            pass
    db.commit()
    return jsonify({"ok": True})


@features_bp.route("/api/account/profile-image", methods=["POST"])
def account_profile_image():
    """Upload / replace the account profile photo."""
    _ensure_auth_tables()
    acc = _get_account()
    if not acc:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    f = request.files.get("image")
    if not f:
        return jsonify({"ok": False, "error": "No file"})
    ext = os.path.splitext(f.filename)[1].lower() or ".jpg"
    if ext not in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
        return jsonify({"ok": False, "error": "Only JPG/PNG/WEBP allowed"})
    import uuid as _uuid
    fname = f"avatar_{acc['id']}_{_uuid.uuid4().hex[:8]}{ext}"
    save_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "static", "website", "img", "avatars"
    )
    os.makedirs(save_dir, exist_ok=True)
    fpath = os.path.join(save_dir, fname)
    f.save(fpath)
    try:
        from app.utils.image_optimize import optimize_image as _oi
        fpath = _oi(fpath); fname = os.path.basename(fpath)
    except Exception:
        pass
    url = "/static/website/img/avatars/" + fname
    db = get_db()
    db.execute("UPDATE web_accounts SET profile_image=? WHERE id=?", (url, acc["id"]))
    db.commit()
    return jsonify({"ok": True, "url": url})


@features_bp.route("/api/account/addresses")
def account_addresses_list():
    acc = _get_account()
    if not acc:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    _ensure_addresses_table()
    rows = get_db().execute(
        "SELECT * FROM web_addresses WHERE account_id=? ORDER BY is_default DESC, id DESC",
        (acc["id"],)
    ).fetchall()
    return jsonify({"ok": True, "addresses": [dict(r) for r in rows]})


@features_bp.route("/api/account/addresses", methods=["POST"])
def account_addresses_add():
    acc = _get_account()
    if not acc:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    _ensure_addresses_table()
    d        = request.get_json(force=True, silent=True) or {}
    label     = (d.get("label")     or "Home").strip()
    full_name = (d.get("full_name") or "").strip()
    mobile    = (d.get("mobile")    or "").strip()
    line1     = (d.get("line1")     or "").strip()
    line2     = (d.get("line2")     or "").strip()
    city      = (d.get("city")      or "").strip()
    state     = (d.get("state")     or "").strip()
    pincode   = (d.get("pincode")   or "").strip()
    if not line1 or not city:
        return jsonify({"ok": False, "error": "Address line and city required"})
    db = get_db()
    # if this is first address, mark as default
    count = db.execute(
        "SELECT COUNT(*) FROM web_addresses WHERE account_id=?", (acc["id"],)
    ).fetchone()[0]
    is_default = 1 if count == 0 else 0
    db.execute(
        """INSERT INTO web_addresses
           (account_id, label, full_name, mobile, line1, line2, city, state, pincode, is_default)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (acc["id"], label, full_name, mobile, line1, line2, city, state, pincode, is_default)
    )
    db.commit()
    return jsonify({"ok": True})


@features_bp.route("/api/account/addresses/<int:addr_id>/delete", methods=["POST"])
def account_addresses_delete(addr_id):
    acc = _get_account()
    if not acc:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    db = get_db()
    db.execute(
        "DELETE FROM web_addresses WHERE id=? AND account_id=?",
        (addr_id, acc["id"])
    )
    db.commit()
    return jsonify({"ok": True})


@features_bp.route("/api/account/addresses/<int:addr_id>/default", methods=["POST"])
def account_addresses_set_default(addr_id):
    acc = _get_account()
    if not acc:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    db = get_db()
    db.execute(
        "UPDATE web_addresses SET is_default=0 WHERE account_id=?", (acc["id"],)
    )
    db.execute(
        "UPDATE web_addresses SET is_default=1 WHERE id=? AND account_id=?",
        (addr_id, acc["id"])
    )
    db.commit()
    return jsonify({"ok": True})


@features_bp.route("/api/account/orders")
def account_orders_list():
    acc = _get_account()
    if not acc:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    db   = get_db()
    rows = []
    try:
        # 1. Orders linked directly by web_account_id
        linked = db.execute(
            """SELECT o.id, o.order_code, o.order_date, o.delivery_date,
                      o.payable_amount, o.status, o.payment_mode, o.note,
                      c.name as customer_name
               FROM orders o
               LEFT JOIN customers c ON c.id=o.customer_id
               WHERE o.web_account_id=?
               ORDER BY o.id DESC LIMIT 50""",
            (acc["id"],)
        ).fetchall()
        order_ids = {r["id"] for r in linked}
        rows = list(linked)

        # 2. Orders matched by customer mobile (for orders placed before account linkage)
        mobile     = (acc["mobile"] or "").lstrip("0")
        mobile_alt = "0" + mobile
        cust = db.execute(
            "SELECT id FROM customers WHERE mobile=? OR mobile=? ORDER BY id DESC LIMIT 1",
            (mobile, mobile_alt)
        ).fetchone()
        if cust:
            extra = db.execute(
                """SELECT o.id, o.order_code, o.order_date, o.delivery_date,
                          o.payable_amount, o.status, o.payment_mode, o.note,
                          c.name as customer_name
                   FROM orders o
                   LEFT JOIN customers c ON c.id=o.customer_id
                   WHERE o.customer_id=? AND o.id NOT IN ({})
                   ORDER BY o.id DESC LIMIT 50""".format(
                    ",".join(str(i) for i in order_ids) if order_ids else "0"
                ),
                (cust["id"],)
            ).fetchall()
            rows = rows + list(extra)
            rows.sort(key=lambda r: r["id"], reverse=True)
            rows = rows[:50]

        # Enrich each order with its garment types from order_items
        result = []
        for r in rows:
            d = dict(r)
            items = db.execute(
                "SELECT garment_type, quantity, rate FROM order_items WHERE order_id=?",
                (r["id"],)
            ).fetchall()
            d["items"] = [dict(i) for i in items]
            d["garment_name"] = ", ".join(i["garment_type"] for i in items) if items else ""
            result.append(d)

    except Exception as e:
        return jsonify({"ok": True, "orders": [], "error": str(e)})

    return jsonify({"ok": True, "orders": result})


# ═══════════════════════════════════════════════════════════════════════════════
# WISHLIST
# ═══════════════════════════════════════════════════════════════════════════════

def _ensure_wishlist_table():
    """
    Ensure web_wishlist has all required columns.
    The base table may already exist with a minimal schema (id, account_id, item_id, created_at)
    so we CREATE IF NOT EXISTS and then ALTER to add missing columns.
    """
    db = get_db()
    try:
        db.execute(
            """CREATE TABLE IF NOT EXISTS web_wishlist (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                item_id    INTEGER NOT NULL,
                created_at TEXT DEFAULT (datetime('now','localtime')),
                UNIQUE(account_id, item_id)
            )"""
        )
        db.commit()
    except Exception:
        pass
    # Add extra columns if they don't exist yet
    for stmt in [
        "ALTER TABLE web_wishlist ADD COLUMN item_name TEXT DEFAULT ''",
        "ALTER TABLE web_wishlist ADD COLUMN item_price REAL DEFAULT 0",
        "ALTER TABLE web_wishlist ADD COLUMN item_img TEXT DEFAULT ''",
        "ALTER TABLE web_wishlist ADD COLUMN added_at TEXT DEFAULT (datetime('now','localtime'))",
        "ALTER TABLE web_wishlist ADD COLUMN price_snapshot REAL",
        "ALTER TABLE web_wishlist ADD COLUMN stock_snapshot INTEGER",
    ]:
        try:
            db.execute(stmt)
        except Exception:
            pass
    try:
        db.execute("UPDATE web_wishlist SET added_at=created_at WHERE added_at IS NULL OR added_at=''")
        db.commit()
    except Exception:
        pass


@features_bp.route("/api/account/wishlist")
def account_wishlist_list():
    acc = _get_account()
    if not acc:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    _ensure_wishlist_table()
    rows = get_db().execute(
        "SELECT * FROM web_wishlist WHERE account_id=? ORDER BY added_at DESC",
        (acc["id"],)
    ).fetchall()
    return jsonify({"ok": True, "wishlist": [dict(r) for r in rows]})


@features_bp.route("/api/account/wishlist/toggle", methods=["POST"])
def account_wishlist_toggle():
    acc = _get_account()
    if not acc:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    _ensure_wishlist_table()
    d        = request.get_json(force=True, silent=True) or {}
    item_id   = int(d.get("item_id", 0))
    item_name = (d.get("item_name") or "").strip()
    item_price= float(d.get("item_price") or 0)
    item_img  = (d.get("item_img") or "").strip()
    if not item_id:
        return jsonify({"ok": False, "error": "item_id required"})
    db  = get_db()
    row = db.execute(
        "SELECT id FROM web_wishlist WHERE account_id=? AND item_id=?",
        (acc["id"], item_id)
    ).fetchone()
    if row:
        db.execute(
            "DELETE FROM web_wishlist WHERE account_id=? AND item_id=?",
            (acc["id"], item_id)
        )
        db.commit()
        return jsonify({"ok": True, "action": "removed"})
    else:
        try:
            db.execute(
                """INSERT INTO web_wishlist(account_id, item_id, item_name, item_price, item_img)
                   VALUES(?,?,?,?,?)""",
                (acc["id"], item_id, item_name, item_price, item_img)
            )
            db.commit()
        except Exception:
            pass  # already exists
        return jsonify({"ok": True, "action": "added"})


@features_bp.route("/api/account/wishlist/merge", methods=["POST"])
def account_wishlist_merge():
    """
    Merge guest wishlist into logged-in account's wishlist.
    Accepts EITHER:
      {item_ids: [1, 2, 3]}          — sent by base.html / account.html
      {items: [{item_id, ...}, ...]} — richer format
    """
    acc = _get_account()
    if not acc:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    _ensure_wishlist_table()
    d        = request.get_json(force=True, silent=True) or {}
    db       = get_db()

    # Support both payload formats
    item_ids = d.get("item_ids") or []   # simple ID list
    items    = d.get("items")    or []   # rich object list

    # Normalise item_ids → items
    for iid in item_ids:
        try:
            iid = int(iid)
            if iid > 0:
                items.append({"item_id": iid, "item_name": "", "item_price": 0, "item_img": ""})
        except Exception:
            pass

    for item in items:
        try:
            item_id = int(item.get("item_id", 0))
            if item_id <= 0:
                continue
            # Try to resolve item details from DB if not provided
            item_name  = (item.get("item_name")  or "").strip()
            item_price = float(item.get("item_price") or 0)
            item_img   = (item.get("item_img")   or "").strip()
            if not item_name:
                row = db.execute(
                    "SELECT name, price, image_url FROM web_service_items WHERE id=?", (item_id,)
                ).fetchone()
                if row:
                    item_name  = row["name"]  or ""
                    item_price = float(row["price"] or 0)
                    item_img   = row["image_url"] or ""
            db.execute(
                """INSERT OR IGNORE INTO web_wishlist(account_id, item_id, item_name, item_price, item_img, added_at)
                   VALUES(?,?,?,?,?,datetime('now','localtime'))""",
                (acc["id"], item_id, item_name, item_price, item_img)
            )
        except Exception:
            pass
    db.commit()
    return jsonify({"ok": True})


@features_bp.route("/api/wishlist-status")
def wishlist_status():
    """Return which item IDs from ?ids=1,2,3 are wishlisted by current account."""
    acc = _get_account()
    if not acc:
        return jsonify({"ok": True, "wishlisted": []})
    _ensure_wishlist_table()
    ids_param = request.args.get("ids", "")
    try:
        ids = [int(x) for x in ids_param.split(",") if x.strip().isdigit()]
    except Exception:
        ids = []
    if not ids:
        return jsonify({"ok": True, "wishlisted": []})
    placeholders = ",".join("?" * len(ids))
    rows = get_db().execute(
        f"SELECT item_id FROM web_wishlist WHERE account_id=? AND item_id IN ({placeholders})",
        [acc["id"]] + ids
    ).fetchall()
    return jsonify({"ok": True, "wishlisted": [r["item_id"] for r in rows]})


# ═══════════════════════════════════════════════════════════════════════════════
# PAYMENT METHODS
# ═══════════════════════════════════════════════════════════════════════════════

@features_bp.route("/api/account/payment-methods")
def account_payment_methods_list():
    acc = _get_account()
    if not acc:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    _ensure_payment_methods_table()
    rows = get_db().execute(
        "SELECT * FROM web_payment_methods WHERE account_id=? ORDER BY is_default DESC, id DESC",
        (acc["id"],)
    ).fetchall()
    return jsonify({"ok": True, "methods": [dict(r) for r in rows]})


@features_bp.route("/api/account/payment-methods/add", methods=["POST"])
def account_payment_methods_add():
    acc = _get_account()
    if not acc:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    _ensure_payment_methods_table()
    d            = request.get_json(force=True, silent=True) or {}
    method_type  = (d.get("method_type")  or "card").strip()
    label        = (d.get("label")        or "").strip()
    masked_detail= (d.get("masked_detail")or "").strip()
    last4        = (d.get("last4")        or "").strip()[-4:]
    expiry_month = (d.get("expiry_month") or "").strip()
    expiry_year  = (d.get("expiry_year")  or "").strip()
    upi_id       = (d.get("upi_id")       or "").strip()
    if not label and not last4 and not upi_id:
        return jsonify({"ok": False, "error": "Please fill in the payment details"})
    db = get_db()
    count = db.execute(
        "SELECT COUNT(*) FROM web_payment_methods WHERE account_id=?", (acc["id"],)
    ).fetchone()[0]
    is_default = 1 if count == 0 else 0
    db.execute(
        """INSERT INTO web_payment_methods
           (account_id, method_type, label, masked_detail, last4, expiry_month, expiry_year, upi_id, is_default)
           VALUES(?,?,?,?,?,?,?,?,?)""",
        (acc["id"], method_type, label, masked_detail, last4, expiry_month, expiry_year, upi_id, is_default)
    )
    db.commit()
    return jsonify({"ok": True})


@features_bp.route("/api/account/payment-methods/<int:pm_id>/delete", methods=["POST"])
def account_payment_methods_delete(pm_id):
    acc = _get_account()
    if not acc:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    db = get_db()
    db.execute(
        "DELETE FROM web_payment_methods WHERE id=? AND account_id=?",
        (pm_id, acc["id"])
    )
    db.commit()
    return jsonify({"ok": True})


# ═══════════════════════════════════════════════════════════════════════════════
# CHANGE PASSWORD / DELETE ACCOUNT
# ═══════════════════════════════════════════════════════════════════════════════

@features_bp.route("/api/account/change-password", methods=["POST"])
def account_change_password():
    from werkzeug.security import check_password_hash, generate_password_hash
    acc = _get_account()
    if not acc:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    d        = request.get_json(force=True, silent=True) or {}
    old_pw   = (d.get("old_password") or "").strip()
    new_pw   = (d.get("new_password") or "").strip()
    if not new_pw or len(new_pw) < 6:
        return jsonify({"ok": False, "error": "New password must be at least 6 characters"})
    pw_hash = acc["password_hash"] if "password_hash" in acc.keys() else ""
    if pw_hash and not check_password_hash(pw_hash, old_pw):
        return jsonify({"ok": False, "error": "Current password is incorrect"})
    db = get_db()
    db.execute(
        "UPDATE web_accounts SET password_hash=? WHERE id=?",
        (generate_password_hash(new_pw), acc["id"])
    )
    db.commit()
    return jsonify({"ok": True})


@features_bp.route("/api/account/delete", methods=["POST"])
def account_delete():
    acc = _get_account()
    if not acc:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    db  = get_db()
    now = _now()
    db.execute(
        "UPDATE web_accounts SET is_active=0, deleted_at=? WHERE id=?",
        (now, acc["id"])
    )
    db.commit()
    session.pop("web_account_id", None)
    return jsonify({"ok": True})


# ═══════════════════════════════════════════════════════════════════════════════
# CART
# ═══════════════════════════════════════════════════════════════════════════════

@features_bp.route("/api/cart/add", methods=["POST"])
def cart_add():
    acc = _get_account()
    if not acc:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    d          = request.get_json(force=True, silent=True) or {}
    item_id    = int(d.get("item_id", 0))
    item_name  = (d.get("item_name")  or "").strip()
    item_price = float(d.get("item_price") or 0)
    item_img   = (d.get("item_img")   or "").strip()
    qty        = max(1, int(d.get("qty") or 1))
    if not item_id:
        return jsonify({"ok": False, "error": "item_id required"})
    db  = get_db()
    row = db.execute(
        "SELECT id, qty FROM web_carts WHERE account_id=? AND item_id=?",
        (acc["id"], item_id)
    ).fetchone()
    if row:
        db.execute(
            "UPDATE web_carts SET qty=qty+? WHERE id=?", (qty, row["id"])
        )
    else:
        db.execute(
            """INSERT INTO web_carts(account_id, item_id, item_name, item_price, item_img, qty)
               VALUES(?,?,?,?,?,?)""",
            (acc["id"], item_id, item_name, item_price, item_img, qty)
        )
    db.commit()
    count = db.execute(
        "SELECT COALESCE(SUM(qty),0) FROM web_carts WHERE account_id=?", (acc["id"],)
    ).fetchone()[0]
    return jsonify({"ok": True, "cart_count": count})


@features_bp.route("/api/cart/sync", methods=["POST"])
def cart_sync():
    """Merge guest cart (JSON array) into account cart after login."""
    acc = _get_account()
    if not acc:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    d     = request.get_json(force=True, silent=True) or {}
    items = d.get("items") or []
    db    = get_db()
    for item in items:
        try:
            item_id    = int(item.get("item_id", 0))
            item_name  = (item.get("item_name")  or "")
            item_price = float(item.get("item_price") or 0)
            item_img   = (item.get("item_img")   or "")
            qty        = max(1, int(item.get("qty") or 1))
            row = db.execute(
                "SELECT id FROM web_carts WHERE account_id=? AND item_id=?",
                (acc["id"], item_id)
            ).fetchone()
            if row:
                db.execute("UPDATE web_carts SET qty=qty+? WHERE id=?", (qty, row["id"]))
            else:
                db.execute(
                    """INSERT INTO web_carts(account_id, item_id, item_name, item_price, item_img, qty)
                       VALUES(?,?,?,?,?,?)""",
                    (acc["id"], item_id, item_name, item_price, item_img, qty)
                )
        except Exception:
            pass
    db.commit()
    count = db.execute(
        "SELECT COALESCE(SUM(qty),0) FROM web_carts WHERE account_id=?", (acc["id"],)
    ).fetchone()[0]
    return jsonify({"ok": True, "cart_count": count})


@features_bp.route("/api/cart")
def cart_list():
    acc = _get_account()
    if not acc:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    rows = get_db().execute(
        "SELECT * FROM web_carts WHERE account_id=? ORDER BY added_at DESC",
        (acc["id"],)
    ).fetchall()
    return jsonify({"ok": True, "items": [dict(r) for r in rows]})


@features_bp.route("/api/cart/remove", methods=["POST"])
def cart_remove():
    acc = _get_account()
    if not acc:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    d       = request.get_json(force=True, silent=True) or {}
    cart_id = int(d.get("cart_id", 0))
    db      = get_db()
    db.execute("DELETE FROM web_carts WHERE id=? AND account_id=?", (cart_id, acc["id"]))
    db.commit()
    count = db.execute(
        "SELECT COALESCE(SUM(qty),0) FROM web_carts WHERE account_id=?", (acc["id"],)
    ).fetchone()[0]
    return jsonify({"ok": True, "cart_count": count})


# ═══════════════════════════════════════════════════════════════════════════════
# ITEM VIEWS / RECOMMENDATIONS
# ═══════════════════════════════════════════════════════════════════════════════

@features_bp.route("/api/item/view", methods=["POST"])
def item_view():
    """Record that the current visitor viewed an item."""
    d          = request.get_json(force=True, silent=True) or {}
    item_id    = int(d.get("item_id", 0))
    if not item_id:
        return jsonify({"ok": False})
    acc        = _get_account()
    acc_id     = acc["id"] if acc else None
    session_key= session.get("session_key") or str(uuid.uuid4().hex)
    session["session_key"] = session_key
    db = get_db()
    try:
        db.execute(
            """INSERT OR REPLACE INTO web_item_views(item_id, account_id, session_key, viewed_at)
               VALUES(?,?,?,datetime('now','localtime'))""",
            (item_id, acc_id, session_key)
        )
        db.commit()
    except Exception:
        pass
    return jsonify({"ok": True})


@features_bp.route("/api/item/viewers/<int:item_id>")
def item_viewers(item_id):
    """Return recent unique viewer count for social proof."""
    try:
        since = (datetime.now() - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
        count = get_db().execute(
            """SELECT COUNT(DISTINCT COALESCE(account_id, session_key)) FROM web_item_views
               WHERE item_id=? AND viewed_at >= ?""",
            (item_id, since)
        ).fetchone()[0]
    except Exception:
        count = 0
    return jsonify({"ok": True, "viewers": count})


@features_bp.route("/api/recommendations")
def recommendations():
    """Return up to 8 recommended item IDs based on recent views."""
    acc        = _get_account()
    session_key= session.get("session_key", "")
    db         = get_db()
    try:
        if acc:
            rows = db.execute(
                """SELECT item_id, COUNT(*) AS cnt FROM web_item_views
                   WHERE account_id=?
                   GROUP BY item_id ORDER BY cnt DESC LIMIT 20""",
                (acc["id"],)
            ).fetchall()
        elif session_key:
            rows = db.execute(
                """SELECT item_id, COUNT(*) AS cnt FROM web_item_views
                   WHERE session_key=?
                   GROUP BY item_id ORDER BY cnt DESC LIMIT 20""",
                (session_key,)
            ).fetchall()
        else:
            rows = []
        item_ids = [r["item_id"] for r in rows]
        return jsonify({"ok": True, "item_ids": item_ids[:8]})
    except Exception as e:
        return jsonify({"ok": True, "item_ids": []})


# ═══════════════════════════════════════════════════════════════════════════════
# ORDERS CREATE (JSON-based, used by order_review.html)
# ═══════════════════════════════════════════════════════════════════════════════

@features_bp.route("/api/orders/create", methods=["POST"])
def orders_create():
    """
    JSON-based order creation used by order_review.html.
    Uses the REAL orders schema: customer_id FK + order_code + order_items table.
    """
    import json as _json
    from database import next_order_code as _next_code

    d = request.get_json(force=True, silent=True) or {}

    customer_name    = (d.get("customer_name")  or "").strip()
    customer_phone   = (d.get("customer_phone") or "").strip().lstrip("0")
    customer_address = (d.get("customer_address") or "").strip()
    garment_name     = (d.get("garment_name")   or "").strip()
    garment_price    = float(d.get("garment_price") or 0)
    quantity         = max(1, int(d.get("quantity") or 1))
    size             = (d.get("size")     or "").strip()
    fabric           = (d.get("fabric")   or "own").strip()
    notes            = (d.get("notes")    or "").strip()
    delivery         = (d.get("delivery") or "pickup").strip()
    delivery_date    = (d.get("delivery_date") or "").strip()
    urgent           = bool(d.get("urgent", False))
    coupon_code      = (d.get("coupon_code") or "").strip().upper()
    measurements     = d.get("measurements") or {}
    styles           = d.get("styles") or {}
    cart_items_raw   = d.get("cart_items")

    cart_items_parsed = []
    if cart_items_raw and isinstance(cart_items_raw, list):
        for ci in cart_items_raw:
            ci_name  = str(ci.get("name") or "").strip()
            ci_price = float(ci.get("price") or 0)
            ci_qty   = max(1, int(ci.get("qty") or 1))
            if ci_name:
                cart_items_parsed.append({"name": ci_name, "price": ci_price, "qty": ci_qty, "amount": round(ci_price * ci_qty, 2)})
        if cart_items_parsed:
            garment_name  = ", ".join(ci["name"] + (" x"+str(ci["qty"]) if ci["qty"] > 1 else "") for ci in cart_items_parsed)
            garment_price = sum(ci["amount"] for ci in cart_items_parsed)
            quantity      = 1

    if not customer_name or not customer_phone:
        return jsonify({"ok": False, "error": "Name and phone required"})
    if not garment_name:
        return jsonify({"ok": False, "error": "Garment name required"})

    db  = get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    today = datetime.now().strftime("%Y-%m-%d")

    # ── Find or create customer ──────────────────────────────────────────────
    cust = db.execute(
        "SELECT id FROM customers WHERE mobile=? ORDER BY id DESC LIMIT 1",
        (customer_phone,)
    ).fetchone()
    if cust:
        customer_id = cust["id"]
        # Update address if provided
        if customer_address:
            db.execute("UPDATE customers SET address=? WHERE id=?", (customer_address, customer_id))
    else:
        db.execute(
            "INSERT INTO customers(name, mobile, address, created_at) VALUES(?,?,?,?)",
            (customer_name, customer_phone, customer_address, now)
        )
        row = db.execute(
            "SELECT id FROM customers WHERE mobile=? ORDER BY id DESC LIMIT 1",
            (customer_phone,)
        ).fetchone()
        customer_id = row["id"] if row else None

    if not customer_id:
        return jsonify({"ok": False, "error": "Could not create customer record"})

    # ── Coupon validation ────────────────────────────────────────────────────
    base_amount     = round(garment_price * quantity, 2)
    extra_charges   = round(base_amount * 0.10, 2) if urgent else 0.0
    payable_amount  = round(base_amount + extra_charges, 2)
    coupon_discount = 0.0
    coupon_row      = None
    if coupon_code:
        try:
            coupon_row = db.execute(
                """SELECT * FROM web_coupons WHERE code=? AND active=1
                   AND (expires_on='' OR expires_on IS NULL OR expires_on >= date('now'))
                   AND (max_uses=0 OR used_count < max_uses)""",
                (coupon_code,)
            ).fetchone()
            if coupon_row and payable_amount >= coupon_row["min_order"]:
                if coupon_row["discount_type"] == "percent":
                    coupon_discount = round(payable_amount * coupon_row["discount_value"] / 100, 2)
                else:
                    coupon_discount = float(coupon_row["discount_value"])
                coupon_discount = min(coupon_discount, payable_amount)
        except Exception:
            coupon_discount = 0.0
    payable_amount = round(payable_amount - coupon_discount, 2)

    # ── Build order note ─────────�
    # ── Build order note (pipe-separated, parsed by _extract_note_highlights) ──
    meas_str = ""
    if measurements:
        try:
            meas_str = "meas:" + ",".join(f"{k}={v}" for k, v in measurements.items() if v)
        except Exception:
            meas_str = ""

    note_parts = [customer_name, garment_name]
    if meas_str:
        note_parts.append(meas_str)
    if notes:
        note_parts.append(f"[NOTE] {notes}")
    if coupon_code and coupon_discount > 0:
        note_parts.append(f"coupon:{coupon_code}(-Rs.{int(coupon_discount)})")
    if delivery == "delivery":
        note_parts.append("delivery:home")

    # gift-for from session gifting flow
    gift_for = (d.get("gift_for") or "").strip()
    if gift_for:
        note_parts.append(f"gift-for:{gift_for}")

    note = " | ".join(note_parts)

    # ── Generate order code ──────────────────────────────────────────────────
    try:
        order_code = _next_code()
    except Exception:
        import random
        order_code = str(int(datetime.now().strftime("%H%M%S")) + random.randint(1000, 9999))

    # ── Link web account if logged in ────────────────────────────────────────
    web_account_id = session.get("web_account_id")

    # ── Insert order ─────────────────────────────────────────────────────────
    try:
        cur = db.execute(
            """INSERT INTO orders
               (order_code, customer_id, order_date, delivery_date,
                total_amount, extra_charges, payable_amount,
                advance_paid, remaining, payment_mode, status,
                is_urgent, note, web_account_id, created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                order_code,
                customer_id,
                today,
                delivery_date or "",
                base_amount,
                extra_charges,
                payable_amount,
                0.0,           # advance_paid (paid later at counter / Razorpay)
                payable_amount, # remaining = full amount until advance collected
                "online",
                "pending",
                1 if urgent else 0,
                note,
                web_account_id,
                now,
            )
        )
        order_id = cur.lastrowid

        # ── Insert garment into order_items ──────────────────────────────────
        db.execute(
            """INSERT INTO order_items
               (order_id, garment_type, quantity, rate, amount, notes)
               VALUES(?,?,?,?,?,?)""",
            (
                order_id,
                garment_name,
                quantity,
                garment_price,
                base_amount,
                notes,
            )
        )

        # ── Increment coupon usage ────────────────────────────────────────────
        if coupon_row and coupon_discount > 0:
            try:
                db.execute(
                    "UPDATE web_coupons SET used_count = used_count + 1 WHERE code=?",
                    (coupon_code,)
                )
            except Exception:
                pass

        db.commit()

    except Exception as e:
        db.rollback()
        return jsonify({"ok": False, "error": f"DB error: {e}"}), 500

    # ── Send order confirmation SMS ──────────────────────────────────────────
    try:
        from app.utils.sms import send_order_sms as _order_sms
        _order_sms(
            mobile          = customer_phone,
            order_code      = order_code,
            customer_name   = customer_name,
            garment         = garment_name,
            total           = payable_amount,
            advance         = 0.0,
            delivery_date   = delivery_date,
            is_home_delivery= (delivery == "delivery"),
        )
    except Exception:
        pass  # SMS failure never blocks order confirmation

    # ── Send order confirmation email ─────────────────────────────────────────
    try:
        _cust_email = (d.get("customer_email") or "").strip()
        if not _cust_email and web_account_id:
            _acc_row = db.execute(
                "SELECT email FROM web_accounts WHERE id=? LIMIT 1", (web_account_id,)
            ).fetchone()
            if _acc_row:
                _cust_email = (_acc_row["email"] or "").strip()
        if _cust_email:
            from app.utils.email_notify import send_order_email as _oemail
            _oemail(
                to=_cust_email, order_code=order_code,
                customer_name=customer_name, garment=garment_name,
                total=payable_amount, advance=0.0,
                delivery_date=delivery_date,
                is_home_delivery=(delivery == "delivery"),
            )
    except Exception:
        pass

    # ── Send FCM push notification ────────────────────────────────────────────
    try:
        if web_account_id:
            from app.utils.fcm import push_order_placed as _fcm_order
            _fcm_order(web_account_id, order_code, garment_name)
    except Exception:
        pass

    return jsonify({
        "ok": True,
        "success": True,
        "order_id": order_id,
        "order_code": order_code,
        "payable_amount": payable_amount,
        "coupon_discount": coupon_discount,
        "message": "Order placed successfully",
    })


# ── FCM token registration ────────────────────────────────────────────────────

@features_bp.route("/api/register-fcm-token", methods=["POST"])
def register_fcm_token():
    """Save FCM push token for the logged-in account."""
    d = request.get_json(silent=True) or {}
    token = (d.get("token") or "").strip()
    if not token:
        return jsonify({"ok": False, "error": "Token required"})
    acc = _get_account()
    if session.get("owner_logged_in"):
        account_id = 0  # owner devices
    else:
        account_id = acc["id"] if acc else None
    try:
        from app.utils.fcm import save_token as _save_tok
        _save_tok(account_id, token)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


# ── Firebase service worker route ─────────────────────────────────────────────

@features_bp.route("/firebase-messaging-sw.js")
def firebase_sw():
    """Serve FCM service worker from static folder (must be at root path)."""
    from flask import send_from_directory
    return send_from_directory(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../static"),
        "firebase-messaging-sw.js",
        mimetype="application/javascript",
    )


@features_bp.route("/api/fcm-web-config")
def fcm_web_config():
    """Return Firebase web config + VAPID key for frontend SDK init."""
    try:
        db = get_db()
        wc_row = db.execute(
            "SELECT value FROM settings WHERE key='fcm_web_config' LIMIT 1"
        ).fetchone()
        vk_row = db.execute(
            "SELECT value FROM settings WHERE key='fcm_vapid_key' LIMIT 1"
        ).fetchone()
        wc = (wc_row["value"] if wc_row and wc_row["value"] else "").strip()
        vk = (vk_row["value"] if vk_row and vk_row["value"] else "").strip()
        import json as _json
        from app.utils.fcm import _DEFAULT_WEB_CONFIG, _DEFAULT_VAPID_KEY
        config = _json.loads(wc) if wc else _DEFAULT_WEB_CONFIG
        vapid  = vk or _DEFAULT_VAPID_KEY or None
        return jsonify({"config": config, "vapidKey": vapid})
    except Exception:
        return jsonify({"config": None, "vapidKey": None})


# ═══════════════════════════════════════════════════════════════════════════════
# WISHLIST ADD / REMOVE by item_id  (called by base.html toggleWishlist JS)
# base.html posts to /api/account/wishlist/<id> (add) and /api/account/wishlist/<id>/delete (remove)
# ═══════════════════════════════════════════════════════════════════════════════

@features_bp.route("/api/account/wishlist/<int:item_id>", methods=["POST"])
def account_wishlist_add(item_id):
    """Add item to wishlist — called by base.html JS with empty body."""
    acc = _get_account()
    if not acc:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    _ensure_wishlist_table()
    db = get_db()
    # Look up item details
    item = db.execute(
        "SELECT name, price, thumbnail_url FROM web_service_items WHERE id=?", (item_id,)
    ).fetchone()
    item_name  = item["name"]  if item else ""
    item_price = float(item["price"]) if item else 0.0
    item_img   = item["thumbnail_url"] if item else ""
    existing = db.execute(
        "SELECT id FROM web_wishlist WHERE account_id=? AND item_id=?",
        (acc["id"], item_id)
    ).fetchone()
    if not existing:
        try:
            db.execute(
                """INSERT INTO web_wishlist(account_id, item_id, item_name, item_price, item_img)
                   VALUES(?,?,?,?,?)""",
                (acc["id"], item_id, item_name, item_price, item_img)
            )
            db.commit()
        except Exception:
            pass  # already exists
        return jsonify({"ok": True})


@features_bp.route("/api/account/wishlist/<int:item_id>/delete", methods=["POST"])
def account_wishlist_remove(item_id):
    """Remove item from wishlist."""
    acc = _get_account()
    if not acc:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    _ensure_wishlist_table()
    db = get_db()
    db.execute(
        "DELETE FROM web_wishlist WHERE account_id=? AND item_id=?",
        (acc["id"], item_id)
    )
    db.commit()
    return jsonify({"ok": True})
# ── Razorpay Payment Routes ──────────────────────────────────────────────────

@features_bp.route("/api/payment/razorpay/create-order", methods=["POST"])
def razorpay_create_order():
    """Step 1: Create a Razorpay order for advance payment."""
    import os as _os, hmac as _hmac, hashlib as _hl
    try:
        import razorpay as _rzp
    except ImportError:
        return jsonify({"ok": False, "error": "Razorpay package not installed on server"}), 500

    d = request.get_json(force=True, silent=True) or {}
    order_id     = d.get("order_id")
    amount_rs    = float(d.get("amount", 0))
    order_code   = str(d.get("order_code", ""))

    if not order_id or amount_rs < 1:
        return jsonify({"ok": False, "error": "Invalid order details"})

    key_id     = _os.environ.get("RAZORPAY_KEY_ID", "")
    key_secret = _os.environ.get("RAZORPAY_KEY_SECRET", "")
    if not key_id or not key_secret:
        return jsonify({"ok": False, "error": "Payment gateway not configured on server"}), 500

    try:
        client   = _rzp.Client(auth=(key_id, key_secret))
        rz_order = client.order.create({
            "amount":   int(amount_rs * 100),  # paise
            "currency": "INR",
            "receipt":  f"ut_{order_code}",
            "notes":    {"order_id": str(order_id), "order_code": order_code}
        })
        return jsonify({
            "ok":               True,
            "razorpay_order_id": rz_order["id"],
            "amount_paise":     int(amount_rs * 100),
            "key_id":           key_id,
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@features_bp.route("/api/payment/razorpay/verify", methods=["POST"])
def razorpay_verify_payment():
    """Step 2: Verify Razorpay signature + update order advance in DB."""
    import os as _os, hmac as _hmac, hashlib as _hl
    d = request.get_json(force=True, silent=True) or {}

    rz_order_id   = d.get("razorpay_order_id", "")
    rz_payment_id = d.get("razorpay_payment_id", "")
    rz_signature  = d.get("razorpay_signature", "")
    order_id      = d.get("order_id")
    order_code    = d.get("order_code", "")
    advance_rs    = float(d.get("advance_amount", 0))

    key_secret = _os.environ.get("RAZORPAY_KEY_SECRET", "")
    if not key_secret:
        return jsonify({"ok": False, "error": "Payment gateway not configured"}), 500

    # Verify HMAC-SHA256 signature
    try:
        msg          = f"{rz_order_id}|{rz_payment_id}"
        expected_sig = _hmac.new(
            key_secret.encode("utf-8"),
            msg.encode("utf-8"),
            _hl.sha256
        ).hexdigest()
        if expected_sig != rz_signature:
            return jsonify({"ok": False, "error": "Payment verification failed — signature mismatch"}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": f"Signature error: {e}"}), 500

    # Update order in DB — record advance paid
    try:
        db = get_db()
        db.execute(
            """UPDATE orders
               SET advance_paid  = ?,
                   remaining     = MAX(0, payable_amount - ?),
                   payment_mode  = 'razorpay',
                   note          = note || ' | rpay:' || ?
               WHERE id = ?""",
            (advance_rs, advance_rs, rz_payment_id, order_id)
        )
        db.commit()
    except Exception as e:
        return jsonify({"ok": False, "error": f"DB error: {e}"}), 500

    return jsonify({"ok": True, "order_code": order_code, "advance_paid": advance_rs})



@features_bp.route("/api/orders/<int:order_id>/cancel", methods=["POST"])
def order_cancel(order_id):
    """Cancel (delete) an unpaid order — called when Razorpay is dismissed or payment fails."""
    try:
        db = get_db()
        db.execute("DELETE FROM order_items WHERE order_id=?", (order_id,))
        db.execute("DELETE FROM orders WHERE id=? AND advance_paid=0", (order_id,))
        db.commit()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
