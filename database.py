import os
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
            # Escape literal % in LIKE patterns BEFORE replacing ? with %s
            # e.g. LIKE 'types_%' → LIKE 'types_%%' so psycopg2 doesn't treat it as param
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
            # ALTER TABLE ADD COLUMN → ADD COLUMN IF NOT EXISTS (PostgreSQL 9.6+)
            sql = re.sub(r"ALTER TABLE (\w+) ADD COLUMN (\w+)",
                         r"ALTER TABLE  ADD COLUMN IF NOT EXISTS ", sql, flags=re.IGNORECASE)
            # Add ON CONFLICT for settings upsert
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
                # Rollback aborted transaction so connection stays usable
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
        def execute(self, sql, params=None):
            cur = _Cursor(self._conn.cursor())
            cur.execute(sql, params or [])
            return cur
        def cursor(self):
            return _Cursor(self._conn.cursor())
        def commit(self):   self._conn.commit()
        def close(self):    self._conn.close()
        def __enter__(self): return self
        def __exit__(self, *a): self._conn.commit(); self._conn.close()

    def get_db():
        url = os.environ["DATABASE_URL"]
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        conn = psycopg2.connect(url)
        conn.autocommit = False
        return _Conn(conn)

else:
    import sqlite3

    def get_db():
        conn = sqlite3.connect(Config.DATABASE)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
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
            customer_id INTEGER NOT NULL, order_date TEXT, delivery_date TEXT,
            total_amount REAL DEFAULT 0, extra_charges REAL DEFAULT 0,
            payable_amount REAL DEFAULT 0, advance_paid REAL DEFAULT 0,
            remaining REAL DEFAULT 0, payment_mode TEXT DEFAULT 'cash',
            status TEXT DEFAULT 'pending', is_urgent INTEGER DEFAULT 0,
            note TEXT DEFAULT '', repeat_of TEXT, delivered_at TEXT,
            created_at TEXT DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'))""",
        """CREATE TABLE IF NOT EXISTS order_items (
            id SERIAL PRIMARY KEY, order_id INTEGER NOT NULL,
            garment_type TEXT NOT NULL, quantity INTEGER DEFAULT 1,
            rate REAL DEFAULT 0, amount REAL DEFAULT 0,
            measurements TEXT DEFAULT '{}', notes TEXT)""",
        """CREATE TABLE IF NOT EXISTS order_images (
            id SERIAL PRIMARY KEY, order_id INTEGER NOT NULL,
            file_path TEXT NOT NULL,
            uploaded_at TEXT DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'))""",
        """CREATE TABLE IF NOT EXISTS work_logs (
            id SERIAL PRIMARY KEY, order_id INTEGER NOT NULL,
            order_code TEXT NOT NULL, garment_type TEXT NOT NULL,
            qty_done INTEGER DEFAULT 0,
            log_date TEXT DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD'),
            making_rate REAL DEFAULT 0, notes TEXT DEFAULT '',
            employee_name TEXT DEFAULT '', is_non_stitch INTEGER DEFAULT 0,
            rate_override REAL DEFAULT 0,
            created_at TEXT DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'))""",
        """CREATE TABLE IF NOT EXISTS finance (
            id SERIAL PRIMARY KEY, tx_date TEXT NOT NULL,
            tx_type TEXT NOT NULL, category TEXT NOT NULL,
            amount REAL NOT NULL, mode TEXT DEFAULT 'cash',
            order_id INTEGER, note TEXT, created_by TEXT DEFAULT 'employee',
            created_at TEXT DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'))""",
        """CREATE TABLE IF NOT EXISTS inventory (
            id SERIAL PRIMARY KEY, item_name TEXT UNIQUE NOT NULL,
            quantity REAL DEFAULT 0, unit TEXT DEFAULT 'pcs',
            low_alert_at REAL DEFAULT 0,
            updated_at TEXT DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'))""",
        """CREATE TABLE IF NOT EXISTS whatsapp_log (
            id SERIAL PRIMARY KEY, order_id INTEGER,
            mobile TEXT NOT NULL, message_type TEXT,
            sent_at TEXT DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'))""",
        """CREATE TABLE IF NOT EXISTS employees (
            id SERIAL PRIMARY KEY, name TEXT NOT NULL UNIQUE,
            phone TEXT DEFAULT '', active INTEGER DEFAULT 1,
            skills TEXT DEFAULT 'stitch', hindi_name TEXT DEFAULT '',
            created_at TEXT DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'))""",
        """CREATE TABLE IF NOT EXISTS measurement_fields (
            id SERIAL PRIMARY KEY, garment_type TEXT NOT NULL,
            field_name TEXT NOT NULL, sort_order INTEGER DEFAULT 0,
            UNIQUE(garment_type, field_name))""",
        """CREATE TABLE IF NOT EXISTS shop_logo (id INTEGER PRIMARY KEY, data TEXT)""",
        """CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)""",
        """CREATE TABLE IF NOT EXISTS salary_advances (
            id SERIAL PRIMARY KEY, employee_name TEXT,
            amount REAL, note TEXT, advance_date TEXT, created_at TEXT)""",
        """CREATE TABLE IF NOT EXISTS notify_log (
            id SERIAL PRIMARY KEY, order_code TEXT,
            customer TEXT, mobile TEXT, lang TEXT, sent_at TEXT)""",
        """CREATE TABLE IF NOT EXISTS gallery_types (
            id SERIAL PRIMARY KEY, name TEXT NOT NULL,
            parent_id INTEGER DEFAULT NULL, sort_order INTEGER DEFAULT 0,
            created_at TEXT DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'))""",
        """CREATE TABLE IF NOT EXISTS gallery_images (
            id SERIAL PRIMARY KEY, type_id INTEGER NOT NULL,
            filename TEXT NOT NULL, caption TEXT DEFAULT '',
            sort_order INTEGER DEFAULT 0,
            created_at TEXT DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'))""",
    ]
    for s in statements:
        cur.execute(s)

    _insert_defaults_pg(cur)
    conn.commit()
    conn.close()


