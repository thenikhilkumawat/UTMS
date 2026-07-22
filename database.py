import os
import sqlite3
from config import Config

# ── Detect PostgreSQL or SQLite ──────────────────────────────────────────────
USE_PG = bool(os.environ.get("DATABASE_URL", ""))

if USE_PG:
    import psycopg2
    import psycopg2.extras
    import re

    class _Row(dict):
        def __getitem__(self, key):
            if isinstance(key, int):
                return list(self.values())[key]
            return super().__getitem__(key)
        def keys(self):
            return super().keys()

    class _Cursor:
        def __init__(self, cur):
            self._cur = cur

        def _fix(self, sql, params):
            import re as _re
            sql = _re.sub(r"%(?![s{])", "%%", sql)
            sql = sql.replace("?", "%s")
            sql = sql.replace("datetime('now','localtime')", "NOW()")
            sql = sql.replace("datetime('now')",             "NOW()")
            sql = sql.replace("date('now','localtime')",     "CURRENT_DATE")
            sql = sql.replace("date('now')",                 "CURRENT_DATE")
            sql = re.sub(r"GROUP_CONCAT\((.+?),\s*'(.+?)'\)",
                         lambda m: f"STRING_AGG(CAST({m.group(1)} AS TEXT), '{m.group(2)}')", sql)
            sql = re.sub(r"INSERT\s+OR\s+IGNORE\s+INTO",  "INSERT INTO", sql, flags=re.IGNORECASE)
            sql = re.sub(r"INSERT\s+OR\s+REPLACE\s+INTO", "INSERT INTO", sql, flags=re.IGNORECASE)
            if "INTO settings" in sql and "ON CONFLICT" not in sql:
                sql = sql.rstrip().rstrip(";") + " ON CONFLICT(key) DO UPDATE SET value=EXCLUDED.value"
            elif "INSERT INTO" in sql and "ON CONFLICT" not in sql and "DO NOTHING" not in sql:
                sql = sql.rstrip().rstrip(";") + " ON CONFLICT DO NOTHING"
            return sql, params or []

        def execute(self, sql, params=None):
            sql, params = self._fix(sql, params)
            try:
                self._cur.execute(sql, params)
            except Exception as e:
                try:
                    self._cur.connection.rollback()
                except Exception:
                    pass
                raise e
            return self

        def fetchone(self):
            row = self._cur.fetchone()
            if row is None: return None
            cols = [d[0] for d in self._cur.description]
            return _Row(zip(cols, row))

        def fetchall(self):
            rows = self._cur.fetchall()
            if not rows: return []
            cols = [d[0] for d in self._cur.description]
            return [_Row(zip(cols, r)) for r in rows]

        @property
        def lastrowid(self):
            try:
                self._cur.execute("SELECT lastval()")
                row = self._cur.fetchone()
                return int(row[0]) if row else None
            except Exception:
                return None

        @property
        def rowcount(self):
            return self._cur.rowcount

    class _Conn:
        def __init__(self, conn):
            self._conn = conn
            self._closed = False
        def execute(self, sql, params=None):
            cur = _Cursor(self._conn.cursor())
            cur.execute(sql, params or [])
            return cur
        def cursor(self):
            return _Cursor(self._conn.cursor())
        def commit(self):
            if not self._closed:
                self._conn.commit()
        def close(self):
            if not self._closed:
                self._closed = True
                try:
                    self._conn.close()
                except Exception:
                    pass
        def __enter__(self): return self
        def __exit__(self, *a):
            try:
                self._conn.commit()
            except Exception:
                pass
            self.close()
        def __del__(self):
            self.close()

    def get_db():
        url = os.environ["DATABASE_URL"]
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        for attempt in range(3):
            try:
                conn = psycopg2.connect(url, connect_timeout=10)
                conn.autocommit = False
                cur = conn.cursor()
                cur.execute("SELECT 1")
                cur.close()
                return _Conn(conn)
            except Exception:
                if attempt == 2:
                    raise
                import time
                time.sleep(1)

