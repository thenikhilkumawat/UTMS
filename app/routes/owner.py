from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
import json
from functools import wraps
from datetime import date, datetime, timedelta
from database import get_db, get_setting, set_setting

bp = Blueprint("owner", __name__, url_prefix="/owner")

def fmt_d(d):
    """Format date string from YYYY-MM-DD to DD-MM-YYYY"""
    if not d: return "—"
    try:
        parts = str(d).split("-")
        if len(parts) == 3:
            return f"{parts[2]}-{parts[1]}-{parts[0]}"
    except: pass
    return str(d)


def owner_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("owner_logged_in"):
            return redirect(url_for("owner.login"))
        return f(*args, **kwargs)
    return decorated

@bp.route("/login")
def login():
    if request.args.get("expired"):
        flash("Session expired. Please login again.", "warning")
    return render_template("owner/login.html", active_page=None, show_voice=False, urgent_count=0)

@bp.route("/verify-pin", methods=["POST"])
def verify_pin():
    data = request.get_json(silent=True) or {}
    entered = str(data.get("pin",""))
    real_pin = get_setting("owner_pin","1234")
    if entered == real_pin:
        session["owner_logged_in"] = True
        session.permanent = False
        return jsonify({"ok": True})
    return jsonify({"ok": False})

@bp.route("/logout", methods=["GET","POST"])
def logout():
    session.pop("owner_logged_in", None)
    return redirect(url_for("owner.login"))

@bp.route("/dashboard")
@owner_required
def dashboard():
    conn = get_db()
    today = date.today().isoformat()
    month_start = date.today().replace(day=1).isoformat()

    # Allow owner to pick a date via ?date=YYYY-MM-DD, default to most recent active date
    selected_date_str = request.args.get("date", "").strip()
    
    # If no date param, find the most recent date that has transactions
    # This fixes the server-date vs laptop-date mismatch
    if not selected_date_str:
        last_tx = conn.execute("SELECT tx_date FROM finance ORDER BY id DESC LIMIT 1").fetchone()
        if last_tx:
            # Use the date of the last transaction as "today" if it's within last 2 days
            from datetime import timedelta
            last_date = last_tx["tx_date"]
            server_today = date.today().isoformat()
            # If last transaction date is today or yesterday, show it
            yesterday = (date.today() - timedelta(days=1)).isoformat()
            if last_date in [server_today, yesterday]:
                selected_date = last_date
            else:
                selected_date = server_today
        else:
            selected_date = today
    else:
        selected_date = selected_date_str
    
    # Recalculate month_start based on selected_date
    try:
        sel_dt = datetime.strptime(selected_date, "%Y-%m-%d").date()
    except:
        sel_dt = date.today()
    month_start = sel_dt.replace(day=1).isoformat()

    # Today income/expense totals (using selected_date)
    rows = conn.execute("SELECT tx_type, SUM(amount) as total FROM finance WHERE tx_date=? GROUP BY tx_type",(selected_date,)).fetchall()
    fin_today = {r["tx_type"]: r["total"] or 0 for r in rows}

    # Month totals
    rows_m = conn.execute("SELECT tx_type, SUM(amount) as total FROM finance WHERE tx_date >= ? GROUP BY tx_type",(month_start,)).fetchall()
    fin_month = {r["tx_type"]: r["total"] or 0 for r in rows_m}

    # Month cash/upi breakdown
    month_cash = conn.execute(
        "SELECT COALESCE(SUM(amount),0) as t FROM finance WHERE tx_date>=? AND tx_type='income' AND LOWER(mode)='cash'",(month_start,)
    ).fetchone()["t"]
    month_upi = conn.execute(
        "SELECT COALESCE(SUM(amount),0) as t FROM finance WHERE tx_date>=? AND tx_type='income' AND LOWER(mode)='upi'",(month_start,)
    ).fetchone()["t"]

    # Selected date cash/upi
    cash_today = conn.execute(
        "SELECT COALESCE(SUM(amount),0) as t FROM finance WHERE tx_date=? AND tx_type='income' AND LOWER(mode)='cash'",(selected_date,)
    ).fetchone()["t"]
    upi_today = conn.execute(
        "SELECT COALESCE(SUM(amount),0) as t FROM finance WHERE tx_date=? AND tx_type='income' AND LOWER(mode)='upi'",(selected_date,)
    ).fetchone()["t"]

    # Full transaction log for selected date
    today_transactions = conn.execute(
        "SELECT f.*, o.order_code FROM finance f LEFT JOIN orders o ON o.id=f.order_id WHERE f.tx_date=? ORDER BY f.id DESC",(selected_date,)
    ).fetchall()

    dues = conn.execute("SELECT SUM(remaining) as total, COUNT(*) as cnt FROM orders WHERE status != 'delivered' AND remaining > 0").fetchone()
    work_today = conn.execute("SELECT SUM(qty_done) as total FROM work_logs WHERE log_date=?",(today,)).fetchone()
    # If no work logs yet, count items from today's orders as a proxy
    work_today_val = (work_today["total"] or 0) if work_today else 0
    if work_today_val == 0:
        items_today = conn.execute("""SELECT COALESCE(SUM(oi.quantity),0) as total
            FROM order_items oi JOIN orders o ON o.id=oi.order_id
            WHERE o.order_date=?""",(today,)).fetchone()
        work_today_proxy = items_today["total"] or 0
    low_stock = conn.execute("SELECT * FROM inventory WHERE quantity <= low_alert_at ORDER BY quantity ASC").fetchall()
    urgent_count = conn.execute("SELECT COUNT(*) as c FROM orders WHERE is_urgent=1 AND status != 'delivered' AND delivery_date >= ?",(today,)).fetchone()["c"]

    # All rate settings
    custom_rates = conn.execute("SELECT key,value FROM settings WHERE key LIKE '%rate%'").fetchall()
    conn.close()

    today_str = datetime.today().strftime("%A, %d %B %Y")
    d = date.today()
    today_date = f"{d.day:02d}-{d.month:02d}-{d.year}"

    garment_names = [
        "Shirt","Shirt Linen","Pant","Pant Double","Jeans","Suit 2pc","Suit 3pc",
        "Blazer","Kurta","Kurta Pajama","Pajama","Pathani","Sherwani","Safari","Waistcoat",
        "Alteration","Cutting Only"
    ]
    # Customer rates (what customers pay)
    garment_rates = {}
    for n in garment_names:
        r = get_setting("customer_rate_"+n,"") or get_setting("rate_"+n,"0")
        garment_rates[n] = r
    # Add custom customer rates
    for row in custom_rates:
        if row["key"].startswith("customer_rate_"):
            name = row["key"][14:]
            if name not in garment_rates:
                garment_rates[name] = row["value"]

    # Stitching rates (what employees get paid)
    stitch_rates = {n: get_setting("stitch_rate_"+n,"0") for n in garment_names}
    for row in custom_rates:
        if row["key"].startswith("stitch_rate_"):
            name = row["key"][12:]
            if name not in stitch_rates:
                stitch_rates[name] = row["value"]

    return render_template("owner/dashboard.html",
        active_page="owner_dashboard", show_voice=False, urgent_count=urgent_count,
        today_str=today_str, today_date=selected_date,
        selected_date=selected_date,
        low_stock=low_stock,
        garment_rates=garment_rates,
        stitch_rates=stitch_rates,
        today_transactions=today_transactions,
        stats={
            "today_income":  fin_today.get("income",0),
            "today_expense": fin_today.get("expense",0),
            "today_cash":    cash_today,
            "today_upi":     upi_today,
            "month_income":  fin_month.get("income",0),
            "month_cash":    month_cash,
            "month_upi":     month_upi,
            "month_net":     fin_month.get("income",0) - fin_month.get("expense",0),
            "pending_dues":  dues["total"] or 0 if dues else 0,
            "pending_orders":dues["cnt"] or 0 if dues else 0,
            "work_today":    work_today_proxy if (work_today["total"] or 0)==0 else work_today["total"],
        }
    )