def _insert_defaults_pg(cur):
    defaults = [
        ("owner_pin","1234"),("shop_name","Uttam Tailors"),
        ("whatsapp_number",""),("default_language","hinglish"),
        ("last_order_code","3599"),("work_rate_measurement","0"),
        ("work_rate_cutting","25"),("work_rate_alteration","15"),
        ("finance_income_cats","advance,payment,alteration,other income"),
        ("finance_expense_cats","thread,buttons,fabric,electricity,rent,salary,transport,maintenance,other expense"),
        ("rate_list_image",""),
    ]
    for k,v in defaults:
        cur.execute("INSERT INTO settings(key,value) VALUES(%s,%s) ON CONFLICT(key) DO NOTHING",(k,v))

    cust_rates = [
        ("customer_rate_Shirt","350"),("customer_rate_Shirt Linen","450"),
        ("customer_rate_Pant","450"),("customer_rate_Pant Double","550"),
        ("customer_rate_Jeans","550"),("customer_rate_Suit 2pc","2800"),
        ("customer_rate_Suit 3pc","3500"),("customer_rate_Blazer","2300"),
        ("customer_rate_Kurta","800"),("customer_rate_Kurta Pajama","1000"),
        ("customer_rate_Pajama","300"),("customer_rate_Pathani","800"),
        ("customer_rate_Sherwani","3500"),("customer_rate_Safari","1500"),
        ("customer_rate_Waistcoat","800"),("customer_rate_Alteration","100"),
        ("customer_rate_Cutting Only","100"),
    ]
    for k,v in cust_rates:
        cur.execute("INSERT INTO settings(key,value) VALUES(%s,%s) ON CONFLICT(key) DO NOTHING",(k,v))

    stitch_rates = [
        ("stitch_rate_Shirt","100"),("stitch_rate_Shirt Linen","120"),
        ("stitch_rate_Pant","105"),("stitch_rate_Pant Double","120"),
        ("stitch_rate_Jeans","110"),("stitch_rate_Suit 2pc","350"),
        ("stitch_rate_Suit 3pc","450"),("stitch_rate_Blazer","300"),
        ("stitch_rate_Kurta","120"),("stitch_rate_Kurta Pajama","180"),
        ("stitch_rate_Pajama","80"),("stitch_rate_Pathani","120"),
        ("stitch_rate_Sherwani","450"),("stitch_rate_Safari","200"),
        ("stitch_rate_Waistcoat","100"),("stitch_rate_Alteration","50"),
        ("stitch_rate_Cutting Only","40"),
    ]
    for k,v in stitch_rates:
        cur.execute("INSERT INTO settings(key,value) VALUES(%s,%s) ON CONFLICT(key) DO NOTHING",(k,v))

    cur.execute("SELECT COUNT(*) FROM measurement_fields")
    if cur.fetchone()[0] == 0:
        meas = [
            ("Pant","Lambai",1),("Pant","Kamar",2),("Pant","Seat",3),("Pant","Mori",4),("Pant","Jangh",5),("Pant","Goda",6),("Pant","Langot",7),
            ("Pant Double","Lambai",1),("Pant Double","Kamar",2),("Pant Double","Seat",3),("Pant Double","Mori",4),("Pant Double","Jangh",5),("Pant Double","Goda",6),("Pant Double","Langot",7),
            ("Jeans","Lambai",1),("Jeans","Kamar",2),("Jeans","Seat",3),("Jeans","Mori",4),("Jeans","Jangh",5),("Jeans","Goda",6),("Jeans","Langot",7),
            ("Pajama","Lambai",1),("Pajama","Kamar",2),("Pajama","Seat",3),("Pajama","Mori",4),("Pajama","Jangh",5),("Pajama","Goda",6),("Pajama","Langot",7),
            ("Shirt","Lambai",1),("Shirt","Seeno",2),("Shirt","Kamar",3),("Shirt","Shoulder",4),("Shirt","Collar",5),("Shirt","Aastin",6),("Shirt","Cough",7),("Shirt","Part 1",8),("Shirt","Part 2",9),("Shirt","Part 3",10),
            ("Shirt Linen","Lambai",1),("Shirt Linen","Seeno",2),("Shirt Linen","Kamar",3),("Shirt Linen","Shoulder",4),("Shirt Linen","Collar",5),("Shirt Linen","Aastin",6),("Shirt Linen","Cough",7),("Shirt Linen","Part 1",8),("Shirt Linen","Part 2",9),("Shirt Linen","Part 3",10),
            ("Kurta","Lambai",1),("Kurta","Seeno",2),("Kurta","Kamar",3),("Kurta","Shoulder",4),("Kurta","Collar",5),("Kurta","Aastin",6),("Kurta","Cough",7),("Kurta","Part 1",8),("Kurta","Part 2",9),("Kurta","Part 3",10),
            ("Pathani","Lambai",1),("Pathani","Seeno",2),("Pathani","Kamar",3),("Pathani","Shoulder",4),("Pathani","Collar",5),("Pathani","Aastin",6),("Pathani","Cough",7),("Pathani","Part 1",8),("Pathani","Part 2",9),("Pathani","Part 3",10),
            ("Sherwani","Lambai",1),("Sherwani","Seeno",2),("Sherwani","Kamar",3),("Sherwani","Shoulder",4),("Sherwani","Collar",5),("Sherwani","Aastin",6),("Sherwani","Cough",7),("Sherwani","Part 1",8),("Sherwani","Part 2",9),("Sherwani","Part 3",10),
            ("Blazer","Lambai",1),("Blazer","Seeno",2),("Blazer","Kamar",3),("Blazer","Shoulder",4),("Blazer","Aastin",5),("Blazer","Mori",6),("Blazer","Back Paat",7),
            ("Suit 2pc","Lambai",1),("Suit 2pc","Seeno",2),("Suit 2pc","Kamar",3),("Suit 2pc","Shoulder",4),("Suit 2pc","Aastin",5),("Suit 2pc","Mori",6),("Suit 2pc","Back Paat",7),("Suit 2pc","P-Lambai",8),("Suit 2pc","P-Kamar",9),("Suit 2pc","P-Seat",10),("Suit 2pc","P-Mori",11),
            ("Suit 3pc","Lambai",1),("Suit 3pc","Seeno",2),("Suit 3pc","Kamar",3),("Suit 3pc","Shoulder",4),("Suit 3pc","Aastin",5),("Suit 3pc","Mori",6),("Suit 3pc","Back Paat",7),("Suit 3pc","P-Lambai",8),("Suit 3pc","P-Kamar",9),("Suit 3pc","P-Seat",10),("Suit 3pc","P-Mori",11),
            ("Safari","Lambai",1),("Safari","Seeno",2),("Safari","Kamar",3),("Safari","Shoulder",4),("Safari","Collar",5),("Safari","Aastin",6),("Safari","Cough",7),("Safari","P-Lambai",8),("Safari","P-Kamar",9),("Safari","P-Seat",10),("Safari","P-Mori",11),
            ("Kurta Pajama","Lambai",1),("Kurta Pajama","Seeno",2),("Kurta Pajama","Kamar",3),("Kurta Pajama","Shoulder",4),("Kurta Pajama","Aastin",5),("Kurta Pajama","P-Lambai",6),("Kurta Pajama","P-Jangh",7),("Kurta Pajama","P-Mori",8),
            ("Waistcoat","Lambai",1),("Waistcoat","Seeno",2),("Waistcoat","Shoulder",3),("Waistcoat","Kamar",4),
            ("Alteration","Details",1),("Cutting Only","Details",1),
        ]
        for gt,fn,so in meas:
            cur.execute("INSERT INTO measurement_fields(garment_type,field_name,sort_order) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING",(gt,fn,so))

    employees = [("Kamal","कमल","naap+kataai+silai"),("Bhagwan","भगवान","silai"),("Sawarmal","सावरमल","silai"),("Mahesh","महेश","silai"),("Manak Tau","मानक ताऊ","silai")]
    for name,hindi,skills in employees:
        cur.execute("INSERT INTO employees(name,hindi_name,skills,active) VALUES(%s,%s,%s,1) ON CONFLICT(name) DO NOTHING",(name,hindi,skills))


