import sqlite3
import os
from config import Config


def get_db():
    conn = sqlite3.connect(Config.DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create all tables if they don't exist. Safe to call on every startup."""
    conn = get_db()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS customers (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            mobile      TEXT,
            address     TEXT,
            created_at  TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS orders (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            order_code      TEXT UNIQUE NOT NULL,
            customer_id     INTEGER NOT NULL,
            order_date      TEXT,
            delivery_date   TEXT,
            total_amount    REAL DEFAULT 0,
            extra_charges   REAL DEFAULT 0,
            payable_amount  REAL DEFAULT 0,
            advance_paid    REAL DEFAULT 0,
            remaining       REAL DEFAULT 0,
            payment_mode    TEXT DEFAULT 'cash',
            status          TEXT DEFAULT 'pending',
            is_urgent       INTEGER DEFAULT 0,
            note            TEXT,
            repeat_of       TEXT DEFAULT NULL,
            created_at      TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        );

        CREATE TABLE IF NOT EXISTS order_items (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id        INTEGER NOT NULL,
            garment_type    TEXT NOT NULL,
            quantity        INTEGER DEFAULT 1,
            rate            REAL DEFAULT 0,
            amount          REAL DEFAULT 0,
            measurements    TEXT DEFAULT '{}',
            notes           TEXT,
            FOREIGN KEY (order_id) REFERENCES orders(id)
        );

        CREATE TABLE IF NOT EXISTS order_images (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id    INTEGER NOT NULL,
            file_path   TEXT NOT NULL,
            uploaded_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (order_id) REFERENCES orders(id)
        );

        CREATE TABLE IF NOT EXISTS work_logs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id        INTEGER NOT NULL,
            order_code      TEXT NOT NULL,
            garment_type    TEXT NOT NULL,
            qty_done        INTEGER DEFAULT 0,
            log_date        TEXT DEFAULT (date('now','localtime')),
            making_rate     REAL DEFAULT 0,
            notes           TEXT,
            created_at      TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (order_id) REFERENCES orders(id)
        );

        CREATE TABLE IF NOT EXISTS finance (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            tx_date     TEXT NOT NULL,
            tx_type     TEXT NOT NULL,
            category    TEXT NOT NULL,
            amount      REAL NOT NULL,
            mode        TEXT DEFAULT 'cash',
            order_id    INTEGER,
            note        TEXT,
            created_by  TEXT DEFAULT 'employee',
            created_at  TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS inventory (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name       TEXT UNIQUE NOT NULL,
            quantity        REAL DEFAULT 0,
            unit            TEXT DEFAULT 'pcs',
            low_alert_at    REAL DEFAULT 0,
            updated_at      TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS whatsapp_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id        INTEGER,
            mobile          TEXT NOT NULL,
            message_type    TEXT,
            sent_at         TEXT DEFAULT (datetime('now','localtime'))
        );



        CREATE TABLE IF NOT EXISTS employees (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL UNIQUE,
            phone       TEXT DEFAULT '',
            active      INTEGER DEFAULT 1,
            created_at  TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS measurement_fields (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            garment_type TEXT NOT NULL,
            field_name   TEXT NOT NULL,
            sort_order   INTEGER DEFAULT 0,
            UNIQUE(garment_type, field_name)
        );

        CREATE TABLE IF NOT EXISTS shop_logo (
            id      INTEGER PRIMARY KEY,
            data    TEXT
        );
        CREATE TABLE IF NOT EXISTS settings (
            key     TEXT PRIMARY KEY,
            value   TEXT
        );
    """)

    # Insert default settings only if they don't exist
    defaults = [
        ("owner_pin",        "1234"),
        ("shop_name",        "Uttam Tailors"),
        ("whatsapp_number",  ""),
        ("default_language", "hinglish"),
        ("last_order_code",  "3200"),
    ]
    for key, val in defaults:
        cur.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (key, val)
        )


    # Insert NEW measurement fields - Hindi names as per owner specification
    # Only insert if table is empty (to not override manually set fields)
    existing_count = conn.execute("SELECT COUNT(*) FROM measurement_fields").fetchone()[0]
    if existing_count == 0:
        new_meas = [
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
            ("Jacket","Lambai",1),("Jacket","Shoulder",2),("Jacket","Seeno",3),("Jacket","Kamar",4),("Jacket","Seat",5),("Jacket","Collar",6),
            ("Safari","Lambai",1),("Safari","Seeno",2),("Safari","Kamar",3),("Safari","Shoulder",4),("Safari","Collar",5),("Safari","Aastin",6),("Safari","Cough",7),("Safari","P-Lambai",8),("Safari","P-Kamar",9),("Safari","P-Seat",10),("Safari","P-Mori",11),
            ("Kurta Pajama","Lambai",1),("Kurta Pajama","Seeno",2),("Kurta Pajama","Kamar",3),("Kurta Pajama","Shoulder",4),("Kurta Pajama","Aastin",5),("Kurta Pajama","P-Lambai",6),("Kurta Pajama","P-Jangh",7),("Kurta Pajama","P-Mori",8),
            ("Waistcoat","Lambai",1),("Waistcoat","Seeno",2),("Waistcoat","Shoulder",3),("Waistcoat","Kamar",4),
            ("Alteration","Details",1),("Cutting Only","Details",1),
        ]
        for gt,fn,so in new_meas:
            cur.execute("INSERT OR IGNORE INTO measurement_fields(garment_type,field_name,sort_order) VALUES(?,?,?)",(gt,fn,so))


    # Customer-facing rates (what you charge customers)
    cust_rate_defaults = [
        ("customer_rate_Shirt","350"), ("customer_rate_Shirt Linen","450"),
        ("customer_rate_Pant","450"),  ("customer_rate_Pant Double","550"),
        ("customer_rate_Jeans","550"), ("customer_rate_Suit 2pc","2800"),
        ("customer_rate_Suit 3pc","3500"), ("customer_rate_Blazer","2300"),
        ("customer_rate_Kurta","800"), ("customer_rate_Kurta Pajama","1000"),
        ("customer_rate_Pajama","300"), ("customer_rate_Pathani","800"),
        ("customer_rate_Sherwani","3500"), ("customer_rate_Safari","1500"),
        ("customer_rate_Waistcoat","800"), ("customer_rate_Alteration","100"),
        ("customer_rate_Cutting Only","100"),
    ]
    for key, val in cust_rate_defaults:
        cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, val))

    # Employee stitching rates (what you pay employees)
    stitch_rate_defaults = [
        ("stitch_rate_Shirt","100"), ("stitch_rate_Shirt Linen","120"),
        ("stitch_rate_Pant","105"),  ("stitch_rate_Pant Double","120"),
        ("stitch_rate_Jeans","110"), ("stitch_rate_Suit 2pc","350"),
        ("stitch_rate_Suit 3pc","450"), ("stitch_rate_Blazer","300"),
        ("stitch_rate_Kurta","120"), ("stitch_rate_Kurta Pajama","180"),
        ("stitch_rate_Pajama","80"),  ("stitch_rate_Pathani","120"),
        ("stitch_rate_Sherwani","450"), ("stitch_rate_Safari","200"),
        ("stitch_rate_Waistcoat","100"), ("stitch_rate_Alteration","50"),
        ("stitch_rate_Cutting Only","40"),
    ]
    for key, val in stitch_rate_defaults:
        cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, val))

    # Rate list image
    cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", ("rate_list_image", ""))



    # Add delivered_at column if missing
    cur.execute("""
        CREATE TABLE IF NOT EXISTS salary_advances (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_name TEXT,
            amount      REAL,
            note        TEXT,
            advance_date TEXT,
            created_at  TEXT
        )
    """)
    # Create notify_log table if not exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS notify_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            order_code TEXT,
            customer   TEXT,
            mobile     TEXT,
            lang       TEXT,
            sent_at    TEXT
        )
    """)

    cur.execute("PRAGMA table_info(orders)")
    order_cols = [r[1] for r in cur.fetchall()]
    if "delivered_at" not in order_cols:
        cur.execute("ALTER TABLE orders ADD COLUMN delivered_at TEXT DEFAULT NULL")
    # Add logged_by to work_logs if missing
    cur.execute("PRAGMA table_info(work_logs)")
    wl_cols = [r[1] for r in cur.fetchall()]
    if "employee_name" not in wl_cols:
        cur.execute("ALTER TABLE work_logs ADD COLUMN employee_name TEXT DEFAULT ''")

    # Add repeat_of column if missing (migration for existing DBs)
    cur.execute("PRAGMA table_info(orders)")
    order_cols = [r[1] for r in cur.fetchall()]
    if "repeat_of" not in order_cols:
        cur.execute("ALTER TABLE orders ADD COLUMN repeat_of TEXT DEFAULT NULL")

    # ── Employee column migrations ──────────────────────────────────────────
    cur.execute("PRAGMA table_info(employees)")
    emp_cols = [r[1] for r in cur.fetchall()]
    if "skills" not in emp_cols:
        cur.execute("ALTER TABLE employees ADD COLUMN skills TEXT DEFAULT 'stitch'")
    if "hindi_name" not in emp_cols:
        cur.execute("ALTER TABLE employees ADD COLUMN hindi_name TEXT DEFAULT ''")

    # Set Kamal as 'all' skills by default if not already set
    cur.execute("UPDATE employees SET skills='all' WHERE name='Kamal' AND (skills IS NULL OR skills='stitch')")

    # Set Hindi names for known employees if not set
    hindi_map = [
        ("Kamal",     "कमल"),
        ("Bhagwan",   "भगवान"),
        ("Sawarmal",  "सावरमल"),
        ("Mahesh",    "महेश"),
        ("Manak Tau", "मानक ताऊ"),
    ]
    for eng, hin in hindi_map:
        cur.execute(
            "UPDATE employees SET hindi_name=? WHERE name=? AND (hindi_name IS NULL OR hindi_name='')",
            (hin, eng)
        )

    conn.commit()
    conn.close()


def get_setting(key, default=""):
    conn = get_db()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key, value):
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        (key, value)
    )

    # Default work type rates
    for wk, wv in [("work_rate_measurement","0"),("work_rate_cutting","25"),("work_rate_alteration","15")]:
        conn.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (wk, wv))

    # Default finance categories (only if not already set)
    r = conn.execute("SELECT value FROM settings WHERE key='finance_income_cats'").fetchone()
    if not r:
        conn.execute("INSERT INTO settings(key,value) VALUES('finance_income_cats','advance,payment,alteration,other income')")
    r2 = conn.execute("SELECT value FROM settings WHERE key='finance_expense_cats'").fetchone()
    if not r2:
        conn.execute("INSERT INTO settings(key,value) VALUES('finance_expense_cats','thread,buttons,fabric,electricity,rent,salary,transport,maintenance,other expense')")

    # Default employees
    default_employees = ['Kamal', 'Bhagwan', 'Sawarmal', 'Mahesh', 'Manak Tau']
    for emp_name in default_employees:
        conn.execute("INSERT OR IGNORE INTO employees(name,phone,active) VALUES(?,\'\',1)", (emp_name,))

    conn.commit()
    conn.close()


