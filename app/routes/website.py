from flask import Blueprint, render_template, abort, request, jsonify, redirect, url_for, session, current_app
from database import get_db
from datetime import date, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

website_bp = Blueprint("website", __name__)

FREE_PREVIEW_LIMIT = 1   # Anonymous visitors get 1 free preview, then must sign up

# ── Rate-limiter import ───────────────────────────────────────────────────────
# Imported from the shared singleton so no circular dependency with run.py.
from app.extensions import limiter as _limiter, LIMITER_AVAILABLE as _LIMITER_AVAILABLE

def _rl(limit_str):
    """Apply a rate-limit decorator only when flask-limiter is installed.
    Falls back to a no-op decorator so nothing breaks if the package is missing."""
    if _LIMITER_AVAILABLE and _limiter is not None:
        return _limiter.limit(limit_str)
    return lambda fn: fn  # no-op

# ── SEO helpers ──────────────────────────────────────────────────────────────
import re as _re_seo

def make_slug(text):
    s = (text or "").lower().strip()
    s = _re_seo.sub(r"[^a-z0-9\s-]", "", s)
    s = _re_seo.sub(r"[\s-]+", "-", s)
    return s.strip("-")

def get_page_seo(page_key, default_title="", default_desc="", robots="index,follow"):
    try:
        db = get_db()
        row = db.execute("SELECT * FROM seo_static_pages WHERE page_key=?", (page_key,)).fetchone()
        if row:
            return {
                "title": row["meta_title"] or default_title,
                "desc":  row["meta_desc"]  or default_desc,
                "og_image": _row_get(row, "og_image"),
                "robots": _row_get(row, "robots", robots) or robots,
                "canonical": _row_get(row, "canonical"),
            }
    except Exception: pass
    return {"title": default_title, "desc": default_desc, "og_image": "", "robots": robots, "canonical": ""}


def _cat_icon(name):
    n = (name or "").lower()
    for kw, ico in CATEGORY_ICON_RULES:
        if kw in n:
            return ico
    return "\U0001F9F5"  # 🧵 default

def get_categories_grouped():
    """Returns [{id,name,icon,garments:[{id,name,price,image_url}]}] using the real
    web_service_categories / web_service_items tables (admin-managed)."""
    try:
        db = get_db()
        cats = db.execute("SELECT id, name FROM web_service_categories ORDER BY sort_order, id").fetchall()
        items = db.execute("SELECT id, category_id, name, price, image_url FROM web_service_items ORDER BY sort_order, id").fetchall()
        by_cat = {}
        for it in items:
            by_cat.setdefault(it["category_id"], []).append(
                {"id": it["id"], "name": it["name"], "price": it["price"], "image_url": it["image_url"] or ""})
        grouped = []
        for c in cats:
            its = by_cat.get(c["id"], [])
            if not its:
                continue
            grouped.append({"id": c["id"], "name": c["name"], "icon": _cat_icon(c["name"]), "garments": its})
        return grouped
    except Exception:
        return []


def get_auto_categories(db_items):
    """Auto-group all db_items into tabs by name keywords — always shows ALL garments."""
    import re
    cats = [
        ('shirts',   'Shirts',            lambda n: bool(re.search(r'shirt', n, re.I))),
        ('ethnic',   'Ethnic wear',       lambda n: bool(re.search(r'kurta|pathani', n, re.I))),
        ('suits',    'Suits & Sets',      lambda n: bool(re.search(r'suit|blazer|\d[\s\-]?piece|safari', n, re.I))),
        ('trousers', 'Pants',  lambda n: bool(re.search(r'pant|jean|trouser|\bfit\b|cut|leg|baggy|skinny|tapered|relaxed|regular|wide|cigarette|slim|straight|boot', n, re.I))),
        ('ethnic2',  'Ethnic wear',       lambda n: bool(re.search(r'pajama|pathani', n, re.I))),
        ('other',    'Other',             lambda n: True),
    ]
    used = set()
    result = []
    # Merge ethnic cats
    merged = [
        ('shirts',   'Shirts',           lambda n: bool(re.search(r'shirt', n, re.I))),
        ('ethnic',   'Ethnic wear',      lambda n: bool(re.search(r'kurta|pathani|pajama set', n, re.I))),
        ('suits',    'Suits & Sets',     lambda n: bool(re.search(r'suit|blazer|\d[\s\-]?piece|safari', n, re.I))),
        ('trousers', 'Pants', lambda n: bool(re.search(r'pant|jean|trouser|\bfit\b|cut|leg|baggy|skinny|tapered|relaxed|regular|wide|cigarette|slim|straight|boot', n, re.I))),
        ('other',    'Other',            lambda n: True),
    ]
    for cat_id, cat_name, test in merged:
        garments = [dict(i) for i in db_items if i['id'] not in used and test(i['name'])]
        if garments:
            for g in garments:
                used.add(g['id'])
            result.append({'id': cat_id, 'name': cat_name, 'icon': '', 'garments': garments})
    return result


def get_commission_settings():
    """Returns all commission page settings from the settings table."""
    try:
        db = get_db()
        rows = db.execute("SELECT key, value FROM settings WHERE key LIKE 'commission_%'").fetchall()
        s = {r["key"]: r["value"] for r in rows}
        return {
            "header_image":    s.get("commission_header_image", ""),
            "header_kicker":   s.get("commission_header_kicker", "Customise your garment"),
            "header_title":    s.get("commission_header_title", "Place your order"),
            "header_sub":      s.get("commission_header_sub", "Bring your fabric \u2014 we craft the perfect fit. WhatsApp updates at every step."),
            "step1_title":     s.get("commission_step1_title", "Choose your garment"),
            "step1_sub":       s.get("commission_step1_sub", "Select a category and item \u2014 add as many garments as you like to one order."),
            "step2_title":     s.get("commission_step2_title", "How shall we measure you?"),
            "step2_sub":       s.get("commission_step2_sub", "Choose the method easiest for you."),
            "step3_title":     s.get("commission_step3_title", "Your style picks"),
            "step3_sub":       s.get("commission_step3_sub", "Here's a recap of the fabric and look you chose for each garment — tap to revise anytime."),
            "step4_title":     s.get("commission_step4_title", "Style and finishing"),
            "step4_sub":       s.get("commission_step4_sub", "Customise the details of your garment."),
            "step5_title":     s.get("commission_step5_title", "Delivery preference & date"),
            "step5_sub":       s.get("commission_step5_sub", "Pick when you need it \u2014 we plan the craft around your date."),
            "step6_title":     s.get("commission_step6_title", "Your contact details"),
            "step6_sub":       s.get("commission_step6_sub", "No account needed. We send updates on WhatsApp."),
            "summary_title":   s.get("commission_summary_title", "Order Summary"),
            "trust_pill_1":    s.get("commission_trust_1", "Free alteration if fit is not right"),
            "trust_pill_2":    s.get("commission_trust_2", "WhatsApp updates at every step"),
            "trust_pill_3":    s.get("commission_trust_3", "35+ years of master craft"),
            "trust_pill_4":    s.get("commission_trust_4", "Rs. 100 off your first order"),
            "urgent_title":    s.get("commission_urgent_title", "Urgent order"),
            "urgent_sub":      s.get("commission_urgent_sub", "+Rs. 99 extra \u2022 Delivered in 1\u20133 days (simple items only)"),
            "advance_pct":     int(s.get("commission_advance_pct", "30") or 30),
        }
    except Exception:
        return {}

GARMENTS = {
    "shirt":"Formal Shirt","pant":"Pant","trouser":"Pants",
    "suit":"Two-Piece Suit","suit3pc":"Three-Piece Suit","blazer":"Blazer",
    "kurta":"Kurta only","kurtaset":"Kurta + Pajama","pathani":"Pathani Suit",
    "safari":"Safari Suit","jeans":"Jeans","pajama":"Pajama",
}

def get_settings():
    db = get_db()
    cur = db.execute("SELECT key, value FROM settings")
    rows = cur.fetchall()
    s = {r['key']: r['value'] for r in rows}
    return {
        'addr1':           s.get('web_addr1',          'Subhash Chowk, Sikar'),
        'addr2':           s.get('web_addr2',          'Rajasthan — 332001'),
        'phone':           s.get('web_shop_phone',     '+91 XXXXX XXXXX'),
        'email':           s.get('web_shop_email',     'info.uttamtailors@gmail.com'),
        'hours':           s.get('web_shop_hours',     'Monday – Saturday · 9am – 7pm'),
        'wa_link':         s.get('web_whatsapp_link',  'https://wa.me/91XXXXXXXXXX'),
        'delivery_charge': s.get('web_delivery_charge','49'),
        'turnaround_days': s.get('web_turnaround_days','7'),
    }

def get_fabrics():
    try:
        db = get_db()
        cur = db.execute("SELECT * FROM web_fabrics WHERE active=1 ORDER BY sort_order")
        rows = cur.fetchall()
        try:
            media_rows = db.execute("SELECT fabric_id, url FROM web_fabric_media ORDER BY fabric_id, sort_order").fetchall()
        except Exception:
            media_rows = []
        gallery_map = {}
        for m in media_rows:
            gallery_map.setdefault(m["fabric_id"], []).append(m["url"])
        out = []
        for f in rows:
            d = dict(f)
            gal = []
            if d.get("image_url"):
                gal.append(d["image_url"])
            for u in gallery_map.get(d["id"], []):
                if u and u not in gal:
                    gal.append(u)
            d["gallery"] = gal[:4]
            out.append(d)
        return out
    except:
        return []

def get_item_media():
    """Returns {item_id: {images:[...], video:url}} from web_item_media table.
    Falls back to image_url/video_url columns on web_service_items."""
    try:
        db = get_db()
        # Primary: web_item_media table
        media_rows = db.execute("SELECT * FROM web_item_media ORDER BY item_id, sort_order").fetchall()
        result = {}
        for row in media_rows:
            iid = row["item_id"]
            if iid not in result:
                result[iid] = {"images": [], "video": ""}
            if row["media_type"] == "video":
                result[iid]["video"] = row["url"]
            else:
                result[iid]["images"].append(row["url"])
        # Fallback: if item has image_url but no media entry, use it
        items = db.execute("SELECT id, image_url, video_url FROM web_service_items").fetchall()
        for item in items:
            iid = item["id"]
            if iid not in result:
                result[iid] = {"images": [], "video": ""}
            if item["image_url"] and not result[iid]["images"]:
                result[iid]["images"].append(item["image_url"])
            if item["video_url"] and not result[iid]["video"]:
                try:
                    result[iid]["video"] = item["video_url"]
                except:
                    pass
        return result
    except:
        return {}

# Key mapping: garment_key → DB item name patterns
KEY_TO_NAMES = {
    "shirt":    ["formal shirt", "shirt"],
    "pant":     ["pant", "trouser", "trousers"],
    "suit":     ["suit 2-piece", "suit 2pc", "two-piece suit"],
    "suit3pc":  ["suit 3-piece", "suit 3pc", "three-piece suit"],
    "blazer":   ["blazer"],
    "kurta":    ["kurta only", "kurta"],
    "kurtaset": ["kurta + pajama", "kurta pajama set", "kurta + pajama set"],
    "pajama":   ["pajama only", "pajama"],
    "pathani":  ["pathani suit", "pathani"],
    "safari":   ["safari suit", "safari"],
    "jeans":    ["jeans"],
}

DEFAULT_PRICES = {
    "shirt":450,"pant":550,"suit":2900,"suit3pc":3600,
    "blazer":2400,"kurta":500,"kurtaset":900,"pajama":450,
    "pathani":550,"safari":1200,"jeans":650
}

def get_prices():
    """Fetch garment prices from web_service_items DB. Falls back to defaults."""
    try:
        db = get_db()
        items = db.execute("SELECT name, price FROM web_service_items").fetchall()
        # Build name→price map
        name_price = {row["name"].lower().strip(): row["price"] for row in items}
        prices = {}
        for key, names in KEY_TO_NAMES.items():
            p = None
            for n in names:
                if n in name_price:
                    try: p = int(float(name_price[n]))
                    except: p = None
                    break
            prices[key] = p if p else DEFAULT_PRICES.get(key, 500)
        return prices
    except:
        return DEFAULT_PRICES.copy()

def _current_account():
    """Return the logged-in web_accounts row from session, or None."""
    acc_id = session.get("web_account_id")
    if not acc_id:
        return None
    try:
        return get_db().execute(
            "SELECT * FROM web_accounts WHERE id=? AND is_active=1", (acc_id,)
        ).fetchone()
    except Exception:
        return None


@website_bp.route("/favicon.ico")
def favicon():
    """Serve favicon.ico — Google & browsers look here first."""
    from flask import redirect
    from database import get_db
    db = get_db()
    row = db.execute("SELECT value FROM settings WHERE key='web_favicon_url'").fetchone()
    if row and row[0]:
        return redirect(row[0], code=302)
    # Fallback: 204 No Content (avoids 404 noise in logs)
    from flask import Response
    return Response(status=204)