def _init_sqlite():
    import sqlite3
    conn = sqlite3.connect(Config.DATABASE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, mobile TEXT, address TEXT, created_at TEXT DEFAULT (datetime('now','localtime')));
        CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, order_code TEXT UNIQUE NOT NULL, customer_id INTEGER NOT NULL, order_date TEXT, delivery_date TEXT, total_amount REAL DEFAULT 0, extra_charges REAL DEFAULT 0, payable_amount REAL DEFAULT 0, advance_paid REAL DEFAULT 0, remaining REAL DEFAULT 0, payment_mode TEXT DEFAULT 'cash', status TEXT DEFAULT 'pending', is_urgent INTEGER DEFAULT 0, note TEXT DEFAULT '', repeat_of TEXT, delivered_at TEXT, created_at TEXT DEFAULT (datetime('now','localtime')));
        CREATE TABLE IF NOT EXISTS order_items (id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL, garment_type TEXT NOT NULL, quantity INTEGER DEFAULT 1, rate REAL DEFAULT 0, amount REAL DEFAULT 0, measurements TEXT DEFAULT '{}', notes TEXT);
        CREATE TABLE IF NOT EXISTS order_images (id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL, file_path TEXT NOT NULL, uploaded_at TEXT DEFAULT (datetime('now','localtime')));
        CREATE TABLE IF NOT EXISTS work_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL, order_code TEXT NOT NULL, garment_type TEXT NOT NULL, qty_done INTEGER DEFAULT 0, log_date TEXT DEFAULT (date('now','localtime')), making_rate REAL DEFAULT 0, notes TEXT DEFAULT '', employee_name TEXT DEFAULT '', is_non_stitch INTEGER DEFAULT 0, rate_override REAL DEFAULT 0, created_at TEXT DEFAULT (datetime('now','localtime')));
        CREATE TABLE IF NOT EXISTS finance (id INTEGER PRIMARY KEY AUTOINCREMENT, tx_date TEXT NOT NULL, tx_type TEXT NOT NULL, category TEXT NOT NULL, amount REAL NOT NULL, mode TEXT DEFAULT 'cash', order_id INTEGER, note TEXT, created_by TEXT DEFAULT 'employee', created_at TEXT DEFAULT (datetime('now','localtime')));
        CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT UNIQUE NOT NULL, quantity REAL DEFAULT 0, unit TEXT DEFAULT 'pcs', low_alert_at REAL DEFAULT 0, updated_at TEXT DEFAULT (datetime('now','localtime')));
        CREATE TABLE IF NOT EXISTS whatsapp_log (id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER, mobile TEXT NOT NULL, message_type TEXT, sent_at TEXT DEFAULT (datetime('now','localtime')));
        CREATE TABLE IF NOT EXISTS employees (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, phone TEXT DEFAULT '', active INTEGER DEFAULT 1, skills TEXT DEFAULT 'stitch', hindi_name TEXT DEFAULT '', created_at TEXT DEFAULT (datetime('now','localtime')));
        CREATE TABLE IF NOT EXISTS measurement_fields (id INTEGER PRIMARY KEY AUTOINCREMENT, garment_type TEXT NOT NULL, field_name TEXT NOT NULL, sort_order INTEGER DEFAULT 0, UNIQUE(garment_type, field_name));
        CREATE TABLE IF NOT EXISTS shop_logo (id INTEGER PRIMARY KEY, data TEXT);
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS salary_advances (id INTEGER PRIMARY KEY AUTOINCREMENT, employee_name TEXT, amount REAL, note TEXT, advance_date TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS notify_log (id INTEGER PRIMARY KEY AUTOINCREMENT, order_code TEXT, customer TEXT, mobile TEXT, lang TEXT, sent_at TEXT);
        CREATE TABLE IF NOT EXISTS gallery_types (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, parent_id INTEGER DEFAULT NULL, sort_order INTEGER DEFAULT 0, created_at TEXT DEFAULT (datetime('now','localtime')));
        CREATE TABLE IF NOT EXISTS gallery_images (id INTEGER PRIMARY KEY AUTOINCREMENT, type_id INTEGER NOT NULL, filename TEXT NOT NULL, caption TEXT DEFAULT '', sort_order INTEGER DEFAULT 0, created_at TEXT DEFAULT (datetime('now','localtime')));
    """)
    defaults = [("owner_pin","1234"),("shop_name","Uttam Tailors"),("whatsapp_number",""),("default_language","hinglish"),("last_order_code","3599"),("work_rate_measurement","0"),("work_rate_cutting","25"),("work_rate_alteration","15"),("finance_income_cats","advance,payment,alteration,other income"),("finance_expense_cats","thread,buttons,fabric,electricity,rent,salary,transport,maintenance,other expense"),("rate_list_image","")]
    for k,v in defaults:
        cur.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)",(k,v))
    conn.commit(); conn.close()


# ── get_setting / set_setting ─────────────────────────────────────────────────

_settings_cache = {}
_settings_cache_valid = False

def _load_settings_cache():
    global _settings_cache, _settings_cache_valid
    try:
        conn = get_db()
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
        conn.close()
        _settings_cache = {r["key"]: r["value"] for r in rows}
        _settings_cache_valid = True
    except:
        _settings_cache_valid = False

def get_setting(key, default=""):
    global _settings_cache_valid
    if not _settings_cache_valid:
        _load_settings_cache()
    return _settings_cache.get(key, default)

def set_setting(key, value):
    global _settings_cache, _settings_cache_valid
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, value))
    conn.commit()
    conn.close()
    # Update cache immediately
    _settings_cache[key] = value
    _settings_cache_valid = True

def invalidate_settings_cache():
    global _settings_cache_valid
    _settings_cache_valid = False


# ── order codes ───────────────────────────────────────────────────────────────

def peek_order_code():
    conn = get_db()
    row = conn.execute("SELECT value FROM settings WHERE key='last_order_code'").fetchone()
    setting_last = int(row["value"]) if row else 3599
    max_row = conn.execute("SELECT MAX(CAST(order_code AS INTEGER)) as m FROM orders").fetchone()
    db_last = max_row["m"] if max_row and max_row["m"] else 0
    conn.close()
    return str(max(setting_last, db_last) + 1)


def next_order_code():
    conn = get_db()
    row = conn.execute("SELECT value FROM settings WHERE key='last_order_code'").fetchone()
    setting_last = int(row["value"]) if row else 3599
    max_row = conn.execute("SELECT MAX(CAST(order_code AS INTEGER)) as m FROM orders").fetchone()
    db_last = max_row["m"] if max_row and max_row["m"] else 0
    new_code = max(setting_last, db_last) + 1
    conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('last_order_code',?)", (str(new_code),))
    conn.commit()
    conn.close()
    return str(new_code)import os
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
            # Escape literal % in LIKE patterns BEFORE replacing ? with %s
            # e.g. LIKE 'types_%' → LIKE 'types_%%' so psycopg2 doesn't treat it as param
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
            # ALTER TABLE ADD COLUMN → ADD COLUMN IF NOT EXISTS (PostgreSQL 9.6+)
            sql = re.sub(r"ALTER TABLE (\w+) ADD COLUMN (\w+)",
                         r"ALTER TABLE  ADD COLUMN IF NOT EXISTS ", sql, flags=re.IGNORECASE)
            # Add ON CONFLICT for settings upsert
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
                # Rollback aborted transaction so connection stays usable
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
        def execute(self, sql, params=None):
            cur = _Cursor(self._conn.cursor())
            cur.execute(sql, params or [])
            return cur
        def cursor(self):
            return _Cursor(self._conn.cursor())
        def commit(self):   self._conn.commit()
        def close(self):    self._conn.close()
        def __enter__(self): return self
        def __exit__(self, *a): self._conn.commit(); self._conn.close()

    def get_db():
        url = os.environ["DATABASE_URL"]
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        conn = psycopg2.connect(url)
        conn.autocommit = False
        return _Conn(conn)

else:
    import sqlite3

    def get_db():
        conn = sqlite3.connect(Config.DATABASE)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
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
            customer_id INTEGER NOT NULL, order_date TEXT, delivery_date TEXT,
            total_amount REAL DEFAULT 0, extra_charges REAL DEFAULT 0,
            payable_amount REAL DEFAULT 0, advance_paid REAL DEFAULT 0,
            remaining REAL DEFAULT 0, payment_mode TEXT DEFAULT 'cash',
            status TEXT DEFAULT 'pending', is_urgent INTEGER DEFAULT 0,
            note TEXT DEFAULT '', repeat_of TEXT, delivered_at TEXT,
            created_at TEXT DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'))""",
        """CREATE TABLE IF NOT EXISTS order_items (
            id SERIAL PRIMARY KEY, order_id INTEGER NOT NULL,
            garment_type TEXT NOT NULL, quantity INTEGER DEFAULT 1,
            rate REAL DEFAULT 0, amount REAL DEFAULT 0,
            measurements TEXT DEFAULT '{}', notes TEXT)""",
        """CREATE TABLE IF NOT EXISTS order_images (
            id SERIAL PRIMARY KEY, order_id INTEGER NOT NULL,
            file_path TEXT NOT NULL,
            uploaded_at TEXT DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'))""",
        """CREATE TABLE IF NOT EXISTS work_logs (
            id SERIAL PRIMARY KEY, order_id INTEGER NOT NULL,
            order_code TEXT NOT NULL, garment_type TEXT NOT NULL,
            qty_done INTEGER DEFAULT 0,
            log_date TEXT DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD'),
            making_rate REAL DEFAULT 0, notes TEXT DEFAULT '',
            employee_name TEXT DEFAULT '', is_non_stitch INTEGER DEFAULT 0,
            rate_override REAL DEFAULT 0,
            created_at TEXT DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'))""",
        """CREATE TABLE IF NOT EXISTS finance (
            id SERIAL PRIMARY KEY, tx_date TEXT NOT NULL,
            tx_type TEXT NOT NULL, category TEXT NOT NULL,
            amount REAL NOT NULL, mode TEXT DEFAULT 'cash',
            order_id INTEGER, note TEXT, created_by TEXT DEFAULT 'employee',
            created_at TEXT DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'))""",
        """CREATE TABLE IF NOT EXISTS inventory (
            id SERIAL PRIMARY KEY, item_name TEXT UNIQUE NOT NULL,
            quantity REAL DEFAULT 0, unit TEXT DEFAULT 'pcs',
            low_alert_at REAL DEFAULT 0,
            updated_at TEXT DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'))""",
        """CREATE TABLE IF NOT EXISTS whatsapp_log (
            id SERIAL PRIMARY KEY, order_id INTEGER,
            mobile TEXT NOT NULL, message_type TEXT,
            sent_at TEXT DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'))""",
        """CREATE TABLE IF NOT EXISTS employees (
            id SERIAL PRIMARY KEY, name TEXT NOT NULL UNIQUE,
            phone TEXT DEFAULT '', active INTEGER DEFAULT 1,
            skills TEXT DEFAULT 'stitch', hindi_name TEXT DEFAULT '',
            created_at TEXT DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'))""",
        """CREATE TABLE IF NOT EXISTS measurement_fields (
            id SERIAL PRIMARY KEY, garment_type TEXT NOT NULL,
            field_name TEXT NOT NULL, sort_order INTEGER DEFAULT 0,
            UNIQUE(garment_type, field_name))""",
        """CREATE TABLE IF NOT EXISTS shop_logo (id INTEGER PRIMARY KEY, data TEXT)""",
        """CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)""",
        """CREATE TABLE IF NOT EXISTS salary_advances (
            id SERIAL PRIMARY KEY, employee_name TEXT,
            amount REAL, note TEXT, advance_date TEXT, created_at TEXT)""",
        """CREATE TABLE IF NOT EXISTS notify_log (
            id SERIAL PRIMARY KEY, order_code TEXT,
            customer TEXT, mobile TEXT, lang TEXT, sent_at TEXT)""",
        """CREATE TABLE IF NOT EXISTS gallery_types (
            id SERIAL PRIMARY KEY, name TEXT NOT NULL,
            parent_id INTEGER DEFAULT NULL, sort_order INTEGER DEFAULT 0,
            created_at TEXT DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'))""",
        """CREATE TABLE IF NOT EXISTS gallery_images (
            id SERIAL PRIMARY KEY, type_id INTEGER NOT NULL,
            filename TEXT NOT NULL, caption TEXT DEFAULT '',
            sort_order INTEGER DEFAULT 0,
            created_at TEXT DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'))""",
    ]
    for s in statements:
        cur.execute(s)

    _insert_defaults_pg(cur)
    conn.commit()
    conn.close()