@bp.route("/settings")
@owner_required
def settings():
    conn = get_db()
    today = date.today().isoformat()
    urgent_count = conn.execute("SELECT COUNT(*) as c FROM orders WHERE is_urgent=1 AND status != 'delivered' AND delivery_date >= ?",(today,)).fetchone()["c"]
    conn.close()
    current_settings = {
        "shop_name":        get_setting("shop_name","Uttam Tailors"),
        "shop_name_hi":     get_setting("shop_name_hi","उत्तम टेलर्स"),
        "whatsapp_number":  get_setting("whatsapp_number",""),
        "default_language": get_setting("default_language","hl"),
        "order_code_start": get_setting("last_order_code","3600"),
    }
    garment_names_std = [
        "Shirt","Shirt Linen","Pant","Pant Double","Jeans","Suit 2pc","Suit 3pc",
        "Blazer","Kurta","Kurta Pajama","Pajama","Pathani","Sherwani","Safari",
        "Waistcoat","Alteration","Cutting Only"
    ]
    # Customer rates
    garment_rates = {}
    for n in garment_names_std:
        r = get_setting("customer_rate_"+n,"") or get_setting("rate_"+n,"0")
        garment_rates[n] = r
    # Add any custom customer garments
    from database import get_db as _gdb2
    _c2 = _gdb2()
    all_settings = _c2.execute("SELECT key,value FROM settings WHERE key LIKE 'customer_rate_%'").fetchall()
    _c2.close()
    for row in all_settings:
        name = row["key"][14:]
        if name not in garment_rates:
            garment_rates[name] = row["value"]

    # Stitching rates
    stitch_rates = {}
    for n in garment_names_std:
        stitch_rates[n] = get_setting("stitch_rate_"+n,"0")
    work_rates_map = {
        "work_rate_measurement": get_setting("work_rate_measurement","0"),
        "work_rate_cutting":     get_setting("work_rate_cutting","25"),
        "work_rate_alteration":  get_setting("work_rate_alteration","15"),
    }
    conn2 = get_db()
    # Garment type chips — always show all standard garment types
    ALL_GARMENTS = [
        "Shirt","Shirt Linen","Pant","Pant Double","Jeans",
        "Suit 2pc","Suit 3pc","Blazer","Kurta","Kurta Pajama",
        "Pajama","Pathani","Sherwani","Safari","Waistcoat",
        "Alteration","Cutting Only"
    ]
    existing_chips = {}
    for row in conn2.execute("SELECT key, value FROM settings WHERE key LIKE 'types_%'").fetchall():
        existing_chips[row["key"][6:]] = row["value"] or ""
    # Build ordered dict: standard first, then any custom
    garment_type_chips = {}
    for g in ALL_GARMENTS:
        garment_type_chips[g] = existing_chips.get(g, "")
    for g, v in existing_chips.items():
        if g not in garment_type_chips:
            garment_type_chips[g] = v
    try:
        conn2.execute("ALTER TABLE employees ADD COLUMN skills TEXT DEFAULT 'stitch'")
        conn2.execute("UPDATE employees SET skills='all' WHERE name='Kamal' AND (skills IS NULL OR skills='stitch')")
        conn2.commit()
    except Exception:
        pass
    all_employees = conn2.execute(
        "SELECT id, name, COALESCE(skills,'stitch') as skills FROM employees WHERE active=1 ORDER BY name"
    ).fetchall()
    conn2.close()
    return render_template("owner/settings.html",
        active_page="settings", show_voice=True, urgent_count=urgent_count,
        settings=current_settings, garment_rates=garment_rates,
        stitch_rates=stitch_rates, work_rates_map=work_rates_map,
        all_employees=all_employees,
        garment_type_chips=garment_type_chips
    )