@website_bp.route("/")
def home():
    import json as _json
    prices = get_prices()
    item_media = get_item_media()
    try:
        db = get_db()
        items = db.execute("SELECT id, name FROM web_service_items").fetchall()
        img_map = {}
        for item in items:
            m = item_media.get(item["id"], {})
            imgs = m.get("images", [])
            if imgs: img_map[item["name"].lower()] = imgs[0]
    except: img_map = {}
    try:
        db_all = db.execute("SELECT * FROM web_service_items ORDER BY sort_order, id").fetchall()
    except:
        db_all = []
    # Load homepage sections
    hs = {}
    hs_active = {}
    try:
        rows = db.execute("SELECT section_key,content,active,sort_order FROM home_sections ORDER BY sort_order").fetchall()
        # Keys that always load (images/media used even when section is inactive)
        _always_load = {"bring_inspo", "ai_preview"}
        for r in rows:
            hs_active[r["section_key"]] = bool(r["active"])
            if r["active"] or r["section_key"] in _always_load:
                try: hs[r["section_key"]] = _json.loads(r["content"])
                except: hs[r["section_key"]] = {}
    except: pass
    # (section seeding moved to init_db — no longer runs on every request)
    # Catalogue items from admin selection
    cat_ids = []
    if hs.get("catalogue",{}).get("item_ids"):
        try: cat_ids = [int(x.strip()) for x in hs["catalogue"]["item_ids"].split(",") if x.strip()]
        except: pass
    if cat_ids:
        placeholders = ",".join(["?"]*len(cat_ids))
        try: cat_items = db.execute(f"SELECT w.*, c.name AS cat_name FROM web_service_items w LEFT JOIN web_service_categories c ON c.id=w.category_id WHERE w.id IN ({placeholders})", cat_ids).fetchall()
        except: cat_items = db_all[:6]
    else:
        cat_items = db_all[:6]
    # Live shop status
    live_stats = {"active_count": 0}
    try:
        r = db.execute("SELECT COUNT(*) as cnt FROM orders WHERE status IN ('pending','ready')").fetchone()
        live_stats["active_count"] = r["cnt"] if r else 0
    except: pass
    item_media_home = get_item_media()
    # All categories + items for pricing section
    pricing_cats = []
    try:
        all_cats = db.execute("SELECT id, name FROM web_service_categories ORDER BY sort_order, id").fetchall()
        for cat in all_cats:
            cat_products = db.execute(
                "SELECT id, name, price, image_url FROM web_service_items WHERE category_id=? ORDER BY sort_order, id",
                (cat["id"],)
            ).fetchall()
            if cat_products:
                raw_name = cat["name"]
                # Skip alterations & repairs
                if _re_seo.search(r'alteration|repair', raw_name, _re_seo.I):
                    continue
                # "Trousers & Jeans" or "Pants & Jeans" → just "Jeans"
                if _re_seo.search(r'(pant|trouser).{0,10}jean|jean.{0,10}(pant|trouser)', raw_name, _re_seo.I):
                    display_name = "Jeans"
                else:
                    display_name = _re_seo.sub(r'\bTrousers\b', 'Pants', raw_name)
                    display_name = _re_seo.sub(r'\bTrouser\b', 'Pant', display_name)
                pricing_cats.append({"name": display_name, "products": [dict(p) for p in cat_products]})
        # Also grab uncategorized items
        uncat = db.execute(
            "SELECT id, name, price, image_url FROM web_service_items WHERE category_id IS NULL ORDER BY sort_order, id"
        ).fetchall()
        if uncat:
            pricing_cats.append({"name": "Other", "products": [dict(p) for p in uncat]})
        # Move "Formal Pants" (or any pant category) to 3rd position (index 2)
        fp_idx = next((i for i, c in enumerate(pricing_cats)
                       if _re_seo.search(r'formal.*pant|pant.*formal|formal.*pan|^pants?$', c['name'], _re_seo.I)), None)
        if fp_idx is not None and fp_idx != 2 and len(pricing_cats) > 2:
            pricing_cats.insert(2, pricing_cats.pop(fp_idx))
    except:
        pricing_cats = []
    page_meta = get_page_seo("home",
        "Uttam Tailors — Custom Tailoring in Sikar since 1987",
        "Custom shirts, suits, kurtas & more stitched in Sikar. Order online. Free delivery.")
    return render_template("website/home.html", active="home",
        home_items=cat_items, item_media=item_media_home, prices=prices, img_map=img_map, hs=hs,
        hs_active=hs_active,
        live_stats=live_stats, page_meta=page_meta, pricing_cats=pricing_cats)

@website_bp.route("/our-story")
def about():
    from database import get_db
    db = get_db()
    # Get settings
    rows = db.execute("SELECT key, value FROM settings WHERE key LIKE 'about_%'").fetchall()
    raw = {r["key"].replace("about_",""):r["value"] for r in rows}

    class S: pass
    s = S()
    s.hero_title   = raw.get("hero_title", "")
    s.hero_sub     = raw.get("hero_sub", "")
    s.hero_kicker  = raw.get("hero_kicker", "")
    s.hero_img     = raw.get("hero_img", "")
    s.cta_title    = raw.get("cta_title", "")
    s.cta_sub      = raw.get("cta_sub", "")
    for i in range(1,5):
        setattr(s, f"promise{i}_title", raw.get(f"promise{i}_title",""))
        setattr(s, f"promise{i}_body",  raw.get(f"promise{i}_body",""))

    # Get timeline
    try:
        timeline = db.execute("SELECT * FROM web_story_timeline ORDER BY sort_order, year").fetchall()
    except:
        timeline = []

    from builtins import enumerate as _enum
    page_meta = get_page_seo("about",
        "Our Story — Uttam Tailors, Sikar since 1987",
        "37 years of master tailoring in Sikar. Learn about the craft and legacy of Uttam Tailors.")
    return render_template("website/about.html", active="about", s=s, timeline=timeline, enumerate=_enum,
        page_meta=page_meta)

@website_bp.route("/our-craft")
def services():
    try:
        db = get_db()
        cats = db.execute("SELECT * FROM web_service_categories ORDER BY sort_order, id").fetchall()
        items = db.execute("SELECT * FROM web_service_items ORDER BY sort_order, id").fetchall()
        items_by_cat = {}
        for item in items:
            cid = item["category_id"]
            if cid not in items_by_cat: items_by_cat[cid] = []
            items_by_cat[cid].append(item)
        services_data = [(cat, items_by_cat.get(cat["id"], [])) for cat in cats]
    except: services_data = []
    prices = get_prices()
    item_media = get_item_media()
    # Build fabric_image map {item_id: url}
    try:
        fabric_imgs = {}
        db2 = get_db()
        frows = db2.execute("SELECT id, fabric_image_url FROM web_service_items").fetchall()
        for r in frows:
            if r["fabric_image_url"]: fabric_imgs[r["id"]] = r["fabric_image_url"]
    except Exception:
        fabric_imgs = {}
    page_meta = get_page_seo("our_craft",
        "Custom Tailoring — Our Craft | Uttam Tailors Sikar",
        "Browse our full range of custom tailoring services in Sikar. Suits, shirts, kurtas, pathani & more.")
    breadcrumbs = [("Our Craft", "/our-craft")]
    return render_template("website/services.html", active="services", services=services_data, prices=prices, item_media=item_media,
        fabric_imgs=fabric_imgs, page_meta=page_meta, breadcrumbs=breadcrumbs)

@website_bp.route("/our-services")
def our_services():
    # Canonical page is /our-craft — permanent redirect for SEO
    return redirect("/our-craft", 301)


@website_bp.route("/garment/<int:item_id>")
def product_detail(item_id):
    """Legacy numeric URL — 301 redirect to slug."""
    try:
        row = get_db().execute("SELECT slug FROM web_service_items WHERE id=?", (item_id,)).fetchone()
        if row and row["slug"]:
            from flask import redirect as _redir
            return _redir(f"/garment/{row['slug']}", 301)
    except Exception: pass
    return _render_product(item_id)

@website_bp.route("/garment/<slug>")
def product_by_slug(slug):
    """SEO-friendly product page."""
    try:
        row = get_db().execute("SELECT id FROM web_service_items WHERE slug=?", (slug,)).fetchone()
        if row: return _render_product(row["id"])
    except Exception: pass
    abort(404)

def _row_get(row, key, default=""):
    """sqlite3.Row doesn't support .get() — safe lookup that won't blow up on missing columns."""
    try:
        val = row[key]
        return val if val not in (None, "") else default
    except Exception:
        return default

def _render_product(item_id):
    """Render product detail page with full SEO."""
    try:
        db = get_db()
        item = db.execute("SELECT i.*, c.name as cat_name FROM web_service_items i LEFT JOIN web_service_categories c ON i.category_id=c.id WHERE i.id=?", (item_id,)).fetchone()
        if not item: return "Not found", 404
        media_rows = db.execute("SELECT * FROM web_item_media WHERE item_id=? ORDER BY sort_order", (item_id,)).fetchall()
        images = [r["url"] for r in media_rows if r["media_type"] == "image"]
        videos = [r["url"] for r in media_rows if r["media_type"] == "video"]
        if not images and item["image_url"]: images = [item["image_url"]]
        try:
            reviews = db.execute("SELECT * FROM web_item_reviews WHERE item_id=? ORDER BY id DESC", (item_id,)).fetchall()
        except: reviews = []
        try:
            related = db.execute("""SELECT i.*, c.name as cat_name FROM web_service_items i
                LEFT JOIN web_service_categories c ON i.category_id=c.id
                WHERE i.category_id != ? AND i.id != ? LIMIT 4""", (item["category_id"], item_id)).fetchall()
        except: related = []
        try:
            style_options_rows = db.execute("SELECT * FROM garment_style_options WHERE item_id=? ORDER BY sort_order,id", (item_id,)).fetchall()
            style_options = {}
            # style_value_images: {group: {value_label: image_url}} — for image chips
            style_value_images = {}
            for r in style_options_rows:
                g = r["option_group"]
                if g not in style_options:
                    # Try to load per-value rows (new system with image_url + ai_prompt)
                    try:
                        val_rows = db.execute(
                            "SELECT value_label, image_url FROM garment_style_values WHERE option_id=? ORDER BY sort_order,id",
                            (r["id"],)
                        ).fetchall()
                    except Exception:
                        val_rows = []
                    if val_rows:
                        vals = [v["value_label"] for v in val_rows if v["value_label"]]
                        imgs = {v["value_label"]: v["image_url"] for v in val_rows if v.get("image_url")}
                        if imgs:
                            style_value_images[g] = imgs
                    else:
                        # Fallback: comma-split from option_values column
                        vals = [x.strip() for x in (r["option_values"] or "").split(",") if x.strip()]
                    style_options[g] = {"label": r["option_label"], "values": vals}
        except Exception:
            style_options = {}
            style_value_images = {}
        try: item_tiles = db.execute("SELECT * FROM web_item_tiles WHERE item_id=? ORDER BY sort_order", (item_id,)).fetchall()
        except: item_tiles = []
        try: item_faq = db.execute("SELECT * FROM web_item_faq WHERE item_id=? ORDER BY sort_order", (item_id,)).fetchall()
        except: item_faq = []
        try: item_bullets = db.execute("SELECT * FROM web_item_bullets WHERE item_id=? ORDER BY sort_order", (item_id,)).fetchall()
        except: item_bullets = []
        # "Complete the Look" — admin-curated cross-sell (distinct from the same-category
        # fallback below, which is the "You May Also Like" section).
        try:
            complete_look = db.execute("""SELECT ri.related_item_id as id, i2.name, i2.price, i2.image_url
                FROM web_related_items ri JOIN web_service_items i2 ON ri.related_item_id = i2.id
                WHERE ri.item_id=? ORDER BY ri.sort_order""", (item_id,)).fetchall()
        except: complete_look = []
        # Answered customer Q&A (public-facing; pending ones stay hidden until an admin answers).
        try:
            questions = db.execute("SELECT * FROM web_item_questions WHERE item_id=? AND status='answered' ORDER BY id DESC", (item_id,)).fetchall()
        except: questions = []
        # AI-customize banner copy — detect the garment word from category+name so the
        # link reads "Customize this shirt with AI" instead of a generic "this".
        import re as _re
        _GARMENT_WORDS = [
            (r'shirt', 'shirt', False), (r'suit', 'suit', False), (r'blazer', 'blazer', False),
            (r'kurta', 'kurta', False), (r'sherwani', 'sherwani', False), (r'waistcoat|vest', 'waistcoat', False),
            (r'jean', 'jeans', True), (r'trouser|pant', 'trousers', True), (r'coat', 'coat', False),
            (r'dress', 'dress', False), (r'jacket', 'jacket', False),
        ]
        _hay = ((item["cat_name"] or "") + " " + (item["name"] or "")).lower()
        ai_garment_phrase = "this garment"
        for _pat, _word, _plural in _GARMENT_WORDS:
            if _re.search(_pat, _hay):
                ai_garment_phrase = ("these " if _plural else "this ") + _word
                break
        # Filter fabrics by category (fabric_type matches category keywords)
        cat_name = (item["cat_name"] or "").lower()
        all_fabrics = get_fabrics()
        if "shirt" in cat_name or "kurta" in cat_name or "pathani" in cat_name or "safari" in cat_name:
            cat_key = "shirt"
        elif "trouser" in cat_name or "pant" in cat_name or "jeans" in cat_name:
            cat_key = "pant"
        elif "suit" in cat_name or "blazer" in cat_name:
            cat_key = "suit"
        else:
            cat_key = None
        fabrics = [f for f in all_fabrics if not cat_key or not f["fabric_type"] or f["fabric_type"]==cat_key or f["fabric_type"]=="all"]
        if not fabrics: fabrics = all_fabrics  # fallback: show all
        # Build product SEO from item data + DB override
        _prod_title = _row_get(item, "meta_title") or f"{item['name']} — Custom Stitching in Sikar | Uttam Tailors"
        _prod_desc = _row_get(item, "meta_desc") or f"Get {item['name']} custom stitched in Sikar. {_row_get(item, 'subtitle') or 'Premium quality, perfect fit.'} Book online at Uttam Tailors."
        page_meta = {"title": _prod_title, "desc": _prod_desc, "robots": "index,follow",
                     "og_image": images[0] if images else "", "canonical": ""}
        return render_template("website/product.html", active="services",
            item=item, images=images, videos=videos,
            reviews=reviews, related=related, item_media=get_item_media(),
            style_options=style_options, style_value_images=style_value_images, fabrics=fabrics,
            item_tiles=item_tiles, item_faq=item_faq, item_bullets=item_bullets,
            complete_look=complete_look, questions=questions, ai_garment_phrase=ai_garment_phrase,
            page_meta=page_meta)
    except Exception as e:
        return f"Error: {e}", 500


@website_bp.route("/garment/ask/<int:item_id>", methods=["POST"])
@_rl("5 per minute; 20 per hour")
def ask_item_question(item_id):
    """Public Q&A submission — goes in as 'pending' and only appears on the page
    once an admin answers it from the product editor."""
    db = get_db()
    d = request.get_json() or {}
    name = (d.get("name") or "").strip()[:80]
    question = (d.get("question") or "").strip()[:500]
    if not question:
        return jsonify({"ok": False, "error": "Please type your question."})
    try:
        db.execute("INSERT INTO web_item_questions(item_id,name,question,status) VALUES(?,?,?,'pending')",
                   (item_id, name, question))
        db.commit()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@website_bp.route("/our-work")