else:
    def get_db():
        conn = sqlite3.connect(Config.DATABASE, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=10000")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn


# ── init_db ───────────────────────────────────────────────────────────────────

def init_db():
    if USE_PG:
        _init_pg()
    else:
        _init_sqlite()


def _init_pg():
    url = os.environ["DATABASE_URL"]
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    conn = psycopg2.connect(url)
    cur  = conn.cursor()
    statements = [
        """CREATE TABLE IF NOT EXISTS customers (
            id SERIAL PRIMARY KEY, name TEXT NOT NULL,
            mobile TEXT, address TEXT,
            created_at TEXT DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'))""",
        """CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY, order_code TEXT UNIQUE NOT NULL,
            customer_id INTEGER, order_date TEXT, delivery_date TEXT,
            total_amount REAL DEFAULT 0, extra_charges REAL DEFAULT 0,
            payable_amount REAL DEFAULT 0, advance_paid REAL DEFAULT 0,
            remaining REAL DEFAULT 0, payment_mode TEXT DEFAULT 'cash',
            status TEXT DEFAULT 'received', is_urgent INTEGER DEFAULT 0,
            note TEXT DEFAULT '', repeat_of TEXT,
            delivered_at TEXT, created_at TEXT DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'))""",
        """CREATE TABLE IF NOT EXISTS order_items (
            id SERIAL PRIMARY KEY, order_id INTEGER NOT NULL,
            garment_type TEXT, quantity INTEGER DEFAULT 1,
            rate REAL DEFAULT 0, amount REAL DEFAULT 0,
            measurements TEXT DEFAULT '{}', notes TEXT DEFAULT '')""",
        """CREATE TABLE IF NOT EXISTS order_images (
            id SERIAL PRIMARY KEY, order_id INTEGER NOT NULL,
            image_url TEXT NOT NULL, uploaded_at TEXT DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'))""",
        """CREATE TABLE IF NOT EXISTS work_logs (
            id SERIAL PRIMARY KEY, order_id INTEGER, order_code TEXT DEFAULT '',
            garment_type TEXT DEFAULT '', qty_done INTEGER DEFAULT 0,
            employee_name TEXT DEFAULT '', log_date TEXT,
            making_rate REAL DEFAULT 0, notes TEXT DEFAULT '',
            created_at TEXT DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'))""",
        """CREATE TABLE IF NOT EXISTS finance (
            id SERIAL PRIMARY KEY, tx_date TEXT, tx_type TEXT DEFAULT 'income',
            category TEXT, amount REAL DEFAULT 0, mode TEXT DEFAULT '',
            order_id INTEGER, note TEXT DEFAULT '', employee_name TEXT DEFAULT '',
            created_by TEXT DEFAULT '', created_at TEXT DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'))""",
        """CREATE TABLE IF NOT EXISTS employees (
            id SERIAL PRIMARY KEY, name TEXT NOT NULL, role TEXT,
            mobile TEXT, salary REAL DEFAULT 0, join_date TEXT, active INTEGER DEFAULT 1)""",
        """CREATE TABLE IF NOT EXISTS salary_advances (
            id SERIAL PRIMARY KEY, employee_id INTEGER, amount REAL DEFAULT 0,
            reason TEXT, date TEXT, created_at TEXT DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'))""",
        """CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)""",
        """CREATE TABLE IF NOT EXISTS measurement_fields (
            id SERIAL PRIMARY KEY, garment_type TEXT NOT NULL,
            field_name TEXT NOT NULL, field_label TEXT, sort_order INTEGER DEFAULT 0)""",
        """CREATE TABLE IF NOT EXISTS inventory (
            id SERIAL PRIMARY KEY, item_name TEXT NOT NULL, category TEXT,
            quantity REAL DEFAULT 0, unit TEXT DEFAULT 'pcs',
            low_threshold REAL DEFAULT 0, low_alert_at REAL DEFAULT 0,
            last_updated TEXT)""",
        """CREATE TABLE IF NOT EXISTS gallery_types (
            id SERIAL PRIMARY KEY, name TEXT NOT NULL, slug TEXT UNIQUE)""",
        """CREATE TABLE IF NOT EXISTS gallery_images (
            id SERIAL PRIMARY KEY, type_id INTEGER, image_url TEXT,
            caption TEXT, sort_order INTEGER DEFAULT 0)""",
        """CREATE TABLE IF NOT EXISTS whatsapp_log (
            id SERIAL PRIMARY KEY, customer_id INTEGER, order_id INTEGER,
            template TEXT, message TEXT, status TEXT,
            sent_at TEXT DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'))""",
        """CREATE TABLE IF NOT EXISTS notify_log (
            id SERIAL PRIMARY KEY, order_id INTEGER, customer_id INTEGER,
            message TEXT, sent_at TEXT DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'))""",
        """CREATE TABLE IF NOT EXISTS shop_logo (
            id SERIAL PRIMARY KEY, image_url TEXT, updated_at TEXT)""",
        """CREATE TABLE IF NOT EXISTS web_service_categories (
            id SERIAL PRIMARY KEY, name TEXT NOT NULL, slug TEXT,
            sort_order INTEGER DEFAULT 0)""",
        """CREATE TABLE IF NOT EXISTS web_service_items (
            id SERIAL PRIMARY KEY, category_id INTEGER, name TEXT NOT NULL,
            subtitle TEXT, price REAL DEFAULT 0, sort_order INTEGER DEFAULT 0,
            image_url TEXT, video_url TEXT, description TEXT, long_desc TEXT)""",
        """CREATE TABLE IF NOT EXISTS web_fabrics (
            id SERIAL PRIMARY KEY, name TEXT NOT NULL, price_per_metre REAL DEFAULT 0,
            stock_metres REAL DEFAULT 0, image_url TEXT, active INTEGER DEFAULT 1,
            sort_order INTEGER DEFAULT 0, fabric_type TEXT DEFAULT '')""",
        """CREATE TABLE IF NOT EXISTS web_fabric_media (
            id SERIAL PRIMARY KEY, fabric_id INTEGER NOT NULL,
            url TEXT NOT NULL, sort_order INTEGER DEFAULT 0)""",
        """CREATE TABLE IF NOT EXISTS web_otp_store (
            id SERIAL PRIMARY KEY, mobile TEXT NOT NULL, otp TEXT,
            created_at TEXT DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'))""",
        """CREATE TABLE IF NOT EXISTS web_story_timeline (
            id SERIAL PRIMARY KEY, year TEXT, title TEXT, body TEXT, sort_order INTEGER DEFAULT 0)""",
        """CREATE TABLE IF NOT EXISTS web_item_media (
            id SERIAL PRIMARY KEY, item_id INTEGER NOT NULL,
            media_type TEXT DEFAULT 'image', url TEXT NOT NULL, sort_order INTEGER DEFAULT 0)""",
        """CREATE TABLE IF NOT EXISTS web_item_reviews (
            id SERIAL PRIMARY KEY, item_id INTEGER NOT NULL,
            reviewer_name TEXT NOT NULL, review_text TEXT DEFAULT '',
            rating INTEGER DEFAULT 5, created_at TEXT DEFAULT '')""",
        """CREATE TABLE IF NOT EXISTS garment_style_options (
            id SERIAL PRIMARY KEY, item_id INTEGER NOT NULL,
            option_group TEXT NOT NULL, option_label TEXT NOT NULL,
            option_values TEXT NOT NULL DEFAULT '', sort_order INTEGER DEFAULT 0,
            is_required INTEGER DEFAULT 0)""",
        """CREATE TABLE IF NOT EXISTS garment_style_values (
            id SERIAL PRIMARY KEY,
            option_id INTEGER NOT NULL,
            value_label TEXT NOT NULL,
            value_key TEXT NOT NULL DEFAULT '',
            image_url TEXT DEFAULT '',
            sort_order INTEGER DEFAULT 0,
            ai_prompt TEXT DEFAULT '')""",
        """CREATE TABLE IF NOT EXISTS web_coupons (
            id SERIAL PRIMARY KEY, code TEXT NOT NULL UNIQUE,
            discount_type TEXT NOT NULL DEFAULT 'fixed',
            discount_value REAL NOT NULL DEFAULT 0,
            min_order REAL NOT NULL DEFAULT 0,
            max_uses INTEGER DEFAULT 0, used_count INTEGER DEFAULT 0,
            active INTEGER DEFAULT 1, expires_on TEXT DEFAULT '',
            description TEXT DEFAULT '',
            created_at TEXT DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'))""",

        """CREATE TABLE IF NOT EXISTS web_pages (
            id SERIAL PRIMARY KEY, title TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE, content TEXT DEFAULT '',
            show_in_footer INTEGER DEFAULT 1, sort_order INTEGER DEFAULT 0,
            created_at TEXT DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'))""",
        """CREATE TABLE IF NOT EXISTS web_nav_items (
            id SERIAL PRIMARY KEY, label TEXT NOT NULL,
            url TEXT NOT NULL, open_new_tab INTEGER DEFAULT 0,
            sort_order INTEGER DEFAULT 0, active INTEGER DEFAULT 1)""",
        """CREATE TABLE IF NOT EXISTS web_footer_make (
            id SERIAL PRIMARY KEY, label TEXT NOT NULL,
            url TEXT DEFAULT '', sort_order INTEGER DEFAULT 0)""",
        """CREATE TABLE IF NOT EXISTS garment_default_sizes (
            id SERIAL PRIMARY KEY, garment_category TEXT NOT NULL,
            size_label TEXT NOT NULL, measurements TEXT NOT NULL DEFAULT '{}',
            UNIQUE(garment_category, size_label))""",
        """CREATE TABLE IF NOT EXISTS seo_static_pages (
            id SERIAL PRIMARY KEY, page_key TEXT UNIQUE NOT NULL,
            page_name TEXT DEFAULT '', meta_title TEXT DEFAULT '',
            meta_desc TEXT DEFAULT '', og_image TEXT DEFAULT '',
            robots TEXT DEFAULT 'index,follow', canonical TEXT DEFAULT '')""",
        """CREATE TABLE IF NOT EXISTS web_accounts (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL, mobile TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            preview_count INTEGER DEFAULT 0,
            tryon_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'))""",
    ]
    for stmt in statements:
        try:
            cur.execute(stmt)
        except Exception:
            conn.rollback()
    conn.commit()
    cur.close()
    conn.close()


def _init_sqlite():
    conn = sqlite3.connect(Config.DATABASE)
    cur  = conn.cursor()

    tables = [
        """CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            mobile TEXT, address TEXT, created_at TEXT DEFAULT (datetime('now')))""",
        """CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT, order_code TEXT UNIQUE NOT NULL,
            customer_id INTEGER, order_date TEXT, delivery_date TEXT,
            total_amount REAL DEFAULT 0, extra_charges REAL DEFAULT 0,
            payable_amount REAL DEFAULT 0, advance_paid REAL DEFAULT 0,
            remaining REAL DEFAULT 0, payment_mode TEXT DEFAULT 'cash',
            status TEXT DEFAULT 'received', is_urgent INTEGER DEFAULT 0,
            note TEXT DEFAULT '', repeat_of TEXT,
            delivered_at TEXT, created_at TEXT DEFAULT (datetime('now')))""",
        """CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL,
            garment_type TEXT, quantity INTEGER DEFAULT 1,
            rate REAL DEFAULT 0, amount REAL DEFAULT 0,
            measurements TEXT DEFAULT '{}', notes TEXT DEFAULT '')""",
        """CREATE TABLE IF NOT EXISTS order_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL,
            image_url TEXT NOT NULL, uploaded_at TEXT DEFAULT (datetime('now')))""",
        """CREATE TABLE IF NOT EXISTS work_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER, order_code TEXT DEFAULT '',
            garment_type TEXT DEFAULT '', qty_done INTEGER DEFAULT 0,
            employee_name TEXT DEFAULT '', log_date TEXT,
            making_rate REAL DEFAULT 0, notes TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')))""",
        """CREATE TABLE IF NOT EXISTS finance (
            id INTEGER PRIMARY KEY AUTOINCREMENT, tx_date TEXT, tx_type TEXT DEFAULT 'income',
            category TEXT, amount REAL DEFAULT 0, mode TEXT DEFAULT '',
            order_id INTEGER, note TEXT DEFAULT '', employee_name TEXT DEFAULT '',
            created_by TEXT DEFAULT '', created_at TEXT DEFAULT (datetime('now')))""",
        """CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, role TEXT,
            mobile TEXT, salary REAL DEFAULT 0, join_date TEXT, active INTEGER DEFAULT 1)""",
        """CREATE TABLE IF NOT EXISTS salary_advances (
            id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id INTEGER,
            amount REAL DEFAULT 0, reason TEXT, date TEXT,
            created_at TEXT DEFAULT (datetime('now')))""",
        """CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)""",
        """CREATE TABLE IF NOT EXISTS measurement_fields (
            id INTEGER PRIMARY KEY AUTOINCREMENT, garment_type TEXT NOT NULL,
            field_name TEXT NOT NULL, field_label TEXT, sort_order INTEGER DEFAULT 0)""",
        """CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT NOT NULL,
            category TEXT, quantity REAL DEFAULT 0, unit TEXT DEFAULT 'pcs',
            low_threshold REAL DEFAULT 0, low_alert_at REAL DEFAULT 0,
            last_updated TEXT)""",
        """CREATE TABLE IF NOT EXISTS gallery_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, slug TEXT UNIQUE)""",
        """CREATE TABLE IF NOT EXISTS gallery_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT, type_id INTEGER,
            image_url TEXT, caption TEXT, sort_order INTEGER DEFAULT 0)""",
        """CREATE TABLE IF NOT EXISTS whatsapp_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER,
            order_id INTEGER, template TEXT, message TEXT, status TEXT,
            sent_at TEXT DEFAULT (datetime('now')))""",
        """CREATE TABLE IF NOT EXISTS notify_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER,
            customer_id INTEGER, message TEXT,
            sent_at TEXT DEFAULT (datetime('now')))""",
        """CREATE TABLE IF NOT EXISTS shop_logo (
            id INTEGER PRIMARY KEY AUTOINCREMENT, image_url TEXT, updated_at TEXT)""",
        """CREATE TABLE IF NOT EXISTS web_service_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            slug TEXT, sort_order INTEGER DEFAULT 0)""",
        """CREATE TABLE IF NOT EXISTS web_service_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, category_id INTEGER,
            name TEXT NOT NULL, subtitle TEXT, price REAL DEFAULT 0,
            sort_order INTEGER DEFAULT 0, image_url TEXT, video_url TEXT,
            description TEXT, long_desc TEXT)""",
        """CREATE TABLE IF NOT EXISTS web_fabrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            price_per_metre REAL DEFAULT 0, stock_metres REAL DEFAULT 0,
            image_url TEXT, active INTEGER DEFAULT 1,
            sort_order INTEGER DEFAULT 0, fabric_type TEXT DEFAULT '')""",
        """CREATE TABLE IF NOT EXISTS web_fabric_media (
            id INTEGER PRIMARY KEY AUTOINCREMENT, fabric_id INTEGER NOT NULL,
            url TEXT NOT NULL, sort_order INTEGER DEFAULT 0)""",
        """CREATE TABLE IF NOT EXISTS web_otp_store (
            id INTEGER PRIMARY KEY AUTOINCREMENT, mobile TEXT NOT NULL,
            otp TEXT, created_at TEXT DEFAULT (datetime('now')))""",
        """CREATE TABLE IF NOT EXISTS web_story_timeline (
            id INTEGER PRIMARY KEY AUTOINCREMENT, year TEXT, title TEXT,
            body TEXT, sort_order INTEGER DEFAULT 0)""",
        """CREATE TABLE IF NOT EXISTS web_item_media (
            id INTEGER PRIMARY KEY AUTOINCREMENT, item_id INTEGER NOT NULL,
            media_type TEXT DEFAULT 'image', url TEXT NOT NULL, sort_order INTEGER DEFAULT 0)""",
        """CREATE TABLE IF NOT EXISTS web_item_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT, item_id INTEGER NOT NULL,
            reviewer_name TEXT NOT NULL, review_text TEXT DEFAULT '',
            rating INTEGER DEFAULT 5, created_at TEXT DEFAULT '')""",
        """CREATE TABLE IF NOT EXISTS garment_style_options (
            id INTEGER PRIMARY KEY AUTOINCREMENT, item_id INTEGER NOT NULL,
            option_group TEXT NOT NULL, option_label TEXT NOT NULL,
            option_values TEXT NOT NULL DEFAULT '', sort_order INTEGER DEFAULT 0,
            is_required INTEGER DEFAULT 0)""",
        """CREATE TABLE IF NOT EXISTS garment_style_values (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            option_id INTEGER NOT NULL,
            value_label TEXT NOT NULL,
            value_key TEXT NOT NULL DEFAULT '',
            image_url TEXT DEFAULT '',
            sort_order INTEGER DEFAULT 0,
            ai_prompt TEXT DEFAULT '')""",
        """CREATE TABLE IF NOT EXISTS web_coupons (
            id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT NOT NULL UNIQUE,
            discount_type TEXT NOT NULL DEFAULT 'fixed',
            discount_value REAL NOT NULL DEFAULT 0,
            min_order REAL NOT NULL DEFAULT 0,
            max_uses INTEGER DEFAULT 0, used_count INTEGER DEFAULT 0,
            active INTEGER DEFAULT 1, expires_on TEXT DEFAULT '',
            description TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')))""",

        """CREATE TABLE IF NOT EXISTS web_pages (
            id SERIAL PRIMARY KEY, title TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE, content TEXT DEFAULT '',
            show_in_footer INTEGER DEFAULT 1, sort_order INTEGER DEFAULT 0,
            created_at TEXT DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'))""",
        """CREATE TABLE IF NOT EXISTS web_nav_items (
            id SERIAL PRIMARY KEY, label TEXT NOT NULL,
            url TEXT NOT NULL, open_new_tab INTEGER DEFAULT 0,
            sort_order INTEGER DEFAULT 0, active INTEGER DEFAULT 1)""",
        """CREATE TABLE IF NOT EXISTS web_footer_make (
            id SERIAL PRIMARY KEY, label TEXT NOT NULL,
            url TEXT DEFAULT '', sort_order INTEGER DEFAULT 0)""",
        """CREATE TABLE IF NOT EXISTS garment_default_sizes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, garment_category TEXT NOT NULL,
            size_label TEXT NOT NULL, measurements TEXT NOT NULL DEFAULT '{}',
            UNIQUE(garment_category, size_label))""",
        """CREATE TABLE IF NOT EXISTS seo_static_pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, page_key TEXT UNIQUE NOT NULL,
            page_name TEXT DEFAULT '', meta_title TEXT DEFAULT '',
            meta_desc TEXT DEFAULT '', og_image TEXT DEFAULT '',
            robots TEXT DEFAULT 'index,follow', canonical TEXT DEFAULT '')""",
        """CREATE TABLE IF NOT EXISTS web_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, mobile TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            preview_count INTEGER DEFAULT 0,
            tryon_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')))""",
    ]
    for stmt in tables:
        try:
            cur.execute(stmt)
        except Exception:
            pass
    conn.commit()
    conn.close()


# ── get_setting / set_setting ─────────────────────────────────────────────────

_settings_cache = {}
_settings_cache_valid = False

def get_setting(key, default=""):
    global _settings_cache, _settings_cache_valid
    if not _settings_cache_valid:
        try:
            db = get_db()
            rows = db.execute("SELECT key, value FROM settings").fetchall()
            _settings_cache = {r["key"]: r["value"] for r in rows}
            _settings_cache_valid = True
        except Exception:
            pass
    return _settings_cache.get(key, default)

def set_setting(key, value):
    global _settings_cache_valid
    try:
        db = get_db()
        db.execute("INSERT OR REPLACE INTO settings(key, value) VALUES(?, ?)", (key, str(value)))
        db.commit()
        _settings_cache_valid = False
    except Exception:
        pass


# ── Order code helpers ────────────────────────────────────────────────────────

def _get_order_counter(prefix="UT"):
    try:
        db = get_db()
        row = db.execute(
            "SELECT order_code FROM orders WHERE order_code LIKE ? ORDER BY id DESC LIMIT 1",
            (f"{prefix}-%",)
        ).fetchone()
        if row:
            try:
                return int(row["order_code"].split("-")[1]) + 1
            except Exception:
                pass
        start = int(get_setting("web_order_start_number", "1") or 1)
        return start
    except Exception:
        return 1

def next_order_code():
    n = _get_order_counter("UT")
    return f"UT-{str(n).zfill(4)}"

def peek_order_code():
    return next_order_code()

def next_repeat_code(original_code):
    try:
        db = get_db()
        row = db.execute(
            "SELECT order_code FROM orders WHERE repeat_of=? ORDER BY id DESC LIMIT 1",
            (original_code,)
        ).fetchone()
        base = original_code.rstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        suffix_ord = ord('B')
        if row:
            existing = row["order_code"]
            if existing[-1].isalpha():
                suffix_ord = ord(existing[-1]) + 1
        return base + chr(suffix_ord)
    except Exception:
        return original_code + "B"

def peek_repeat_code(original_code):
    return next_repeat_code(original_code)

# ── SEO Migrations — safe to run multiple times ───────────────────────────────

def make_slug(text):
    """Convert text to clean URL slug."""
    import re
    s = (text or "").lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s-]+", "-", s)
    return s.strip("-")