@bp.route("/settings/save", methods=["POST"])
@owner_required
def settings_save():
    section = request.form.get("section")
    if section == "shop":
        # Handle logo upload
        import base64
        logo_file = request.files.get("shop_logo")
        if logo_file and logo_file.filename:
            data = logo_file.read()
            ext = logo_file.filename.rsplit(".",1)[-1].lower()
            b64 = base64.b64encode(data).decode()
            set_setting("shop_logo", f"data:image/{ext};base64,{b64}")
            flash("Logo updated!", "success")
        set_setting("shop_name",        request.form.get("shop_name","").strip())
        set_setting("shop_name_hi",     request.form.get("shop_name_hi","").strip())
        set_setting("whatsapp_number",  request.form.get("whatsapp_number","").strip())
        set_setting("default_language", request.form.get("default_language","hl"))
        # Order code start - only update last_order_code if value given and valid
        new_code = request.form.get("order_code_start","").strip()
        if new_code.isdigit():
            set_setting("last_order_code", str(int(new_code) - 1))  # next call will increment to this
        flash("Shop settings saved!", "success")
    elif section == "pin":
        current = request.form.get("current_pin","")
        new_pin = request.form.get("new_pin","")
        confirm = request.form.get("confirm_pin","")
        real_pin = get_setting("owner_pin","1234")
        if current != real_pin:
            flash("Current PIN is wrong.", "error")
        elif len(new_pin) != 4 or not new_pin.isdigit():
            flash("New PIN must be exactly 4 digits.", "error")
        elif new_pin != confirm:
            flash("PINs do not match.", "error")
        else:
            set_setting("owner_pin", new_pin)
            flash("PIN changed successfully!", "success")
    elif section == "customer_rates":
        for name in request.form.getlist("delete_rate"):
            conn2 = get_db()
            conn2.execute("DELETE FROM settings WHERE key=?",("customer_rate_"+name,))
            conn2.commit(); conn2.close()
        for key, val in request.form.items():
            if key.startswith("customer_rate_") and val.strip():
                set_setting(key, val)
        flash("Customer rates saved!", "success")
    elif section == "stitch_rates":
        for key, val in request.form.items():
            if key.startswith("stitch_rate_") and val.strip():
                set_setting(key, val)
        flash("Stitching rates saved!", "success")
    elif section == "rate_image":
        import base64
        img = request.files.get("rate_list_image")
        if img and img.filename:
            data = img.read()
            ext = img.filename.rsplit(".",1)[-1].lower()
            b64 = base64.b64encode(data).decode()
            set_setting("rate_list_image", f"data:image/{ext};base64,{b64}")
            flash("Rate list image uploaded!", "success")
    elif section == "add_employee":
        name  = request.form.get("emp_name","").strip()
        phone = request.form.get("emp_phone","").strip()
        if name:
            conn2 = get_db()
            try:
                conn2.execute("INSERT INTO employees(name,phone) VALUES(?,?)", (name, phone))
                conn2.commit()
                flash(f"Employee '{name}' added!", "success")
            except:
                flash("Employee name already exists", "warning")
            conn2.close()
    elif section == "remove_employee":
        emp_id = request.form.get("emp_id","")
        if emp_id:
            conn2 = get_db()
            conn2.execute("UPDATE employees SET active=0 WHERE id=?", (emp_id,))
            conn2.commit(); conn2.close()
            flash("Employee removed.", "success")
    elif section == "rates":
        for name in request.form.getlist("delete_rate"):
            conn2 = get_db()
            conn2.execute("DELETE FROM settings WHERE key=?",("rate_"+name,))
            conn2.commit(); conn2.close()
        for key, val in request.form.items():
            if key.startswith("rate_") and val.strip():
                set_setting(key, val)
        flash("Rates saved!", "success")
    return redirect(url_for("owner.settings"))

@bp.route("/api/owner/earnings-7days")
@owner_required
def earnings_7days():
    conn = get_db()
    labels, income_data, expense_data = [], [], []
    for i in range(6,-1,-1):
        d = (date.today() - timedelta(days=i)).isoformat()
        labels.append(d[5:])
        rows = conn.execute("SELECT tx_type, SUM(amount) as total FROM finance WHERE tx_date=? GROUP BY tx_type",(d,)).fetchall()
        fin = {r["tx_type"]: r["total"] or 0 for r in rows}
        income_data.append(fin.get("income",0))
        expense_data.append(fin.get("expense",0))
    conn.close()
    return jsonify({"labels":labels,"income":income_data,"expense":expense_data})

@bp.route("/api/settings/logo")
def api_logo():
    return jsonify({"value": get_setting("shop_logo","")})

@bp.route("/measurement-fields")
@owner_required
def measurement_fields():
    conn = get_db()
    today = date.today().isoformat()
    urgent_count = conn.execute("SELECT COUNT(*) as c FROM orders WHERE is_urgent=1 AND status!='delivered' AND delivery_date>=?",(today,)).fetchone()["c"]
    # Get all garment types
    garment_types = [
        "Shirt","Shirt Linen","Pant","Pant Double","Jeans","Suit 2pc","Suit 3pc",
        "Blazer","Kurta","Kurta Pajama","Pajama","Pathani","Sherwani","Safari","Waistcoat",
        "Alteration","Cutting Only"
    ]
    # Also get any custom ones from DB
    extra = conn.execute("SELECT DISTINCT garment_type FROM measurement_fields WHERE garment_type NOT IN ({})".format(
        ",".join("?"*len(garment_types))), garment_types).fetchall()
    garment_types += [r["garment_type"] for r in extra]

    fields_by_garment = {}
    rows = conn.execute("SELECT garment_type,field_name,id FROM measurement_fields ORDER BY sort_order ASC,id ASC").fetchall()
    for r in rows:
        fields_by_garment.setdefault(r["garment_type"],[]).append({"id":r["id"],"name":r["field_name"]})
    conn.close()
    return render_template("owner/measurement_fields.html",
        active_page="settings", show_voice=False, urgent_count=urgent_count,
        garment_types=garment_types, fields_by_garment=fields_by_garment)

@bp.route("/measurement-fields/add", methods=["POST"])
@owner_required
def add_measurement_field():
    garment = request.form.get("garment_type","").strip()
    field   = request.form.get("field_name","").strip()
    if garment and field:
        conn = get_db()
        conn.execute("INSERT OR IGNORE INTO measurement_fields(garment_type,field_name,sort_order) VALUES(?,?,99)",(garment,field))
        conn.commit(); conn.close()
        flash(f"Field added to {garment}!", "success")
    return redirect(url_for("owner.measurement_fields"))

@bp.route("/measurement-fields/delete/<int:fid>")
@owner_required
def delete_measurement_field(fid):
    conn = get_db()
    conn.execute("DELETE FROM measurement_fields WHERE id=?",(fid,))
    conn.commit(); conn.close()
    flash("Field removed.", "success")
    return redirect(url_for("owner.measurement_fields"))