def _insert_defaults_pg(cur):
    defaults = [
        ("owner_pin","1234"),("shop_name","Uttam Tailors"),
        ("whatsapp_number",""),("default_language","hinglish"),
        ("last_order_code","3599"),("work_rate_measurement","0"),
        ("work_rate_cutting","25"),("work_rate_alteration","15"),
        ("finance_income_cats","advance,payment,alteration,other income"),
        ("finance_expense_cats","thread,buttons,fabric,electricity,rent,salary,transport,maintenance,other expense"),
        ("rate_list_image",""),
    ]
    for k,v in defaults:
        cur.execute("INSERT INTO settings(key,value) VALUES(%s,%s) ON CONFLICT(key) DO NOTHING",(k,v))

    cust_rates = [
        ("customer_rate_Shirt","350"),("customer_rate_Shirt Linen","450"),
        ("customer_rate_Pant","450"),("customer_rate_Pant Double","550"),
        ("customer_rate_Jeans","550"),("customer_rate_Suit 2pc","2800"),
        ("customer_rate_Suit 3pc","3500"),("customer_rate_Blazer","2300"),
        ("customer_rate_Kurta","800"),("customer_rate_Kurta Pajama","1000"),
        ("customer_rate_Pajama","300"),("customer_rate_Pathani","800"),
        ("customer_rate_Sherwani","3500"),("customer_rate_Safari","1500"),
        ("customer_rate_Waistcoat","800"),("customer_rate_Alteration","100"),
        ("customer_rate_Cutting Only","100"),
    ]
    for k,v in cust_rates:
        cur.execute("INSERT INTO settings(key,value) VALUES(%s,%s) ON CONFLICT(key) DO NOTHING",(k,v))

    stitch_rates = [
        ("stitch_rate_Shirt","100"),("stitch_rate_Shirt Linen","120"),
        ("stitch_rate_Pant","105"),("stitch_rate_Pant Double","120"),
        ("stitch_rate_Jeans","110"),("stitch_rate_Suit 2pc","350"),
        ("stitch_rate_Suit 3pc","450"),("stitch_rate_Blazer","300"),
        ("stitch_rate_Kurta","120"),("stitch_rate_Kurta Pajama","180"),
        ("stitch_rate_Pajama","80"),("stitch_rate_Pathani","120"),
        ("stitch_rate_Sherwani","450"),("stitch_rate_Safari","200"),
        ("stitch_rate_Waistcoat","100"),("stitch_rate_Alteration","50"),
        ("stitch_rate_Cutting Only","40"),
    ]
    for k,v in stitch_rates:
        cur.execute("INSERT INTO settings(key,value) VALUES(%s,%s) ON CONFLICT(key) DO NOTHING",(k,v))

    cur.execute("SELECT COUNT(*) FROM measurement_fields")
    if cur.fetchone()[0] == 0:
        meas = [
            ("Pant","Lambai",1),("Pant","Kamar",2),("Pant","Seat",3),("Pant","Mori",4),("Pant","Jangh",5),("Pant","Goda",6),("Pant","Langot",7),
            ("Pant Double","Lambai",1),("Pant Double","Kamar",2),("Pant Double","Seat",3),("Pant Double","Mori",4),("Pant Double","Jangh",5),("Pant Double","Goda",6),("Pant Double","Langot",7),
            ("Jeans","Lambai",1),("Jeans","Kamar",2),("Jeans","Seat",3),("Jeans","Mori",4),("Jeans","Jangh",5),("Jeans","Goda",6),("Jeans","Langot",7),
            ("Pajama","Lambai",1),("Pajama","Kamar",2),("Pajama","Seat",3),("Pajama","Mori",4),("Pajama","Jangh",5),("Pajama","Goda",6),("Pajama","Langot",7),
            ("Shirt","Lambai",1),("Shirt","Seeno",2),("Shirt","Kamar",3),("Shirt","Shoulder",4),("Shirt","Collar",5),("Shirt","Aastin",6),("Shirt","Cough",7),("Shirt","Part 1",8),("Shirt","Part 2",9),("Shirt","Part 3",10),
            ("Shirt Linen","Lambai",1),("Shirt Linen","Seeno",2),("Shirt Linen","Kamar",3),("Shirt Linen","Shoulder",4),("Shirt Linen","Collar",5),("Shirt Linen","Aastin",6),("Shirt Linen","Cough",7),("Shirt Linen","Part 1",8),("Shirt Linen","Part 2",9),("Shirt Linen","Part 3",10),
            ("Kurta","Lambai",1),("Kurta","Seeno",2),("Kurta","Kamar",3),("Kurta","Shoulder",4),("Kurta","Collar",5),("Kurta","Aastin",6),("Kurta","Cough",7),("Kurta","Part 1",8),("Kurta","Part 2",9),("Kurta","Part 3",10),
            ("Pathani","Lambai",1),("Pathani","Seeno",2),("Pathani","Kamar",3),("Pathani","Shoulder",4),("Pathani","Collar",5),("Pathani","Aastin",6),("Pathani","Cough",7),("Pathani","Part 1",8),("Pathani","Part 2",9),("Pathani","Part 3",10),
            ("Sherwani","Lambai",1),("Sherwani","Seeno",2),("Sherwani","Kamar",3),("Sherwani","Shoulder",4),("Sherwani","Collar",5),("Sherwani","Aastin",6),("Sherwani","Cough",7),("Sherwani","Part 1",8),("Sherwani","Part 2",9),("Sherwani","Part 3",10),
            ("Blazer","Lambai",1),("Blazer","Seeno",2),("Blazer","Kamar",3),("Blazer","Shoulder",4),("Blazer","Aastin",5),("Blazer","Mori",6),("Blazer","Back Paat",7),
            ("Suit 2pc","Lambai",1),("Suit 2pc","Seeno",2),("Suit 2pc","Kamar",3),("Suit 2pc","Shoulder",4),("Suit 2pc","Aastin",5),("Suit 2pc","Mori",6),("Suit 2pc","Back Paat",7),("Suit 2pc","P-Lambai",8),("Suit 2pc","P-Kamar",9),("Suit 2pc","P-Seat",10),("Suit 2pc","P-Mori",11),
            ("Suit 3pc","Lambai",1),("Suit 3pc","Seeno",2),("Suit 3pc","Kamar",3),("Suit 3pc","Shoulder",4),("Suit 3pc","Aastin",5),("Suit 3pc","Mori",6),("Suit 3pc","Back Paat",7),("Suit 3pc","P-Lambai",8),("Suit 3pc","P-Kamar",9),("Suit 3pc","P-Seat",10),("Suit 3pc","P-Mori",11),
            ("Safari","Lambai",1),("Safari","Seeno",2),("Safari","Kamar",3),("Safari","Shoulder",4),("Safari","Collar",5),("Safari","Aastin",6),("Safari","Cough",7),("Safari","P-Lambai",8),("Safari","P-Kamar",9),("Safari","P-Seat",10),("Safari","P-Mori",11),
            ("Kurta Pajama","Lambai",1),("Kurta Pajama","Seeno",2),("Kurta Pajama","Kamar",3),("Kurta Pajama","Shoulder",4),("Kurta Pajama","Aastin",5),("Kurta Pajama","P-Lambai",6),("Kurta Pajama","P-Jangh",7),("Kurta Pajama","P-Mori",8),
            ("Waistcoat","Lambai",1),("Waistcoat","Seeno",2),("Waistcoat","Shoulder",3),("Waistcoat","Kamar",4),
            ("Alteration","Details",1),("Cutting Only","Details",1),
        ]
        for gt,fn,so in meas:
            cur.execute("INSERT INTO measurement_fields(garment_type,field_name,sort_order) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING",(gt,fn,so))

    employees = [("Kamal","कमल","naap+kataai+silai"),("Bhagwan","भगवान","silai"),("Sawarmal","सावरमल","silai"),("Mahesh","महेश","silai"),("Manak Tau","मानक ताऊ","silai")]
    for name,hindi,skills in employees:
        cur.execute("INSERT INTO employees(name,hindi_name,skills,active) VALUES(%s,%s,%s,1) ON CONFLICT(name) DO NOTHING",(name,hindi,skills))


