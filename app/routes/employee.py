from flask import Blueprint, render_template, request, redirect, url_for, jsonify, send_from_directory
from datetime import date, datetime, timedelta
from database import get_db, get_setting, next_order_code, peek_order_code
import json, os, time
from config import Config

bp = Blueprint("employee", __name__)

def check_and_auto_ready(conn, order_code):
    """Check if all garments for an order have been fully stitched.
    If yes, auto-update status to 'ready'. Returns True if became ready."""
    order = conn.execute(
        "SELECT id, status FROM orders WHERE order_code=?", (order_code,)
    ).fetchone()
    if not order or order["status"] in ("ready", "delivered"):
        return False

    # Total required quantities per garment type
    required = {}
    for r in conn.execute(
        "SELECT garment_type, SUM(quantity) as total FROM order_items WHERE order_id=? GROUP BY garment_type",
        (order["id"],)
    ).fetchall():
        required[r["garment_type"]] = r["total"]

    if not required:
        return False

    # Total logged quantities per garment type
    logged = {}
    for r in conn.execute(
        "SELECT garment_type, SUM(qty_done) as total FROM work_logs WHERE order_code=? GROUP BY garment_type",
        (order_code,)
    ).fetchall():
        logged[r["garment_type"]] = r["total"]

    # Check if all garments are fully logged
    all_done = all(
        logged.get(gt, 0) >= qty
        for gt, qty in required.items()
    )

    if all_done:
        conn.execute(
            "UPDATE orders SET status='ready' WHERE order_code=?", (order_code,)
        )
        return True
    return False


def fmt_d(d):
    """Format YYYY-MM-DD to DD-MM-YYYY"""
    if not d: return "—"
    try:
        parts = str(d).split("-")
        if len(parts) == 3: return f"{parts[2]}-{parts[1]}-{parts[0]}"
    except: pass
    return str(d)



def _urgent_count():
    conn = get_db()
    today = date.today().isoformat()
    c = conn.execute("SELECT COUNT(*) as c FROM orders WHERE is_urgent=1 AND status!='delivered' AND delivery_date>=?",(today,)).fetchone()["c"]
    conn.close()
    return c


@bp.route("/")
def dashboard():
    conn = get_db()
    today = date.today().isoformat()
    # Today's orders = created today
    todays_orders = conn.execute("SELECT COUNT(*) as c FROM orders WHERE order_date=?",(today,)).fetchone()["c"]
    # Urgent = any pending urgent order
    urgent_today  = conn.execute("SELECT COUNT(*) as c FROM orders WHERE is_urgent=1 AND status!='delivered'",(noone,)).fetchone()["c"] if False else                     conn.execute("SELECT COUNT(*) as c FROM orders WHERE is_urgent=1 AND status!='delivered'").fetchone()["c"]
    pending_delivery = conn.execute("SELECT COUNT(*) as c FROM orders WHERE status!='delivered'").fetchone()["c"]
    total_customers  = conn.execute("SELECT COUNT(*) as c FROM customers").fetchone()["c"]
    urgent_orders = conn.execute("""
        SELECT o.id,o.order_code,o.delivery_date,o.status,o.is_urgent,
               o.remaining,c.name as customer_name,c.mobile
        FROM orders o LEFT JOIN customers c ON c.id=o.customer_id
        WHERE o.is_urgent=1 AND o.status!='delivered'
        ORDER BY o.delivery_date ASC LIMIT 10
    """).fetchall()
    conn.close()
    today_str = datetime.today().strftime("%A, %d %B %Y")
    # Build CUSTOMER rate list (what customers pay)
    garment_names = [
        "Shirt","Shirt Linen","Pant","Pant Double","Jeans","Suit 2pc","Suit 3pc",
        "Blazer","Kurta","Kurta Pajama","Pajama","Pathani","Sherwani","Safari","Waistcoat",
        "Alteration","Cutting Only"
    ]
    rate_list = []
    for n in garment_names:
        # Try customer_rate_ first, fall back to rate_
        r = get_setting("customer_rate_"+n, "") or get_setting("rate_"+n, "0")
        if r and r != "0":
            rate_list.append({"name": n, "rate": r})
    # Add any custom customer rates
    rate_list_image = get_setting("rate_list_image", "")

    def fmtd(d):
        if not d: return "—"
        p = str(d).split("-")
        return f"{p[2]}-{p[1]}-{p[0]}" if len(p)==3 else d

    urgent_list = [{
        "order_code":    o["order_code"],
        "customer_name": o["customer_name"] or "—",
        "mobile":        o["mobile"] or "",
        "delivery_date_fmt": fmtd(o["delivery_date"]),
        "remaining":     o["remaining"] or 0,
        "status":        o["status"]
    } for o in urgent_orders]

    return render_template("employee/dashboard.html", active_page="dashboard",
        urgent_count=urgent_today, show_voice=True, today_str=today_str,
        stats=dict(todays_orders=todays_orders, urgent_today=urgent_today,
                   pending_delivery=pending_delivery, total_customers=total_customers),
        urgent_orders=urgent_list,
        garment_rates={n: get_setting("customer_rate_"+n,"") or get_setting("rate_"+n,"0") for n in garment_names},
        rate_list=rate_list,
        rate_list_image=rate_list_image)


@bp.route("/new-order")
def new_order():
    order_code = peek_order_code()  # Show code without incrementing - only committed on save
    conn = get_db()
    today = date.today().isoformat()
    urgent_count = conn.execute("SELECT COUNT(*) as c FROM orders WHERE is_urgent=1 AND status!='delivered' AND delivery_date>=?",(today,)).fetchone()["c"]
    garment_rates = {
        "Shirt":        get_setting("rate_Shirt","350"),
        "Shirt Linen":  get_setting("rate_Shirt Linen","450"),
        "Pant":         get_setting("rate_Pant","450"),
        "Pant Double":  get_setting("rate_Pant Double","550"),
        "Jeans":        get_setting("rate_Jeans","550"),
        "Suit 2pc":     get_setting("rate_Suit 2pc","2800"),
        "Suit 3pc":     get_setting("rate_Suit 3pc","3500"),
        "Blazer":       get_setting("rate_Blazer","2300"),
        "Kurta":        get_setting("rate_Kurta","800"),
        "Kurta Pajama": get_setting("rate_Kurta Pajama","1000"),
        "Pajama":       get_setting("rate_Pajama","300"),
        "Pathani":      get_setting("rate_Pathani","800"),
        "Sherwani":     get_setting("rate_Sherwani","3500"),
        "Safari":       get_setting("rate_Safari","1500"),
        "Waistcoat":    get_setting("rate_Waistcoat","800"),
        "Alteration":   get_setting("rate_Alteration","100"),
        "Cutting Only": get_setting("rate_Cutting Only","100"),
    }
    # Get measurement fields per garment from DB
    meas_fields = {}
    mf_rows = conn.execute("SELECT garment_type, field_name FROM measurement_fields ORDER BY sort_order ASC").fetchall()
    for row in mf_rows:
        meas_fields.setdefault(row["garment_type"], []).append(row["field_name"])
    conn.close()

    import json as _json
    # Default chip options for each garment type (seeded if not already in DB)
    DEFAULT_CHIPS = {
        "Shirt":        "RG:रेगुलर|CF:चाइनीज़ कॉलर|HF:हाफ आस्तीन|FH:फुल आस्तीन|SL:स्लिम|PR:पार्टी|KF:कफ|NC:बिना कॉलर|DC:डबल कफ|SC:सिंगल कफ|BP:सीना पॉकेट|NP:बिना पॉकेट|SP:साइड पॉकेट|PP:पैच पॉकेट",
        "Shirt Linen":  "RG:रेगुलर|CF:चाइनीज़ कॉलर|HF:हाफ आस्तीन|FH:फुल आस्तीन|SL:स्लिम|PR:पार्टी|KF:कफ|NC:बिना कॉलर|DC:डबल कफ|SC:सिंगल कफ|BP:सीना पॉकेट|NP:बिना पॉकेट",
        "Pant":         "RS:रेगुलर|SL:स्लिम|PT:प्लेट वाला|NP:बिना प्लेट|CR:मोड़ नीचे|NC:सीधा नीचे|LP:लूप|ZP:ज़िप|BT:बटन|SK:साइड खत|TK:टक",
        "Pant Double":  "RS:रेगुलर|SL:स्लिम|PT:प्लेट वाला|NP:बिना प्लेट|CR:मोड़ नीचे|NC:सीधा नीचे|LP:लूप|ZP:ज़िप|BT:बटन",
        "Jeans":        "SL:स्लिम|RS:रेगुलर|ST:सीधा|SK:स्किनी|LW:लो वेस्ट|HW:हाई वेस्ट|DW:डार्क वॉश|LT:लाइट वॉश",
        "Suit 2pc":     "SL:स्लिम|RS:रेगुलर|2B:2 बटन|3B:3 बटन|DC:डबल ब्रेस्ट|SC:सिंगल ब्रेस्ट|NT:नॉच कॉलर|PK:पीक कॉलर|SH:शॉल कॉलर",
        "Suit 3pc":     "SL:स्लिम|RS:रेगुलर|2B:2 बटन|3B:3 बटन|DC:डबल ब्रेस्ट|SC:सिंगल ब्रेस्ट|NT:नॉच कॉलर|PK:पीक कॉलर|SH:शॉल कॉलर",
        "Blazer":       "SL:स्लिम|RS:रेगुलर|2B:2 बटन|3B:3 बटन|NT:नॉच कॉलर|PK:पीक कॉलर|SH:शॉल कॉलर|DC:डबल ब्रेस्ट|SC:सिंगल ब्रेस्ट",
        "Kurta":        "RG:रेगुलर|CF:चाइनीज़|HF:हाफ आस्तीन|PL:सादा|PR:पार्टी|EM:कढ़ाई|SP:सिंपल|NB:बिना बटन|RB:गोल बटन|LA:लेस|KR:कश्मीरी",
        "Kurta Pajama": "RG:रेगुलर|CF:चाइनीज़|HF:हाफ आस्तीन|PL:सादा|PR:पार्टी|EM:कढ़ाई|SP:सिंपल|NB:बिना बटन|RB:गोल बटन|CP:चूड़ीदार पाजामा|SC:सीधा पाजामा",
        "Pajama":       "CP:चूड़ीदार|ST:सीधा|EL:इलास्टिक|NS:नाड़ा|NK:नक्का",
        "Pathani":      "RG:रेगुलर|SL:स्लिम|CF:चाइनीज़|PL:सादा|EM:कढ़ाई|PR:पार्टी|SH:छोटा कॉलर|LN:लंबा कॉलर",
        "Sherwani":     "RG:रेगुलर|SL:स्लिम|PL:सादा|EM:कढ़ाई|PR:पार्टी|SH:शेरवानी कट|BD:ब्रोच डिज़ाइन|MN:मिरर नेक",
        "Safari":       "2P:2 पॉकेट|4P:4 पॉकेट|SL:स्लिम|RS:रेगुलर|HF:हाफ आस्तीन|FH:फुल आस्तीन",
        "Waistcoat":    "2B:2 बटन|3B:3 बटन|4B:4 बटन|SL:स्लिम|RS:रेगुलर|PL:सादा|EM:कढ़ाई|SC:सिंगल ब्रेस्ट|DC:डबल ब्रेस्ट",
        "Alteration":   "SM:स्लिम करें|WT:कमर टाइट|LT:लंबाई कम|LG:लंबाई बढ़ाएं|WD:चौड़ा करें|ZP:ज़िप लगाएं|BT:बटन लगाएं|PT:पैच लगाएं",
        "Cutting Only": "RG:रेगुलर|SL:स्लिम|CF:चाइनीज़|HF:हाफ|FH:फुल",
    }
    conn2 = get_db()
    # Seed/update defaults — always write Hindi defaults so old English ones get replaced
    for gname, val in DEFAULT_CHIPS.items():
        existing = conn2.execute("SELECT value FROM settings WHERE key=?", ("types_"+gname,)).fetchone()
        if not existing:
            conn2.execute("INSERT INTO settings (key,value) VALUES (?,?) ON CONFLICT DO NOTHING", ("types_"+gname, val))
        else:
            # Replace if value looks like old English (no Hindi chars)
            old_val = existing["value"] or ""
            has_hindi = any('\u0900' <= c <= '\u097f' for c in old_val)
            if not has_hindi:
                conn2.execute("UPDATE settings SET value=? WHERE key=?", (val, "types_"+gname))
    conn2.commit()

    # Load garment type chips (optional style selectors) from settings
    garment_types = {}
    for row in conn2.execute("SELECT key, value FROM settings WHERE key LIKE 'types_%'").fetchall():
        gname = row["key"][6:]  # strip "types_"
        pairs = []
        for t in (row["value"] or "").split("|"):
            if ":" in t:
                k, v = t.split(":", 1)
                pairs.append({"k": k.strip(), "v": v.strip()})
        if pairs:
            garment_types[gname] = pairs

    conn2.close()
    return render_template("employee/new_order.html",
        active_page="new_order", show_voice=True,
        urgent_count=urgent_count,
        order_code=order_code,
        garment_rates=garment_rates,
        garment_rates_json=json.dumps({k: float(v) for k, v in garment_rates.items()}),
        wa_number=get_setting("whatsapp_number",""),
        meas_fields_json=_json.dumps(meas_fields),
        garment_types_json=_json.dumps(garment_types)
    )