# ══════════════════════════════════════════════
#  EXCEL EXPORT & IMPORT
# ══════════════════════════════════════════════

@bp.route("/export/orders")
@owner_required
def export_orders():
    """Export all orders with every field to Excel."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    from io import BytesIO
    import json as _json

    conn = get_db()
    orders = conn.execute("""
        SELECT o.*, c.name as cname, c.mobile, c.address
        FROM orders o LEFT JOIN customers c ON c.id=o.customer_id
        ORDER BY o.id DESC
    """).fetchall()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Orders"

    # Header style
    hdr_fill = PatternFill("solid", fgColor="6366F1")
    hdr_font = Font(bold=True, color="FFFFFF", size=11)

    headers = [
        "Order Code", "Customer Name", "Mobile", "Address",
        "Order Date", "Delivery Date", "Status", "Is Urgent",
        "Garments", "Measurements",
        "Total Amount", "Extra Charges", "Payable Amount",
        "Advance Paid", "Remaining Due", "Payment Mode",
        "Repeat Of", "Note", "Delivered At", "Created At"
    ]

    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = hdr_font
        cell.fill = hdr_fill
        cell.alignment = Alignment(horizontal="center")

    ws.freeze_panes = "A2"

    def fmtd(d):
        if not d: return ""
        p = str(d).split("-")
        return f"{p[2]}-{p[1]}-{p[0]}" if len(p)==3 else d

    for row_idx, o in enumerate(orders, 2):
        items = conn.execute(
            "SELECT garment_type, quantity, rate, amount, measurements FROM order_items WHERE order_id=?",
            (o["id"],)
        ).fetchall()

        garments_str = "; ".join(f"{i['garment_type']} x{i['quantity']} @₹{int(i['rate'])}" for i in items)
        meas_parts = []
        for it in items:
            try:
                m = _json.loads(it["measurements"] or "{}")
                if m:
                    meas_parts.append(f"{it['garment_type']}: " + ", ".join(f"{k}={v}" for k,v in m.items()))
            except: pass
        meas_str = "; ".join(meas_parts)

        delivered_at = ""
        try: delivered_at = fmtd((o["delivered_at"] or "")[:10])
        except: pass

        row = [
            o["order_code"], o["cname"] or "", o["mobile"] or "", o["address"] or "",
            fmtd(o["order_date"]), fmtd(o["delivery_date"]),
            o["status"], "Yes" if o["is_urgent"] else "No",
            garments_str, meas_str,
            o["total_amount"] or 0, o["extra_charges"] or 0, o["payable_amount"] or 0,
            o["advance_paid"] or 0, o["remaining"] or 0, o["payment_mode"] or "",
            o["repeat_of"] or "", o["note"] or "", delivered_at,
            (o["created_at"] or "")[:16]
        ]
        for col, val in enumerate(row, 1):
            ws.cell(row=row_idx, column=col, value=val)
        # Highlight urgent in red
        if o["is_urgent"]:
            for col in range(1, len(headers)+1):
                ws.cell(row=row_idx, column=col).fill = PatternFill("solid", fgColor="FEE2E2")

    # Auto column widths
    for col in ws.columns:
        max_len = max((len(str(cell.value or "")) for cell in col), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 3, 40)

    conn.close()
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    from flask import send_file
    from datetime import datetime as _dt
    fname = f"uttam_tailors_orders_{_dt.now().strftime('%d-%m-%Y')}.xlsx"
    return send_file(buf, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                     as_attachment=True, download_name=fname)


@bp.route("/import/customers", methods=["POST"])
@owner_required
def import_customers():
    """Import customers from Excel sheet."""
    import openpyxl
    from io import BytesIO
    f = request.files.get("customer_file")
    if not f:
        flash("No file selected", "warning")
        return redirect(url_for("owner.settings"))

    try:
        wb = openpyxl.load_workbook(BytesIO(f.read()))
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            flash("File is empty", "warning")
            return redirect(url_for("owner.settings"))

        # Try to detect header row
        header = [str(c or "").lower().strip() for c in rows[0]]
        name_col   = next((i for i,h in enumerate(header) if "name" in h), None)
        mobile_col = next((i for i,h in enumerate(header) if "mobile" in h or "phone" in h), None)
        addr_col   = next((i for i,h in enumerate(header) if "address" in h or "addr" in h), None)

        if name_col is None:
            flash("Could not find 'Name' column in Excel file", "error")
            return redirect(url_for("owner.settings"))

        conn = get_db()
        added = skipped = 0
        from datetime import datetime as _dt
        now = _dt.now().strftime("%Y-%m-%d %H:%M:%S")

        for row in rows[1:]:
            name   = str(row[name_col] or "").strip() if name_col is not None else ""
            mobile = str(row[mobile_col] or "").strip() if mobile_col is not None else ""
            addr   = str(row[addr_col] or "").strip() if addr_col is not None else ""
            if not name:
                continue
            existing = conn.execute("SELECT id FROM customers WHERE name=? AND mobile=?", (name, mobile)).fetchone()
            if existing:
                skipped += 1
            else:
                conn.execute("INSERT INTO customers(name,mobile,address,created_at) VALUES(?,?,?,?)",
                             (name, mobile, addr, now))
                added += 1

        conn.commit(); conn.close()
        flash(f"Import complete: {added} customers added, {skipped} already existed.", "success")
    except Exception as e:
        flash(f"Import error: {str(e)}", "error")

    return redirect(url_for("owner.settings"))


# ══════════════════════════════════════════════
#  INVENTORY MODULE
# ══════════════════════════════════════════════

@bp.route("/inventory")
@owner_required
def inventory():
    conn = get_db()
    today = date.today().isoformat()
    items = conn.execute("SELECT * FROM inventory ORDER BY item_name").fetchall()
    urgent_count = conn.execute(
        "SELECT COUNT(*) as c FROM orders WHERE is_urgent=1 AND status!='delivered'"
    ).fetchone()["c"]
    conn.close()
    return render_template("owner/inventory.html",
        active_page="inventory", show_voice=False,
        urgent_count=urgent_count, items=items)


@bp.route("/inventory/save", methods=["POST"])
@owner_required
def inventory_save():
    name      = request.form.get("item_name","").strip()
    quantity  = int(request.form.get("quantity",0) or 0)
    unit      = request.form.get("unit","").strip()
    threshold = int(request.form.get("low_threshold",0) or 0)
    if name:
        conn = get_db()
        # Upsert
        existing = conn.execute("SELECT id FROM inventory WHERE item_name=?", (name,)).fetchone()
        if existing:
            conn.execute("UPDATE inventory SET quantity=?, unit=?, low_threshold=? WHERE item_name=?",
                        (quantity, unit, threshold, name))
        else:
            conn.execute("INSERT INTO inventory(item_name,quantity,unit,low_threshold) VALUES(?,?,?,?)",
                        (name, quantity, unit, threshold))
        conn.commit(); conn.close()
        flash(f"'{name}' saved!", "success")
    return redirect(url_for("owner.inventory"))


@bp.route("/inventory/delete/<int:item_id>", methods=["POST"])
@owner_required
def inventory_delete(item_id):
    conn = get_db()
    conn.execute("DELETE FROM inventory WHERE id=?", (item_id,))
    conn.commit(); conn.close()
    flash("Item deleted", "success")
    return redirect(url_for("owner.inventory"))


# ══════════════════════════════════════════════
#  OWNER CUSTOMERS MODULE
# ══════════════════════════════════════════════

@bp.route("/customers")
@owner_required
def owner_customers():
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT c.id, c.name, COALESCE(c.mobile,'') as mobile,
                   COALESCE(c.address,'') as address,
                   COUNT(o.id) as order_count,
                   COALESCE(SUM(o.payable_amount),0) as total_billed,
                   COALESCE(SUM(o.remaining),0) as total_due,
                   MAX(o.order_date) as last_order_date
            FROM customers c LEFT JOIN orders o ON o.customer_id=c.id
            GROUP BY c.id ORDER BY c.id DESC
        """).fetchall()
    except Exception as e:
        conn.close()
        return f"<h2>DB Error in /owner/customers</h2><pre>{e}</pre>", 500

    def fmtd(d):
        if not d: return "—"
        p = str(d).split("-")
        return f"{p[2]}-{p[1]}-{p[0]}" if len(p)==3 else d

    # Get all order codes per customer in one query
    all_codes = conn.execute(
        "SELECT customer_id, order_code FROM orders ORDER BY id DESC"
    ).fetchall()
    codes_by_cust = {}
    for row in all_codes:
        codes_by_cust.setdefault(row["customer_id"], []).append(row["order_code"])

    customers = [{
        "id":             r["id"],
        "name":           r["name"],
        "mobile":         r["mobile"] or "",
        "address":        r["address"] or "",
        "order_count":    r["order_count"],
        "total_billed":   r["total_billed"] or 0,
        "total_due":      r["total_due"] or 0,
        "last_order_date":fmtd(r["last_order_date"]),
        "order_codes":    " ".join(codes_by_cust.get(r["id"], []))
    } for r in rows]
    urgent_count = conn.execute(
        "SELECT COUNT(*) as c FROM orders WHERE is_urgent=1 AND status!='delivered'"
    ).fetchone()["c"]
    conn.close()
    return render_template("owner/customers.html",
        active_page="customers", show_voice=False,
        urgent_count=urgent_count, customers=customers, total=len(customers))