def _init_sqlite():
    import sqlite3
    conn = sqlite3.connect(Config.DATABASE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, mobile TEXT, address TEXT, created_at TEXT DEFAULT (datetime('now','localtime')));
        CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, order_code TEXT UNIQUE NOT NULL, customer_id INTEGER NOT NULL, order_date TEXT, delivery_date TEXT, total_amount REAL DEFAULT 0, extra_charges REAL DEFAULT 0, payable_amount REAL DEFAULT 0, advance_paid REAL DEFAULT 0, remaining REAL DEFAULT 0, payment_mode TEXT DEFAULT 'cash', status TEXT DEFAULT 'pending', is_urgent INTEGER DEFAULT 0, note TEXT DEFAULT '', repeat_of TEXT, delivered_at TEXT, created_at TEXT DEFAULT (datetime('now','localtime')));
        CREATE TABLE IF NOT EXISTS order_items (id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL, garment_type TEXT NOT NULL, quantity INTEGER DEFAULT 1, rate REAL DEFAULT 0, amount REAL DEFAULT 0, measurements TEXT DEFAULT '{}', notes TEXT);
        CREATE TABLE IF NOT EXISTS order_images (id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL, file_path TEXT NOT NULL, uploaded_at TEXT DEFAULT (datetime('now','localtime')));
        CREATE TABLE IF NOT EXISTS work_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL, order_code TEXT NOT NULL, garment_type TEXT NOT NULL, qty_done INTEGER DEFAULT 0, log_date TEXT DEFAULT (date('now','localtime')), making_rate REAL DEFAULT 0, notes TEXT DEFAULT '', employee_name TEXT DEFAULT '', is_non_stitch INTEGER DEFAULT 0, rate_override REAL DEFAULT 0, created_at TEXT DEFAULT (datetime('now','localtime')));
        CREATE TABLE IF NOT EXISTS finance (id INTEGER PRIMARY KEY AUTOINCREMENT, tx_date TEXT NOT NULL, tx_type TEXT NOT NULL, category TEXT NOT NULL, amount REAL NOT NULL, mode TEXT DEFAULT 'cash', order_id INTEGER, note TEXT, created_by TEXT DEFAULT 'employee', created_at TEXT DEFAULT (datetime('now','localtime')));
        CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT UNIQUE NOT NULL, quantity REAL DEFAULT 0, unit TEXT DEFAULT 'pcs', low_alert_at REAL DEFAULT 0, updated_at TEXT DEFAULT (datetime('now','localtime')));
        CREATE TABLE IF NOT EXISTS whatsapp_log (id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER, mobile TEXT NOT NULL, message_type TEXT, sent_at TEXT DEFAULT (datetime('now','localtime')));
        CREATE TABLE IF NOT EXISTS employees (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, phone TEXT DEFAULT '', active INTEGER DEFAULT 1, skills TEXT DEFAULT 'stitch', hindi_name TEXT DEFAULT '', created_at TEXT DEFAULT (datetime('now','localtime')));
        CREATE TABLE IF NOT EXISTS measurement_fields (id INTEGER PRIMARY KEY AUTOINCREMENT, garment_type TEXT NOT NULL, field_name TEXT NOT NULL, sort_order INTEGER DEFAULT 0, UNIQUE(garment_type, field_name));
        CREATE TABLE IF NOT EXISTS shop_logo (id INTEGER PRIMARY KEY, data TEXT);
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS salary_advances (id INTEGER PRIMARY KEY AUTOINCREMENT, employee_name TEXT, amount REAL, note TEXT, advance_date TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS notify_log (id INTEGER PRIMARY KEY AUTOINCREMENT, order_code TEXT, customer TEXT, mobile TEXT, lang TEXT, sent_at TEXT);
        CREATE TABLE IF NOT EXISTS gallery_types (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, parent_id INTEGER DEFAULT NULL, sort_order INTEGER DEFAULT 0, created_at TEXT DEFAULT (datetime('now','localtime')));
        CREATE TABLE IF NOT EXISTS gallery_images (id INTEGER PRIMARY KEY AUTOINCREMENT, type_id INTEGER NOT NULL, filename TEXT NOT NULL, caption TEXT DEFAULT '', sort_order INTEGER DEFAULT 0, created_at TEXT DEFAULT (datetime('now','localtime')));
    """)
    defaults = [("owner_pin","1234"),("shop_name","Uttam Tailors"),("whatsapp_number",""),("default_language","hinglish"),("last_order_code","3599"),("work_rate_measurement","0"),("work_rate_cutting","25"),("work_rate_alteration","15"),("finance_income_cats","advance,payment,alteration,other income"),("finance_expense_cats","thread,buttons,fabric,electricity,rent,salary,transport,maintenance,other expense"),("rate_list_image","")]
    for k,v in defaults:
        cur.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)",(k,v))
    conn.commit(); conn.close()


# ── get_setting / set_setting ─────────────────────────────────────────────────

_settings_cache = {}
_settings_cache_valid = False

def _load_settings_cache():
    global _settings_cache, _settings_cache_valid
    try:
        conn = get_db()
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
        conn.close()
        _settings_cache = {r["key"]: r["value"] for r in rows}
        _settings_cache_valid = True
    except:
        _settings_cache_valid = False

def get_setting(key, default=""):
    global _settings_cache_valid
    if not _settings_cache_valid:
        _load_settings_cache()
    return _settings_cache.get(key, default)

def set_setting(key, value):
    global _settings_cache, _settings_cache_valid
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, value))
    conn.commit()
    conn.close()
    # Update cache immediately
    _settings_cache[key] = value
    _settings_cache_valid = True

def invalidate_settings_cache():
    global _settings_cache_valid
    _settings_cache_valid = False


# ── order codes ───────────────────────────────────────────────────────────────

def peek_order_code():
    conn = get_db()
    row = conn.execute("SELECT value FROM settings WHERE key='last_order_code'").fetchone()
    setting_last = int(row["value"]) if row else 3599
    max_row = conn.execute("SELECT MAX(CAST(order_code AS INTEGER)) as m FROM orders").fetchone()
    db_last = max_row["m"] if max_row and max_row["m"] else 0
    conn.close()
    return str(max(setting_last, db_last) + 1)


def next_order_code():
    conn = get_db()
    row = conn.execute("SELECT value FROM settings WHERE key='last_order_code'").fetchone()
    setting_last = int(row["value"]) if row else 3599
    max_row = conn.execute("SELECT MAX(CAST(order_code AS INTEGER)) as m FROM orders").fetchone()
    db_last = max_row["m"] if max_row and max_row["m"] else 0
    new_code = max(setting_last, db_last) + 1
    conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('last_order_code',?)", (str(new_code),))
    conn.commit()
    conn.close()
    return str(new_code)