def our_work():
    """Daily stitched clothes gallery page."""
    try:
        db = get_db()
        tag = request.args.get("tag", "").strip()
        page = max(1, int(request.args.get("page", 1)))
        per_page = 24
        offset = (page - 1) * per_page
        if tag:
            items = db.execute(
                "SELECT * FROM web_daily_craft WHERE is_published=1 AND tag=? ORDER BY id DESC LIMIT ? OFFSET ?",
                (tag, per_page, offset)
            ).fetchall()
            total = db.execute(
                "SELECT COUNT(*) FROM web_daily_craft WHERE is_published=1 AND tag=?", (tag,)
            ).fetchone()[0]
        else:
            items = db.execute(
                "SELECT * FROM web_daily_craft WHERE is_published=1 ORDER BY id DESC LIMIT ? OFFSET ?",
                (per_page, offset)
            ).fetchall()
            total = db.execute("SELECT COUNT(*) FROM web_daily_craft WHERE is_published=1").fetchone()[0]
        tags = db.execute(
            "SELECT DISTINCT tag FROM web_daily_craft WHERE is_published=1 AND tag!='' ORDER BY tag"
        ).fetchall()
        tags = [r["tag"] for r in tags]
        pages = max(1, (total + per_page - 1) // per_page)
    except Exception:
        items, tags, page, pages, tag = [], [], 1, 1, ""
    breadcrumbs = [("Fresh From The Workshop", "/our-work")]
    return render_template("website/our_work.html",
        active="our_work", items=items, tags=tags,
        current_tag=tag, page=page, pages=pages,
        breadcrumbs=breadcrumbs)

@website_bp.route("/api/daily-craft/latest")
def api_daily_craft_latest():
    """Return latest N published items for homepage section."""
    try:
        db = get_db()
        limit = min(12, int(request.args.get("n", 6)))
        rows = db.execute(
            "SELECT * FROM web_daily_craft WHERE is_published=1 ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return jsonify({"ok": True, "items": [dict(r) for r in rows]})
    except Exception as ex:
        return jsonify({"ok": False, "error": str(ex)})

@website_bp.route("/ai-customize")
def ai_customize():
    db = get_db()
    try:
        fabrics = [dict(f) for f in db.execute("SELECT id,name,image_url,fabric_type FROM web_fabrics WHERE active=1 ORDER BY sort_order").fetchall()]
    except Exception:
        fabrics = []
    try:
        items = [dict(i) for i in db.execute("SELECT id,name,image_url FROM web_service_items ORDER BY sort_order,id").fetchall()]
    except Exception:
        items = []
    acc = _current_account()
    init_tokens = None
    init_previews = None
    if acc:
        try:
            tok_row = db.execute("SELECT token_balance FROM web_accounts WHERE id=?", (acc["id"],)).fetchone()
            init_tokens = (tok_row["token_balance"] or 0) if tok_row else 0
        except Exception:
            init_tokens = 0
    else:
        from flask import session as _sess
        used = _sess.get("preview_count", 0)
        init_previews = max(0, FREE_PREVIEW_LIMIT - used)
    return render_template("website/ai_customize.html",
        fabrics=fabrics, items=items,
        init_tokens=init_tokens,
        init_previews=init_previews,
        logged_in_name=(acc["name"] if acc else ""),
        logged_in_mobile=(acc["mobile"] if acc else ""),
        page_meta={"title":"AI Style Studio — Uttam Tailors",
                   "desc":"Design your perfect custom garment with AI. See a photorealistic preview before ordering.",
                   "robots":"index,follow","og_image":"","canonical":""})


@website_bp.route("/privacy")
@website_bp.route("/privacy-policy")
def privacy_policy():
    return render_template("website/privacy.html")

@website_bp.route("/shipping")
@website_bp.route("/shipping-policy")
def shipping_policy():
    return render_template("website/shipping.html")

@website_bp.route("/terms")
@website_bp.route("/terms-and-conditions")
def terms_conditions():
    # No separate terms template — serve privacy page which covers legal info
    return render_template("website/privacy.html")

@website_bp.route("/refund")
@website_bp.route("/refund-policy")
def refund_policy():
    # No separate refund template — shipping page covers refund/return info
    return render_template("website/shipping.html")


@website_bp.route("/page/<slug>")
def custom_page(slug):
    db = get_db()
    try:
        page = db.execute("SELECT * FROM web_pages WHERE slug=?", (slug,)).fetchone()
    except:
        page = None
    if not page:
        abort(404)
    page_meta = {
        "title": (_row_get(page, "meta_title") or page["title"] + " — Uttam Tailors"),
        "desc": _row_get(page, "meta_desc"),
        "robots": "index,follow", "og_image": "", "canonical": ""
    }
    return render_template("website/custom_page.html", active="", page=page, page_meta=page_meta)



# ── Sitemap & Robots ─────────────────────────────────────────────────────────

@website_bp.route("/api/commission/create-advance-order", methods=["POST"])
def api_commission_create_advance_order():
    """Create Razorpay order for commission advance payment."""
    import uuid as _uuid
    data = request.get_json() or {}
    amount_paise = int(data.get("amount_paise", 0))
    if amount_paise < 100:
        return jsonify({"ok": False, "error": "Advance amount too small"})
    db = get_db()
    try:
        _rz1 = db.execute("SELECT value FROM settings WHERE key='razorpay_key_id'").fetchone()
        _rz2 = db.execute("SELECT value FROM settings WHERE key='razorpay_key_secret'").fetchone()
        def _rz_clean(v): return (v.split("=",1)[-1] if v and "=" in v else v or "").strip()
        rz_key_id  = _rz_clean(_rz1["value"] if _rz1 else "")
        rz_key_sec = _rz_clean(_rz2["value"] if _rz2 else "")
    except Exception:
        rz_key_id = rz_key_sec = ""
    if not rz_key_id or not rz_key_sec:
        return jsonify({"ok": False, "no_gateway": True,
                        "error": "Payment gateway not configured — order will be placed without advance."})
    try:
        import requests as _req
        resp = _req.post(
            "https://api.razorpay.com/v1/orders",
            auth=(rz_key_id, rz_key_sec),
            json={"amount": amount_paise, "currency": "INR",
                  "receipt": f"adv_{_uuid.uuid4().hex[:10]}"},
            timeout=10
        ).json()
        if "id" not in resp:
            return jsonify({"ok": False, "error": "Could not create payment order. Try again."})
        return jsonify({"ok": True, "order_id": resp["id"],
                        "amount": amount_paise, "razorpay_key": rz_key_id})
    except Exception as ex:
        return jsonify({"ok": False, "error": str(ex)})

@website_bp.route("/commission")
def commission():
    from datetime import datetime, timedelta
    cs = get_commission_settings()
    min_date    = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
    urgent_until= (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
    preselect_method = request.args.get("method", "")

    # Garment categories + items for Step 1
    categories = get_categories_grouped()
    try:
        db       = get_db()
        db_items = db.execute("SELECT id, name, price FROM web_service_items ORDER BY sort_order, id").fetchall()
        db_items = [dict(r) for r in db_items]
    except Exception:
        db_items = []

    # Fabrics for Step 2
    fabrics = get_fabrics()

    # Item media (same source PLP uses — primary: web_item_media, fallback: image_url)
    item_media = get_item_media()

    page_meta = {
        "title": "Custom Stitching — Place Your Order | Uttam Tailors",
        "desc": "Custom tailoring in Sikar. Choose your garment, share your measurements and we stitch it perfectly. WhatsApp updates at every step.",
        "robots": "index,follow",
        "og_image": cs.get("header_image", ""),
    }
    # Pass logged-in user info for prefill
    _current_user = None
    _web_acc_id = session.get("web_account_id")
    if _web_acc_id:
        try:
            _row = get_db().execute(
                "SELECT name, mobile, email FROM web_accounts WHERE id=? LIMIT 1", (_web_acc_id,)
            ).fetchone()
            if _row:
                _current_user = {"name": _row["name"] or "", "mobile": _row["mobile"] or "", "email": _row["email"] or ""}
        except Exception:
            pass

    return render_template(
        "website/commission.html",
        cs=cs,
        min_date=min_date,
        urgent_until=urgent_until,
        preselect_method=preselect_method,
        categories=categories,
        db_items=db_items,
        fabrics=fabrics,
        item_media=item_media,
        page_meta=page_meta,
        current_user=_current_user,
    )

@website_bp.route("/track-order")
def track_order():
    code  = request.args.get("code", "").strip()
    phone = request.args.get("phone", "").strip()
    page_meta = {
        "title": "Track Your Order — Uttam Tailors",
        "desc": "Enter your order code or mobile number to see the live status of your garment at every stitch.",
        "robots": "noindex,nofollow",
        "og_image": "",
    }
    return render_template("website/track_order.html",
        page_meta=page_meta,
        prefill_code=code, prefill_phone=phone)


@website_bp.route("/api/track-order")
def api_track_order():
    code  = (request.args.get("code") or "").strip().upper()
    phone = (request.args.get("phone") or "").strip().lstrip("0")
    if not code and not phone:
        return jsonify({"ok": False, "error": "Provide order code or phone"})
    try:
        db = get_db()
        if code:
            row = db.execute(
                "SELECT o.*, c.name as cust_name, c.mobile as cust_mobile "
                "FROM orders o LEFT JOIN customers c ON c.id=o.customer_id "
                "WHERE o.order_code=? LIMIT 1", (code,)
            ).fetchone()
        else:
            # Find most recent order for that phone
            cust = db.execute(
                "SELECT id FROM customers WHERE mobile=? ORDER BY id DESC LIMIT 1", (phone,)
            ).fetchone()
            if not cust:
                return jsonify({"ok": False, "error": "Not found"})
            row = db.execute(
                "SELECT o.*, c.name as cust_name, c.mobile as cust_mobile "
                "FROM orders o LEFT JOIN customers c ON c.id=o.customer_id "
                "WHERE o.customer_id=? ORDER BY o.id DESC LIMIT 1", (cust["id"],)
            ).fetchone()

        if not row:
            return jsonify({"ok": False, "error": "Order not found"})

        o = dict(row)

        # Parse note (pipe-separated: name | garment | ... | delivery:home | ...)
        note = o.get("note") or ""
        note_parts = [p.strip() for p in note.split("|")]
        garment = note_parts[1] if len(note_parts) > 1 else "Custom Order"
        is_home_delivery = any("delivery:home" in p for p in note_parts)

        # Customer details
        cust_name    = o.get("cust_name") or (note_parts[0] if note_parts else "")
        cust_mobile  = o.get("cust_mobile") or ""
        cust_address = o.get("address") or ""

        # Live stitch stage
        stage_row = None
        try:
            stage_row = db.execute(
                "SELECT stage, note FROM order_stages WHERE order_code=? ORDER BY updated_at DESC LIMIT 1",
                (o["order_code"],)
            ).fetchone()
        except Exception:
            pass

        stage  = int(stage_row["stage"]) if stage_row else 1
        status = (o.get("status") or "pending").lower()
        max_stage = 6 if is_home_delivery else 5

        # Auto-advance stage to match status label
        if status == "ready"     and stage < 5: stage = 5
        if status == "delivered" and stage < max_stage: stage = max_stage + 1

        # Only expose fields needed to track the order — no mobile/address (PII)
        _is_admin = session.get("owner_logged_in")
        _resp = {
            "order_code":       o["order_code"],
            "status":           status,
            "garment":          garment,
            "cust_name":        cust_name,
            "order_date":       o.get("order_date", ""),
            "delivery_date":    o.get("delivery_date", ""),
            "remaining":        o.get("remaining", 0),
            "total":            o.get("total_amount", 0),
            "advance":          o.get("advance_paid", 0),
            "stage":            stage,
            "stitch_note":      stage_row["note"] if stage_row else "",
            "is_home_delivery": is_home_delivery,
        }
        if _is_admin:
            _resp["cust_mobile"]  = cust_mobile
            _resp["cust_address"] = cust_address
        return jsonify({"ok": True, "order": _resp})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)})


@website_bp.route("/contact")
def contact():
    try:
        s = get_settings()
    except Exception:
        s = {}
    page_meta = {
        "title": "Contact Us — Uttam Tailors, Sikar",
        "desc": "Find us at Subhash Chowk, Sikar. Call, WhatsApp or book a home visit. Monday to Saturday, 9am–7pm.",
        "robots": "index,follow",
        "og_image": "",
    }
    return render_template("website/contact.html", s=s, page_meta=page_meta)


@website_bp.route("/order-confirmed")
def order_confirmed():
    from flask import request as _req
    order_id   = _req.args.get("id", type=int)
    order_code = (_req.args.get("code") or "").strip()
    paid_flag  = _req.args.get("paid") == "1"
    cod_flag   = _req.args.get("cod")  == "1"
    order = None
    try:
        db = get_db()
        if order_id:
            row = db.execute(
                "SELECT o.*, c.name as cust_name, c.mobile as cust_mobile, c.address as cust_address "
                "FROM orders o LEFT JOIN customers c ON c.id=o.customer_id "
                "WHERE o.id=?", (order_id,)
            ).fetchone()
        elif order_code:
            row = db.execute(
                "SELECT o.*, c.name as cust_name, c.mobile as cust_mobile, c.address as cust_address "
                "FROM orders o LEFT JOIN customers c ON c.id=o.customer_id "
                "WHERE o.order_code=? ORDER BY o.id DESC LIMIT 1",
                (order_code,)
            ).fetchone()
        else:
            row = None
        if row:
            order = dict(row)
    except Exception:
        pass
    return render_template("website/order_confirmed.html",
        order=order, paid_flag=paid_flag, cod_flag=cod_flag)