# ══════════════════════════════════════════════
#  OWNER FINANCE MODULE
# ══════════════════════════════════════════════

@bp.route("/finance")
@owner_required
def owner_finance():
    today = date.today().isoformat()
    from_date = request.args.get("from", today[:7]+"-01")
    to_date   = request.args.get("to",   today)

    conn = get_db()
    rows = conn.execute("""
        SELECT f.*, o.order_code
        FROM finance f LEFT JOIN orders o ON o.id=f.order_id
        WHERE f.tx_date >= ? AND f.tx_date <= ?
        ORDER BY f.tx_date DESC, f.id DESC
    """, (from_date, to_date)).fetchall()

    stats_r = conn.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN tx_type='income' THEN amount ELSE 0 END),0) as income,
            COALESCE(SUM(CASE WHEN tx_type='income' AND mode='cash' THEN amount ELSE 0 END),0) as cash_i,
            COALESCE(SUM(CASE WHEN tx_type='income' AND mode='upi' THEN amount ELSE 0 END),0) as upi_i,
            COALESCE(SUM(CASE WHEN tx_type='expense' THEN amount ELSE 0 END),0) as expense,
            COUNT(CASE WHEN tx_type='expense' THEN 1 END) as exp_count
        FROM finance WHERE tx_date >= ? AND tx_date <= ?
    """, (from_date, to_date)).fetchone()

    pending_due = conn.execute(
        "SELECT COALESCE(SUM(remaining),0) as d FROM orders WHERE status!='delivered'"
    ).fetchone()["d"]
    urgent_count = conn.execute(
        "SELECT COUNT(*) as c FROM orders WHERE is_urgent=1 AND status!='delivered'"
    ).fetchone()["c"]
    conn.close()

    def fmtd(d):
        if not d: return "—"
        p = str(d).split("-")
        return f"{p[2]}-{p[1]}-{p[0]}" if len(p)==3 else d

    transactions = [{
        "tx_date":     r["tx_date"],
        "tx_date_fmt": fmtd(r["tx_date"]),
        "tx_time":     (r["created_at"] or "")[11:16],
        "tx_type":     r["tx_type"],
        "category":    r["category"] or "",
        "note":        r["note"] or "",
        "mode":        r["mode"] or "",
        "amount":      r["amount"] or 0,
        "order_code":  r["order_code"] or "",
        "created_by":  r["created_by"] or ""
    } for r in rows]

    net = int((stats_r["income"] or 0) - (stats_r["expense"] or 0))
    return render_template("owner/finance.html",
        active_page="finance", show_voice=False,
        urgent_count=urgent_count,
        from_date=from_date, to_date=to_date,
        stats={
            "total_income":  int(stats_r["income"] or 0),
            "cash_income":   int(stats_r["cash_i"] or 0),
            "upi_income":    int(stats_r["upi_i"] or 0),
            "total_expense": int(stats_r["expense"] or 0),
            "expense_count": int(stats_r["exp_count"] or 0),
            "net":           net,
            "pending_due":   int(pending_due or 0)
        },
        transactions=transactions
    )


# ══════════════════════════════════════════════
#  WHATSAPP BROADCAST
# ══════════════════════════════════════════════

@bp.route("/whatsapp")
@owner_required
def whatsapp():
    conn = get_db()
    # Load all customers with due amounts and ready order flags
    rows = conn.execute("""
        SELECT c.id, c.name, c.mobile,
               COALESCE(SUM(o.remaining),0) as due,
               MAX(CASE WHEN o.status='ready' THEN 1 ELSE 0 END) as has_ready
        FROM customers c
        LEFT JOIN orders o ON o.customer_id=c.id AND o.status!='delivered'
        WHERE c.mobile IS NOT NULL AND c.mobile != ''
        GROUP BY c.id ORDER BY c.name
    """).fetchall()

    customers = [{"id":r["id"],"name":r["name"],"mobile":r["mobile"] or "",
                  "due":r["due"] or 0,"has_ready":r["has_ready"] or 0}
                 for r in rows]

    # Recent broadcast log
    logs_raw = conn.execute("""
        SELECT message_type, COUNT(*) as count, MAX(sent_at) as sent_at
        FROM whatsapp_log GROUP BY message_type ORDER BY MAX(sent_at) DESC LIMIT 10
    """).fetchall()

    def fmtd(d):
        if not d: return "—"
        p = str(d).split("-")
        return f"{p[2]}-{p[1]}-{p[0]}" if len(p)==3 else d

    broadcast_log = [{"message_type":r["message_type"],"count":r["count"],
                      "sent_at_fmt":fmtd((r["sent_at"] or "")[:10])} for r in logs_raw]

    urgent_count = conn.execute(
        "SELECT COUNT(*) as c FROM orders WHERE is_urgent=1 AND status!='delivered'"
    ).fetchone()["c"]
    shop_name = get_setting("shop_name","Uttam Tailors")
    conn.close()

    # Template definitions (names only for Jinja, messages in JS)
    # Load saved custom order confirmation message templates from settings
    order_confirm_tpl_en = get_setting("wa_order_confirm_en",
        "*{shop}* - Order Confirmed\n\nHello {name}!\n\n---\nOrder No: *#{code}*\nCustomer: {name}\nMobile: {mobile}\nOrder Date: {order_date}\nDelivery Date: *{delivery_date}*\n\nGarments: {items}\n---\nTotal: Rs. {total}\nAdvance Paid: Rs. {advance}\nRemaining Due: Rs. {remaining}\nMode: {mode}\n\nThank you for choosing {shop}!")
    order_confirm_tpl_hi = get_setting("wa_order_confirm_hi",
        "*{shop}* - ऑर्डर पक्का हो गया\n\nनमस्ते {name} जी!\n\n---\nऑर्डर नंबर: *#{code}*\nग्राहक: {name}\nमोबाइल: {mobile}\nऑर्डर दिनांक: {order_date}\nडिलीवरी दिनांक: *{delivery_date}*\n\nकपड़े: {items}\n---\nकुल राशि: Rs. {total}\nअग्रिम: Rs. {advance}\nबकाया: Rs. {remaining}\nभुगतान: {mode}\n\n{shop} में आने का धन्यवाद!")

    templates = [
        {"name":"Order Ready",      "icon":"🟢"},
        {"name":"Payment Due",      "icon":"💰"},
        {"name":"Festival Wishes",  "icon":"🎉"},
        {"name":"Eid Mubarak",      "icon":"🌙"},
        {"name":"New Collection",   "icon":"✨"},
        {"name":"Shop Closed",      "icon":"🚪"},
        {"name":"General Reminder", "icon":"📢"},
        {"name":"Diwali Wishes",    "icon":"🪔"},
    ]

    return render_template("owner/whatsapp.html",
        active_page="whatsapp", show_voice=False,
        urgent_count=urgent_count,
        customers=customers,
        customers_json=json.dumps(customers),
        shop_name=shop_name,
        templates=templates,
        broadcast_log=broadcast_log,
        order_confirm_tpl_en=order_confirm_tpl_en,
        order_confirm_tpl_hi=order_confirm_tpl_hi,
    )


@bp.route("/api/whatsapp-log", methods=["POST"])
@owner_required
def whatsapp_log():
    data  = request.get_json(silent=True) or {}
    count = data.get("count", 1)
    btype = data.get("type", "broadcast")
    now   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn  = get_db()
    # Log one entry per send session
    conn.execute(
        "INSERT INTO whatsapp_log(order_id,mobile,message_type,sent_at) VALUES(?,?,?,?)",
        (None, f"bulk:{count}", btype, now)
    )
    conn.commit(); conn.close()
    return jsonify({"ok":True})


# ══════════════════════════════════════════════
#  FINANCE CATEGORIES MANAGEMENT
# ══════════════════════════════════════════════

@bp.route("/api/finance-categories", methods=["GET"])
@owner_required
def get_finance_categories():
    income_cats  = get_setting("finance_income_cats",  "advance,payment,alteration,other income").split(",")
    expense_cats = get_setting("finance_expense_cats", "thread,buttons,fabric,electricity,rent,salary,transport,maintenance,other expense").split(",")
    return jsonify({
        "income":  [c.strip() for c in income_cats  if c.strip()],
        "expense": [c.strip() for c in expense_cats if c.strip()]
    })

@bp.route("/api/finance-categories/save", methods=["POST"])
@owner_required
def save_finance_categories():
    data    = request.get_json(silent=True) or {}
    cat_type = data.get("type","")   # "income" or "expense"
    cats    = data.get("categories", [])
    if cat_type not in ("income","expense"):
        return jsonify({"ok":False,"error":"Invalid type"})
    key = f"finance_{cat_type}_cats"
    set_setting(key, ",".join([c.strip() for c in cats if c.strip()]))
    return jsonify({"ok":True})


# ══════════════════════════════════════════════
#  ORDER CANCEL
# ══════════════════════════════════════════════

@bp.route("/orders/cancel/<order_code>", methods=["POST"])
@owner_required
def cancel_order(order_code):
    conn = get_db()
    conn.execute("UPDATE orders SET status='cancelled' WHERE order_code=?", (order_code,))
    conn.commit()
    conn.close()
    flash(f"Order #{order_code} cancelled.", "success")
    return redirect(request.referrer or url_for("owner.owner_dashboard"))


# ══════════════════════════════════════════════
#  WHATSAPP ORDER TEMPLATE SAVE
# ══════════════════════════════════════════════

@bp.route("/api/save-wa-template", methods=["POST"])
@owner_required
def save_wa_template():
    data = request.get_json(silent=True) or {}
    from database import set_setting
    if "en" in data:
        set_setting("wa_order_confirm_en", data["en"])
    if "hi" in data:
        set_setting("wa_order_confirm_hi", data["hi"])
    return jsonify({"ok": True})


# ══════════════════════════════════════════════
#  ORDER MANAGEMENT (Owner)
# ══════════════════════════════════════════════

@bp.route("/orders")
@owner_required
def owner_orders():
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT o.order_code, o.status, o.order_date, o.delivery_date,
                   COALESCE(o.payable_amount,0) as payable_amount,
                   COALESCE(o.remaining,0) as remaining,
                   COALESCE(o.is_urgent,0) as is_urgent,
                   COALESCE(o.note,'') as note,
                   COALESCE(c.name,'—') as cname, COALESCE(c.mobile,'') as mobile,
                   GROUP_CONCAT(oi.garment_type||' x'||oi.quantity, ', ') as garments_str
            FROM orders o
            LEFT JOIN customers c ON c.id=o.customer_id
            LEFT JOIN order_items oi ON oi.order_id=o.id
            GROUP BY o.id
            ORDER BY o.id DESC
        """).fetchall()
    except Exception as e:
        conn.close()
        return f"<h2>DB Error in /owner/orders</h2><pre>{e}</pre>", 500

    def fmtd(d):
        if not d: return "—"
        p = str(d).split("-")
        return f"{p[2]}-{p[1]}-{p[0]}" if len(p)==3 else d

    orders = [{
        "order_code":    r["order_code"],
        "status":        r["status"],
        "order_date":    fmtd(r["order_date"]),
        "delivery_date": fmtd(r["delivery_date"]),
        "payable":       r["payable_amount"] or 0,
        "remaining":     r["remaining"] or 0,
        "is_urgent":     r["is_urgent"],
        "note":          r["note"] or "",
        "cname":         r["cname"] or "—",
        "mobile":        r["mobile"] or "",
        "garments":      r["garments_str"] or "—"
    } for r in rows]

    urgent_count = conn.execute(
        "SELECT COUNT(*) as c FROM orders WHERE is_urgent=1 AND status!='delivered'"
    ).fetchone()["c"]
    conn.close()
    return render_template("owner/orders.html",
        active_page="owner_orders", show_voice=False,
        urgent_count=urgent_count, orders=orders, total=len(orders))