@bp.route("/upload/<order_code>", methods=["GET","POST"])
def upload_images(order_code):
    if request.method == "POST":
        import os as _os
        try:
            files = request.files.getlist("photos")
            use_cloudinary = bool(_os.environ.get("CLOUDINARY_CLOUD_NAME"))
            saved = 0
            slots = 5

            if use_cloudinary:
                import cloudinary, cloudinary.uploader
                cloudinary.config(
                    cloud_name = _os.environ.get("CLOUDINARY_CLOUD_NAME"),
                    api_key    = _os.environ.get("CLOUDINARY_API_KEY"),
                    api_secret = _os.environ.get("CLOUDINARY_API_SECRET")
                )
                conn = get_db()
                order = conn.execute("SELECT id FROM orders WHERE order_code=?", (order_code,)).fetchone()
                order_id = order["id"] if order else 0
                existing_count = conn.execute(
                    "SELECT COUNT(*) as c FROM order_images WHERE order_id=?", (order_id,)
                ).fetchone()["c"] or 0
                slots = max(0, 5 - existing_count)
                for f in files:
                    if saved >= slots: break
                    if f and f.filename:
                        result = cloudinary.uploader.upload(
                            f,
                            folder=f"uttam_tailors/{order_code}",
                            public_id=f"{order_code}_{int(time.time())}_{saved+1}",
                            overwrite=True
                        )
                        url = result.get("secure_url")
                        if url:
                            if order_id:
                                conn.execute("INSERT INTO order_images(order_id, file_path) VALUES(?,?)", (order_id, url))
                            else:
                                conn.execute("INSERT INTO order_images(order_id, file_path) VALUES(?,?)", (0, f"temp:{order_code}:{url}"))
                            saved += 1
                conn.commit()
                conn.close()
            else:
                folder = os.path.join(Config.UPLOAD_FOLDER, order_code)
                os.makedirs(folder, exist_ok=True)
                existing = [f for f in os.listdir(folder) if f.lower().endswith((".jpg",".jpeg",".png",".gif",".webp"))]
                slots = max(0, 5 - len(existing))
                for f in files:
                    if saved >= slots: break
                    if f and f.filename:
                        ext = os.path.splitext(f.filename)[1].lower() or ".jpg"
                        fname = f"{int(time.time())}_{len(existing)+saved+1}{ext}"
                        f.save(os.path.join(folder, fname))
                        saved += 1

            msg = f"Uploaded {saved} image(s). Max 5 per order." if saved else ("Max 5 images reached." if slots==0 else "No image selected.")
            return f"""<html><body style="font-family:sans-serif;padding:30px;text-align:center;">
            <h2>{"✅ Done!" if saved else "⚠️"}</h2><p>{msg}</p>
            <a href="" style="color:#6366f1;font-weight:700;">← Upload more</a></body></html>"""
        except Exception as e:
            return f"""<html><body style="font-family:sans-serif;padding:30px;text-align:center;">
            <h2>⚠️ Upload Error</h2><p>{str(e)}</p>
            <a href="" style="color:#6366f1;font-weight:700;">← Try again</a></body></html>"""
    return f"""<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<title>Upload Photos</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, sans-serif; background: #f3f4f6; min-height: 100vh; padding: 20px; }}
  .card {{ background: #fff; border-radius: 20px; padding: 24px 20px; max-width: 420px; margin: 0 auto; box-shadow: 0 4px 24px rgba(0,0,0,0.10); }}
  h2 {{ color: #111827; font-size: 19px; margin-bottom: 4px; }}
  .subtitle {{ color: #6b7280; font-size: 13px; margin-bottom: 20px; }}
  .counter {{ display: inline-block; background: #eef2ff; color: #6366f1; font-size: 13px; font-weight: 700; padding: 3px 10px; border-radius: 20px; margin-bottom: 18px; }}

  /* Preview grid */
  .preview-grid {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 20px; min-height: 0; }}
  .thumb-wrap {{ position: relative; width: 90px; height: 90px; border-radius: 12px; overflow: hidden; border: 2px solid #e5e7eb; }}
  .thumb-wrap img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
  .remove-btn {{ position: absolute; top: 4px; right: 4px; background: rgba(0,0,0,0.6); color: #fff; border: none; border-radius: 50%; width: 22px; height: 22px; font-size: 13px; line-height: 22px; text-align: center; cursor: pointer; padding: 0; }}

  /* Add more / First capture button */
  .add-btn {{ width: 90px; height: 90px; border-radius: 12px; border: 2px dashed #c7d2fe; background: #eef2ff; color: #6366f1; font-size: 32px; cursor: pointer; display: flex; align-items: center; justify-content: center; flex-direction: column; gap: 2px; }}
  .add-btn span {{ font-size: 11px; font-weight: 600; color: #6366f1; }}

  /* First-time big camera button */
  .camera-btn-big {{ display: block; width: 100%; padding: 20px; background: #eef2ff; border: 2px dashed #c7d2fe; border-radius: 16px; color: #6366f1; font-size: 16px; font-weight: 700; text-align: center; cursor: pointer; margin-bottom: 20px; }}
  .camera-btn-big .icon {{ font-size: 36px; display: block; margin-bottom: 6px; }}

  /* Upload button */
  .upload-btn {{ display: block; width: 100%; padding: 16px; background: #6366f1; color: #fff; border: none; border-radius: 14px; font-size: 17px; font-weight: 700; cursor: pointer; }}
  .upload-btn:disabled {{ background: #c7d2fe; cursor: not-allowed; }}
  .upload-btn:active {{ background: #4f46e5; }}

  input[type=file] {{ display: none; }}
  .uploading {{ text-align: center; padding: 20px; color: #6366f1; font-weight: 600; }}
</style>
</head>
<body>
<div class="card">
  <h2>📷 Order #{order_code}</h2>
  <p class="subtitle">Take photos to attach to this order</p>
  <div class="counter" id="counter">0 / 5 photos</div>

  <div id="preview-grid" class="preview-grid"></div>

  <!-- Hidden camera input (single capture each time) -->
  <input type="file" id="cam-input" accept="image/*" capture="environment">

  <!-- Big camera button shown when no photos yet -->
  <div id="big-cam-btn" class="camera-btn-big" onclick="openCamera()">
    <span class="icon">📸</span>
    Tap to take a photo
  </div>

  <!-- Upload form (hidden, used for submission) -->
  <form id="upload-form" method="POST" enctype="multipart/form-data" style="display:none;">
  </form>

  <button class="upload-btn" id="upload-btn" disabled onclick="submitPhotos()">
    Upload Photos
  </button>
</div>

<script>
var capturedFiles = [];

function openCamera() {{
  if (capturedFiles.length >= 5) return;
  document.getElementById('cam-input').value = '';
  document.getElementById('cam-input').click();
}}

document.getElementById('cam-input').addEventListener('change', function() {{
  var file = this.files[0];
  if (!file) return;
  if (capturedFiles.length >= 5) return;
  capturedFiles.push(file);
  renderPreviews();
}});

function renderPreviews() {{
  var grid = document.getElementById('preview-grid');
  var bigBtn = document.getElementById('big-cam-btn');
  var uploadBtn = document.getElementById('upload-btn');
  var counter = document.getElementById('counter');

  counter.textContent = capturedFiles.length + ' / 5 photos';
  grid.innerHTML = '';

  capturedFiles.forEach(function(file, idx) {{
    var wrap = document.createElement('div');
    wrap.className = 'thumb-wrap';
    var img = document.createElement('img');
    img.src = URL.createObjectURL(file);
    var rm = document.createElement('button');
    rm.className = 'remove-btn';
    rm.textContent = '✕';
    rm.onclick = function() {{ removePhoto(idx); }};
    wrap.appendChild(img);
    wrap.appendChild(rm);
    grid.appendChild(wrap);
  }});

  // Show + button if less than 5
  if (capturedFiles.length > 0 && capturedFiles.length < 5) {{
    var addBtn = document.createElement('div');
    addBtn.className = 'add-btn';
    addBtn.onclick = openCamera;
    addBtn.innerHTML = '+<span>Add</span>';
    grid.appendChild(addBtn);
  }}

  // Toggle big button
  bigBtn.style.display = capturedFiles.length === 0 ? 'block' : 'none';

  // Enable upload only when photos added
  uploadBtn.disabled = capturedFiles.length === 0;
}}

function removePhoto(idx) {{
  capturedFiles.splice(idx, 1);
  renderPreviews();
}}

function submitPhotos() {{
  if (capturedFiles.length === 0) return;
  var form = document.getElementById('upload-form');
  form.style.display = 'block';
  // Clear old inputs
  form.innerHTML = '';
  // Build FormData and submit via fetch
  var fd = new FormData();
  capturedFiles.forEach(function(file) {{
    fd.append('photos', file, file.name || 'photo.jpg');
  }});
  document.getElementById('upload-btn').disabled = true;
  document.getElementById('upload-btn').textContent = 'Uploading...';
  fetch('', {{ method: 'POST', body: fd }})
    .then(function(r) {{ return r.text(); }})
    .then(function(html) {{
      document.body.innerHTML = html;
    }})
    .catch(function() {{
      document.getElementById('upload-btn').disabled = false;
      document.getElementById('upload-btn').textContent = 'Upload Photos';
      alert('Upload failed, please try again.');
    }});
}}
</script>
</body></html>"""