@website_bp.route("/create-order", methods=["POST"])
def create_order():
    """Handle commission form POST — create customer + order, redirect to confirmation."""
    import json as _json
    from datetime import datetime as _dt
    from database import next_order_code as _next_code

    try:
        db = get_db()
        now = _dt.now().strftime("%Y-%m-%d %H:%M:%S")
        today = _dt.now().strftime("%Y-%m-%d")

        # ── Customer ──
        cust_name  = (request.form.get("cust_name") or "").strip()
        cust_phone = (request.form.get("cust_phone") or "").strip().lstrip("0")
        if not cust_name or not cust_phone:
            return "Missing customer name or phone", 400

        existing = db.execute(
            "SELECT id FROM customers WHERE mobile=? ORDER BY id DESC LIMIT 1",
            (cust_phone,)
        ).fetchone()
        if existing:
            customer_id = existing["id"]
        else:
            db.execute(
                "INSERT INTO customers(name,mobile,created_at) VALUES(?,?,?)",
                (cust_name, cust_phone, now)
            )
            row = db.execute(
                "SELECT id FROM customers WHERE mobile=? ORDER BY id DESC LIMIT 1",
                (cust_phone,)
            ).fetchone()
            customer_id = row["id"] if row else None

        # ── Order basics ──
        order_code    = _next_code()
        delivery_date = request.form.get("delivery_date") or ""
        is_urgent     = 1 if request.form.get("is_urgent") else 0
        measure_method= request.form.get("measure_method", "size")

        # Garment types + prices — rates ALWAYS looked up from DB settings,
        # never trusted from form POST (prevents price manipulation & fixes ₹0 orders)
        garment_types = request.form.getlist("garment_type[]")
        total_amount  = 0.0
        item_rows     = []
        _all_settings = {r["key"]: r["value"] for r in db.execute("SELECT key,value FROM settings").fetchall()}
        for gt in garment_types:
            qty_key = "qty_" + gt
            qty  = max(1, int(request.form.get(qty_key, 1) or 1))
            # Look up server-side rate — try customer_rate_X then rate_X
            _rate_raw = (_all_settings.get("customer_rate_" + gt)
                         or _all_settings.get("rate_" + gt) or "0")
            try:
                rate = float(str(_rate_raw).split("–")[0].split("-")[0].strip() or 0)
            except (ValueError, TypeError):
                rate = 0.0
            item_rows.append({"type": gt, "qty": qty, "rate": rate})
            total_amount += qty * rate

        # Fabric cost
        fabric_cost = float(request.form.get("fabric_cost", 0) or 0)
        total_amount += fabric_cost

        # Urgent surcharge 10%
        extra_charges = round(total_amount * 0.10, 2) if is_urgent else 0.0
        payable_amount = round(total_amount + extra_charges, 2)

        # ── Coupon discount (server-side re-validation) ──
        coupon_code = (request.form.get("coupon_code") or "").strip().upper()
        coupon_discount = 0.0
        coupon_row = None
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
        # ── Razorpay advance payment verification ────────────────────────────
        rz_pay_id  = (request.form.get("rz_payment_id") or "").strip()
        rz_order_id = (request.form.get("rz_order_id") or "").strip()
        rz_sig     = (request.form.get("rz_signature") or "").strip()
        rz_advance  = float(request.form.get("rz_advance_amount", 0) or 0)
        if rz_pay_id and rz_order_id and rz_sig:
            try:
                import hmac as _hmac, hashlib as _hsh
                _rz2 = db.execute("SELECT value FROM settings WHERE key='razorpay_key_secret'").fetchone()
                _rs = (_rz2["value"] if _rz2 else "")
                _rs = (_rs.split("=",1)[-1] if "=" in _rs else _rs).strip()
                _exp = _hmac.new(_rs.encode(), f"{rz_order_id}|{rz_pay_id}".encode(), _hsh.sha256).hexdigest()
                if _hmac.compare_digest(_exp, rz_sig):
                    advance_paid = rz_advance
                else:
                    advance_paid = 0.0
            except Exception:
                advance_paid = 0.0
        else:
            advance_paid  = 0.0
        remaining     = max(0, round(payable_amount - advance_paid, 2))

        # Gift fields
        is_gift      = 1 if request.form.get("is_gift") else 0
        gift_name    = (request.form.get("gift_recipient_name") or "").strip()
        gift_wa      = (request.form.get("gift_whatsapp") or "").strip()
        gift_msg     = (request.form.get("gift_message") or "").strip()

        # Build note
        note_parts = [cust_name]
        if garment_types:
            note_parts.append(", ".join(garment_types))
        if measure_method:
            note_parts.append("meas:" + measure_method)
        if is_gift:
            note_parts.append(f"gift-for:{gift_name}" if gift_name else "gift")
        if coupon_code and coupon_discount:
            note_parts.append(f"coupon:{coupon_code}(-Rs.{int(coupon_discount)})")
        note = " | ".join(note_parts)

        # Insert order
        _web_acc_id_order = session.get("web_account_id")
        db.execute(
            """INSERT INTO orders(order_code,customer_id,order_date,delivery_date,
               total_amount,extra_charges,payable_amount,advance_paid,remaining,
               payment_mode,status,is_urgent,note,web_account_id,created_at)
               VALUES(?,?,?,?,?,?,?,?,?,'pending','pending',?,?,?,?)""",
            (order_code, customer_id, today, delivery_date,
             total_amount, extra_charges, payable_amount,
             advance_paid, remaining, is_urgent, note, _web_acc_id_order, now)
        if rz_pay_id:
            db.execute("UPDATE orders SET payment_mode='online' WHERE order_code=?", (order_code,))
        )
        order_row = db.execute(
            "SELECT id FROM orders WHERE order_code=?", (order_code,)
        ).fetchone()
        order_id = order_row["id"] if order_row else None

        # Insert items
        if order_id:
            meas_json = request.form.get("size_per_garment") or "{}"
            style_json = request.form.get("style_json") or "{}"
            for it in item_rows:
                db.execute(
                    """INSERT INTO order_items(order_id,garment_type,quantity,rate,amount,measurements,notes)
                       VALUES(?,?,?,?,?,?,?)""",
                    (order_id, it["type"], it["qty"], it["rate"],
                     it["qty"] * it["rate"], meas_json, style_json)
                )

        # Increment coupon used_count
        if coupon_row and coupon_discount:
            try:
                db.execute("UPDATE web_coupons SET used_count=used_count+1 WHERE code=?", (coupon_code,))
            except Exception:
                pass

        db.commit()

        # ── SMS confirmation ──────────────────────────────────────────────────
        if order_id:
            try:
                from app.utils.sms import send_order_sms as _osms
                _garment_names = ", ".join(it["type"] for it in item_rows) if item_rows else "Custom Order"
                is_home = any("delivery:home" in p for p in note.split("|"))
                _osms(
                    mobile          = cust_phone,
                    order_code      = order_code,
                    customer_name   = cust_name,
                    garment         = _garment_names,
                    total           = payable_amount,
                    advance         = advance_paid,
                    delivery_date   = delivery_date,
                    is_home_delivery= is_home,
                )
            except Exception:
                pass

        # ── Email + FCM confirmation ──────────────────────────────────────────
        if order_id:
            try:
                _web_acc_id = session.get("web_account_id")
                # Email: prefer web account email, fallback to form field
                _cust_email = (request.form.get("cust_email") or "").strip()
                if _web_acc_id:
                    _acc_row = db.execute(
                        "SELECT email FROM web_accounts WHERE id=? LIMIT 1", (_web_acc_id,)
                    ).fetchone()
                    if _acc_row and (_acc_row["email"] or "").strip():
                        _cust_email = (_acc_row["email"] or "").strip()
                if _cust_email:
                    from app.utils.email_notify import send_order_email as _oe
                    _garment_names_e = ", ".join(it["type"] for it in item_rows) if item_rows else "Custom Order"
                    _is_home_e = any("delivery:home" in p for p in note.split("|"))
                    _oe(
                        to=_cust_email, order_code=order_code,
                        customer_name=cust_name, garment=_garment_names_e,
                        total=payable_amount, advance=advance_paid,
                        delivery_date=delivery_date, is_home_delivery=_is_home_e,
                    )
            except Exception:
                pass
            try:
                _web_acc_id2 = session.get("web_account_id")
                if _web_acc_id2:
                    from app.utils.fcm import push_order_placed as _fcm_op
                    _garment_names_f = ", ".join(it["type"] for it in item_rows) if item_rows else "Custom Order"
                    _fcm_op(_web_acc_id2, order_code, _garment_names_f)
            except Exception:
                pass

        if order_id:
            return redirect(url_for("website.order_confirmed", id=order_id))
        return redirect(url_for("website.home"))

    except Exception as exc:
        try: db.rollback()
        except: pass
        import traceback as _tb
        print(f"[create_order ERROR] {exc}\n{_tb.format_exc()}", flush=True)
        return redirect(url_for("website.home") + "?order_error=1")


@website_bp.route("/sitemap.xml")
def sitemap():
    from flask import Response
    from datetime import datetime
    db = get_db()
    base = "https://uttamtailors.in"
    today = datetime.now().strftime("%Y-%m-%d")
    urls = []

    # Static pages
    static_pages = [
        ("", "1.0", "weekly"),
        ("/our-craft", "0.9", "weekly"),
        ("/our-story", "0.7", "monthly"),
        ("/contact", "0.7", "monthly"),
        ("/commission", "0.9", "weekly"),
    ]
    for path, priority, freq in static_pages:
        urls.append(f"""  <url>
    <loc>{base}{path}</loc>
    <changefreq>{freq}</changefreq>
    <priority>{priority}</priority>
    <lastmod>{today}</lastmod>
  </url>""")

    # Product pages
    try:
        items = db.execute("SELECT slug, id FROM web_service_items WHERE slug != '' AND slug IS NOT NULL").fetchall()
        for item in items:
            urls.append(f"""  <url>
    <loc>{base}/garment/{item['slug']}</loc>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
    <lastmod>{today}</lastmod>
  </url>""")
    except Exception: pass

    # Custom pages
    try:
        pages = db.execute("SELECT slug FROM web_pages").fetchall()
        for page in pages:
            urls.append(f"""  <url>
    <loc>{base}/page/{page['slug']}</loc>
    <changefreq>monthly</changefreq>
    <priority>0.5</priority>
  </url>""")
    except Exception: pass

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    xml += "\n".join(urls)
    xml += "\n</urlset>"
    return Response(xml, mimetype="application/xml")


@website_bp.route("/robots.txt")
def robots_txt():
    from flask import Response
    try:
        db = get_db()
        row = db.execute("SELECT value FROM settings WHERE key='robots_txt'").fetchone()
        if row and row["value"]:
            return Response(row["value"], mimetype="text/plain")
    except Exception: pass
    default = """User-agent: *
Allow: /
Disallow: /manage/
Disallow: /owner/
Disallow: /api/
Disallow: /order-review
Disallow: /order-confirmed

Sitemap: https://uttamtailors.in/sitemap.xml"""
    return Response(default, mimetype="text/plain")

@website_bp.route("/api/validate-coupon", methods=["POST"])
def validate_coupon():
    db = get_db()
    d = request.get_json() or {}
    code = (d.get("code","")).strip().upper()
    order_total = float(d.get("order_total",0))
    if not code:
        return jsonify({"valid":False,"message":"Enter a coupon code"})
    try:
        coupon = db.execute("""SELECT * FROM web_coupons WHERE code=? AND active=1
            AND (expires_on='' OR expires_on IS NULL OR expires_on >= date('now'))
            AND (max_uses=0 OR used_count < max_uses)""", (code,)).fetchone()
        if not coupon:
            return jsonify({"valid":False,"message":"Invalid or expired coupon"})
        if order_total < coupon["min_order"]:
            return jsonify({"valid":False,"message":f"Min order Rs.{int(coupon['min_order'])} required"})
        if coupon["discount_type"] == "percent":
            discount = round(order_total * coupon["discount_value"] / 100)
        else:
            discount = int(coupon["discount_value"])
        return jsonify({"valid":True,"discount":discount,"message":f"✓ {coupon['description'] or code} applied"})
    except:
        return jsonify({"valid":False,"message":"Could not validate coupon"})

@website_bp.route("/api/complete-the-look")
def api_complete_the_look():
    """Given the item ids currently in the cart, return admin-curated 'Complete the Look'
    suggestions — deduped, excluding anything already in the cart."""
    ids_param = request.args.get("ids", "")
    ids = []
    for x in ids_param.split(","):
        x = x.strip()
        if x.isdigit():
            ids.append(int(x))
    if not ids:
        return jsonify({"ok": True, "items": []})
    db = get_db()
    try:
        placeholders = ",".join("?" * len(ids))
        rows = db.execute(
            f"SELECT DISTINCT related_item_id FROM web_related_items WHERE item_id IN ({placeholders})", ids
        ).fetchall()
        related_ids = [r["related_item_id"] for r in rows if r["related_item_id"] not in ids]
        if not related_ids:
            return jsonify({"ok": True, "items": []})
        placeholders2 = ",".join("?" * len(related_ids))
        items = db.execute(
            f"SELECT id, name, price, image_url, stock_qty FROM web_service_items WHERE id IN ({placeholders2})",
            related_ids
        ).fetchall()
        return jsonify({"ok": True, "items": [dict(r) for r in items][:8]})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "items": []})

@website_bp.route("/api/default-sizes/<garment_category>/<size_label>")
def api_default_sizes(garment_category, size_label):
    db = get_db()
    import json
    try:
        row = db.execute("SELECT measurements FROM garment_default_sizes WHERE garment_category=? AND size_label=?",
                         (garment_category.lower(), size_label)).fetchone()
        if row:
            return jsonify({"ok":True,"measurements":json.loads(row["measurements"])})
        return jsonify({"ok":False,"measurements":{}})
    except:
        return jsonify({"ok":False,"measurements":{}})

@website_bp.route("/api/fabric-metres")
def api_fabric_metres():
    """Returns admin-configured fabric metres-needed per garment category + size,
    e.g. {"shirt": {"S": 1.3, "M": 1.4, ...}, "pant": {...}}.
    Read from garment_default_sizes.measurements.fabric_metres (set in admin Sizes panel)."""
    db = get_db()
    import json
    out = {}
    try:
        rows = db.execute("SELECT garment_category, size_label, measurements FROM garment_default_sizes").fetchall()
        for r in rows:
            try:
                meas = json.loads(r["measurements"] or "{}")
                fm = meas.get("fabric_metres")
                if fm not in (None, ""):
                    cat = (r["garment_category"] or "").lower()
                    out.setdefault(cat, {})[r["size_label"]] = float(fm)
            except Exception:
                continue
    except Exception:
        pass
    return jsonify({"ok": True, "data": out})


@website_bp.route("/api/size-measurements")
def api_size_measurements():
    """Returns admin-configured measurements per garment category + size,
    normalised to a fixed set of keys (chest, waist, shoulder, length, trouser)
    so the customer-facing 'fine-tune measurements' fields can be pre-filled
    with whatever the shop owner entered in the Sizes admin tab."""
    db = get_db()
    import json
    out = {}

    def _pick(meas, candidates):
        for k in candidates:
            if k in meas and meas[k] not in (None, ""):
                return meas[k]
        return None

    try:
        rows = db.execute("SELECT garment_category, size_label, measurements FROM garment_default_sizes").fetchall()
        for r in rows:
            try:
                meas = json.loads(r["measurements"] or "{}")
                meas_lc = {(k or "").lower(): v for k, v in meas.items()}
                cat = (r["garment_category"] or "").lower()
                norm = {
                    "chest":    _pick(meas_lc, ["chest"]),
                    "waist":    _pick(meas_lc, ["waist"]),
                    "shoulder": _pick(meas_lc, ["shoulder"]),
                    "length":   _pick(meas_lc, ["shirt_length", "kurta_length", "jacket_length", "length"]),
                    "trouser":  _pick(meas_lc, ["pant_length", "trouser_length", "trouser", "pant"]),
                }
                norm = {k: v for k, v in norm.items() if v not in (None, "")}
                if norm:
                    out.setdefault(cat, {})[r["size_label"]] = norm
            except Exception:
                continue
    except Exception:
        pass
    return jsonify({"ok": True, "data": out})