def run_seo_migrations():
    """Add SEO columns to existing tables. Safe to run multiple times."""
    try:
        db = get_db()
        if USE_PG:
            alters = [
                "ALTER TABLE web_service_items ADD COLUMN IF NOT EXISTS slug TEXT DEFAULT ''",
                "ALTER TABLE web_service_items ADD COLUMN IF NOT EXISTS meta_title TEXT DEFAULT ''",
                "ALTER TABLE web_service_items ADD COLUMN IF NOT EXISTS meta_desc TEXT DEFAULT ''",
                "ALTER TABLE web_service_categories ADD COLUMN IF NOT EXISTS meta_title TEXT DEFAULT ''",
                "ALTER TABLE web_service_categories ADD COLUMN IF NOT EXISTS meta_desc TEXT DEFAULT ''",
                "ALTER TABLE web_pages ADD COLUMN IF NOT EXISTS meta_title TEXT DEFAULT ''",
                "ALTER TABLE web_pages ADD COLUMN IF NOT EXISTS meta_desc TEXT DEFAULT ''",
            ]
            for stmt in alters:
                try:
                    db.execute(stmt)
                except Exception:
                    pass
        else:
            alters = [
                "ALTER TABLE web_service_items ADD COLUMN slug TEXT DEFAULT ''",
                "ALTER TABLE web_service_items ADD COLUMN meta_title TEXT DEFAULT ''",
                "ALTER TABLE web_service_items ADD COLUMN meta_desc TEXT DEFAULT ''",
                "ALTER TABLE web_service_categories ADD COLUMN meta_title TEXT DEFAULT ''",
                "ALTER TABLE web_service_categories ADD COLUMN meta_desc TEXT DEFAULT ''",
                "ALTER TABLE web_pages ADD COLUMN meta_title TEXT DEFAULT ''",
                "ALTER TABLE web_pages ADD COLUMN meta_desc TEXT DEFAULT ''",
            ]
            for stmt in alters:
                try:
                    db.execute(stmt)
                except Exception:
                    pass  # Column already exists
        db.commit()

        # Auto-populate slugs for items that don't have one yet
        try:
            items = db.execute("SELECT id, name FROM web_service_items WHERE slug IS NULL OR slug = ''").fetchall()
            for item in items:
                slug = make_slug(item["name"])
                # Ensure uniqueness: append -2, -3 etc if needed
                base_slug = slug
                counter = 2
                while True:
                    existing = db.execute("SELECT id FROM web_service_items WHERE slug=? AND id!=?", (slug, item["id"])).fetchone()
                    if not existing:
                        break
                    slug = f"{base_slug}-{counter}"
                    counter += 1
                db.execute("UPDATE web_service_items SET slug=? WHERE id=?", (slug, item["id"]))
            if items:
                db.commit()
        except Exception:
            pass
    except Exception:
        pass