@bp.route("/images/<order_code>")
def list_images(order_code):
    import os as _os
    srcs = []

    # Try DB first (Cloudinary URLs stored here)
    conn = get_db()
    order = conn.execute("SELECT id FROM orders WHERE order_code=?", (order_code,)).fetchone()
    if order:
        rows = conn.execute("SELECT file_path FROM order_images WHERE order_id=? ORDER BY id", (order["id"],)).fetchall()
        srcs = [r["file_path"] for r in rows if r["file_path"] and not r["file_path"].startswith("temp:")]
    # Also check temp images
    temp_rows = conn.execute("SELECT file_path FROM order_images WHERE order_id=0 AND file_path LIKE ?", (f"temp:{order_code}:%",)).fetchall()
    for r in temp_rows:
        srcs.append(r["file_path"][len(f"temp:{order_code}:"):])
    conn.close()

    # Fallback: local folder
    if not srcs:
        folder = os.path.join(Config.UPLOAD_FOLDER, order_code)
        if os.path.isdir(folder):
            files = sorted(f for f in os.listdir(folder) if f.lower().endswith((".jpg",".jpeg",".png",".gif",".webp")))
            srcs = [f"/static/order_images/{order_code}/{f}" for f in files]

    if not srcs:
        return ""
    return "".join(
        f'<img src="{src}" style="width:80px;height:80px;object-fit:cover;border-radius:8px;border:2px solid #e5e7eb;cursor:zoom-in;">' for src in srcs
    )


@bp.route("/save-order", methods=["POST"])
def save_order():
    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"status":"error","message":"No data received"}), 400
    try:
        conn = get_db()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Always get a fresh order code at save time - this is when we actually commit it
        # The peeked code from the page is discarded; we use the real next code
        order_code = next_order_code()
        customer_name   = (data.get("customer_name") or "").strip()
        mobile          = (data.get("mobile") or "").strip()
        address         = (data.get("address") or "").strip()
        existing_id     = data.get("existing_customer_id")
        order_date      = data.get("order_date") or date.today().isoformat()
        delivery_date   = data.get("delivery_date") or ""
        note            = data.get("note") or ""
        is_urgent       = 1 if data.get("is_urgent") else 0
        total_amount    = float(data.get("total_amount") or 0)
        extra_charges   = float(data.get("extra_charges") or 0)
        payable_amount  = float(data.get("payable_amount") or 0)
        advance_paid    = float(data.get("advance_paid") or 0)
        remaining       = float(data.get("remaining") or 0)
        payment_mode    = data.get("payment_mode","cash")
        items           = data.get("items") or []

        if not customer_name:
            return jsonify({"status":"error","message":"Customer name required"}), 400
        if not items:
            return jsonify({"status":"error","message":"Add at least one garment"}), 400

        # Customer
        if existing_id:
            customer_id = int(existing_id)
            conn.execute("UPDATE customers SET name=?,mobile=?,address=? WHERE id=?",
                         (customer_name, mobile, address, customer_id))
        else:
            # For new customers: block duplicate mobile numbers
            if mobile:
                dup = conn.execute("SELECT id, name FROM customers WHERE mobile=?", (mobile,)).fetchone()
                if dup:
                    conn.close()
                    return jsonify({"status":"error","message":f"Mobile {mobile} already registered under '{dup['name']}'. Use Existing Customer flow to add a new order for them."}), 400
            cur = conn.execute("INSERT INTO customers(name,mobile,address,created_at) VALUES(?,?,?,?)",
                               (customer_name, mobile, address, now))
            row = conn.execute("SELECT id FROM customers WHERE name=? AND (mobile=? OR mobile IS NULL) ORDER BY id DESC LIMIT 1", (customer_name, mobile)).fetchone()
            customer_id = row["id"] if row else None

        repeat_of = (data.get("repeat_of") or "").strip() or None

        # Order
        cur = conn.execute("""
            INSERT INTO orders(order_code,customer_id,order_date,delivery_date,total_amount,
            extra_charges,payable_amount,advance_paid,remaining,payment_mode,status,is_urgent,note,repeat_of,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,'pending',?,?,?,?)
        """,(order_code,customer_id,order_date,delivery_date,total_amount,extra_charges,
             payable_amount,advance_paid,remaining,payment_mode,is_urgent,note,repeat_of,now))
        row = conn.execute("SELECT id FROM orders WHERE order_code=?", (order_code,)).fetchone()
        order_id = row["id"] if row else None
        if not order_id:
            import time as _t; _t.sleep(0.1)
            row2 = conn.execute("SELECT id FROM orders WHERE order_code=?", (order_code,)).fetchone()
            order_id = row2["id"] if row2 else None

        # Items
        for it in items:
            meas = it.get("measurements") or {}
            raw_notes = it.get("notes","")
            sel_types = it.get("selectedTypes") or []
            # Append selected style codes to notes as [CODE1,CODE2]
            if sel_types:
                raw_notes = (raw_notes.split("[")[0].strip() + " [" + ",".join(sel_types) + "]").strip()
            conn.execute("""INSERT INTO order_items(order_id,garment_type,quantity,rate,amount,measurements,notes)
                VALUES(?,?,?,?,?,?,?)""",
                (order_id, it.get("type",""), int(it.get("qty",1)),
                 float(it.get("rate",0)), int(it.get("qty",1))*float(it.get("rate",0)),
                 json.dumps(meas), raw_notes))

        # Finance entry for advance
        if advance_paid > 0:
            conn.execute("""INSERT INTO finance(tx_date,tx_type,category,amount,mode,order_id,note,created_by,created_at)
                VALUES(?,'income','advance',?,?,?,?,'employee',?)""",
                (order_date, advance_paid, payment_mode, order_id,
                 f"Advance for order #{order_code}", now))

        # Link temp images (Cloudinary URLs stored before order existed)
        if order_id:
            temp_imgs = conn.execute(
                "SELECT id, file_path FROM order_images WHERE order_id=0 AND file_path LIKE ?",
                (f"temp:{order_code}:%",)
            ).fetchall()
            for img in temp_imgs:
                real_url = img["file_path"][len(f"temp:{order_code}:"):]
                conn.execute("UPDATE order_images SET order_id=?, file_path=? WHERE id=?",
                             (order_id, real_url, img["id"]))

        conn.commit()
        conn.close()
        return jsonify({"status":"ok","order_id":order_id,"order_code":order_code,"repeat_of":repeat_of})

    except Exception as e:
        try: conn.rollback(); conn.close()
        except: pass
        return jsonify({"status":"error","message":str(e)}), 500