@website_bp.route("/api/style-options/<int:item_id>")
def api_style_options(item_id):
    db = get_db()
    try:
        rows = db.execute("SELECT * FROM garment_style_options WHERE item_id=? ORDER BY sort_order,id", (item_id,)).fetchall()
        result = []
        for r in rows:
            vals = db.execute("SELECT * FROM garment_style_values WHERE option_id=? ORDER BY sort_order,id", (r["id"],)).fetchall()
            opt = dict(r)
            opt["values"] = [dict(v) for v in vals]
            result.append(opt)
        return jsonify({"ok": True, "options": result})
    except:
        return jsonify({"ok": True, "options": []})


def _resolve_style_ai_prompts(item_id):
    """Look up admin-authored explicit AI instructions for an item's style
    values, from garment_style_values.ai_prompt.

    Returns a dict keyed by (option_group.lower().strip(), value_label.lower().strip())
    -> ai_prompt, containing ONLY rows where the admin has actually filled in
    an instruction (blank ai_prompt rows are skipped, so the hardcoded
    keyword-matching below still covers them as a fallback).

    This is the fix for "style options added in Admin must automatically
    reach the AI backend" — every Replicate call costs real money, so any
    style value the keyword-matcher doesn't recognize should use the admin's
    own explicit, accurate instruction text instead of falling through to a
    vague generic phrase that wastes the generation."""
    if not item_id:
        return {}
    try:
        db = get_db()
        rows = db.execute(
            "SELECT go.option_group AS grp, gv.value_label AS lbl, gv.ai_prompt AS ai "
            "FROM garment_style_values gv JOIN garment_style_options go ON go.id = gv.option_id "
            "WHERE go.item_id=? AND gv.ai_prompt IS NOT NULL AND gv.ai_prompt != ''",
            (item_id,)
        ).fetchall()
        return {
            ((r["grp"] or "").lower().strip(), (r["lbl"] or "").lower().strip()): r["ai"].strip()
            for r in rows if (r["ai"] or "").strip()
        }
    except Exception:
        return {}


def _style_detail_phrases(styles, ai_map=None):
    """Shared: turn a {option_group: chosen_value} dict into precise, explicit
    descriptive phrases (collar/sleeve/pocket-count/placket/buttons/hem/fit).
    Used by any prompt that DESCRIBES the garment to generate (not edit-style
    prompts, which phrase things as "change X to Y" instead).

    If ai_map (from _resolve_style_ai_prompts) has an explicit admin-authored
    instruction for this exact (group, value), it is used VERBATIM instead of
    the hardcoded keyword guesses below — that's the accurate, intentional
    instruction an admin wrote for this specific style choice."""
    ai_map = ai_map or {}
    style_terms = []
    for group, value in (styles or {}).items():
        if group.startswith("__") or not value:
            continue
        v = str(value).lower()
        g_grp = (group or "").lower()
        ai = ai_map.get((g_grp.strip(), v.strip()))
        # Collar
        if ai:
            style_terms.append(ai)
        elif "mandarin" in v or "chinese" in v:
            style_terms.append("a short mandarin/Chinese stand-up band collar that sits straight up around the neck with NO fold-down points and NO spread — clearly different from a regular pointed shirt collar")
        elif "band" in v and "collar" in v:
            style_terms.append("a plain band collar, short stand-up collar with no points")
        elif "button-down" in v or "button down" in v:
            style_terms.append("a button-down collar with visible buttons fastening the collar points to the shirt")
        elif "spread" in v:
            style_terms.append("a wide spread collar with points spread far apart")
        # Sleeves
        elif "full" in v and "sleeve" in v:
            style_terms.append("full-length long sleeves reaching the wrists, with buttoned cuffs")
        elif "half" in v and "sleeve" in v:
            style_terms.append("short half sleeves ending above the elbow")
        elif "3/4" in v or ("three" in v and "quarter" in v):
            style_terms.append("three-quarter length sleeves ending below the elbow")
        elif "sleeveless" in v:
            style_terms.append("sleeveless, no sleeves at all, open armholes")
        # Pockets — must come before the generic fallback so counts are rendered explicitly
        elif "pocket" in v or "pocket" in g_grp:
            if "no pocket" in v or v.strip() in ("no pocket", "no pockets"):
                style_terms.append("a completely plain front with NO chest pockets at all")
            elif "2" in v or "two" in v:
                style_terms.append("exactly TWO patch pockets on the chest — one on the left side and one on the right side, symmetrical and clearly visible")
            elif "1" in v or "one" in v:
                style_terms.append("exactly ONE single patch pocket on the left chest only — no pocket on the right side")
            else:
                style_terms.append(v)
        # Placket
        elif "concealed" in v or "hidden" in v:
            style_terms.append("a concealed hidden-button placket with no visible buttons, clean minimalist front")
        elif "french" in v and "placket" in v:
            style_terms.append("a French placket (folded fabric front band) with visible top-stitching")
        elif "standard" in v and "placket" in g_grp:
            style_terms.append("a standard shirt placket with regular visible buttons down the front")
        # Buttons
        elif "gold" in v or "metal" in v:
            style_terms.append("gold-toned metal buttons")
        elif "white" in v or "pearl" in v:
            style_terms.append("white pearl buttons")
        elif "dark" in v or "black" in v:
            style_terms.append("dark black buttons")
        elif "denim" in v and "button" in v:
            style_terms.append("denim-covered fabric buttons matching the garment")
        # Hem
        elif "round" in v and "hem" in v:
            style_terms.append("a rounded curved hem at the bottom — the side seams curve gently inward toward the bottom corners instead of forming sharp square corners")
        elif "straight" in v and "hem" in v:
            style_terms.append("a straight horizontal hem at the bottom with sharp square corners, no curve")
        elif "side" in v and ("cut" in v or "slit" in v):
            style_terms.append("side slit openings at the bottom hem on both side seams")
        # Fit
        elif "slim" in v:
            style_terms.append("a slim tailored fit")
        elif "regular" in v:
            style_terms.append("a regular comfortable fit")
        elif "loose" in v or "relaxed" in v:
            style_terms.append("a relaxed loose fit")
        # Fallback
        else:
            clean = value.strip()
            if len(clean) < 40:
                style_terms.append(clean.lower())
    return style_terms


_BRAND_LABEL_PHRASE = (
    "IMPORTANT BRANDING DETAIL — this is a studio reference photo for \"Uttam Tailors, Sikar\" and must "
    "carry their mark so customers cannot screenshot and reuse it elsewhere: show a small, elegant woven "
    "or embroidered fabric label sewn onto the INSIDE of the collar (the inside back-neck placket area, "
    "exactly where real branded shirts have their maker's label), reading \"UTTAM\" on one line and "
    "\"Est. 1987\" in smaller text below it, in a tasteful gold-on-black or tone-on-tone serif style "
    "consistent with a premium heritage tailoring house — subtle, neatly stitched, and proportioned like "
    "a genuine designer label, not a sticker or watermark plastered over the photo."
)



def _is_bottom_wear(garment):
    """Return True for pants/jeans/trousers — these need a full-leg shot with feet."""
    g = (garment or "").lower()
    return any(k in g for k in ("pant", "jean", "trouser", "pajama", "dhoti", "churidar"))

def build_garment_prompt(garment, styles, ai_map=None):
    """Build a detailed Replicate/Flux prompt from garment + style selections."""
    g = garment.lower()
    garment_map = {
        "formal shirt": "men's formal dress shirt",
        "shirt":        "men's dress shirt",
        "kurta":        "men's Indian kurta, ethnic traditional wear",
        "kurta + pajama": "men's kurta pajama set, Indian ethnic wear",
        "pathani":      "men's pathani suit, traditional wear",
        "safari suit":  "men's safari suit",
        "blazer":       "men's blazer jacket, tailored",
        "suit 2-piece": "men's 2-piece suit, jacket and pants",
        "suit 3-piece": "men's 3-piece suit with waistcoat",
        "pant":         "men's dress pants",
        "jeans":        "men's jeans",
        "trouser":      "men's tailored pants",
    }
    base = None
    for key, val in garment_map.items():
        if key in g:
            base = val
            break
    if not base:
        base = "men's " + garment

    style_terms = _style_detail_phrases(styles, ai_map)
    style_str = "; ".join(style_terms) if style_terms else "classic style"

    _shot = (
        "Full-length fashion catalog photo of this garment on a premium headless male mannequin, "
        "standing upright, full body visible from head to toe so all design details are clear. "
        if not _is_bottom_wear(garment) else
        "Fashion catalog photo of this garment worn on a premium headless male mannequin, "
        "showing full leg length from waist down, both feet clearly visible at the bottom. "
    )
    prompt = (
        f"Professional fashion catalog photograph, {base}, with these EXACT design details — {style_str}. "
        "Follow every one of these design details precisely and do not substitute a generic/standard "
        "version of any of them. "
        + _shot
        + "Pure white studio background, even studio lighting, sharp focus, high resolution, "
        "no face, no head, mannequin body only, fashion editorial quality. "
        + _BRAND_LABEL_PHRASE
    )
    return prompt


def build_img2img_style_prompt(garment, styles, ai_map=None):
    """Build an *edit* prompt for img2img (Flux Kontext) — describes ONLY the
    requested style changes (collar/sleeve/placket/buttons/hem/fit). Color,
    pattern and fabric must NOT be re-described here because the reference
    photo already shows them — Kontext keeps everything else from the input
    image untouched and only edits what the prompt tells it to change.

    If ai_map has an admin-authored instruction for a selected value, it is
    used verbatim (wrapped as an explicit "must show" instruction) instead of
    the hardcoded keyword guesses — see _resolve_style_ai_prompts."""
    ai_map = ai_map or {}
    style_terms = []
    for group, value in styles.items():
        if group.startswith("__") or not value:
            continue
        v = value.lower()
        g_grp = (group or "").lower()
        ai = ai_map.get((g_grp.strip(), v.strip()))
        if ai:
            style_terms.append(f"the garment must clearly show: {ai}")
        elif "mandarin" in v or "chinese" in v:
            style_terms.append("REPLACE the collar entirely with a short mandarin/Chinese stand-up band collar — a narrow band that stands straight up around the neck with NO fold-down points and NO spread; remove any pointed collar shape completely")
        elif "band" in v and "collar" in v:
            style_terms.append("change the collar to a plain short band collar with no points")
        elif "button-down" in v or "button down" in v:
            style_terms.append("change the collar to a button-down collar, with small buttons fastening each collar point to the shirt body")
        elif "spread" in v:
            style_terms.append("change the collar to a wide spread collar with the points spread far apart")
        elif "full" in v and "sleeve" in v:
            style_terms.append("change the sleeves to full-length long sleeves that reach the wrists, with buttoned cuffs")
        elif "half" in v and "sleeve" in v:
            style_terms.append("shorten the sleeves to half sleeves that end above the elbow")
        elif "3/4" in v or ("three" in v and "quarter" in v):
            style_terms.append("change the sleeves to three-quarter length, ending below the elbow")
        elif "sleeveless" in v:
            style_terms.append("remove the sleeves entirely to make it sleeveless with open armholes")
        # Pockets — explicit count handling so the model doesn't default to 0 or 1
        elif "pocket" in v or "pocket" in g_grp:
            if "no pocket" in v or v.strip() in ("no pocket", "no pockets"):
                style_terms.append("remove all chest pockets — the front should be completely plain with no pockets")
            elif "2" in v or "two" in v:
                style_terms.append("the garment must have exactly TWO patch pockets on the chest, one on the left side and one on the right side, placed symmetrically and both clearly visible — add a second pocket if only one is currently shown")
            elif "1" in v or "one" in v:
                style_terms.append("the garment must have exactly ONE single patch pocket on the left chest only — remove any pocket on the right side if present")
            else:
                style_terms.append("apply this pocket style: " + v)
        elif "concealed" in v or "hidden" in v:
            style_terms.append("change the front placket to a concealed hidden-button placket so no buttons are visible")
        elif "french" in v and "placket" in v:
            style_terms.append("change the front placket to a French placket (a folded fabric band with visible top-stitching)")
        elif "gold" in v or "metal" in v:
            style_terms.append("change the buttons to gold-toned metal buttons")
        elif "white" in v or "pearl" in v:
            style_terms.append("change the buttons to white pearl buttons")
        elif "dark" in v or "black" in v:
            style_terms.append("change the buttons to dark black buttons")
        elif "denim" in v and "button" in v:
            style_terms.append("change the buttons to denim-covered fabric buttons matching the garment fabric")
        elif "round" in v and "hem" in v:
            style_terms.append("change the hem to a rounded curved hem")
        elif "straight" in v and "hem" in v:
            style_terms.append("change the hem to a straight horizontal hem")
        elif "side" in v and ("cut" in v or "slit" in v):
            style_terms.append("add side slit openings to the hem")
        elif "slim" in v:
            style_terms.append("adjust the fit to a slim tailored fit")
        elif "regular" in v:
            style_terms.append("adjust the fit to a regular comfortable fit")
        elif "loose" in v or "relaxed" in v:
            style_terms.append("adjust the fit to a relaxed loose fit")
        else:
            clean = value.strip()
            if len(clean) < 40:
                style_terms.append("apply this style detail: " + clean.lower())

    if not style_terms:
        return ("Keep this garment exactly as shown — same color, same fabric pattern, "
                "same design — just present it as a clean professional catalog product photo "
                "on a plain white background.")

    # Number each change so the model treats each as an individual requirement
    numbered = " ".join(f"({i+1}) {t}" for i, t in enumerate(style_terms))
    return (
        f"Edit this garment photo. Apply ALL of the following changes — every one is mandatory "
        f"and must be clearly visible in the output: {numbered}. "
        "CRITICAL: keep the EXACT same fabric color, print and texture as the input photo — "
        "do NOT change the color, do NOT alter the fabric pattern or material in any way. "
        "Clean professional fashion catalog photo on a premium headless male mannequin, "
        "pure white background, even studio lighting, no face, no head. "
        "Full body visible — show complete garment on mannequin body."
    )