def peek_order_code():
    """Return what the NEXT order code will be without incrementing.
    Always returns max(setting, max_existing_order) + 1 to prevent collisions."""
    conn = get_db()
    row = conn.execute("SELECT value FROM settings WHERE key='last_order_code'").fetchone()
    setting_last = int(row["value"]) if row else 3599
    # Also check max actual order code in DB to prevent repeats
    max_row = conn.execute("SELECT MAX(CAST(order_code AS INTEGER)) as m FROM orders").fetchone()
    db_last = max_row["m"] if max_row and max_row["m"] else 0
    last = max(setting_last, db_last)
    conn.close()
    return str(last + 1)


def next_order_code():
    """Atomically increment and return the next order code. Prevents duplicates."""
    conn = get_db()
    row = conn.execute("SELECT value FROM settings WHERE key='last_order_code'").fetchone()
    setting_last = int(row["value"]) if row else 3599
    max_row = conn.execute("SELECT MAX(CAST(order_code AS INTEGER)) as m FROM orders").fetchone()
    db_last = max_row["m"] if max_row and max_row["m"] else 0
    last = max(setting_last, db_last)
    new_code = last + 1
    conn.execute(
        "INSERT OR REPLACE INTO settings(key,value) VALUES('last_order_code',?)",
        (str(new_code),)
    )
    conn.commit()
    conn.close()
    return str(new_code)