@bp.route("/print-slip/<order_code>")
def print_slip(order_code):
    conn = get_db()
    o = conn.execute("""SELECT o.*,c.name as cname,c.mobile,c.address,
        COALESCE(o.repeat_of,'') as repeat_of
        FROM orders o LEFT JOIN customers c ON c.id=o.customer_id WHERE o.order_code=?""",(order_code,)).fetchone()
    items = conn.execute("SELECT * FROM order_items WHERE order_id=?",(o["id"],)).fetchall() if o else []
    conn.close()
    if not o:
        return "Order not found", 404
    def fmt_date(d):
        if not d: return "—"
        parts = d.split("-")
        return f"{parts[2]}-{parts[1]}-{parts[0]}" if len(parts)==3 else d
    items_rows = "".join(f'''
        <tr>
          <td style="padding:10px 12px;border-bottom:1px solid #f0f0f0;">
            <div style="font-weight:600;">{i["garment_type"]}</div>
            {("<div style=\'font-size:11px;color:#888;margin-top:2px;\'>" + __import__("re").sub(r"\s*\[.*?\]", "", i["notes"]).strip() + "</div>") if i["notes"] and __import__("re").sub(r"\s*\[.*?\]", "", i["notes"]).strip() else ""}
          </td>
          <td style="padding:10px 12px;text-align:center;border-bottom:1px solid #f0f0f0;">{i["quantity"]}</td>
          <td style="padding:10px 12px;text-align:right;border-bottom:1px solid #f0f0f0;">₹{i["rate"]}</td>
          <td style="padding:10px 12px;text-align:right;border-bottom:1px solid #f0f0f0;font-weight:600;">₹{i["amount"]}</td>
        </tr>''' for i in items)
    shop_name = get_setting("shop_name", "Uttam Tailors")
    shop_name_hi = get_setting("shop_name_hi", "उत्तम टेलर्स")
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Order Receipt #{order_code}</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0;}}
  body{{font-family:'Segoe UI',Arial,sans-serif;background:#fff;color:#1a1d2e;max-width:420px;margin:0 auto;padding:0;}}
  .header{{background:linear-gradient(135deg,#6366f1,#4f46e5);color:#fff;padding:28px 24px;text-align:center;}}
  .shop-name{{font-size:22px;font-weight:800;letter-spacing:-0.5px;}}
  .order-num{{font-size:32px;font-weight:900;letter-spacing:3px;margin:10px 0 4px;}}
  .header-sub{{font-size:13px;opacity:0.85;}}
  .section{{padding:16px 20px;border-bottom:1px solid #f0f0f0;}}
  .section-title{{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#9ca3af;margin-bottom:10px;}}
  .info-row{{display:flex;justify-content:space-between;margin-bottom:6px;font-size:13px;}}
  .info-label{{color:#6b7280;}}
  .info-val{{font-weight:600;}}
  table{{width:100%;border-collapse:collapse;font-size:13px;}}
  th{{background:#f9fafb;padding:10px 12px;text-align:left;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;color:#9ca3af;border-bottom:2px solid #f0f0f0;}}
  th:last-child,td:last-child{{text-align:right;}}
  th:nth-child(2),td:nth-child(2){{text-align:center;}}
  .totals{{padding:16px 20px;background:#f9fafb;}}
  .total-row{{display:flex;justify-content:space-between;padding:7px 0;font-size:14px;border-bottom:1px dashed #e5e7eb;}}
  .total-row:last-child{{border-bottom:none;font-size:16px;font-weight:800;color:#6366f1;padding-top:12px;}}
  .paid-row{{color:#059669;font-weight:700;}}
  .due-row{{color:#dc2626;font-weight:700;}}
  .footer{{padding:20px 24px;text-align:center;background:#fff;}}
  .thank-you{{font-size:15px;font-weight:700;color:#1a1d2e;margin-bottom:6px;}}
  .system-note{{font-size:10px;color:#d1d5db;margin-top:14px;line-height:1.5;}}
  .btn-print{{display:block;width:100%;padding:14px;background:#6366f1;color:#fff;border:none;border-radius:10px;font-size:15px;font-weight:700;cursor:pointer;margin-top:16px;}}
  @media print{{.btn-print{{display:none;}}body{{max-width:100%;}}}}
</style>
</head><body>
<div class="header">
  <div class="shop-name">{shop_name_hi}</div>
  <div style="font-size:13px;opacity:0.75;margin-top:2px;letter-spacing:0.5px;">{shop_name}</div>
  <div class="order-num"># {order_code}</div>
  <div class="header-sub">Order Receipt &nbsp;·&nbsp; {fmt_date(o["order_date"])}</div>
</div>

<div class="section">
  <div class="section-title">Customer Details</div>
  <div class="info-row"><span class="info-label">Name</span><span class="info-val">{o["cname"]}</span></div>
  <div class="info-row"><span class="info-label">Mobile</span><span class="info-val">{o["mobile"] or "—"}</span></div>
  <div class="info-row"><span class="info-label">Address</span><span class="info-val">{o["address"] or "—"}</span></div>
  <div class="info-row"><span class="info-label">Order Date</span><span class="info-val">{fmt_date(o["order_date"])}</span></div>
  <div class="info-row"><span class="info-label">Delivery Date</span><span class="info-val" style="color:#6366f1;font-weight:700;">{fmt_date(o["delivery_date"])}</span></div>
  {('<div class="info-row"><span class="info-label">Note</span><span class="info-val">' + o["note"] + '</span></div>') if o["note"] else ""}
</div>

<div class="section" style="padding:0;">
  <table>
    <thead><tr><th>Item</th><th>Qty</th><th>Rate</th><th>Amount</th></tr></thead>
    <tbody>{items_rows}</tbody>
  </table>
</div>

<div class="totals">
  <div class="total-row"><span>Total</span><span>₹{o["total_amount"]}</span></div>
  {('<div class="total-row"><span>Extra Charges</span><span>₹' + str(o["extra_charges"]) + '</span></div>') if o["extra_charges"] else ""}
  <div class="total-row" style="font-size:15px;font-weight:800;color:#6366f1;"><span>Net Payable</span><span>₹{o["payable_amount"]}</span></div>
  <div class="total-row paid-row"><span>✅ Advance Paid</span><span>₹{o["advance_paid"]}</span></div>
  <div class="total-row due-row"><span>⏳ Remaining Due</span><span>₹{o["remaining"]}</span></div>
</div>

<div class="footer">
  <div class="thank-you">🙏 Thank you for choosing {shop_name}!</div>
  <div style="font-size:12px;color:#6b7280;margin-top:4px;">We appreciate your trust and business.</div>

  <button class="btn-print" onclick="window.print()">🖨️ Print Receipt</button>
</div>
</body></html>"""


@bp.route("/api/customers/search")
def api_customer_search():
    q = request.args.get("q","").strip()
    if not q:
        return jsonify([])
    conn = get_db()
    like = f"%{q}%"
    # Search by order code first (if query looks like a number)
    results = []
    if q.isdigit() or q.startswith("#"):
        code = q.lstrip("#")
        order_rows = conn.execute("""
            SELECT c.id, c.name, c.mobile, c.address, o.order_code as matched_code
            FROM orders o JOIN customers c ON c.id = o.customer_id
            WHERE o.order_code = ?
            LIMIT 5
        """, (code,)).fetchall()
        for r in order_rows:
            results.append({
                "id": r["id"], "name": r["name"],
                "mobile": r["mobile"] or "", "address": r["address"] or "",
                "matched_code": r["matched_code"]
            })
    # Also search by name, mobile, address — include order_count for "old customer" badge
    rows = conn.execute("""
        SELECT c.id, c.name, c.mobile, c.address, COUNT(o.id) as order_count
        FROM customers c
        LEFT JOIN orders o ON o.customer_id = c.id
        WHERE c.name LIKE ? OR c.mobile LIKE ? OR c.address LIKE ?
        GROUP BY c.id
        ORDER BY c.name ASC LIMIT 15
    """, (like, like, like)).fetchall()
    seen_ids = {r["id"] for r in results}
    for r in rows:
        if r["id"] not in seen_ids:
            results.append({"id": r["id"], "name": r["name"],
                "mobile": r["mobile"] or "", "address": r["address"] or "",
                "matched_code": None, "order_count": r["order_count"] or 0})
            seen_ids.add(r["id"])
    # Also add order_count to the code-matched results
    for res in results:
        if "order_count" not in res:
            cnt = conn.execute("SELECT COUNT(*) as c FROM orders WHERE customer_id=?", (res["id"],)).fetchone()
            res["order_count"] = cnt["c"] if cnt else 0
    conn.close()
    return jsonify(results[:15])





@bp.route("/api/customers/<int:customer_id>")
def api_customer_detail(customer_id):
    """Return customer profile + all past orders with items & measurements."""
    conn = get_db()
    cust = conn.execute("SELECT * FROM customers WHERE id=?", (customer_id,)).fetchone()
    if not cust:
        conn.close()
        return jsonify({"error": "not found"}), 404

    orders = conn.execute("""
        SELECT o.id, o.order_code, o.order_date, o.delivery_date, o.status,
               o.payable_amount, o.advance_paid, o.remaining, o.note,
               COALESCE(o.repeat_of, '') as repeat_of
        FROM orders o WHERE o.customer_id=?
        ORDER BY o.id DESC
    """, (customer_id,)).fetchall()

    order_list = []
    for o in orders:
        items = conn.execute(
            "SELECT * FROM order_items WHERE order_id=?", (o["id"],)
        ).fetchall()
        import json as _json
        item_list = []
        for it in items:
            try:
                meas = _json.loads(it["measurements"] or "{}")
            except:
                meas = {}
            item_list.append({
                "id":           it["id"],
                "garment_type": it["garment_type"],
                "quantity":     it["quantity"],
                "rate":         it["rate"],
                "measurements": meas,
                "notes":        it["notes"] or ""
            })
        order_list.append({
            "id":            o["id"],
            "order_code":    o["order_code"],
            "order_date":    o["order_date"],
            "delivery_date": o["delivery_date"],
            "status":        o["status"],
            "payable_amount":o["payable_amount"],
            "advance_paid":  o["advance_paid"],
            "remaining":     o["remaining"],
            "note":          o["note"] or "",
            "repeat_of":     o["repeat_of"] or "",
            "items":         item_list
        })

    conn.close()
    return jsonify({
        "id":       cust["id"],
        "name":     cust["name"],
        "mobile":   cust["mobile"] or "",
        "address":  cust["address"] or "",
        "orders":   order_list
    })


@bp.route("/api/customers/<int:customer_id>/measurements")
def api_customer_measurements(customer_id):
    """Return the most recent measurements for each garment type for this customer."""
    conn = get_db()
    import json as _json
    # Get latest order items for each garment type
    rows = conn.execute("""
        SELECT oi.garment_type, oi.measurements, o.order_date, o.order_code
        FROM order_items oi
        JOIN orders o ON o.id = oi.order_id
        WHERE o.customer_id = ?
        ORDER BY o.id DESC
    """, (customer_id,)).fetchall()
    conn.close()

    # Keep only the most recent measurement per garment type
    seen = {}
    for r in rows:
        gt = r["garment_type"]
        if gt not in seen:
            try:
                meas = _json.loads(r["measurements"] or "{}")
            except:
                meas = {}
            seen[gt] = {
                "garment_type": gt,
                "measurements": meas,
                "order_code":   r["order_code"],
                "order_date":   r["order_date"]
            }
    return jsonify(list(seen.values()))


@bp.route("/api/settings/shop_name")
def api_shop_name():
    return jsonify({"value": get_setting("shop_name","Uttam Tailors")})



# ══════════════════════════════════════════════
#  ORDER STATUS MODULE
# ══════════════════════════════════════════════

@bp.route("/order-status")
def order_status():
    conn = get_db()
    today = date.today().isoformat()
    now_dt = datetime.now()

    # Single fast query - no correlated subqueries
    raw = conn.execute("""
        SELECT o.id, o.order_code, o.status, o.is_urgent, o.note,
               o.order_date, o.delivery_date, o.delivered_at, o.repeat_of,
               o.payable_amount, o.advance_paid, o.remaining, o.customer_id,
               c.name as cname, c.mobile
        FROM orders o
        LEFT JOIN customers c ON c.id = o.customer_id
        ORDER BY
          o.is_urgent DESC,
          CASE o.status WHEN 'pending' THEN 0 WHEN 'ready' THEN 1 ELSE 2 END,
          o.id DESC
    """).fetchall()

    # Customer order counts in one query
    cust_counts = {}
    for row in conn.execute("SELECT customer_id, COUNT(*) as cnt FROM orders GROUP BY customer_id").fetchall():
        cust_counts[row["customer_id"]] = row["cnt"]

    # Bulk load ALL order items at once
    all_items = conn.execute("SELECT id, order_id, garment_type, quantity, rate, amount, measurements, notes FROM order_items").fetchall()
    items_by_order = {}
    for it in all_items:
        items_by_order.setdefault(it["order_id"], []).append(it)

    # Bulk load ALL work logs at once
    all_wl = conn.execute("SELECT order_code, qty_done, notes FROM work_logs").fetchall()
    wl_by_code = {}
    for wl in all_wl:
        wl_by_code.setdefault(wl["order_code"], []).append(wl)

    orders = []
    for o in raw:
        items_raw = items_by_order.get(o["id"], [])
        wl_rows = wl_by_code.get(o["order_code"], [])
        naap_total = kataai_total = silai_total = 0
        for wl in wl_rows:
            n = (wl["notes"] or "").strip()
            q = wl["qty_done"] or 0
            if any(x in n for x in ["Measurement","Naap","नाप"]):
                naap_total += q
            elif any(x in n for x in ["Kataai","Cutting","कटाई"]):
                kataai_total += q
            else:
                silai_total += q

        # Total garment quantity for this order
        total_order_qty = sum(it["quantity"] for it in items_raw) or 1

        # Only parse measurements for non-delivered orders (saves time)
        is_delivered = o["status"] == "delivered"
        items = []
        for it in items_raw:
            qty = it["quantity"] or 1
            gt  = it["garment_type"]
            share = qty / total_order_qty
            naap_done   = min(qty, int(naap_total   * share + 0.999))
            cut_done    = min(qty, int(kataai_total  * share + 0.999))
            stitch_done = min(qty, int(silai_total   * share + 0.999))
            pct = min(100, int((stitch_done / qty) * 100)) if qty else 0
            if not is_delivered:
                try: meas = json.loads(it["measurements"] or "{}")
                except: meas = {}
            else:
                meas = {}  # Skip JSON parse for delivered orders
            items.append({
                "garment_type":  gt,
                "quantity":      qty,
                "rate":          it["rate"],
                "amount":        it["amount"],
                "measurements":  meas,
                "notes":         it["notes"] or "",
                "logged":        stitch_done,
                "progress_pct":  pct,
                "naap_done":     naap_done,
                "cut_done":      cut_done,
                "stitch_done":   stitch_done,
                "naap_pct":      min(100, int((naap_done/qty)*100))   if qty else 0,
                "cut_pct":       min(100, int((cut_done/qty)*100))    if qty else 0,
                "stitch_pct":    pct,
            })

        def fmtd(d):
            if not d: return "—"
            p = str(d).split("-")
            return f"{p[2]}-{p[1]}-{p[0]}" if len(p)==3 else d

        try:
            dl = datetime.strptime(o["delivery_date"], "%Y-%m-%d").date() if o["delivery_date"] else None
            overdue  = dl and dl < date.today() and o["status"] != "delivered"
            days_left = (dl - date.today()).days if dl else 999
            due_soon = dl and not overdue and days_left <= 5 and o["status"] != "delivered"
        except:
            overdue = due_soon = False

        orders.append({
            "order_code":       o["order_code"],
            "cname":            o["cname"] or "—",
            "mobile":           o["mobile"] or "",
            "status":           o["status"],
            "is_urgent":        o["is_urgent"],
            "repeat_of":        o["repeat_of"],
            "delivery_date":    o["delivery_date"] or "",
            "delivery_date_fmt":fmtd(o["delivery_date"]),
            "order_date_fmt":   fmtd(o["order_date"]),
            "payable_amount":   o["payable_amount"] or 0,
            "advance_paid":     o["advance_paid"] or 0,
            "remaining":        o["remaining"] or 0,
            "note":             o["note"] or "",
            "overdue":          overdue,
            "due_soon":         due_soon,
            "days_left":        days_left if (dl and not overdue) else 999,
            "delivered_at":     (o["delivered_at"] if "delivered_at" in o.keys() else "") or "",
            "delivered_at_fmt": fmtd(((o["delivered_at"] if "delivered_at" in o.keys() else "") or "")[:10]),
            "garments":         items,
            "customer_order_count": cust_counts.get(o["customer_id"], 1)
        })

    # Images not loaded on order status page (for speed)

    counts = {
        "total":     len(orders),
        "late":      sum(1 for o in orders if o["overdue"] and o["status"]!="delivered"),
        "upcoming":  sum(1 for o in orders if o["due_soon"] and not o["overdue"] and o["status"]!="delivered"),
        "ready":     sum(1 for o in orders if o["status"]=="ready"),
        "delivered": sum(1 for o in orders if o["status"]=="delivered"),
        "cancelled": sum(1 for o in orders if o["status"]=="cancelled"),
        "urgent":    sum(1 for o in orders if o["is_urgent"] and o["status"]!="delivered"),
    }
    conn.close()
    HINDI_MAP = {
        "Lambai":"लंबाई","Seeno":"सीना","Kamar":"कमर","Shoulder":"कंधा",
        "Collar":"कॉलर","Aastin":"आस्तीन","Cough":"कफ",
        "Part 1":"पाट 1","Part 2":"पाट 2","Part 3":"पाट 3",
        "Seat":"सीट","Mori":"मोरी","Jangh":"जांघ","Goda":"घुटना",
        "Langot":"लंगोट","Back Paat":"बैक पाट",
        "Hip":"हिप","Details":"विवरण",
    }
    return render_template("employee/order_status.html",
        active_page="order_status", show_voice=True,
        urgent_count=counts["urgent"], orders=orders,
        total=counts["total"], late_count=counts["late"],
        upcoming_count=counts["upcoming"],
        ready_count=counts["ready"], delivered_count=counts["delivered"],
        cancelled_count=counts["cancelled"],
        hindi_map=HINDI_MAP)


@bp.route("/api/order/update-status", methods=["POST"])
def api_update_status():
    data = request.get_json(silent=True) or {}
    code       = data.get("order_code","")
    new_status = data.get("status","")
    if new_status not in ("pending","ready","delivered"):
        return jsonify({"ok": False, "error": "Invalid status"})
    conn = get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if new_status == "delivered":
        conn.execute("UPDATE orders SET status=?, delivered_at=? WHERE order_code=?",
                     (new_status, now, code))
    else:
        conn.execute("UPDATE orders SET status=? WHERE order_code=?", (new_status, code))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@bp.route("/api/order/collect-payment", methods=["POST"])
def api_collect_payment():
    data     = request.get_json(silent=True) or {}
    code     = data.get("order_code","")
    amount   = float(data.get("amount", 0))
    mode     = data.get("mode","cash")
    discount = data.get("discount", False)  # True = waive remaining balance
    if amount < 0:
        return jsonify({"ok": False, "error": "Invalid amount"})
    conn = get_db()
    order = conn.execute(
        "SELECT id, remaining, advance_paid, payable_amount FROM orders WHERE order_code=?", (code,)
    ).fetchone()
    if not order:
        conn.close()
        return jsonify({"ok": False, "error": "Order not found"})
    today = date.today().isoformat()
    now   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if discount:
        # Customer paid less — waive the remaining balance, mark as complete
        waived = round(order["remaining"] - amount, 2)
        new_adv = round(order["advance_paid"] + amount, 2)
        note = f"Collected ₹{int(amount)} for order #{code}. Discount/waived ₹{int(waived)}."
        conn.execute("UPDATE orders SET remaining=0, advance_paid=? WHERE order_code=?",
                     (new_adv, code))
        if amount > 0:
            conn.execute("""INSERT INTO finance(tx_date,tx_type,category,amount,mode,order_id,note,created_by,created_at)
                VALUES(?,'income','payment',?,?,?,?,'employee',?)""",
                (today, amount, mode, order["id"], note, now))
        if waived > 0:
            conn.execute("""INSERT INTO finance(tx_date,tx_type,category,amount,mode,order_id,note,created_by,created_at)
                VALUES(?,'expense','discount',?,?,?,?,'employee',?)""",
                (today, waived, mode, order["id"], f"Discount given on order #{code}", now))
        conn.execute("UPDATE orders SET status='delivered', delivered_at=? WHERE order_code=? AND status='ready'",
                     (now, code))
        new_rem = 0
    else:
        # Normal payment
        if amount <= 0:
            conn.close()
            return jsonify({"ok": False, "error": "Invalid amount"})
        new_rem = max(0, round(order["remaining"] - amount, 2))
        new_adv = round(order["advance_paid"] + amount, 2)
        conn.execute("UPDATE orders SET remaining=?, advance_paid=? WHERE order_code=?",
                     (new_rem, new_adv, code))
        conn.execute("""INSERT INTO finance(tx_date,tx_type,category,amount,mode,order_id,note,created_by,created_at)
            VALUES(?,'income','payment',?,?,?,?,'employee',?)""",
            (today, amount, mode, order["id"], f"Balance collected for order #{code}", now))
        if new_rem == 0:
            conn.execute("UPDATE orders SET status='delivered', delivered_at=? WHERE order_code=? AND status='ready'",
                         (now, code))

    conn.commit()
    conn.close()
    return jsonify({"ok": True, "remaining": new_rem})



# ══════════════════════════════════════════════
#  WORK LOG MODULE
# ══════════════════════════════════════════════


@bp.route("/gallery")
def gallery():
    conn = get_db()
    urgent_count = conn.execute("SELECT COUNT(*) as c FROM orders WHERE is_urgent=1 AND status!='delivered'").fetchone()["c"]
    conn.close()
    return render_template("employee/gallery.html",
        active_page="gallery", show_voice=False, urgent_count=urgent_count)

@bp.route("/work-log")
def work_log():
    conn = get_db()
    today = date.today().isoformat()
    # Ensure skills column exists (for existing databases) - skip for PostgreSQL
    # Skip ALTER TABLE for PostgreSQL - columns already created in init_db
    import os as _os
    if not _os.environ.get("DATABASE_URL"):
        try:
            conn.execute("ALTER TABLE employees ADD COLUMN skills TEXT DEFAULT 'stitch'")
            conn.commit()
        except Exception:
            try: conn.execute("ROLLBACK")
            except: pass
        try:
            conn.execute("ALTER TABLE employees ADD COLUMN hindi_name TEXT")
            conn.commit()
        except Exception:
            try: conn.execute("ROLLBACK")
            except: pass
    # Set default skills and Hindi names
    hindi_map = {"Kamal":"कमल","Bhagwan":"भगवान","Sawarmal":"सावरमल","Mahesh":"महेश","Manak Tau":"मानक ताऊ"}
    conn.execute("UPDATE employees SET skills='all' WHERE name='Kamal' AND (skills IS NULL OR skills='stitch')")
    for eng, hin in hindi_map.items():
        conn.execute("UPDATE employees SET hindi_name=? WHERE name=? AND (hindi_name IS NULL OR hindi_name='')", (hin, eng))
    conn.commit()
    # Load all active employees
    employees = conn.execute(
        "SELECT id, name, COALESCE(hindi_name,'') as hindi_name, phone, COALESCE(skills,'stitch') as skills FROM employees WHERE active=1 ORDER BY name"
    ).fetchall()
    urgent_count = conn.execute(
        "SELECT COUNT(*) as c FROM orders WHERE is_urgent=1 AND status!='delivered'"
    ).fetchone()["c"]
    conn.close()
    work_rates = {
        "measure":   get_setting("work_rate_measurement", "0"),
        "cutting":   get_setting("work_rate_cutting", "25"),
        "alteration":get_setting("work_rate_alteration", "15"),
    }
    return render_template("employee/work_log.html",
        active_page="work_log", show_voice=True,
        urgent_count=urgent_count, employees=employees,
        work_rates=work_rates)


@bp.route("/api/work-log/employee-stats")
def api_employee_stats():
    emp_id  = request.args.get("emp_id","")
    period  = request.args.get("period","week")
    conn    = get_db()

    # Get employee name
    emp = conn.execute("SELECT name FROM employees WHERE id=?", (emp_id,)).fetchone()
    if not emp:
        conn.close()
        return jsonify({"error":"Employee not found"})

    today = date.today()
    if period == "week":
        # Monday of current week
        start = (today - timedelta(days=today.weekday())).isoformat()
        period_label = f"{start[8:]}-{start[5:7]}-{start[:4]} to {today.day:02d}-{today.month:02d}-{today.year}"
    else:
        start = today.replace(day=1).isoformat()
        period_label = f"{today.strftime('%B %Y')}"

    logs = conn.execute("""
        SELECT wl.*, o.order_code
        FROM work_logs wl
        LEFT JOIN orders o ON o.id = wl.order_id
        WHERE wl.employee_name = ? AND wl.log_date >= ?
        ORDER BY wl.log_date DESC, wl.id DESC
    """, (emp["name"], start)).fetchall()
    conn.close()

    # Aggregate
    total_pieces   = sum(r["qty_done"] for r in logs)
    total_orders   = len(set(r["order_code"] for r in logs if r["order_code"]))
    total_earnings = sum((r["qty_done"] or 0) * (r["making_rate"] or 0) for r in logs)

    # Group by date
    from collections import defaultdict
    by_date = defaultdict(list)
    for r in logs:
        by_date[r["log_date"]].append(r)

    def fmtd(d):
        if not d: return "—"
        p = str(d).split("-")
        return f"{p[2]}-{p[1]}-{p[0]}" if len(p)==3 else d

    daily = []
    for log_date in sorted(by_date.keys(), reverse=True):
        entries = by_date[log_date]
        day_qty      = sum(e["qty_done"] for e in entries)
        day_earnings = sum((e["qty_done"] or 0) * (e["making_rate"] or 0) for e in entries)
        daily.append({
            "date_fmt":     fmtd(log_date),
            "total_qty":    day_qty,
            "day_earnings": int(day_earnings),
            "entries": [{
                "order_code":  e["order_code"] or "—",
                "garment_type":e["garment_type"],
                "qty_done":    e["qty_done"],
                "notes":       e["notes"] or "",
                "earnings":    int((e["qty_done"] or 0) * (e["making_rate"] or 0)),
                "time":        (e["created_at"] or "")[ 11:16 ]
            } for e in entries]
        })

    return jsonify({
        "total_pieces":   total_pieces,
        "total_orders":   total_orders,
        "total_earnings": int(total_earnings),
        "period_label":   period_label,
        "daily":          daily
    })


@bp.route("/api/work-log/order-info")
def api_worklog_order_info():
    code = request.args.get("code","").strip().lstrip("#")
    conn = get_db()
    order = conn.execute("""
        SELECT o.*, c.name as cname, c.mobile
        FROM orders o LEFT JOIN customers c ON c.id=o.customer_id
        WHERE o.order_code=?
    """, (code,)).fetchone()
    if not order:
        conn.close()
        return jsonify({"error":"not found"})

    items_raw = conn.execute(
        "SELECT garment_type, quantity, rate FROM order_items WHERE order_id=?",
        (order["id"],)
    ).fetchall()

    # Build per-garment naap/kataai/silai maps (handles both old and new format)
    wl_all = conn.execute(
        "SELECT garment_type, qty_done, notes FROM work_logs WHERE order_code=?", (code,)
    ).fetchall()
    actual_garments_in_order = [it["garment_type"] for it in items_raw]
    naap_map   = {}
    kataai_map = {}
    silai_map  = {}
    for wl in wl_all:
        gt_wl = wl["garment_type"]
        n     = (wl["notes"] or "").strip()
        q     = wl["qty_done"] or 0
        is_naap   = any(x in n for x in ["Measurement","Naap","नाप"])
        is_kataai = any(x in n for x in ["Kataai","Cutting","कटाई"])
        is_old    = "Order #" in gt_wl
        if is_naap:
            if is_old:
                for ag in actual_garments_in_order:
                    naap_map[ag] = naap_map.get(ag, 0) + q
            else:
                naap_map[gt_wl] = naap_map.get(gt_wl, 0) + q
        elif is_kataai:
            if is_old:
                for ag in actual_garments_in_order:
                    kataai_map[ag] = kataai_map.get(ag, 0) + q
            else:
                kataai_map[gt_wl] = kataai_map.get(gt_wl, 0) + q
        else:
            silai_map[gt_wl] = silai_map.get(gt_wl, 0) + q

    def fmtd(d):
        if not d: return "—"
        p = str(d).split("-")
        return f"{p[2]}-{p[1]}-{p[0]}" if len(p)==3 else d

    items = [{
        "garment_type":  it["garment_type"],
        "required":      it["quantity"],
        "rate":          it["rate"],
        "logged":        silai_map.get(it["garment_type"], 0),
        "naap_done":     min(naap_map.get(it["garment_type"], 0),   it["quantity"]),
        "cut_done":      min(kataai_map.get(it["garment_type"], 0), it["quantity"]),
        "stitch_done":   min(silai_map.get(it["garment_type"], 0),  it["quantity"]),
    } for it in items_raw]

    conn.close()
    return jsonify({
        "order_code":       code,
        "customer_name":    order["cname"] or "—",
        "mobile":           order["mobile"] or "",
        "status":           order["status"],
        "is_urgent":        order["is_urgent"],
        "delivery_date_fmt":fmtd(order["delivery_date"]),
        "remaining":        order["remaining"] or 0,
        "items":            items
    })


@bp.route("/api/work-log/add", methods=["POST"])
def api_worklog_add():
    data      = request.get_json(silent=True) or {}
    code      = data.get("order_code","").strip().lstrip("#")
    gt        = data.get("garment_type","").strip()
    qty       = int(data.get("qty_done", 0))
    emp_name  = data.get("employee_name","").strip()
    notes     = data.get("notes","").strip()

    is_non_stitch = data.get("is_non_stitch", False)

    if not code or qty < 1:
        return jsonify({"ok": False, "error": "Missing required fields"})
    if not is_non_stitch and not gt:
        return jsonify({"ok": False, "error": "Missing garment type"})

    conn = get_db()
    order = conn.execute(
        "SELECT id, status FROM orders WHERE order_code=?", (code,)
    ).fetchone()
    if not order:
        conn.close()
        return jsonify({"ok": False, "error": f"Order #{code} not found"})

    rate_override = data.get("rate_override")

    if is_non_stitch:
        # Determine work type: Naap or Kataai
        work_type = notes.strip()  # e.g. "Measurement" or "Cutting" or "Kataai — Shirt"
        is_naap   = any(x in work_type for x in ["Measurement","Naap","नाप"])
        is_kataai = any(x in work_type for x in ["Cutting","Kataai","कटाई"])

        # garment_type: use gt if provided, else extract from notes or fall back to notes
        garment = gt if gt else notes

        # If a specific garment is given, check per-garment quantity cap & duplicate
        if gt:
            item = conn.execute(
                "SELECT quantity FROM order_items WHERE order_id=? AND garment_type=?",
                (order["id"], gt)
            ).fetchone()
            if not item:
                conn.close()
                return jsonify({"ok": False, "error": f"{gt} not found in order #{code}."})
            max_qty = item["quantity"]
            if qty > max_qty:
                conn.close()
                return jsonify({"ok": False, "error": f"Quantity {qty} exceeds garment quantity ({max_qty}) in order #{code}."})

            # Duplicate check - check by garment (new format) + order total (old format)
            if is_naap:
                # Check per garment (new format entries where garment_type=gt)
                already_gt = conn.execute(
                    "SELECT COALESCE(SUM(qty_done),0) as t FROM work_logs WHERE order_code=? AND garment_type=? AND (notes LIKE 'Naap%' OR notes LIKE 'Measurement%')",
                    (code, gt)
                ).fetchone()["t"] or 0
                # Check old format (garment_type contains "Measurement" - order-level entry)
                already_old = conn.execute(
                    "SELECT COALESCE(SUM(qty_done),0) as t FROM work_logs WHERE order_code=? AND garment_type LIKE 'Measurement%' AND (notes LIKE 'Measurement%' OR notes LIKE 'Naap%')",
                    (code,)
                ).fetchone()["t"] or 0
                already = already_gt + already_old
                if already >= max_qty:
                    conn.close()
                    return jsonify({"ok": False, "error": f"नाप पहले से हो गई है {gt} के लिए ऑर्डर #{code} में। ({already}/{max_qty})"})
            elif is_kataai:
                already_gt = conn.execute(
                    "SELECT COALESCE(SUM(qty_done),0) as t FROM work_logs WHERE order_code=? AND garment_type=? AND (notes LIKE 'Kataai%' OR notes LIKE 'Cutting%')",
                    (code, gt)
                ).fetchone()["t"] or 0
                already_old = conn.execute(
                    "SELECT COALESCE(SUM(qty_done),0) as t FROM work_logs WHERE order_code=? AND garment_type LIKE 'Cutting%' AND (notes LIKE 'Kataai%' OR notes LIKE 'Cutting%')",
                    (code,)
                ).fetchone()["t"] or 0
                already = already_gt + already_old
                if already >= max_qty:
                    conn.close()
                    return jsonify({"ok": False, "error": f"कटाई पहले से हो गई है {gt} के लिए ऑर्डर #{code} में। ({already}/{max_qty})"})
        else:
            # No garment specified - cap to total order quantity
            total_garment_qty = conn.execute(
                "SELECT COALESCE(SUM(quantity),0) as t FROM order_items WHERE order_id=?",
                (order["id"],)
            ).fetchone()["t"] or 0
            if total_garment_qty > 0 and qty > total_garment_qty:
                conn.close()
                return jsonify({"ok": False, "error": f"Quantity {qty} exceeds total garments in order ({total_garment_qty})."})

        # Read correct rate from settings if not overridden
        if rate_override is not None and float(rate_override) > 0:
            making_rate = float(rate_override)
        elif is_naap:
            making_rate = float(get_setting("work_rate_measurement", "0") or 0)
        elif is_kataai:
            making_rate = float(get_setting("work_rate_cutting", "25") or 25)
        else:
            making_rate = float(get_setting("work_rate_alteration", "15") or 15)
        today = date.today().isoformat()
        now   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("""
            INSERT INTO work_logs(order_id, order_code, garment_type, qty_done,
                                  employee_name, log_date, making_rate, notes, created_at)
            VALUES(?,?,?,?,?,?,?,?,?)
        """, (order["id"], code, garment, qty, emp_name, today, making_rate, notes, now))
        conn.commit()
        conn.close()
        return jsonify({"ok": True, "auto_ready": False, "progress": f"{notes}: {qty} piece(s) logged"})

    # STITCHING — validate garment exists in order
    item = conn.execute(
        "SELECT quantity FROM order_items WHERE order_id=? AND garment_type=?",
        (order["id"], gt)
    ).fetchone()
    if not item:
        conn.close()
        return jsonify({"ok": False, "error": f"{gt} not found in order #{code}. Check garment type."})

    already_logged = conn.execute(
        "SELECT COALESCE(SUM(qty_done),0) as t FROM work_logs WHERE order_code=? AND garment_type=? AND (notes IS NULL OR notes NOT LIKE 'Measure%' AND notes NOT LIKE 'Cut%' AND notes NOT LIKE 'Naap%' AND notes NOT LIKE 'Kataai%')",
        (code, gt)
    ).fetchone()["t"] or 0
    remaining_to_log = item["quantity"] - already_logged
    if remaining_to_log <= 0:
        conn.close()
        return jsonify({"ok": False, "error": f"{gt} already fully stitched ({item['quantity']}/{item['quantity']})."})
    if qty > remaining_to_log:
        conn.close()
        return jsonify({"ok": False, "error": f"Only {remaining_to_log} piece(s) left to stitch for {gt}."})

    making_rate = float(rate_override) if rate_override is not None else float(get_setting(f"stitch_rate_{gt}", "0"))
    today = date.today().isoformat()
    now   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn.execute("""
        INSERT INTO work_logs(order_id, order_code, garment_type, qty_done,
                              employee_name, log_date, making_rate, notes, created_at)
        VALUES(?,?,?,?,?,?,?,?,?)
    """, (order["id"], code, gt, qty, emp_name, today, making_rate, notes, now))
    conn.commit()

    auto_ready = check_and_auto_ready(conn, code)
    conn.commit()

    total_logged = conn.execute(
        "SELECT COALESCE(SUM(qty_done),0) as t FROM work_logs WHERE order_code=? AND garment_type=?",
        (code, gt)
    ).fetchone()["t"]
    conn.close()

    progress = f"{gt}: {total_logged}/{item['quantity']} done"
    return jsonify({"ok": True, "auto_ready": auto_ready, "progress": progress})


# ══════════════════════════════════════════════
#  PICKUP & DELIVERY MODULE
# ══════════════════════════════════════════════

@bp.route("/pickup")
def pickup():
    conn = get_db()
    urgent_count = conn.execute(
        "SELECT COUNT(*) as c FROM orders WHERE is_urgent=1 AND status!='delivered'"
    ).fetchone()["c"]
    conn.close()
    upi_qr = get_setting("upi_qr_image", "") or "https://cdn.shopify.com/s/files/1/0587/4778/1225/files/WhatsApp_Image_2026-02-05_at_2.01.51_PM.jpg?v=1774547615"
    return render_template("employee/pickup.html",
        active_page="pickup", show_voice=True, urgent_count=urgent_count,
        upi_qr=upi_qr)


@bp.route("/api/pickup/search")
def api_pickup_search():
    q = request.args.get("q","").strip()
    if not q:
        return jsonify([])
    conn = get_db()

    def fmtd(d):
        if not d: return "—"
        p = str(d).split("-")
        return f"{p[2]}-{p[1]}-{p[0]}" if len(p)==3 else d

    like = f"%{q}%"
    rows = []

    # Search by order code first
    if q.lstrip("#").isdigit():
        code = q.lstrip("#")
        r = conn.execute("""
            SELECT o.order_code, o.status, o.delivery_date, o.remaining, o.is_urgent,
                   c.name as customer_name, c.mobile
            FROM orders o LEFT JOIN customers c ON c.id=o.customer_id
            WHERE o.order_code=? LIMIT 5
        """, (code,)).fetchall()
        rows += list(r)

    # Search by name or mobile
    r2 = conn.execute("""
        SELECT o.order_code, o.status, o.delivery_date, o.remaining, o.is_urgent,
               c.name as customer_name, c.mobile
        FROM orders o LEFT JOIN customers c ON c.id=o.customer_id
        WHERE (c.name LIKE ? OR c.mobile LIKE ?)
        AND o.order_code NOT IN ({})
        ORDER BY o.id DESC LIMIT 10
    """.format(",".join("?" * len(rows)) if rows else "'__none__'"),
        [like, like] + [r["order_code"] for r in rows]
    ).fetchall()
    rows += list(r2)
    conn.close()

    return jsonify([{
        "order_code":       r["order_code"],
        "status":           r["status"],
        "customer_name":    r["customer_name"] or "—",
        "mobile":           r["mobile"] or "",
        "delivery_date_fmt":fmtd(r["delivery_date"]),
        "remaining":        r["remaining"] or 0,
        "is_urgent":        r["is_urgent"]
    } for r in rows])


@bp.route("/api/pickup/order")
def api_pickup_order():
    code = request.args.get("code","").strip().lstrip("#")
    conn = get_db()

    o = conn.execute("""
        SELECT o.*, c.name as customer_name, c.mobile,
               COALESCE(o.repeat_of,'') as repeat_of
        FROM orders o LEFT JOIN customers c ON c.id=o.customer_id
        WHERE o.order_code=?
    """, (code,)).fetchone()

    if not o:
        conn.close()
        return jsonify({"error":"not found"})

    items = conn.execute(
        "SELECT garment_type, quantity, rate, amount FROM order_items WHERE order_id=?",
        (o["id"],)
    ).fetchall()

    def fmtd(d):
        if not d: return "—"
        p = str(d).split("-")
        return f"{p[2]}-{p[1]}-{p[0]}" if len(p)==3 else d

    try:
        delivered_at_raw = (o["delivered_at"] if "delivered_at" in o.keys() else "") or ""
    except:
        delivered_at_raw = ""

    conn.close()
    return jsonify({
        "order_code":       o["order_code"],
        "customer_name":    o["customer_name"] or "—",
        "mobile":           o["mobile"] or "",
        "status":           o["status"],
        "is_urgent":        o["is_urgent"],
        "repeat_of":        o["repeat_of"],
        "order_date_fmt":   fmtd(o["order_date"]),
        "delivery_date_fmt":fmtd(o["delivery_date"]),
        "payable_amount":   o["payable_amount"] or 0,
        "advance_paid":     o["advance_paid"] or 0,
        "remaining":        o["remaining"] or 0,
        "note":             o["note"] or "",
        "delivered_at_fmt": fmtd(delivered_at_raw[:10]),
        "garments": [{
            "garment_type": it["garment_type"],
            "quantity":     it["quantity"],
            "rate":         it["rate"],
            "amount":       it["amount"]
        } for it in items]
    })


@bp.route("/api/pickup/collect-and-deliver", methods=["POST"])
def api_pickup_collect_and_deliver():
    """Collect payment AND mark as delivered in one step."""
    data   = request.get_json(silent=True) or {}
    code   = data.get("order_code","").strip().lstrip("#")
    amount = float(data.get("amount", 0))
    mode   = data.get("mode","cash")

    if not code or amount <= 0:
        return jsonify({"ok":False, "error":"Invalid request"})

    conn = get_db()
    order = conn.execute(
        "SELECT id, remaining, advance_paid FROM orders WHERE order_code=?", (code,)
    ).fetchone()
    if not order:
        conn.close()
        return jsonify({"ok":False, "error":"Order not found"})

    today = date.today().isoformat()
    now   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    new_rem = max(0, round(order["remaining"] - amount, 2))
    new_adv = round(order["advance_paid"] + amount, 2)

    # Check status before delivering
    order_status_check = conn.execute("SELECT status FROM orders WHERE order_code=?", (code,)).fetchone()
    if order_status_check and order_status_check["status"] == "pending":
        conn.close()
        return jsonify({"ok":False, "error":"Cannot deliver a pending order. Clothes must be stitched and marked Ready first."})

    # Update order: payment + delivered
    conn.execute(
        "UPDATE orders SET remaining=?, advance_paid=?, status='delivered', delivered_at=? WHERE order_code=?",
        (new_rem, new_adv, now, code)
    )
    # Log finance entry
    conn.execute("""
        INSERT INTO finance(tx_date,tx_type,category,amount,mode,order_id,note,created_by,created_at)
        VALUES(?,'income','payment',?,?,?,?,'employee',?)
    """, (today, amount, mode, order["id"], f"Final payment on delivery #{code}", now))
    conn.commit()
    conn.close()
    return jsonify({"ok":True})


@bp.route("/api/pickup/deliver", methods=["POST"])
def api_pickup_deliver():
    """Mark order as delivered (already fully paid). Only allowed if status is 'ready'."""
    data = request.get_json(silent=True) or {}
    code = data.get("order_code","").strip().lstrip("#")
    if not code:
        return jsonify({"ok":False, "error":"No order code"})

    conn = get_db()
    order = conn.execute("SELECT status FROM orders WHERE order_code=?", (code,)).fetchone()
    if not order:
        conn.close()
        return jsonify({"ok":False, "error":"Order not found"})
    if order["status"] == "pending":
        conn.close()
        return jsonify({"ok":False, "error":"Cannot deliver a pending order. Clothes must be stitched first (status must be Ready)."})
    if order["status"] == "delivered":
        conn.close()
        return jsonify({"ok":False, "error":"Order is already delivered."})

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "UPDATE orders SET status='delivered', delivered_at=? WHERE order_code=?",
        (now, code)
    )
    conn.commit()
    conn.close()
    return jsonify({"ok":True})


# ══════════════════════════════════════════════
#  FINANCE MODULE
# ══════════════════════════════════════════════

@bp.route("/finance")
def finance():
    conn = get_db()
    today     = date.today().isoformat()
    month_start = today[:7] + "-01"

    def fmt_d(d):
        if not d: return "—"
        p = str(d).split("-")
        return f"{p[2]}-{p[1]}-{p[0]}" if len(p) == 3 else d

    # Monthly totals
    m = conn.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN tx_type='income' THEN amount ELSE 0 END),0) as income,
            COALESCE(SUM(CASE WHEN tx_type='income' AND mode='cash' THEN amount ELSE 0 END),0) as cash,
            COALESCE(SUM(CASE WHEN tx_type='income' AND mode='upi' THEN amount ELSE 0 END),0) as upi,
            COALESCE(SUM(CASE WHEN tx_type='expense' THEN amount ELSE 0 END),0) as expense,
            COUNT(CASE WHEN tx_type='expense' THEN 1 END) as exp_count
        FROM finance WHERE tx_date >= ?
    """, (month_start,)).fetchone()

    t = conn.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN tx_type='income' THEN amount ELSE 0 END),0) as income,
            COALESCE(SUM(CASE WHEN tx_type='income' AND mode='cash' THEN amount ELSE 0 END),0) as cash,
            COALESCE(SUM(CASE WHEN tx_type='income' AND mode='upi' THEN amount ELSE 0 END),0) as upi,
            COALESCE(SUM(CASE WHEN tx_type='expense' THEN amount ELSE 0 END),0) as expense,
            COUNT(CASE WHEN tx_type='expense' THEN 1 END) as exp_count
        FROM finance WHERE tx_date = ?
    """, (today,)).fetchone()

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    y = conn.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN tx_type='income' THEN amount ELSE 0 END),0) as income,
            COALESCE(SUM(CASE WHEN tx_type='income' AND mode='cash' THEN amount ELSE 0 END),0) as cash,
            COALESCE(SUM(CASE WHEN tx_type='income' AND mode='upi' THEN amount ELSE 0 END),0) as upi,
            COALESCE(SUM(CASE WHEN tx_type='expense' THEN amount ELSE 0 END),0) as expense,
            COUNT(CASE WHEN tx_type='expense' THEN 1 END) as exp_count
        FROM finance WHERE tx_date = ?
    """, (yesterday,)).fetchone()

    # All transactions with order codes
    rows = conn.execute("""
        SELECT f.*, o.order_code
        FROM finance f
        LEFT JOIN orders o ON o.id = f.order_id
        ORDER BY f.tx_date DESC, f.id DESC
    """).fetchall()

    urgent_count = conn.execute(
        "SELECT COUNT(*) as c FROM orders WHERE is_urgent=1 AND status!='delivered'"
    ).fetchone()["c"]
    conn.close()

    transactions = [{
        "tx_date":     r["tx_date"],
        "tx_date_fmt": fmt_d(r["tx_date"]),
        "tx_time":     (r["created_at"] or "")[11:16],
        "tx_type":     r["tx_type"],
        "category":    r["category"] or "",
        "note":        r["note"] or "",
        "mode":        r["mode"] or "",
        "amount":      r["amount"] or 0,
        "order_id":    r["order_id"],
        "order_code":  r["order_code"] or ""
    } for r in rows]

    return render_template("employee/finance.html",
        active_page="finance", show_voice=True,
        urgent_count=urgent_count,
        today_income=int(t["income"]),   today_cash=int(t["cash"]),
        today_upi=int(t["upi"]),         today_expense=int(t["expense"]),
        today_expense_count=int(t["exp_count"]),
        yesterday_income=int(y["income"]),  yesterday_cash=int(y["cash"]),
        yesterday_upi=int(y["upi"]),        yesterday_expense=int(y["expense"]),
        yesterday_expense_count=int(y["exp_count"]),
        transactions=transactions,
        get_setting=get_setting
    )


@bp.route("/api/finance/add", methods=["POST"])
def api_finance_add():
    data      = request.get_json(silent=True) or {}
    tx_type   = data.get("tx_type","income")
    amount    = float(data.get("amount", 0))
    category  = data.get("category","").strip()
    mode      = data.get("mode","cash")
    tx_date   = data.get("tx_date", date.today().isoformat())
    note      = data.get("note","").strip()
    order_code= data.get("order_code","").strip().lstrip("#")

    if amount <= 0 or not category:
        return jsonify({"ok": False, "error": "Amount and category required"})
    if tx_type not in ("income","expense"):
        return jsonify({"ok": False, "error": "Invalid type"})

    conn = get_db()
    order_id = None
    if order_code:
        o = conn.execute("SELECT id FROM orders WHERE order_code=?", (order_code,)).fetchone()
        if o: order_id = o["id"]

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("""
        INSERT INTO finance(tx_date,tx_type,category,amount,mode,order_id,note,created_by,created_at)
        VALUES(?,?,?,?,?,?,?,'employee',?)
    """, (tx_date, tx_type, category, amount, mode, order_id, note, now))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


# ══════════════════════════════════════════════
#  CUSTOMERS MODULE (Employee)
# ══════════════════════════════════════════════

@bp.route("/customers")
def customers():
    conn = get_db()
    all_c = conn.execute("""
        SELECT c.id, c.name, c.mobile, c.address,
               COUNT(o.id) as order_count,
               COALESCE(SUM(o.remaining),0) as remaining_total
        FROM customers c
        LEFT JOIN orders o ON o.customer_id = c.id
        GROUP BY c.id, c.name, c.mobile, c.address ORDER BY c.id DESC
    """).fetchall()

    def fmtd(d):
        if not d: return "—"
        p = str(d).split("-")
        return f"{p[2]}-{p[1]}-{p[0]}" if len(p)==3 else d

    customers_list = []
    for c in all_c:
        orders = conn.execute("""
            SELECT o.*, STRING_AGG(CAST(oi.garment_type||' x'||oi.quantity AS TEXT), ', ') as garments_str
            FROM orders o
            LEFT JOIN order_items oi ON oi.order_id = o.id
            WHERE o.customer_id=?
            GROUP BY o.id, o.order_code, o.status, o.order_date, o.delivery_date,
                 o.total_amount, o.extra_charges, o.payable_amount, o.advance_paid,
                 o.remaining, o.payment_mode, o.is_urgent, o.note, o.repeat_of,
                 o.delivered_at, o.created_at, c.name, c.mobile
        ORDER BY o.id DESC
        """, (c["id"],)).fetchall()
        order_list = [{
            "order_code":       o["order_code"],
            "status":           o["status"],
            "repeat_of":        (o["repeat_of"] if "repeat_of" in o.keys() else "") or "",
            "order_date_fmt":   fmtd(o["order_date"]),
            "delivery_date_fmt":fmtd(o["delivery_date"]),
            "payable_amount":   o["payable_amount"] or 0,
            "remaining":        o["remaining"] or 0,
            "garments":         (o["garments_str"] or "").split(", ") if o["garments_str"] else []
        } for o in orders]
        customers_list.append({
            "id":             c["id"],
            "name":           c["name"],
            "mobile":         c["mobile"] or "",
            "address":        c["address"] or "",
            "order_count":    c["order_count"],
            "remaining_total":c["remaining_total"]
        })

    urgent_count = conn.execute(
        "SELECT COUNT(*) as c FROM orders WHERE is_urgent=1 AND status!='delivered'"
    ).fetchone()["c"]
    conn.close()

    # Need to re-attach orders to customers_list (above just has summary)
    # Re-do with orders included
    conn2 = get_db()
    final_list = []
    for cu in customers_list:
        ords = conn2.execute("""
            SELECT o.*, STRING_AGG(CAST(oi.garment_type||' x'||oi.quantity AS TEXT), ', ') as garments_str
            FROM orders o LEFT JOIN order_items oi ON oi.order_id = o.id
            WHERE o.customer_id=? GROUP BY o.id, o.order_code, o.status, o.order_date,
                 o.delivery_date, o.payable_amount, o.advance_paid, o.remaining,
                 o.payment_mode, o.is_urgent, o.note, o.delivered_at
        ORDER BY o.id DESC
        """, (cu["id"],)).fetchall()
        cu["orders"] = [{
            "order_code":       o["order_code"],
            "status":           o["status"],
            "repeat_of":        (o["repeat_of"] if "repeat_of" in o.keys() else "") or "",
            "order_date_fmt":   fmtd(o["order_date"]),
            "delivery_date_fmt":fmtd(o["delivery_date"]),
            "payable_amount":   o["payable_amount"] or 0,
            "remaining":        o["remaining"] or 0,
            "garments":         (o["garments_str"] or "").split(", ") if o["garments_str"] else []
        } for o in ords]
        final_list.append(cu)
    conn2.close()

    return render_template("employee/customers.html",
        active_page="customers", show_voice=True,
        urgent_count=urgent_count, customers=final_list, total=len(final_list))


@bp.route("/api/finance-categories")
def public_finance_categories():
    """Public endpoint - returns finance categories for employee use."""
    income_cats  = get_setting("finance_income_cats",  "advance,payment,alteration,other income").split(",")
    expense_cats = get_setting("finance_expense_cats", "thread,buttons,fabric,electricity,rent,salary,transport,maintenance,other expense").split(",")
    return jsonify({
        "income":  [c.strip() for c in income_cats  if c.strip()],
        "expense": [c.strip() for c in expense_cats if c.strip()]
    })


@bp.route("/api/log-notify", methods=["POST"])
def api_log_notify():
    """Log when a WhatsApp notify is sent to a customer."""
    data = request.get_json(silent=True) or {}
    order_code = data.get("order_code","")
    customer   = data.get("customer","")
    mobile     = data.get("mobile","")
    lang       = data.get("lang","en")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db()
    conn.execute(
        "INSERT INTO notify_log(order_code,customer,mobile,lang,sent_at) VALUES(?,?,?,?,?)",
        (order_code, customer, mobile, lang, now)
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


# ══════════════════════════════════════════════
#  ORDER MEASUREMENTS (Cutting Reference)
# ══════════════════════════════════════════════

@bp.route("/measurements")
def measurements_page():
    """Show all pending/ready orders with measurements for cutting reference."""
    conn = get_db()
    import json as _json

    # Hindi field name map — full built-in map, merged with any DB overrides
    BUILT_IN_HINDI_MAP = {
        "Lambai": "लंबाई", "Seeno": "सीना", "Kamar": "कमर", "Shoulder": "कंधा",
        "Collar": "कॉलर", "Aastin": "आस्तीन", "Cough": "कफ",
        "Part 1": "पाट 1", "Part 2": "पाट 2", "Part 3": "पाट 3",
        "Seat": "सीट", "Mori": "मोरी", "Jangh": "जांघ", "Goda": "घुटना",
        "Langot": "लंगोट", "Back Paat": "बैक पाट",
        "P-Lambai": "पाय. लंबाई", "P-Kamar": "पाय. कमर", "P-Seat": "पाय. सीट",
        "P-Mori": "पाय. मोरी", "P-Jangh": "पाय. जांघ",
        "Hip": "हिप", "Length": "लंबाई", "Chest": "सीना", "Waist": "कमर",
        "Thigh": "जांघ", "Bottom": "मोरी", "Details": "विवरण",
    }
    try:
        db_map = _json.loads(get_setting("hindi_field_map", "{}"))
    except:
        db_map = {}
    hindi_map = {**BUILT_IN_HINDI_MAP, **db_map}

    # Garment types config
    garment_types_cfg = {}
    for row in conn.execute("SELECT key, value FROM settings WHERE key LIKE 'types_%'").fetchall():
        gname = row["key"][6:]
        types_raw = row["value"].split("|")
        pairs = []
        for t in types_raw:
            if ":" in t:
                k, v = t.split(":", 1)
                pairs.append({"k": k, "v": v})
            elif t:
                pairs.append({"k": t, "v": t})
        garment_types_cfg[gname] = pairs

    orders = conn.execute("""
        SELECT o.*, c.name as customer_name, c.mobile
        FROM orders o LEFT JOIN customers c ON c.id=o.customer_id
        WHERE o.status NOT IN ('delivered','cancelled')
        ORDER BY o.is_urgent DESC, o.delivery_date ASC
    """).fetchall()

    urgent_count = conn.execute(
        "SELECT COUNT(*) as c FROM orders WHERE is_urgent=1 AND status!='delivered'"
    ).fetchone()["c"]

    # Load employees for the "who cut it" modal
    try:
        conn.execute("ALTER TABLE employees ADD COLUMN skills TEXT DEFAULT 'stitch'")
        conn.commit()
    except: pass
    try:
        conn.execute("ALTER TABLE employees ADD COLUMN hindi_name TEXT")
        conn.commit()
    except: pass
    employees = conn.execute(
        "SELECT id, name, COALESCE(hindi_name, name) as hindi_name FROM employees WHERE active=1 ORDER BY name"
    ).fetchall()
    emp_list = [{"id": e["id"], "name": e["name"], "hindi_name": e["hindi_name"]} for e in employees]

    def fmtd(d):
        if not d: return "—"
        p = str(d).split("-")
        return f"{p[2]}-{p[1]}-{p[0]}" if len(p)==3 else d

    order_list = []
    for o in orders:
        items = conn.execute(
            "SELECT * FROM order_items WHERE order_id=?", (o["id"],)
        ).fetchall()
        garments = []
        for it in items:
            try:
                meas = _json.loads(it["measurements"] or "{}")
            except:
                meas = {}
            # Check if cutting already logged for this garment in this order
            cut_row = conn.execute(
                "SELECT employee_name FROM work_logs WHERE order_code=? AND garment_type=? AND notes LIKE 'Kataai%' ORDER BY created_at DESC LIMIT 1",
                (o["order_code"], it["garment_type"])
            ).fetchone()
            cut_done = cut_row["employee_name"] if cut_row else None
            garments.append({
                "item_id":      it["id"],
                "garment_type": it["garment_type"],
                "quantity":     it["quantity"],
                "measurements": meas,
                "notes":        it["notes"] or "",
                "cut_done":     cut_done,
            })
        order_list.append({
            "order_code":        o["order_code"],
            "customer_name":     o["customer_name"] or "—",
            "mobile":            o["mobile"] or "",
            "status":            o["status"],
            "is_urgent":         o["is_urgent"],
            "delivery_date_fmt": fmtd(o["delivery_date"]),
            "order_date_fmt":    fmtd(o["order_date"]),
            "note":              o["note"] or "",
            "garments":          garments
        })

    # Load images for each order - DB first (Cloudinary), then filesystem fallback
    for o in order_list:
        order_row = conn.execute("SELECT id FROM orders WHERE order_code=?", (o["order_code"],)).fetchone()
        imgs = []
        if order_row:
            img_rows = conn.execute("SELECT file_path FROM order_images WHERE order_id=? ORDER BY id", (order_row["id"],)).fetchall()
            imgs = [r["file_path"] for r in img_rows if r["file_path"] and not r["file_path"].startswith("temp:")]
        if not imgs:
            folder = os.path.join(Config.UPLOAD_FOLDER, o["order_code"])
            if os.path.isdir(folder):
                files = sorted(f for f in os.listdir(folder) if f.lower().endswith((".jpg",".jpeg",".png",".gif",".webp")))
                imgs = [f"/static/order_images/{o['order_code']}/{f}" for f in files]
        o["images"] = imgs

    conn.close()
    return render_template("employee/measurements.html",
        active_page="measurements", show_voice=True,
        urgent_count=urgent_count, orders=order_list,
        hindi_map=hindi_map, garment_types_cfg=garment_types_cfg,
        employees=emp_list)