def build_fabric_to_garment_prompt(garment, styles, fabric_name="", ai_map=None):
    """Edit prompt used when the customer picked a fabric from our catalog —
    the reference image is a photo of THAT FABRIC (swatch/texture), not the
    generic product photo, so the model should render the garment USING this
    fabric's exact color, weave, print and texture, shaped per the garment +
    style selections."""
    style_terms = _style_detail_phrases(styles, ai_map)
    fab_phrase = (f"the \"{fabric_name}\" fabric" if fabric_name else "this fabric")

    # Number each style requirement so the model treats each as a separate obligation
    if style_terms:
        numbered = " ".join(f"({i+1}) {t}" for i, t in enumerate(style_terms))
        style_block = f"Apply ALL of the following design details — every single one is mandatory and must be clearly visible in the output: {numbered}."
    else:
        style_block = "Classic standard style — keep the silhouette clean and well-tailored."

    return (
        f"CRITICAL REQUIREMENT — READ THIS BEFORE GENERATING ANYTHING: "
        f"The attached reference image is a CLOSE-UP PHOTO OF A FABRIC SWATCH — {fab_phrase}. "
        "Examine every part of this swatch image before you output anything. "
        "Identify: (a) the exact base color; (b) EVERY print, pattern or motif visible on it — "
        "polka-dots, stripes, checks, florals, geometric shapes, weave texture, flecks, or any other "
        "surface detail, no matter how small or subtle. "
        "The fabric on the finished garment MUST reproduce this swatch's color and pattern at TRUE SCALE — "
        "if the swatch has dots, the garment must show those same dots at the same size, spacing and color; "
        "if the swatch has stripes or checks, those exact stripes or checks must appear on every panel. "
        "ABSOLUTE RULES FOR THE FABRIC — NEVER VIOLATE THESE: "
        "DO NOT simplify the fabric to a plain solid color. "
        "DO NOT blur, smooth or blend away any pattern. "
        "DO NOT substitute a different or generic fabric pattern. "
        "The pattern must be clearly readable across the entire garment — chest, back, sleeves and all panels. "
        f"GARMENT TO GENERATE: A professional fashion catalog photograph of a fully stitched {garment} "
        f"made entirely from the fabric shown in the swatch. {style_block} "
        "Do not substitute a generic version of any styling detail. "
        "Show the garment flat-lay or on an invisible mannequin. "
        "Pure white studio background, even studio lighting, sharp focus, high-resolution — "
        "the fabric's print and texture must be crisp and clearly legible in the final output. "
        "No people, no mannequin face, garment only. "
        f"{_BRAND_LABEL_PHRASE}"
    )


def build_multi_image_fabric_garment_prompt(garment, styles, fabric_name="", ai_map=None):
    """Edit prompt for the multi-image Kontext model (two reference images).
    Image 1 = the product's own reference photo — a REAL garment photo, so its
    collar/sleeve/pocket/placket/hem shapes are already correct; we only tell
    the model what to CHANGE about that structure (same reliable edit-phrasing
    as build_img2img_style_prompt). Image 2 = the fabric swatch the customer
    picked — used only for color/pattern/texture.

    Generating exact pocket counts / collar shapes / hem shapes purely from a
    fabric swatch + text description (the old single-image fabric path) asks
    the model to invent the entire garment structure from scratch, which
    diffusion models are unreliable at. Anchoring structure to a real photo
    and only describing the deltas is far more reliable.

    If ai_map has an admin-authored instruction for a selected value, it is
    used verbatim instead of the hardcoded keyword guesses — see
    _resolve_style_ai_prompts."""
    ai_map = ai_map or {}
    style_terms = []
    for group, value in (styles or {}).items():
        if group.startswith("__") or not value:
            continue
        v = str(value).lower()
        g_grp = (group or "").lower()
        ai = ai_map.get((g_grp.strip(), v.strip()))
        if ai:
            style_terms.append(f"in Image 1, the garment must clearly show: {ai}")
        elif "mandarin" in v or "chinese" in v:
            style_terms.append("REPLACE the collar in Image 1 entirely with a short mandarin/Chinese stand-up band collar — a narrow band that stands straight up around the neck with NO fold-down points and NO spread; remove any pointed collar shape completely")
        elif "band" in v and "collar" in v:
            style_terms.append("change the collar in Image 1 to a plain short band collar with no points")
        elif "button-down" in v or "button down" in v:
            style_terms.append("change the collar in Image 1 to a button-down collar, with small buttons fastening each collar point to the shirt body")
        elif "spread" in v:
            style_terms.append("change the collar in Image 1 to a wide spread collar with the points spread far apart")
        elif "full" in v and "sleeve" in v:
            style_terms.append("change the sleeves in Image 1 to full-length long sleeves that reach the wrists, with buttoned cuffs")
        elif "half" in v and "sleeve" in v:
            style_terms.append("shorten the sleeves in Image 1 to half sleeves that end above the elbow")
        elif "3/4" in v or ("three" in v and "quarter" in v):
            style_terms.append("change the sleeves in Image 1 to three-quarter length, ending below the elbow")
        elif "sleeveless" in v:
            style_terms.append("remove the sleeves in Image 1 entirely to make it sleeveless with open armholes")
        elif "pocket" in v or "pocket" in g_grp:
            if "no pocket" in v or v.strip() in ("no pocket", "no pockets"):
                style_terms.append("remove all chest pockets from Image 1 — the front should be completely plain with no pockets")
            elif "2" in v or "two" in v:
                style_terms.append("the garment must have exactly TWO patch pockets on the chest, one on the left side and one on the right side, placed symmetrically and both clearly visible — add a second pocket if Image 1 shows only one")
            elif "1" in v or "one" in v:
                style_terms.append("the garment must have exactly ONE single patch pocket on the left chest only — remove any pocket on the right side if Image 1 shows one")
            else:
                style_terms.append("apply this pocket style to Image 1: " + v)
        elif "concealed" in v or "hidden" in v:
            style_terms.append("change the front placket in Image 1 to a concealed hidden-button placket so no buttons are visible")
        elif "french" in v and "placket" in v:
            style_terms.append("change the front placket in Image 1 to a French placket (a folded fabric band with visible top-stitching)")
        elif "gold" in v or "metal" in v:
            style_terms.append("use gold-toned metal buttons")
        elif "white" in v or "pearl" in v:
            style_terms.append("use white pearl buttons")
        elif "dark" in v or "black" in v:
            style_terms.append("use dark black buttons")
        elif "denim" in v and "button" in v:
            style_terms.append("use denim-covered fabric buttons matching the garment fabric")
        elif "round" in v and "hem" in v:
            style_terms.append("change the hem in Image 1 to a rounded curved hem")
        elif "straight" in v and "hem" in v:
            style_terms.append("change the hem in Image 1 to a straight horizontal hem")
        elif "side" in v and ("cut" in v or "slit" in v):
            style_terms.append("add side slit openings to the hem in Image 1")
        elif "slim" in v:
            style_terms.append("adjust the fit to a slim tailored fit")
        elif "regular" in v:
            style_terms.append("adjust the fit to a regular comfortable fit")
        elif "loose" in v or "relaxed" in v:
            style_terms.append("adjust the fit to a relaxed loose fit")
        else:
            clean = value.strip()
            if len(clean) < 40:
                style_terms.append("apply this style detail to Image 1: " + clean.lower())

    structure_str = ("; ".join(style_terms) if style_terms
                      else "keep the garment's collar, sleeves, pockets, placket and hem exactly as shown in Image 1")
    fab_phrase = (f"the \"{fabric_name}\" fabric" if fabric_name else "this fabric")

    return (
        f"TWO REFERENCE IMAGES PROVIDED — both are mandatory inputs:\n"
        f"IMAGE 1 (STRUCTURE SOURCE): A photo of a real finished {garment}. "
        "Use its shape, cut and silhouette as the structural skeleton for the output.\n"
        f"IMAGE 2 (FABRIC SOURCE — MOST CRITICAL): A close-up photo of {fab_phrase} swatch. "
        "This drives the ENTIRE color and surface appearance of the output garment. "
        "Study it pixel by pixel before generating.\n\n"
        "STEP 1 — FABRIC (highest priority, non-negotiable): "
        "Identify every detail in Image 2: (a) exact base color; (b) EVERY pattern, print or motif — "
        "polka-dots, stripes, checks, florals, geometric shapes, weave lines, texture grain, or any other "
        "surface detail visible, no matter how subtle. "
        "The finished garment MUST be rendered in the EXACT color AND pattern of Image 2. "
        "Concrete rules: if Image 2 shows dots → the garment fabric must have those same dots at the same size and spacing; "
        "if Image 2 shows stripes → exact same stripes on the garment; "
        "if Image 2 shows checks → exact same checks. "
        "FORBIDDEN — DO NOT EVER: simplify to a plain solid color; smooth or blur the pattern; "
        "substitute a different or invented pattern. "
        "The Image 2 fabric pattern must be clearly visible and readable on EVERY panel of the finished garment "
        "(chest, back, sleeves, collar — all of it).\n\n"
        f"STEP 2 — STRUCTURE CHANGES (apply to Image 1's silhouette, every one is mandatory): {structure_str}. "
        "Each change must be clearly visible in the output — do not skip or soften any of them.\n\n"
        "OUTPUT: One finished professional fashion catalog photograph. "
        "The garment uses Image 1's structure (with Step 2 changes applied) dressed entirely in Image 2's EXACT fabric. "
        "Show the garment on a premium headless male mannequin, standing upright, full body visible. "
        "Pure white studio background, even studio lighting, sharp focus, high resolution — "
        "the fabric pattern must be crisp and clearly legible across the entire garment on the mannequin. "
        "No face, no head, mannequin body only. "
        f"{_BRAND_LABEL_PHRASE}"
    )



def _replicate_resolve_latest_version(owner_model, api_key):
    """Resolve the current 'latest' pinned version id for a community
    Replicate model via GET /v1/models/<owner>/<name> — needed because the
    shorthand /v1/models/<owner>/<name>/predictions endpoint 404s for some
    community models (see the IDM_VTON_VERSION note above). Resolving
    dynamically (instead of hardcoding another hash) means this never goes
    stale if the model publisher pushes a new version. Cached per-process
    since it rarely changes; on any failure, return None so the caller can
    skip the optional step rather than erroring out."""
    if owner_model in _REPLICATE_VERSION_CACHE:
        return _REPLICATE_VERSION_CACHE[owner_model]
    try:
        import requests
        r = requests.get(
            f"https://api.replicate.com/v1/models/{owner_model}",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15
        )
        if r.status_code == 200:
            vid = ((r.json() or {}).get("latest_version") or {}).get("id")
            if vid:
                _REPLICATE_VERSION_CACHE[owner_model] = vid
                return vid
    except Exception:
        pass
    return None



@website_bp.route("/api/upload-tryon-photo", methods=["POST"])
@_rl("20 per hour")   # 20 uploads/hour per IP — stops bulk scraping
def upload_tryon_photo():
    """Accepts a customer's own photo for the virtual try-on feature and
    stores it under static/uploads/tryon/. No AI cost is incurred here — the
    paid Replicate call only happens later in /api/generate-style-preview,
    which is where the free-trial gate is actually enforced. This endpoint
    validates extension + MIME magic bytes, enforces size, then saves the file."""
    import os, uuid
    # ── MIME magic-byte whitelist ─────────────────────────────────────────────
    MIME_MAGIC = {
        b"\xff\xd8\xff": "jpg",   # JPEG
        b"\x89PNG\r\n":  "png",   # PNG
        b"RIFF":          "webp",  # WEBP (starts with RIFF....WEBP)
    }
    f = request.files.get("photo")
    if not f or not f.filename:
        return jsonify({"ok": False, "error": "No photo uploaded"})

    # Extension check
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        return jsonify({"ok": False, "error": "Please upload a JPG, PNG or WEBP photo"})

    # Size check (read first so we can also inspect magic bytes)
    header = f.read(12)
    f.seek(0, os.SEEK_END)
    size = f.tell()
    f.seek(0)
    if size > 8 * 1024 * 1024:
        return jsonify({"ok": False, "error": "Photo is too large — please use one under 8MB"})
    if size == 0:
        return jsonify({"ok": False, "error": "That file appears to be empty"})

    # MIME magic check — reject files whose bytes don't match a real image
    is_valid_mime = (
        header[:3] == b"\xff\xd8\xff"          # JPEG
        or header[:6] == b"\x89PNG\r\n"         # PNG
        or (header[:4] == b"RIFF" and header[8:12] == b"WEBP")  # WEBP
    )
    if not is_valid_mime:
        return jsonify({"ok": False, "error": "File does not appear to be a valid image"})

    fname = "tryon_" + uuid.uuid4().hex[:16] + ext
    upload_dir = os.path.join(os.path.dirname(__file__), "..", "..", "static", "uploads", "tryon")
    os.makedirs(upload_dir, exist_ok=True)
    fpath = os.path.join(upload_dir, fname)
    f.save(fpath)
    return jsonify({"ok": True, "url": "/static/uploads/tryon/" + fname})