# ══════════════════════════════════════════════
#  ORDER DELETE (Owner)
# ══════════════════════════════════════════════

@bp.route("/orders/delete/<order_code>", methods=["POST"])
@owner_required
def delete_order(order_code):
    conn = get_db()
    order = conn.execute("SELECT id FROM orders WHERE order_code=?", (order_code,)).fetchone()
    if order:
        conn.execute("DELETE FROM work_logs WHERE order_id=?", (order["id"],))
        conn.execute("DELETE FROM order_items WHERE order_id=?", (order["id"],))
        conn.execute("DELETE FROM finance WHERE order_id=?", (order["id"],))
        conn.execute("DELETE FROM orders WHERE id=?", (order["id"],))
        conn.commit()
        flash(f"Order #{order_code} deleted permanently.", "success")
    else:
        flash(f"Order #{order_code} not found.", "error")
    conn.close()
    return redirect(request.referrer or url_for("owner.owner_dashboard"))


# ══════════════════════════════════════════════
#  CUSTOMER DETAIL (Owner)
# ══════════════════════════════════════════════

@bp.route("/customers/<int:customer_id>")
@owner_required
def owner_customer_detail(customer_id):
    conn = get_db()
    cust = conn.execute("SELECT * FROM customers WHERE id=?", (customer_id,)).fetchone()
    if not cust:
        conn.close()
        return "Customer not found", 404

    orders = conn.execute("""
        SELECT o.*, GROUP_CONCAT(oi.garment_type||' x'||oi.quantity, ', ') as garments_str
        FROM orders o LEFT JOIN order_items oi ON oi.order_id=o.id
        WHERE o.customer_id=? GROUP BY o.id ORDER BY o.id DESC
    """, (customer_id,)).fetchall()

    def fmtd(d):
        if not d: return "—"
        p = str(d).split("-")
        return f"{p[2]}-{p[1]}-{p[0]}" if len(p)==3 else d

    urgent_count = conn.execute(
        "SELECT COUNT(*) as c FROM orders WHERE is_urgent=1 AND status!='delivered'"
    ).fetchone()["c"]
    conn.close()

    orders_list = [{
        "order_code":       o["order_code"],
        "status":           o["status"],
        "order_date_fmt":   fmtd(o["order_date"]),
        "delivery_date_fmt":fmtd(o["delivery_date"]),
        "payable_amount":   o["payable_amount"] or 0,
        "advance_paid":     o["advance_paid"] or 0,
        "remaining":        o["remaining"] or 0,
        "is_urgent":        o["is_urgent"],
        "note":             o["note"] or "",
        "garments_str":     o["garments_str"] or "",
    } for o in orders]

    total_billed = sum(o["payable_amount"] for o in orders_list)
    total_due    = sum(o["remaining"] for o in orders_list)

    return render_template("owner/customer_detail.html",
        active_page="customers", show_voice=False,
        urgent_count=urgent_count,
        cust={"id":cust["id"],"name":cust["name"],"mobile":cust["mobile"] or "",
              "address":cust["address"] or ""},
        orders=orders_list,
        total_billed=int(total_billed), total_due=int(total_due)
    )