# ── Customer-account migrations (email/Google login, addresses, orders link,
#    wishlist, saved payment refs, soft-delete) — safe to run multiple times ──

def run_account_migrations():
    try:
        db = get_db()
        if USE_PG:
            alters = [
                "ALTER TABLE web_accounts ADD COLUMN IF NOT EXISTS email TEXT",
                "ALTER TABLE web_accounts ADD COLUMN IF NOT EXISTS google_id TEXT",
                "ALTER TABLE web_accounts ADD COLUMN IF NOT EXISTS is_active INTEGER DEFAULT 1",
                "ALTER TABLE web_accounts ADD COLUMN IF NOT EXISTS deleted_at TEXT DEFAULT ''",
                "ALTER TABLE web_accounts ADD COLUMN IF NOT EXISTS address_line1 TEXT DEFAULT ''",
                "ALTER TABLE web_accounts ADD COLUMN IF NOT EXISTS address_line2 TEXT DEFAULT ''",
                "ALTER TABLE web_accounts ADD COLUMN IF NOT EXISTS address_city TEXT DEFAULT ''",
                "ALTER TABLE web_accounts ADD COLUMN IF NOT EXISTS address_state TEXT DEFAULT ''",
                "ALTER TABLE web_accounts ADD COLUMN IF NOT EXISTS address_pincode TEXT DEFAULT ''",
                "ALTER TABLE web_accounts ADD COLUMN IF NOT EXISTS tryon_count INTEGER DEFAULT 0",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS web_account_id INTEGER",
            ]
        else:
            alters = [
                "ALTER TABLE web_accounts ADD COLUMN email TEXT",
                "ALTER TABLE web_accounts ADD COLUMN google_id TEXT",
                "ALTER TABLE web_accounts ADD COLUMN is_active INTEGER DEFAULT 1",
                "ALTER TABLE web_accounts ADD COLUMN deleted_at TEXT DEFAULT ''",
                "ALTER TABLE web_accounts ADD COLUMN address_line1 TEXT DEFAULT ''",
                "ALTER TABLE web_accounts ADD COLUMN address_line2 TEXT DEFAULT ''",
                "ALTER TABLE web_accounts ADD COLUMN address_city TEXT DEFAULT ''",
                "ALTER TABLE web_accounts ADD COLUMN address_state TEXT DEFAULT ''",
                "ALTER TABLE web_accounts ADD COLUMN address_pincode TEXT DEFAULT ''",
                "ALTER TABLE web_accounts ADD COLUMN tryon_count INTEGER DEFAULT 0",
                "ALTER TABLE orders ADD COLUMN web_account_id INTEGER",
            ]
        for stmt in alters:
            try:
                db.execute(stmt)
            except Exception:
                pass  # column already exists
        db.commit()

        if USE_PG:
            new_tables = [
                """CREATE TABLE IF NOT EXISTS web_addresses (
                    id SERIAL PRIMARY KEY, account_id INTEGER NOT NULL,
                    label TEXT DEFAULT 'Home', full_name TEXT DEFAULT '', mobile TEXT DEFAULT '',
                    line1 TEXT DEFAULT '', line2 TEXT DEFAULT '', city TEXT DEFAULT '',
                    state TEXT DEFAULT '', pincode TEXT DEFAULT '', is_default INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'))""",
                """CREATE TABLE IF NOT EXISTS web_wishlist (
                    id SERIAL PRIMARY KEY, account_id INTEGER NOT NULL, item_id INTEGER NOT NULL,
                    created_at TEXT DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'),
                    UNIQUE(account_id, item_id))""",
                """CREATE TABLE IF NOT EXISTS web_payment_methods (
                    id SERIAL PRIMARY KEY, account_id INTEGER NOT NULL,
                    method_type TEXT DEFAULT 'upi', label TEXT DEFAULT '', masked_detail TEXT DEFAULT '',
                    is_default INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'))""",
                """CREATE TABLE IF NOT EXISTS web_related_items (
                    id SERIAL PRIMARY KEY, item_id INTEGER NOT NULL, related_item_id INTEGER NOT NULL,
                    sort_order INTEGER DEFAULT 0,
                    UNIQUE(item_id, related_item_id))""",
            ]
        else:
            new_tables = [
                """CREATE TABLE IF NOT EXISTS web_addresses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, account_id INTEGER NOT NULL,
                    label TEXT DEFAULT 'Home', full_name TEXT DEFAULT '', mobile TEXT DEFAULT '',
                    line1 TEXT DEFAULT '', line2 TEXT DEFAULT '', city TEXT DEFAULT '',
                    state TEXT DEFAULT '', pincode TEXT DEFAULT '', is_default INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now')))""",
                """CREATE TABLE IF NOT EXISTS web_wishlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, account_id INTEGER NOT NULL, item_id INTEGER NOT NULL,
                    created_at TEXT DEFAULT (datetime('now')),
                    UNIQUE(account_id, item_id))""",
                """CREATE TABLE IF NOT EXISTS web_payment_methods (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, account_id INTEGER NOT NULL,
                    method_type TEXT DEFAULT 'upi', label TEXT DEFAULT '', masked_detail TEXT DEFAULT '',
                    is_default INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now')))""",
                """CREATE TABLE IF NOT EXISTS web_related_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, item_id INTEGER NOT NULL, related_item_id INTEGER NOT NULL,
                    sort_order INTEGER DEFAULT 0,
                    UNIQUE(item_id, related_item_id))""",
            ]
        for stmt in new_tables:
            try:
                db.execute(stmt)
            except Exception:
                pass
        db.commit()

        # Wishlist price-drop / back-in-stock alerts: ready-made stock on items,
        # and a snapshot of price/stock taken at the moment an item is wishlisted.
        if USE_PG:
            wl_alters = [
                "ALTER TABLE web_service_items ADD COLUMN IF NOT EXISTS stock_qty INTEGER DEFAULT -1",
                "ALTER TABLE web_wishlist ADD COLUMN IF NOT EXISTS price_snapshot REAL",
                "ALTER TABLE web_wishlist ADD COLUMN IF NOT EXISTS stock_snapshot INTEGER",
            ]
        else:
            wl_alters = [
                "ALTER TABLE web_service_items ADD COLUMN stock_qty INTEGER DEFAULT -1",
                "ALTER TABLE web_wishlist ADD COLUMN price_snapshot REAL",
                "ALTER TABLE web_wishlist ADD COLUMN stock_snapshot INTEGER",
            ]
        for stmt in wl_alters:
            try:
                db.execute(stmt)
            except Exception:
                pass
        db.commit()

        # PDP: per-item delivery estimate text + customer Q&A (ask-a-question,
        # admin answers, then shows publicly).
        if USE_PG:
            pdp_alters = ["ALTER TABLE web_service_items ADD COLUMN IF NOT EXISTS delivery_estimate TEXT DEFAULT ''"]
            pdp_tables = ["""CREATE TABLE IF NOT EXISTS web_item_questions (
                id SERIAL PRIMARY KEY, item_id INTEGER NOT NULL,
                name TEXT DEFAULT '', question TEXT NOT NULL, answer TEXT DEFAULT '',
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'),
                answered_at TEXT DEFAULT '')"""]
        else:
            pdp_alters = ["ALTER TABLE web_service_items ADD COLUMN delivery_estimate TEXT DEFAULT ''"]
            pdp_tables = ["""CREATE TABLE IF NOT EXISTS web_item_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, item_id INTEGER NOT NULL,
                name TEXT DEFAULT '', question TEXT NOT NULL, answer TEXT DEFAULT '',
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT (datetime('now')),
                answered_at TEXT DEFAULT '')"""]
        for stmt in pdp_alters + pdp_tables:
            try:
                db.execute(stmt)
            except Exception:
                pass
        db.commit()

        # ── Server-side cart sync + item view tracking ────────────────────
        # web_carts: persists logged-in customer's localStorage cart so we
        #   can (a) restore it on next login, (b) send abandoned-cart emails.
        # web_item_views: anonymous + logged-in page-view log, used for
        #   "X people viewing" social proof and personalised recommendations.
        if USE_PG:
            engagement_tables = [
                """CREATE TABLE IF NOT EXISTS web_carts (
                    id SERIAL PRIMARY KEY,
                    account_id INTEGER NOT NULL,
                    item_id INTEGER NOT NULL,
                    item_name TEXT DEFAULT '',
                    item_price REAL DEFAULT 0,
                    item_img TEXT DEFAULT '',
                    qty INTEGER DEFAULT 1,
                    added_at TEXT DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'),
                    reminded_at TEXT DEFAULT NULL,
                    UNIQUE(account_id, item_id))""",
                """CREATE TABLE IF NOT EXISTS web_item_views (
                    id SERIAL PRIMARY KEY,
                    item_id INTEGER NOT NULL,
                    account_id INTEGER DEFAULT NULL,
                    session_key TEXT DEFAULT '',
                    viewed_at TEXT DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'))""",
            ]
        else:
            engagement_tables = [
                """CREATE TABLE IF NOT EXISTS web_carts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER NOT NULL,
                    item_id INTEGER NOT NULL,
                    item_name TEXT DEFAULT '',
                    item_price REAL DEFAULT 0,
                    item_img TEXT DEFAULT '',
                    qty INTEGER DEFAULT 1,
                    added_at TEXT DEFAULT (datetime('now')),
                    reminded_at TEXT DEFAULT NULL,
                    UNIQUE(account_id, item_id))""",
                """CREATE TABLE IF NOT EXISTS web_item_views (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER NOT NULL,
                    account_id INTEGER DEFAULT NULL,
                    session_key TEXT DEFAULT '',
                    viewed_at TEXT DEFAULT (datetime('now')))""",
            ]
        for stmt in engagement_tables:
            try:
                db.execute(stmt)
            except Exception:
                pass
        db.commit()

        # ── OTP store: add missing columns (mobile alias, expires_at, used) ──
        # The original table only had: id, phone, otp, created_at
        # Auth code uses: mobile, expires_at, used — migrate them safely.
        otp_alters = [
            "ALTER TABLE web_otp_store ADD COLUMN mobile TEXT DEFAULT ''",
            "ALTER TABLE web_otp_store ADD COLUMN expires_at TEXT DEFAULT ''",
            "ALTER TABLE web_otp_store ADD COLUMN used INTEGER DEFAULT 0",
        ]
        for stmt in otp_alters:
            try:
                db.execute(stmt)
            except Exception:
                pass
        # Backfill mobile from phone where mobile is empty
        try:
            db.execute("UPDATE web_otp_store SET mobile=phone WHERE mobile='' OR mobile IS NULL")
        except Exception:
            pass
        db.commit()

        # ── Wishlist: add item_name/price/img/added_at columns ───────────────
        wl_extra_alters = [
            "ALTER TABLE web_wishlist ADD COLUMN item_name TEXT DEFAULT ''",
            "ALTER TABLE web_wishlist ADD COLUMN item_price REAL DEFAULT 0",
            "ALTER TABLE web_wishlist ADD COLUMN item_img TEXT DEFAULT ''",
            "ALTER TABLE web_wishlist ADD COLUMN added_at TEXT DEFAULT (datetime('now'))",
        ]
        for stmt in wl_extra_alters:
            try:
                db.execute(stmt)
            except Exception:
                pass
        # Backfill added_at from created_at
        try:
            db.execute("UPDATE web_wishlist SET added_at=created_at WHERE added_at='' OR added_at IS NULL")
        except Exception:
            pass
        db.commit()



        # ── finance table: migrate wrong column names (txn_date→tx_date etc.) ─
        # database.py used to create finance with txn_date/txn_type/description
        # but owner.py always expected tx_date/tx_type/mode/order_id/note/etc.
        # This migration detects the old schema and recreates the table correctly.
        try:
            _fcols = {r[1] for r in db.execute("PRAGMA table_info(finance)").fetchall()}
            if "txn_date" in _fcols:
                # Recreate with correct schema, preserving existing rows
                db.executescript("""
                    CREATE TABLE IF NOT EXISTS finance_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tx_date TEXT,
                        tx_type TEXT DEFAULT 'income',
                        category TEXT,
                        amount REAL DEFAULT 0,
                        mode TEXT DEFAULT '',
                        order_id INTEGER,
                        note TEXT DEFAULT '',
                        employee_name TEXT DEFAULT '',
                        created_by TEXT DEFAULT '',
                        created_at TEXT DEFAULT (datetime('now'))
                    );
                    INSERT INTO finance_new(id, tx_date, tx_type, category, amount, created_at)
                        SELECT id,
                               COALESCE(txn_date, ''),
                               COALESCE(txn_type, 'income'),
                               COALESCE(category, ''),
                               COALESCE(amount, 0),
                               COALESCE(created_at, datetime('now'))
                        FROM finance;
                    DROP TABLE finance;
                    ALTER TABLE finance_new RENAME TO finance;
                """)
                db.commit()
        except Exception:
            pass

        # ── work_logs: migrate old schema (stage/note/logged_by/logged_at → full schema) ──
        try:
            _wl_cols = {r[1] for r in db.execute("PRAGMA table_info(work_logs)").fetchall()}
            if "qty_done" not in _wl_cols:
                db.executescript("""
                    CREATE TABLE IF NOT EXISTS work_logs_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        order_id INTEGER,
                        order_code TEXT DEFAULT '',
                        garment_type TEXT DEFAULT '',
                        qty_done INTEGER DEFAULT 0,
                        employee_name TEXT DEFAULT '',
                        log_date TEXT,
                        making_rate REAL DEFAULT 0,
                        notes TEXT DEFAULT '',
                        created_at TEXT DEFAULT (datetime('now'))
                    );
                    INSERT INTO work_logs_new(id, order_id, notes, created_at)
                        SELECT id, order_id,
                               COALESCE(note, ''),
                               COALESCE(logged_at, datetime('now'))
                        FROM work_logs;
                    DROP TABLE work_logs;
                    ALTER TABLE work_logs_new RENAME TO work_logs;
                """)
                db.commit()
        except Exception:
            pass

        # ── inventory: add low_alert_at / low_threshold if missing ───────────
        try:
            _inv_cols = {r[1] for r in db.execute("PRAGMA table_info(inventory)").fetchall()}
            for _col in ["low_threshold", "low_alert_at"]:
                if _col not in _inv_cols:
                    db.execute(f"ALTER TABLE inventory ADD COLUMN {_col} REAL DEFAULT 0")
            db.commit()
        except Exception:
            pass

        # ── token_balance on web_accounts + token_transactions table ─────────
        try:
            if USE_PG:
                db.execute("ALTER TABLE web_accounts ADD COLUMN IF NOT EXISTS token_balance INTEGER DEFAULT 0")
                db.execute("""CREATE TABLE IF NOT EXISTS token_transactions (
                    id SERIAL PRIMARY KEY,
                    account_id INTEGER NOT NULL,
                    tokens INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    razorpay_payment_id TEXT DEFAULT '',
                    razorpay_order_id TEXT DEFAULT '',
                    created_at TEXT DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'))""")
            else:
                try:
                    db.execute("ALTER TABLE web_accounts ADD COLUMN token_balance INTEGER DEFAULT 0")
                except Exception:
                    pass
                db.execute("""CREATE TABLE IF NOT EXISTS token_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER NOT NULL,
                    tokens INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    razorpay_payment_id TEXT DEFAULT '',
                    razorpay_order_id TEXT DEFAULT '',
                    created_at TEXT DEFAULT (datetime('now','localtime')))""")
            db.commit()
        except Exception:
            pass
        # ── support_chats: add customer_email if missing ─────────────────────
        try:
            db.execute("ALTER TABLE support_chats ADD COLUMN customer_email TEXT DEFAULT ''")
        except Exception:
            pass
        db.commit()


        # ── Performance indexes (added once, SQLite ignores if already exists) ──
        try:
            db.executescript("""
                CREATE INDEX IF NOT EXISTS idx_web_item_media_item_id
                    ON web_item_media(item_id);
                CREATE INDEX IF NOT EXISTS idx_web_service_items_cat_id
                    ON web_service_items(category_id);
                CREATE INDEX IF NOT EXISTS idx_web_service_items_sort
                    ON web_service_items(sort_order, id);
                CREATE INDEX IF NOT EXISTS idx_orders_status
                    ON orders(status);
                CREATE INDEX IF NOT EXISTS idx_orders_customer_id
                    ON orders(customer_id);
                CREATE INDEX IF NOT EXISTS idx_orders_order_code
                    ON orders(order_code);
                CREATE INDEX IF NOT EXISTS idx_web_accounts_mobile
                    ON web_accounts(mobile);
                CREATE INDEX IF NOT EXISTS idx_web_accounts_email
                    ON web_accounts(email);
                CREATE INDEX IF NOT EXISTS idx_occasions_account_id
                    ON occasions(account_id);
                CREATE INDEX IF NOT EXISTS idx_home_sections_key
                    ON home_sections(section_key);
                CREATE INDEX IF NOT EXISTS idx_web_daily_craft_published
                    ON web_daily_craft(is_published, id);
                CREATE INDEX IF NOT EXISTS idx_web_addresses_account_id
                    ON web_addresses(account_id);
            """)
            db.commit()
        except Exception:
            pass

        # ── Seed homepage sections (runs once at startup via init_db) ──────────
        try:
            _default_sections = [
                ("hero",            "Hero",              1),
                ("price_estimator", "Price Estimator",   1),
                ("occasion_finder", "Occasion Finder",   1),
                ("fabric_guide",    "Fabric Guide",      1),
                ("shop_status",     "Live Shop Status",  1),
                ("brands_ticker",   "Brands Ticker",     0),
                ("action_cards",    "Action Cards",      1),
                ("ai_preview",      "AI Style Preview",  1),
                ("bring_inspo",     "Bring Your Inspo",  1),
                ("catalogue",       "Catalogue",         1),
                ("reviews",         "Reviews",           1),
                ("heritage",        "Heritage",          1),
            ]
            for _key, _title, _active in _default_sections:
                db.execute(
                    "INSERT OR IGNORE INTO home_sections (section_key,section_title,content,sort_order,active)"
                    " VALUES (?,?,'{}',99,?)",
                    (_key, _title, _active)
                )
            db.commit()
        except Exception:
            pass

    except Exception:
        pass