@website_bp.route("/api/generate-style-preview", methods=["POST"])
@_rl("10 per minute; 30 per hour")   # Each call hits Replicate — protect the AI budget
def generate_style_preview():
    import requests, time
    data = request.get_json() or {}
    garment      = data.get("garment", "shirt")
    styles       = data.get("styles", {})
    item_id      = data.get("item_id")
    fabric_choice = (data.get("fabric_choice") or "").strip().lower()
    fabric_id_raw = (data.get("fabric_id") or "").strip()
    fabric_name   = (data.get("fabric_name") or "").strip()

    # ── Free-preview limit gate ──────────────────────────────────────────────
    acc = _current_account()
    db  = get_db()
    if not acc:
        # Anonymous: enforce session-based free limit
        used = session.get("preview_count", 0)
        if used >= FREE_PREVIEW_LIMIT:
            return jsonify({
                "ok": False, "need_login": True,
                "error": f"You've used your {FREE_PREVIEW_LIMIT} free previews. Log in or create a free account to keep going."
            })
    else:
        # Logged-in: enforce token balance
        tok_row = db.execute("SELECT token_balance FROM web_accounts WHERE id=?", (acc["id"],)).fetchone()
        tok_bal = (tok_row["token_balance"] or 0) if tok_row else 0
        if tok_bal <= 0:
            return jsonify({
                "ok": False, "need_tokens": True,
                "error": "You have no credits left. Buy a token pack to continue generating."
            })
    try:
        row = db.execute("SELECT value FROM settings WHERE key='replicate_api_key'").fetchone()
        api_key = row["value"].strip() if row and row["value"] else None
    except Exception:
        api_key = None
    if not api_key:
        return jsonify({"ok": False, "error": "Replicate API key not configured."})

    def _to_data_uri_or_url(raw_url):
        raw_url = (raw_url or "").strip()
        if not raw_url:
            return None
        if raw_url.startswith("http://") or raw_url.startswith("https://"):
            return raw_url
        if raw_url.startswith("/static/"):
            import os, base64, mimetypes
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            fpath = os.path.join(project_root, raw_url.lstrip("/").replace("/", os.sep))
            if os.path.isfile(fpath):
                mime = mimetypes.guess_type(fpath)[0] or "image/jpeg"
                with open(fpath, "rb") as fh:
                    b64 = base64.b64encode(fh.read()).decode("ascii")
                return f"data:{mime};base64,{b64}"
        return None

    # Fabric image (from catalog selection)
    ref_image_url = None
    ref_is_fabric = False
    if fabric_choice == "catalog" and fabric_id_raw and fabric_id_raw != "own":
        try:
            fid = int(fabric_id_raw)
            fab_img_raw = None
            media_row = db.execute(
                "SELECT url FROM web_fabric_media WHERE fabric_id=? ORDER BY sort_order LIMIT 1", (fid,)
            ).fetchone()
            if media_row and media_row["url"]:
                fab_img_raw = media_row["url"]
            else:
                frow = db.execute("SELECT image_url, name FROM web_fabrics WHERE id=?", (fid,)).fetchone()
                if frow:
                    fab_img_raw = frow["image_url"]
                    if not fabric_name and frow["name"]:
                        fabric_name = frow["name"]
            candidate = _to_data_uri_or_url(fab_img_raw)
            if candidate:
                ref_image_url = candidate
                ref_is_fabric = True
        except Exception:
            pass

    # Product reference photo (structure anchor)
    product_image_url = None
    if item_id:
        try:
            prow = db.execute("SELECT image_url FROM web_service_items WHERE id=?", (item_id,)).fetchone()
            product_image_url = _to_data_uri_or_url(prow["image_url"] if prow else "")
        except Exception:
            product_image_url = None

    use_multi_image = bool(ref_image_url and ref_is_fabric and product_image_url)
    use_img2img    = bool(ref_image_url or product_image_url)

    ai_map = _resolve_style_ai_prompts(item_id)

    # Choose prompt + model
    if use_multi_image:
        prompt    = build_multi_image_fabric_garment_prompt(garment, styles, fabric_name, ai_map)
        model_url = "https://api.replicate.com/v1/models/flux-kontext-apps/multi-image-kontext-pro/predictions"
        payload   = {"input": {"prompt": prompt, "input_image_1": product_image_url,
                               "input_image_2": ref_image_url,
                               "aspect_ratio": "match_input_image", "output_format": "png",
                               "safety_tolerance": 2}}
    elif ref_image_url and ref_is_fabric:
        prompt    = build_fabric_to_garment_prompt(garment, styles, fabric_name, ai_map)
        model_url = "https://api.replicate.com/v1/models/black-forest-labs/flux-kontext-pro/predictions"
        payload   = {"input": {"prompt": prompt, "input_image": ref_image_url,
                               "aspect_ratio": "2:3", "output_format": "png",
                               "safety_tolerance": 2}}
    elif use_img2img:
        if not ref_image_url:
            ref_image_url = product_image_url
        prompt    = build_img2img_style_prompt(garment, styles, ai_map)
        model_url = "https://api.replicate.com/v1/models/black-forest-labs/flux-kontext-pro/predictions"
        payload   = {"input": {"prompt": prompt, "input_image": ref_image_url,
                               "aspect_ratio": "match_input_image", "output_format": "png",
                               "safety_tolerance": 2}}
    else:
        prompt    = build_garment_prompt(garment, styles, ai_map)
        model_url = "https://api.replicate.com/v1/models/black-forest-labs/flux-1.1-pro/predictions"
        payload   = {"input": {"prompt": prompt, "aspect_ratio": "2:3",
                               "output_format": "webp", "output_quality": 85,
                               "safety_tolerance": 2}}

    try:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "Prefer": "wait"}
        resp   = requests.post(model_url, headers=headers, json=payload, timeout=90)
        result = resp.json()

        def _record_and_respond(img_url):
            """Deduct credit / increment counter, then return response."""
            try:
                if acc:
                    # Deduct 1 token + log the transaction
                    db.execute(
                        "UPDATE web_accounts SET token_balance = MAX(0, COALESCE(token_balance,0)-1), "
                        "preview_count = COALESCE(preview_count,0)+1 WHERE id=?",
                        (acc["id"],)
                    )
                    db.execute(
                        "INSERT INTO token_transactions (account_id, tokens, type) VALUES (?,?,'debit')",
                        (acc["id"], -1)
                    )
                    db.commit()
                    remaining = None
                    tok = db.execute("SELECT token_balance FROM web_accounts WHERE id=?", (acc["id"],)).fetchone()
                    token_balance = (tok["token_balance"] or 0) if tok else 0
                else:
                    session["preview_count"] = session.get("preview_count", 0) + 1
                    remaining = max(0, FREE_PREVIEW_LIMIT - session.get("preview_count", 0))
                    token_balance = None
            except Exception:
                remaining = None
                token_balance = None
            return jsonify({"ok": True, "image_url": img_url, "prompt": prompt,
                            "previews_remaining": remaining, "token_balance": token_balance})

        def _extract_url(output):
            url = (output[0] if isinstance(output, list) else output) or ""
            return url.strip()

        if result.get("status") == "succeeded":
            img_url = _extract_url(result.get("output"))
            if not img_url:
                return jsonify({"ok": False, "error": "Generation returned no image — please try again."})
            return _record_and_respond(img_url)

        pred_id = result.get("id")
        if not pred_id:
            return jsonify({"ok": False, "error": "Prediction start failed: " + str(result.get("detail", ""))})

        for _ in range(60):
            time.sleep(2)
            poll = requests.get(f"https://api.replicate.com/v1/predictions/{pred_id}",
                                headers={"Authorization": f"Bearer {api_key}"}, timeout=15).json()
            if poll.get("status") == "succeeded":
                img_url = _extract_url(poll.get("output"))
                if not img_url:
                    return jsonify({"ok": False, "error": "Generation returned no image — please try again."})
                return _record_and_respond(img_url)
            if poll.get("status") in ("failed", "canceled"):
                return jsonify({"ok": False, "error": "Generation failed: " + str(poll.get("error", ""))})
        return jsonify({"ok": False, "error": "Timed out — please try again"})

    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)})




@website_bp.route("/cart")
def cart():
    return render_template("website/cart.html", active="cart", page_meta={
        "title": "Your Cart — Uttam Tailors",
        "desc": "Review your cart and proceed to checkout.",
        "robots": "noindex,nofollow", "og_image": "", "canonical": ""
    })


@website_bp.route("/order-review")
def order_review():
    return render_template("website/order_review.html", active="order_review", page_meta={
        "title": "Order Review — Uttam Tailors",
        "desc": "Review your order before confirming.",
        "robots": "noindex,nofollow", "og_image": "", "canonical": ""
    })


@website_bp.route("/account")
def account_page():
    google_error = request.args.get("google_error", "")
    return render_template("website/account.html",
        google_error=google_error,
        page_meta={
            "title": "My Account — Uttam Tailors",
            "desc": "Manage your account, orders, wishlist and measurements.",
            "robots": "noindex,nofollow", "og_image": "", "canonical": ""
        }
    )


# ── Google OAuth ──────────────────────────────────────────────────────────────

@website_bp.route("/auth/google/login")
def auth_google_login():
    """Redirect user to Google OAuth consent screen."""
    import secrets as _sec, urllib.parse as _up
    from config import Config
    client_id = Config.GOOGLE_CLIENT_ID
    if not client_id:
        next_url = request.args.get("next", "/account")
        return redirect(f"{next_url}?google_error=Google+sign-in+is+not+configured+yet")

    state = _sec.token_urlsafe(24)
    session["oauth_state"]    = state
    session["oauth_next"]     = request.args.get("next", "/account")

    params = {
        "client_id":     client_id,
        "redirect_uri":  _google_redirect_uri(),
        "response_type": "code",
        "scope":         "openid email profile",
        "state":         state,
        "access_type":   "online",
        "prompt":        "select_account",
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + _up.urlencode(params)
    return redirect(url)


@website_bp.route("/auth/google/callback")
def auth_google_callback():
    """Handle Google OAuth callback — create or log in account."""
    import urllib.parse as _up
    from config import Config
    import requests as _req

    # CSRF check
    state      = request.args.get("state", "")
    sess_state = session.pop("oauth_state", "")
    next_url   = session.pop("oauth_next", "/account")
    # Validate next_url is a safe relative path (prevent open redirect)
    if not next_url or not next_url.startswith("/") or next_url.startswith("//"):
        next_url = "/account"
    error      = request.args.get("error", "")

    if error:
        return redirect(f"{next_url}?google_error=Google+sign-in+was+cancelled")
    if not state or state != sess_state:
        return redirect(f"{next_url}?google_error=Invalid+OAuth+state+%E2%80%94+please+try+again")

    code = request.args.get("code", "")
    if not code:
        return redirect(f"{next_url}?google_error=No+authorisation+code+from+Google")

    # Exchange code for tokens
    try:
        tok_resp = _req.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code":          code,
                "client_id":     Config.GOOGLE_CLIENT_ID,
                "client_secret": Config.GOOGLE_CLIENT_SECRET,
                "redirect_uri":  _google_redirect_uri(),
                "grant_type":    "authorization_code",
            },
            timeout=10,
        )
        tok_data = tok_resp.json()
    except Exception:
        return redirect(f"{next_url}?google_error=Could+not+reach+Google+%E2%80%94+try+again")

    if "error" in tok_data:
        return redirect(f"{next_url}?google_error=Google+token+error+%E2%80%94+please+try+again")

    access_token = tok_data.get("access_token", "")
    if not access_token:
        return redirect(f"{next_url}?google_error=Missing+access+token+from+Google")

    # Fetch user info
    try:
        ui_resp = _req.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        ui = ui_resp.json()
    except Exception:
        return redirect(f"{next_url}?google_error=Could+not+fetch+Google+profile")

    google_id = ui.get("sub", "")
    email     = (ui.get("email") or "").strip().lower()
    name      = (ui.get("name")  or ui.get("given_name") or "").strip()

    if not google_id or not email:
        return redirect(f"{next_url}?google_error=Google+did+not+share+your+email")

    # Create or log in account
    db  = get_db()
    acc = db.execute(
        "SELECT * FROM web_accounts WHERE google_id=? AND is_active=1 LIMIT 1",
        (google_id,)
    ).fetchone()

    if not acc:
        # Try matching by email (user may have signed up via email before)
        acc = db.execute(
            "SELECT * FROM web_accounts WHERE LOWER(email)=? AND is_active=1 LIMIT 1",
            (email,)
        ).fetchone()

    if acc:
        # Update google_id if not set
        if not acc["google_id"]:
            db.execute("UPDATE web_accounts SET google_id=? WHERE id=?", (google_id, acc["id"]))
            db.commit()
        session["web_account_id"] = acc["id"]
        session.permanent = True
        return redirect(next_url)
    else:
        # New user — create account with free tokens
        try:
            free_tokens = NEW_ACCOUNT_FREE_TOKENS
        except NameError:
            free_tokens = 3
        # mobile must be unique+NOT NULL — Google users get a unique placeholder
        _g_mobile = f"g:{google_id}"
        try:
            db.execute(
                "INSERT INTO web_accounts(name, email, mobile, google_id, password_hash, token_balance, is_active, created_at) "
                "VALUES(?,?,?,?,?,?,1,datetime('now','localtime'))",
                (name, email, _g_mobile, google_id, "", free_tokens)
            )
            db.commit()
        except Exception as _ie:
            import logging as _lg
            _lg.getLogger(__name__).error("Google signup INSERT failed for %s: %s", email, _ie)
            return redirect(f"{next_url}?google_error=Account+creation+failed+%E2%80%94+please+try+again")
        new_acc = db.execute(
            "SELECT * FROM web_accounts WHERE google_id=? LIMIT 1", (google_id,)
        ).fetchone()
        if new_acc:
            session["web_account_id"] = new_acc["id"]
            session.permanent = True
            try:
                db.execute(
                    "INSERT INTO token_transactions(account_id, tokens, type) VALUES(?,?,'signup_bonus')",
                    (new_acc["id"], free_tokens)
                )
                db.commit()
            except Exception:
                pass  # non-critical
        return redirect(next_url)


def _google_redirect_uri():
    """Canonical redirect URI — always use the production domain."""
    return "https://uttamtailors.in/auth/google/callback"


# ── OTP endpoints ─────────────────────────────────────────────────────────────

@website_bp.route("/api/send-otp", methods=["POST"])
@_rl("5 per minute; 10 per hour")   # 5 SMS requests/min per IP — stops OTP flooding
def api_send_otp():
    data = request.get_json(silent=True) or {}
    mobile = (data.get("mobile") or "").strip()
    purpose = (data.get("purpose") or "login").strip()
    if not mobile:
        return jsonify({"success": False, "error": "Mobile required"})
    try:
        db = get_db()
        # Rate limit: max 3 OTPs per mobile per 10 minutes
        recent = db.execute(
            """SELECT COUNT(*) as cnt FROM otp_log
               WHERE mobile=? AND created_at > datetime('now','localtime','-10 minutes')
               AND used=0""",
            (mobile,)
        ).fetchone()
        if recent and recent["cnt"] >= 3:
            return jsonify({"success": False, "error": "Too many OTPs. Please wait 10 minutes."})
        from app.utils.sms import send_otp as _send_otp
        otp = _send_otp(mobile)
        if not otp:
            return jsonify({"success": False, "error": "Failed to send OTP"})
        db.execute(
            """INSERT INTO otp_log (mobile, otp, purpose) VALUES (?, ?, ?)""",
            (mobile, otp, purpose)
        )
        db.commit()
        return jsonify({"success": True, "message": "OTP sent"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})



# ── Token credit system ───────────────────────────────────────────────────────
# Each AI generation costs 1 token. Anonymous visitors get FREE_PREVIEW_LIMIT
# free generations; after that they must log in and buy token packs.
# Razorpay collects payment → webhook/verify credits the account automatically.

TOKEN_PACKS = {
     5:  4900,   #  5 credits → ₹49
    15:  9900,   # 15 credits → ₹99
    40: 19900,   # 40 credits → ₹199
}


# ── Email OTP signup / login for AI Studio gate ───────────────────────────────
import random as _random, hashlib as _hashlib

NEW_ACCOUNT_FREE_TOKENS = 3   # tokens gifted on first signup