# ══════════════════════════════════════════════
#  CUSTOMER EDIT (Owner)
# ══════════════════════════════════════════════

@bp.route("/customers/<int:customer_id>/edit", methods=["POST"])
@owner_required
def owner_customer_edit(customer_id):
    name    = request.form.get("name","").strip()
    mobile  = request.form.get("mobile","").strip()
    address = request.form.get("address","").strip()
    if not name:
        flash("Name is required", "error")
        return redirect(url_for("owner.owner_customer_detail", customer_id=customer_id))
    conn = get_db()
    conn.execute("UPDATE customers SET name=?,mobile=?,address=? WHERE id=?",
                 (name, mobile, address, customer_id))
    conn.commit()
    conn.close()
    flash("Customer updated!", "success")
    return redirect(url_for("owner.owner_customer_detail", customer_id=customer_id))


@bp.route("/notify-log")
@owner_required
def notify_log_view():
    """Owner sees all WhatsApp notifies sent."""
    conn = get_db()
    logs = conn.execute(
        "SELECT * FROM notify_log ORDER BY sent_at DESC"
    ).fetchall()
    urgent_count = conn.execute(
        "SELECT COUNT(*) as c FROM orders WHERE is_urgent=1 AND status!='delivered'"
    ).fetchone()["c"]
    conn.close()

    def fmtdt(d):
        if not d: return "—"
        parts = str(d).split(" ")
        dp = parts[0].split("-") if parts else []
        date_fmt = f"{dp[2]}-{dp[1]}-{dp[0]}" if len(dp)==3 else parts[0]
        time_fmt = parts[1][:5] if len(parts)>1 else ""
        return f"{date_fmt} {time_fmt}"

    log_list = [{"order_code":r["order_code"],"customer":r["customer"],
                 "mobile":r["mobile"],"lang":r["lang"].upper(),"sent_at":fmtdt(r["sent_at"])}
                for r in logs]
    return render_template("owner/notify_log.html",
        active_page="whatsapp", show_voice=False,
        urgent_count=urgent_count, logs=log_list)