# ── SEO helpers ──────────────────────────────────────────────────────────────

def make_slug(text):
    import re
    s = (text or "").lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s-]+", "-", s)
    return s.strip("-")


def run_seo_migrations():
    """Add SEO columns to existing tables. Safe to run multiple times."""
    try:
        db = get_db()
        alters = [
            "ALTER TABLE web_service_items ADD COLUMN slug TEXT DEFAULT ''",
            "ALTER TABLE web_service_items ADD COLUMN meta_title TEXT DEFAULT ''",
            "ALTER TABLE web_service_items ADD COLUMN meta_desc TEXT DEFAULT ''",
            "ALTER TABLE web_service_categories ADD COLUMN meta_title TEXT DEFAULT ''",
            "ALTER TABLE web_service_categories ADD COLUMN meta_desc TEXT DEFAULT ''",
            "ALTER TABLE web_pages ADD COLUMN meta_title TEXT DEFAULT ''",
            "ALTER TABLE web_pages ADD COLUMN meta_desc TEXT DEFAULT ''",
        ]
        if USE_PG:
            alters = [a.replace("ADD COLUMN ", "ADD COLUMN IF NOT EXISTS ") for a in alters]
        for stmt in alters:
            try: db.execute(stmt)
            except Exception: pass
        db.commit()
        # Auto-populate slugs
        try:
            items = db.execute("SELECT id, name FROM web_service_items WHERE slug IS NULL OR slug = ''").fetchall()
            for item in items:
                slug = make_slug(item["name"])
                base_slug, counter = slug, 2
                while db.execute("SELECT id FROM web_service_items WHERE slug=? AND id!=?", (slug, item["id"])).fetchone():
                    slug = f"{base_slug}-{counter}"; counter += 1
                db.execute("UPDATE web_service_items SET slug=? WHERE id=?", (slug, item["id"]))
            if items: db.commit()
        except Exception: pass
    except Exception: pass