@website_bp.route("/api/account/send-email-otp", methods=["POST"])
def api_send_email_otp():
    """Send a 6-digit OTP to an email for signup verification."""
    try:
        from app.utils.email_notify import send_otp_email
        import random as _rnd
        data  = request.get_json(force=True, silent=True) or {}
        email = (data.get("email") or "").strip().lower()
        name  = (data.get("name")  or "").strip()
        if not email or "@" not in email:
            return jsonify({"ok": False, "error": "Enter a valid email address"})

        db = get_db()
        # Ensure otp store table exists
        db.execute("""CREATE TABLE IF NOT EXISTS web_otp_store (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mobile TEXT NOT NULL DEFAULT '',
            otp TEXT NOT NULL DEFAULT '',
            expires_at TEXT NOT NULL DEFAULT '',
            used INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime')))""")
        db.commit()

        # Block if email already registered
        try:
            existing = db.execute("SELECT id FROM web_accounts WHERE email=?", (email,)).fetchone()
        except Exception:
            existing = None
        if existing:
            return jsonify({"ok": False, "error": "This email is already registered — please log in", "already_exists": True})

        otp = str(_rnd.randint(100000, 999999))
        try:
            db.execute("UPDATE web_otp_store SET used=1 WHERE mobile=? AND used=0", (email,))
        except Exception:
            pass
        db.execute(
            "INSERT INTO web_otp_store(phone, mobile, otp, expires_at) VALUES(?, ?, ?, datetime('now','localtime','+10 minutes'))",
            (email, email, otp)
        )
        db.commit()

        sent = send_otp_email(email, otp, name)
        if not sent:
            return jsonify({"ok": False, "error": "Could not send email — please check your email address."})
        return jsonify({"ok": True, "message": f"OTP sent to {email}"})
    except Exception as ex:
        import logging as _logging
        _logging.getLogger(__name__).error("send-email-otp error: %s", ex, exc_info=True)
        return jsonify({"ok": False, "error": "Could not send OTP — please try again."})


@website_bp.route("/api/account/verify-email-otp", methods=["POST"])
@_rl("10 per minute; 30 per hour")   # OTP brute-force guard
def api_verify_email_otp():
    """Verify OTP → create account with free tokens → log in."""
    data     = request.get_json(force=True, silent=True) or {}
    email    = (data.get("email")    or "").strip().lower()
    otp      = (data.get("otp")      or "").strip()
    name     = (data.get("name")     or "").strip()
    password = (data.get("password") or "").strip()

    if not email or not otp or not password:
        return jsonify({"ok": False, "error": "Email, OTP and password are required"})
    if len(password) < 6:
        return jsonify({"ok": False, "error": "Password must be at least 6 characters"})

    db = get_db()
    row = db.execute(
        """SELECT * FROM web_otp_store
           WHERE mobile=? AND otp=? AND used=0
             AND expires_at >= datetime('now','localtime')
           ORDER BY id DESC LIMIT 1""",
        (email, otp)
    ).fetchone()
    if not row:
        return jsonify({"ok": False, "error": "Invalid or expired OTP — request a new one"})

    db.execute("UPDATE web_otp_store SET used=1 WHERE id=?", (row["id"],))

    # Create account
    from werkzeug.security import generate_password_hash as _gph
    pw_hash = _gph(password)
    try:
        db.execute(
            "INSERT INTO web_accounts(name, email, mobile, password_hash, token_balance, is_active, created_at) "
            "VALUES(?,?,?,?,?,1,datetime('now','localtime'))",
            (name or email.split("@")[0], email, '', pw_hash, NEW_ACCOUNT_FREE_TOKENS)
        )
        db.commit()
    except Exception as e:
        return jsonify({"ok": False, "error": "Account creation failed: " + str(e)})

    acc = db.execute("SELECT * FROM web_accounts WHERE LOWER(email)=?", (email,)).fetchone()
    if not acc:
        return jsonify({"ok": False, "error": "Account creation failed"})

    # Log the 3 free tokens as a transaction
    try:
        db.execute(
            "INSERT INTO token_transactions(account_id, tokens, type) VALUES(?,?,'signup_bonus')",
            (acc["id"], NEW_ACCOUNT_FREE_TOKENS)
        )
        db.commit()
    except Exception:
        pass

    session["web_account_id"] = acc["id"]
    session.permanent = True
    return jsonify({
        "ok": True,
        "token_balance": NEW_ACCOUNT_FREE_TOKENS,
        "account": {"id": acc["id"], "name": acc["name"] or "", "email": email}
    })


@website_bp.route("/api/account/email-login", methods=["POST"])
@_rl("10 per minute; 30 per hour")   # Password brute-force guard
def api_email_login():
    """Login with email + password."""
    from werkzeug.security import check_password_hash as _cph
    data     = request.get_json(force=True, silent=True) or {}
    email    = (data.get("email")    or "").strip().lower()
    password = (data.get("password") or "").strip()
    if not email or not password:
        return jsonify({"ok": False, "error": "Email and password are required"})

    db  = get_db()
    acc = db.execute(
        "SELECT * FROM web_accounts WHERE LOWER(email)=? AND is_active=1", (email,)
    ).fetchone()
    pw_hash = acc["password_hash"] if acc and "password_hash" in acc.keys() else ""
    # Detect Google-only account (no password set)
    if acc and not pw_hash and acc["google_id"]:
        return jsonify({"ok": False, "error": "google_account",
                        "message": "This email is linked to Google sign-in. Please use \"Continue with Google\" to log in."})
    if not acc or not pw_hash or not _cph(pw_hash, password):
        return jsonify({"ok": False, "error": "Invalid email or password"})

    session["web_account_id"] = acc["id"]
    session.permanent = True
    tok = acc["token_balance"] if "token_balance" in acc.keys() else 0
    return jsonify({
        "ok": True,
        "token_balance": tok or 0,
        "account": {"id": acc["id"], "name": acc["name"] or "", "email": email}
    })


@website_bp.route("/api/tokens/debug-keys")
def api_tokens_debug_keys():
    """Temporary debug — shows key format without exposing full values."""
    from flask import session as _s
    # Only owner can call this
    acc = _current_account()
    if not acc:
        return jsonify({"ok": False, "error": "not logged in"})
    db = get_db()
    _rz1 = db.execute("SELECT value FROM settings WHERE key='razorpay_key_id'").fetchone()
    _rz2 = db.execute("SELECT value FROM settings WHERE key='razorpay_key_secret'").fetchone()
    key_id  = (_rz1["value"] if _rz1 else "")
    key_sec = (_rz2["value"] if _rz2 else "")
    return jsonify({
        "key_id_prefix": key_id[:12] if key_id else "(empty)",
        "key_id_len": len(key_id),
        "key_sec_prefix": key_sec[:8] if key_sec else "(empty)",
        "key_sec_len": len(key_sec),
        "key_id_has_spaces": " " in key_id or key_id != key_id.strip(),
        "key_sec_has_spaces": " " in key_sec or key_sec != key_sec.strip(),
    })

@website_bp.route("/api/tokens/create-order", methods=["POST"])
def api_tokens_create_order():
    """Create a Razorpay order for a token pack purchase."""
    acc = _current_account()
    if not acc:
        return jsonify({"ok": False, "error": "Please log in before purchasing credits."})
    data   = request.get_json() or {}
    tokens = int(data.get("tokens", 0))
    price  = data.get("price")
    if tokens not in TOKEN_PACKS:
        return jsonify({"ok": False, "error": "Invalid token pack."})
    amount_paise = TOKEN_PACKS[tokens]
    db = get_db()
    try:
        _rz1 = db.execute("SELECT value FROM settings WHERE key='razorpay_key_id'").fetchone()
        _rz2 = db.execute("SELECT value FROM settings WHERE key='razorpay_key_secret'").fetchone()
        def _rz_clean(v): return (v.split("=",1)[-1] if v and "=" in v else v or "").strip()
        rz_key_id  = _rz_clean(_rz1["value"] if _rz1 else "")
        rz_key_sec = _rz_clean(_rz2["value"] if _rz2 else "")
    except Exception:
        rz_key_id = rz_key_sec = ""
    if not rz_key_id or not rz_key_sec:
        return jsonify({"ok": False, "error": "Payment gateway not configured yet. Please contact us directly."})
    try:
        import requests as _req, uuid
        resp = _req.post(
            "https://api.razorpay.com/v1/orders",
            auth=(rz_key_id, rz_key_sec),
            json={"amount": amount_paise, "currency": "INR",
                  "receipt": f"tok_{acc['id']}_{tokens}_{uuid.uuid4().hex[:8]}",
                  "notes": {"account_id": str(acc["id"]), "tokens": str(tokens)}},
            timeout=10
        ).json()
        if "id" not in resp:
            rz_err = (resp.get("error") or {}).get("description") or str(resp)
            return jsonify({"ok": False, "error": f"Razorpay: {rz_err}"})
        return jsonify({"ok": True, "order_id": resp["id"],
                        "amount": amount_paise, "razorpay_key": rz_key_id})
    except Exception as ex:
        return jsonify({"ok": False, "error": str(ex)})


@website_bp.route("/api/tokens/verify-payment", methods=["POST"])
def api_tokens_verify_payment():
    """Verify Razorpay signature and credit tokens to account."""
    acc = _current_account()
    if not acc:
        return jsonify({"ok": False, "error": "Not logged in."})
    data = request.get_json() or {}
    payment_id = (data.get("razorpay_payment_id") or "").strip()
    order_id   = (data.get("razorpay_order_id")   or "").strip()
    signature  = (data.get("razorpay_signature")   or "").strip()
    tokens     = int(data.get("tokens", 0))
    if tokens not in TOKEN_PACKS or not payment_id or not order_id or not signature:
        return jsonify({"ok": False, "error": "Invalid payment data."})
    db = get_db()
    try:
        _rz2b = db.execute("SELECT value FROM settings WHERE key='razorpay_key_secret'").fetchone()
        _raw_sec = (_rz2b["value"] if _rz2b else "")
        # Strip env-var prefix if stored as "RAZORPAY_KEY_SECRET=actual_secret"
        rz_key_sec = (_raw_sec.split("=",1)[-1] if _raw_sec and "=" in _raw_sec else _raw_sec or "").strip()
    except Exception:
        rz_key_sec = ""
    if not rz_key_sec:
        return jsonify({"ok": False, "error": "Payment gateway not configured."})
    # Verify HMAC signature
    import hmac as _hmac, hashlib as _hashlib
    expected = _hmac.new(
        rz_key_sec.encode(), f"{order_id}|{payment_id}".encode(), _hashlib.sha256
    ).hexdigest()
    if not _hmac.compare_digest(expected, signature):
        return jsonify({"ok": False, "error": "Payment verification failed. Please contact support."})
    # Guard: reject duplicate payment_id
    try:
        dup = db.execute("SELECT id FROM token_transactions WHERE razorpay_payment_id=?", (payment_id,)).fetchone()
        if dup:
            return jsonify({"ok": False, "error": "This payment was already credited."})
    except Exception:
        pass
    try:
        db.execute(
            "UPDATE web_accounts SET token_balance = COALESCE(token_balance,0)+? WHERE id=?",
            (tokens, acc["id"])
        )
        db.execute(
            """INSERT INTO token_transactions (account_id, tokens, type, razorpay_payment_id, razorpay_order_id)
               VALUES (?,?,'purchase',?,?)""",
            (acc["id"], tokens, payment_id, order_id)
        )
        db.commit()
        new_bal = db.execute("SELECT token_balance FROM web_accounts WHERE id=?", (acc["id"],)).fetchone()["token_balance"]
        return jsonify({"ok": True, "token_balance": new_bal})
    except Exception as ex:
        return jsonify({"ok": False, "error": str(ex)})


@website_bp.route("/api/tokens/history")
def api_tokens_history():
    """Return logged-in customer's token balance + full transaction log."""
    acc = _current_account()
    if not acc:
        return jsonify({"ok": False, "error": "Not logged in."}), 401
    db = get_db()
    try:
        bal_row = db.execute(
            "SELECT token_balance FROM web_accounts WHERE id=?", (acc["id"],)
        ).fetchone()
        balance = int(bal_row["token_balance"] or 0) if bal_row else 0
        rows = db.execute(
            """SELECT id, tokens, type, razorpay_payment_id, created_at
               FROM token_transactions
               WHERE account_id=?
               ORDER BY id DESC LIMIT 100""",
            (acc["id"],)
        ).fetchall()
        # Reverse-map token count → amount paid for purchase transactions
        _pack_map = {5: 49, 15: 99, 40: 199}
        txns = []
        for r in rows:
            t = dict(r)
            t["amount_paid"] = _pack_map.get(t["tokens"], 0) if t["type"] == "purchase" else 0
            txns.append(t)
        return jsonify({"ok": True, "balance": balance, "transactions": txns})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@website_bp.route("/api/verify-otp", methods=["POST"])
@_rl("10 per minute; 20 per hour")   # Brute-force guard: max 10 guesses/min per IP
def api_verify_otp():
    data = request.get_json(silent=True) or {}
    mobile = (data.get("mobile") or "").strip()
    otp    = (data.get("otp") or "").strip()
    if not mobile or not otp:
        return jsonify({"success": False, "error": "Mobile and OTP required"})
    # Input length guard — real OTPs are 6 digits
    if not otp.isdigit() or len(otp) not in (4, 6):
        return jsonify({"success": False, "error": "Invalid OTP format"})
    try:
        db = get_db()
        # Brute-force lockout: if 5+ failed attempts on this mobile in last 15 min, block
        fails = db.execute(
            """SELECT COUNT(*) as cnt FROM otp_log
               WHERE mobile=? AND used=2
               AND created_at > datetime('now','localtime','-15 minutes')""",
            (mobile,)
        ).fetchone()
        if fails and fails["cnt"] >= 5:
            return jsonify({"success": False, "error": "Too many failed attempts. Please request a new OTP."})

        row = db.execute(
            """SELECT id FROM otp_log
               WHERE mobile=? AND otp=? AND used=0
               AND expires_at > datetime('now','localtime')
               ORDER BY id DESC LIMIT 1""",
            (mobile, otp)
        ).fetchone()
        if not row:
            # Mark failed attempt (used=2) so we can count brute-force retries
            db.execute(
                """UPDATE otp_log SET used=2
                   WHERE mobile=? AND used=0
                   AND expires_at > datetime('now','localtime')""",
                (mobile,)
            )
            db.commit()
            return jsonify({"success": False, "error": "Invalid or expired OTP"})
        db.execute("UPDATE otp_log SET used=1 WHERE id=?", (row["id"],))
        db.commit()
        return jsonify({"success": True, "message": "OTP verified"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