# ══════════════════════════════════════════════
#  SALARY MODULE
# ══════════════════════════════════════════════

@bp.route("/salary")
@owner_required
def salary():
    conn = get_db()
    period = request.args.get("period","month")
    today  = date.today().isoformat()

    if period == "week":
        from datetime import timedelta as td
        start = (date.today() - timedelta(days=date.today().weekday())).isoformat()
        period_label = f"This week ({start[8:]}-{start[5:7]} to {today[8:]}-{today[5:7]})"
    elif period == "all":
        start = "2000-01-01"
        period_label = "All time"
    else:
        period = "month"
        start = today[:7] + "-01"
        period_label = date.today().strftime("%B %Y")

    emps = conn.execute("SELECT name FROM employees WHERE active=1 ORDER BY name").fetchall()
    advances_all = conn.execute(
        "SELECT * FROM salary_advances ORDER BY advance_date DESC"
    ).fetchall()

    employees = []
    for emp in emps:
        name = emp["name"]
        logs = conn.execute("""
            SELECT order_code, garment_type, qty_done, making_rate, log_date,
                   CAST(qty_done AS REAL) * CAST(making_rate AS REAL) as earning
            FROM work_logs
            WHERE employee_name=? AND log_date >= ?
            ORDER BY log_date DESC, id DESC
        """, (name, start)).fetchall()

        total_earned  = sum(r["earning"] or 0 for r in logs)
        total_pieces  = sum(r["qty_done"] or 0 for r in logs)
        total_orders  = len(set(r["order_code"] for r in logs if r["order_code"]))

        adv_period = conn.execute(
            "SELECT COALESCE(SUM(amount),0) as total FROM salary_advances WHERE employee_name=? AND advance_date >= ?",
            (name, start)
        ).fetchone()["total"] or 0

        employees.append({
            "name":         name,
            "total_pieces": total_pieces,
            "total_orders": total_orders,
            "total_earned": total_earned,
            "total_advance":adv_period,
            "net_payable":  total_earned - adv_period,
            "logs": [{"order_code":r["order_code"],"garment_type":r["garment_type"],
                      "qty_done":r["qty_done"],"earning":r["earning"] or 0,
                      "log_date":r["log_date"]} for r in logs]
        })

    def fmtd(d):
        if not d: return "—"
        p = str(d).split("-")
        return f"{p[2]}-{p[1]}-{p[0]}" if len(p)==3 else d

    advances = [{"employee_name":a["employee_name"],"amount":a["amount"],
                 "note":a["note"] or "","advance_date":fmtd(a["advance_date"])} for a in advances_all]

    urgent_count = conn.execute(
        "SELECT COUNT(*) as c FROM orders WHERE is_urgent=1 AND status!='delivered'"
    ).fetchone()["c"]
    conn.close()

    return render_template("owner/salary.html",
        active_page="salary", show_voice=False,
        urgent_count=urgent_count,
        employees=employees, advances=advances,
        period=period, period_label=period_label)


@bp.route("/api/salary/advance", methods=["POST"])
@owner_required
def api_salary_advance():
    data   = request.get_json(silent=True) or {}
    name   = data.get("employee_name","").strip()
    amount = float(data.get("amount",0) or 0)
    note   = data.get("note","").strip()
    if not name or amount <= 0:
        return jsonify({"ok":False,"error":"Name and amount required"})
    today = date.today().isoformat()
    now   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn  = get_db()
    conn.execute(
        "INSERT INTO salary_advances(employee_name,amount,note,advance_date,created_at) VALUES(?,?,?,?,?)",
        (name, amount, note, today, now)
    )
    conn.commit(); conn.close()
    return jsonify({"ok":True})


@bp.route("/api/save-setting", methods=["POST"])
@owner_required
def api_save_setting():
    data  = request.get_json(silent=True) or {}
    key   = data.get("key","").strip()
    value = data.get("value","").strip()
    if not key:
        return jsonify({"ok":False,"error":"No key"})
    set_setting(key, value)
    return jsonify({"ok":True})


@bp.route("/api/employee-skill", methods=["POST"])
@owner_required
def api_employee_skill():
    data   = request.get_json(silent=True) or {}
    emp_id = data.get("employee_id")
    skills = data.get("skills","stitch")
    if not emp_id:
        return jsonify({"ok":False,"error":"No employee id"})
    conn = get_db()
    conn.execute("UPDATE employees SET skills=? WHERE id=?", (skills, emp_id))
    conn.commit(); conn.close()
    return jsonify({"ok":True})
