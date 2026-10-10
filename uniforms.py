# ============================================================
# UNIFORM SALES POS — PROFESSIONAL EDITION (PERFORMANCE FIX)
# ============================================================
import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from datetime import datetime, timedelta, date
import streamlit.components.v1 as components
from contextlib import contextmanager
import bcrypt
import io
import json

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Uniform Sales",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# DESIGN SYSTEM
# ============================================================
st.markdown("""
<style>
    .stApp { background-color: #f8fafc; }
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI',
                     Roboto, sans-serif;
        color: #1e293b;
    }
    h1 { font-size: 28px; font-weight: 700; color: #0f172a; letter-spacing: -0.5px; margin-bottom: 4px; }
    h2 { font-size: 20px; font-weight: 600; color: #1e293b; margin-top: 8px; margin-bottom: 8px; }
    h3 { font-size: 16px; font-weight: 600; color: #334155; margin-top: 12px; margin-bottom: 6px; }
    p  { color: #475569; }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
        border-right: 1px solid #334155;
    }
    [data-testid="stSidebar"] * { color: #cbd5e1; }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 { color: #f1f5f9; }
    [data-testid="stSidebar"] .stButton > button {
        background-color: transparent;
        color: #cbd5e1;
        border: none;
        text-align: left;
        justify-content: flex-start;
        padding: 8px 12px;
        font-weight: 500;
        font-size: 14px;
        border-radius: 6px;
        transition: background 0.15s;
        width: 100%;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background-color: #334155;
        color: #f1f5f9;
    }
    [data-testid="stSidebar"] hr {
        border-color: #334155;
        margin: 12px 0;
    }

    .stButton > button {
        background-color: #f1f5f9;
        color: #0f172a;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        font-weight: 500;
        padding: 6px 14px;
        transition: all 0.15s;
    }
    .stButton > button:hover {
        background-color: #e2e8f0;
        border-color: #cbd5e1;
        color: #0f172a;
    }
    .stButton > button[kind="primary"] {
        background-color: #1e293b;
        color: #ffffff;
        border: 1px solid #1e293b;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #0f172a;
        border-color: #0f172a;
        color: #ffffff;
    }
    .stDownloadButton > button {
        background-color: #f1f5f9;
        color: #0f172a;
        border: 1px solid #e2e8f0;
    }

    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 16px 18px;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    div[data-testid="stMetric"] > label {
        color: #64748b !important;
        font-size: 12px !important;
        font-weight: 500 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    div[data-testid="stMetricValue"] {
        color: #0f172a !important;
        font-size: 26px !important;
        font-weight: 700 !important;
    }

    .card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 18px 20px;
        margin-bottom: 14px;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    .card-title {
        font-size: 13px;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        margin: 0 0 12px 0;
    }

    .kpi-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 16px 18px;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
        height: 100%;
    }
    .kpi-label {
        font-size: 12px;
        font-weight: 500;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 8px;
    }
    .kpi-value {
        font-size: 26px;
        font-weight: 700;
        color: #0f172a;
        letter-spacing: -0.5px;
        line-height: 1.1;
    }
    .kpi-sub {
        font-size: 12px;
        color: #64748b;
        margin-top: 6px;
    }
    .kpi-sub.pos { color: #059669; }
    .kpi-sub.neg { color: #dc2626; }

    .alert-item {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 10px 12px;
        background: #fef9c3;
        border-left: 3px solid #eab308;
        border-radius: 6px;
        margin-bottom: 8px;
        font-size: 14px;
        color: #713f12;
    }
    .alert-item.danger {
        background: #fee2e2;
        border-left-color: #dc2626;
        color: #7f1d1d;
    }
    .alert-item.ok {
        background: #dcfce7;
        border-left-color: #16a34a;
        color: #14532d;
    }

    .login-box {
        max-width: 380px;
        margin: 80px auto;
        padding: 40px;
        background: #ffffff;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
    }
    .login-box h1 {
        text-align: center;
        font-size: 22px;
        margin-bottom: 4px;
    }
    .login-box p {
        text-align: center;
        color: #64748b;
        font-size: 14px;
        margin-bottom: 24px;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        border-bottom: 1px solid #e2e8f0;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 16px;
        font-weight: 500;
        color: #64748b;
        background: transparent;
        border-radius: 0;
    }
    .stTabs [aria-selected="true"] {
        color: #0f172a !important;
        border-bottom: 2px solid #1e293b !important;
    }

    hr {
        border: none;
        border-top: 1px solid #e2e8f0;
        margin: 16px 0;
    }

    @media (max-width: 768px) {
        .stButton > button { padding: 10px 14px !important; font-size: 15px !important; min-height: 44px !important; }
        input[type="number"], input[type="text"], input[type="password"] { font-size: 16px !important; }
        h1 { font-size: 22px !important; }
        .kpi-value { font-size: 22px !important; }
    }

    @media print {
        [data-testid="stSidebar"], [data-testid="stHeader"],
        .stButton, .stDownloadButton, [data-testid="stToolbar"],
        footer { display: none !important; }
        .stApp { background: white !important; }
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# DATABASE HELPERS
# ============================================================
def get_connection():
    try:
        db = st.secrets["postgres"]
        return psycopg2.connect(
            host=db["host"], port=db["port"],
            database=db["database"], user=db["user"],
            password=db["password"],
            sslmode=db.get("sslmode", "require"),
            connect_timeout=15,
        )
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return None


@contextmanager
def db_cursor(commit=False, dict_cursor=True):
    conn = get_connection()
    if conn is None:
        yield None
        return
    cur = conn.cursor(cursor_factory=RealDictCursor if dict_cursor else None)
    try:
        yield cur
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def query(sql, params=None, fetch="all"):
    with db_cursor() as cur:
        if cur is None:
            return [] if fetch != "one" else None
        cur.execute(sql, params or ())
        if fetch == "all":
            return cur.fetchall()
        if fetch == "one":
            return cur.fetchone()
        return None


def execute(sql, params=None):
    with db_cursor(commit=True) as cur:
        if cur is None:
            return False
        cur.execute(sql, params or ())
        return True


def execute_returning(sql, params=None):
    with db_cursor(commit=True) as cur:
        if cur is None:
            return None
        cur.execute(sql, params or ())
        return cur.fetchone()


# ============================================================
# CACHED MASTER DATA
# ============================================================
@st.cache_data(ttl=300, show_spinner=False)
def get_schools():
    return query("SELECT school_id, school_name FROM schools ORDER BY school_name;")


@st.cache_data(ttl=300, show_spinner=False)
def get_categories():
    return query("SELECT category_id, category_name FROM product_categories ORDER BY category_name;")


@st.cache_data(ttl=300, show_spinner=False)
def get_products(category_id=None):
    sql = """SELECT p.product_id, p.product_name, p.sku, p.price, p.cost_price,
                    p.category_id, c.category_name
             FROM products p
             LEFT JOIN product_categories c ON c.category_id = p.category_id
             WHERE p.active = TRUE"""
    params = []
    if category_id:
        sql += " AND p.category_id = %s"
        params.append(category_id)
    sql += " ORDER BY p.product_name;"
    return query(sql, tuple(params))


@st.cache_data(ttl=30, show_spinner=False)
def get_all_stock_for_school(school_id):
    """Returns {product_id: available_qty} for all products at a school in ONE query."""
    rows = query(
        """
        SELECT p.product_id,
               COALESCE((
                   SELECT SUM(quantity_brought) FROM stock st
                   WHERE st.school_id = %s AND st.product_id = p.product_id
               ), 0)
               -
               COALESCE((
                   SELECT SUM(si.quantity) FROM sale_items si
                   JOIN sales s ON s.sale_id = si.sale_id
                   WHERE s.school_id = %s AND si.product_id = p.product_id
                     AND s.voided = FALSE
               ), 0)
               +
               COALESCE((
                   SELECT SUM(ri.quantity) FROM refund_items ri
                   JOIN refunds r ON r.refund_id = ri.refund_id
                   JOIN sale_items si2 ON si2.sale_item_id = ri.sale_item_id
                   JOIN sales s2 ON s2.sale_id = si2.sale_id
                   WHERE s2.school_id = %s AND si2.product_id = p.product_id
               ), 0) AS available
        FROM products p
        WHERE p.active = TRUE;
        """,
        (school_id, school_id, school_id),
    )
    return {int(r["product_id"]): int(r["available"] or 0) for r in rows}


@st.cache_data(ttl=60, show_spinner=False)
def get_school_prices_map(school_id):
    """Returns {product_id: price} for all school-specific overrides."""
    rows = query(
        "SELECT product_id, price FROM school_product_prices WHERE school_id = %s;",
        (school_id,),
    )
    return {int(r["product_id"]): float(r["price"]) for r in rows}


def clear_caches():
    try:
        get_schools.clear()
        get_categories.clear()
        get_products.clear()
        get_all_stock_for_school.clear()
        get_school_prices_map.clear()
    except Exception:
        pass


def invalidate_stock_cache():
    try:
        get_all_stock_for_school.clear()
    except Exception:
        pass


# ============================================================
# SETUP DATABASE
# ============================================================
@st.cache_resource(show_spinner=False)
def setup_database():
    conn = get_connection()
    if conn is None:
        return False
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id SERIAL PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                full_name VARCHAR(100) NOT NULL,
                role VARCHAR(20) NOT NULL DEFAULT 'cashier',
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS schools (
                school_id SERIAL PRIMARY KEY,
                school_name VARCHAR(100) NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS product_categories (
                category_id SERIAL PRIMARY KEY,
                category_name VARCHAR(50) NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS products (
                product_id SERIAL PRIMARY KEY,
                product_name VARCHAR(100) NOT NULL UNIQUE,
                sku VARCHAR(50),
                category_id INT REFERENCES product_categories(category_id),
                price NUMERIC(10,2) NOT NULL DEFAULT 0,
                cost_price NUMERIC(10,2) NOT NULL DEFAULT 0,
                active BOOLEAN DEFAULT TRUE
            );
            CREATE TABLE IF NOT EXISTS customers (
                customer_id SERIAL PRIMARY KEY,
                customer_name VARCHAR(100) NOT NULL,
                phone VARCHAR(20)
            );
            CREATE TABLE IF NOT EXISTS sales (
                sale_id SERIAL PRIMARY KEY,
                sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                school_id INT NOT NULL REFERENCES schools(school_id),
                customer_id INT REFERENCES customers(customer_id),
                total_amount NUMERIC(10,2) NOT NULL,
                payment_method VARCHAR(30),
                payment_status VARCHAR(20) DEFAULT 'Paid',
                term VARCHAR(20),
                year INT,
                voided BOOLEAN DEFAULT FALSE,
                voided_at TIMESTAMP,
                voided_by VARCHAR(50),
                void_reason TEXT
            );
            CREATE TABLE IF NOT EXISTS sale_items (
                sale_item_id SERIAL PRIMARY KEY,
                sale_id INT NOT NULL REFERENCES sales(sale_id),
                product_id INT NOT NULL REFERENCES products(product_id),
                quantity INT NOT NULL,
                unit_price NUMERIC(10,2) NOT NULL,
                line_total NUMERIC(10,2) NOT NULL,
                issued BOOLEAN DEFAULT TRUE,
                paid BOOLEAN DEFAULT TRUE
            );
            CREATE TABLE IF NOT EXISTS sale_payments (
                payment_id SERIAL PRIMARY KEY,
                sale_id INT NOT NULL REFERENCES sales(sale_id),
                method VARCHAR(30) NOT NULL,
                amount NUMERIC(10,2) NOT NULL
            );
            CREATE TABLE IF NOT EXISTS refunds (
                refund_id SERIAL PRIMARY KEY,
                sale_id INT NOT NULL REFERENCES sales(sale_id),
                refund_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                amount NUMERIC(10,2) NOT NULL,
                reason TEXT,
                refunded_by VARCHAR(50)
            );
            CREATE TABLE IF NOT EXISTS refund_items (
                refund_item_id SERIAL PRIMARY KEY,
                refund_id INT NOT NULL REFERENCES refunds(refund_id),
                sale_item_id INT NOT NULL REFERENCES sale_items(sale_item_id),
                quantity INT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS school_product_prices (
                school_product_price_id SERIAL PRIMARY KEY,
                school_id INT NOT NULL REFERENCES schools(school_id),
                category_name VARCHAR(100) NOT NULL,
                product_id INT NOT NULL REFERENCES products(product_id),
                price NUMERIC(10,2) NOT NULL DEFAULT 0,
                UNIQUE (school_id, category_name, product_id)
            );
            CREATE TABLE IF NOT EXISTS stock (
                stock_id SERIAL PRIMARY KEY,
                school_id INT NOT NULL REFERENCES schools(school_id),
                product_id INT NOT NULL REFERENCES products(product_id),
                quantity_brought INT NOT NULL,
                date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                term VARCHAR(20),
                year INT,
                unit_cost NUMERIC(10,2) DEFAULT 0,
                adjustment_reason VARCHAR(50),
                notes VARCHAR(255)
            );
            CREATE TABLE IF NOT EXISTS uniform_sets (
                set_id SERIAL PRIMARY KEY,
                school_id INT NOT NULL REFERENCES schools(school_id),
                set_name VARCHAR(100) NOT NULL
            );
            CREATE TABLE IF NOT EXISTS set_items (
                set_item_id SERIAL PRIMARY KEY,
                set_id INT NOT NULL REFERENCES uniform_sets(set_id),
                product_id INT NOT NULL REFERENCES products(product_id),
                quantity INT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS investors (
                investor_id SERIAL PRIMARY KEY,
                investor_name VARCHAR(100) NOT NULL UNIQUE,
                active BOOLEAN DEFAULT TRUE
            );
            CREATE TABLE IF NOT EXISTS financial_transactions (
                transaction_id SERIAL PRIMARY KEY,
                transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                transaction_type VARCHAR(50) NOT NULL,
                category VARCHAR(100) NOT NULL,
                description VARCHAR(255),
                amount NUMERIC(12,2) NOT NULL,
                investor_id INT REFERENCES investors(investor_id),
                term VARCHAR(20),
                year INT
            );
            CREATE TABLE IF NOT EXISTS tailor_production (
                production_id SERIAL PRIMARY KEY,
                school_id INT NOT NULL REFERENCES schools(school_id),
                product_id INT NOT NULL REFERENCES products(product_id),
                tailor_name VARCHAR(100) NOT NULL,
                quantity_produced INT NOT NULL,
                cost_per_item NUMERIC(10,2) NOT NULL,
                amount_paid NUMERIC(12,2) NOT NULL,
                production_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                term VARCHAR(20),
                year INT,
                notes VARCHAR(255)
            );
            CREATE TABLE IF NOT EXISTS audit_log (
                log_id SERIAL PRIMARY KEY,
                log_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                action VARCHAR(50) NOT NULL,
                table_name VARCHAR(100),
                record_id INT,
                user_name VARCHAR(100),
                details TEXT
            );
            CREATE TABLE IF NOT EXISTS daily_closings (
                closing_id SERIAL PRIMARY KEY,
                closing_date DATE NOT NULL UNIQUE,
                expected_cash NUMERIC(12,2) NOT NULL,
                counted_cash NUMERIC(12,2) NOT NULL,
                variance NUMERIC(12,2) NOT NULL,
                total_sales NUMERIC(12,2) NOT NULL,
                total_refunds NUMERIC(12,2) NOT NULL,
                notes TEXT,
                closed_by VARCHAR(50),
                closed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS held_sales (
                held_id SERIAL PRIMARY KEY,
                label VARCHAR(100) NOT NULL,
                cart_json TEXT NOT NULL,
                customer_name VARCHAR(100),
                customer_phone VARCHAR(20),
                school_id INT,
                held_by VARCHAR(50),
                held_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        for stmt in [
            "ALTER TABLE products ADD COLUMN IF NOT EXISTS cost_price NUMERIC(10,2) NOT NULL DEFAULT 0;",
            "ALTER TABLE products ADD COLUMN IF NOT EXISTS sku VARCHAR(50);",
            "ALTER TABLE products ADD COLUMN IF NOT EXISTS category_id INT;",
            "ALTER TABLE products ADD COLUMN IF NOT EXISTS active BOOLEAN DEFAULT TRUE;",
            "ALTER TABLE sales ADD COLUMN IF NOT EXISTS term VARCHAR(20);",
            "ALTER TABLE sales ADD COLUMN IF NOT EXISTS year INT;",
            "ALTER TABLE sales ADD COLUMN IF NOT EXISTS voided BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE sales ADD COLUMN IF NOT EXISTS voided_at TIMESTAMP;",
            "ALTER TABLE sales ADD COLUMN IF NOT EXISTS voided_by VARCHAR(50);",
            "ALTER TABLE sales ADD COLUMN IF NOT EXISTS void_reason TEXT;",
            "ALTER TABLE sale_items ADD COLUMN IF NOT EXISTS issued BOOLEAN DEFAULT TRUE;",
            "ALTER TABLE sale_items ADD COLUMN IF NOT EXISTS paid BOOLEAN DEFAULT TRUE;",
            "ALTER TABLE stock ADD COLUMN IF NOT EXISTS term VARCHAR(20);",
            "ALTER TABLE stock ADD COLUMN IF NOT EXISTS year INT;",
            "ALTER TABLE stock ADD COLUMN IF NOT EXISTS unit_cost NUMERIC(10,2) DEFAULT 0;",
            "ALTER TABLE stock ADD COLUMN IF NOT EXISTS adjustment_reason VARCHAR(50);",
            "ALTER TABLE stock ADD COLUMN IF NOT EXISTS notes VARCHAR(255);",
        ]:
            cur.execute(stmt)

        for cat in ["Uniform", "Sports", "Accessories", "Footwear", "Other"]:
            cur.execute(
                "INSERT INTO product_categories (category_name) VALUES (%s) ON CONFLICT DO NOTHING;",
                (cat,),
            )

        for s in ["LOVING BLOOMS SCHOOL", "WARIDI UTAWALA SCHOOL"]:
            cur.execute(
                "INSERT INTO schools (school_name) VALUES (%s) ON CONFLICT DO NOTHING;",
                (s,),
            )

        cur.execute("SELECT COUNT(*) FROM users;")
        if cur.fetchone()[0] == 0:
            default_hash = bcrypt.hashpw(b"admin2026", bcrypt.gensalt()).decode()
            cur.execute(
                """INSERT INTO users (username, password_hash, full_name, role)
                   VALUES ('admin', %s, 'Administrator', 'admin')""",
                (default_hash,),
            )

        products = [
            ("Skirt", 650), ("Blouse", 500), ("Socks", 200),
            ("Tracksuit Playgroup-PP2", 1600), ("Tracksuit G1-G6", 1800),
            ("Sweater", 1000), ("Tie", 150), ("Bow Tie", 150),
            ("Short", 400), ("Halfcoat", 600), ("Fleece", 2500),
            ("Trouser", 650), ("T-Shirt", 500), ("Wrap Skirt", 500),
            ("Half Sweater", 800),
        ]
        for name, price in products:
            cur.execute(
                """INSERT INTO products (product_name, price, cost_price)
                   VALUES (%s, %s, 0) ON CONFLICT (product_name) DO NOTHING;""",
                (name, price),
            )

        cur.execute(
            "INSERT INTO investors (investor_name, active) VALUES ('Gift', TRUE) "
            "ON CONFLICT (investor_name) DO UPDATE SET active = TRUE;"
        )
        cur.execute(
            "INSERT INTO investors (investor_name, active) VALUES ('Ken', TRUE) "
            "ON CONFLICT (investor_name) DO UPDATE SET active = TRUE;"
        )
        cur.execute(
            "UPDATE investors SET active = FALSE WHERE investor_name NOT IN ('Gift','Ken');"
        )

        for name, amount in [("Gift", 150000), ("Ken", 100000)]:
            cur.execute("SELECT investor_id FROM investors WHERE investor_name = %s;", (name,))
            row = cur.fetchone()
            if not row:
                continue
            inv_id = row[0]
            cur.execute(
                """SELECT COALESCE(SUM(amount),0) FROM financial_transactions
                   WHERE transaction_type = 'Capital Contribution' AND investor_id = %s;""",
                (inv_id,),
            )
            if float(cur.fetchone()[0] or 0) == 0:
                cur.execute(
                    """INSERT INTO financial_transactions
                       (transaction_type, category, description, amount, investor_id, year)
                       VALUES ('Capital Contribution','Investment',%s,%s,%s,%s);""",
                    (f"Initial investment by {name}", amount, inv_id, datetime.now().year),
                )

        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Database setup error: {e}")
        return False
    finally:
        cur.close()
        conn.close()


setup_database()


# ============================================================
# AUDIT LOGGING
# ============================================================
def log_action(action, table_name=None, record_id=None, details=None):
    try:
        user = st.session_state.get("user", {}).get("username", "system")
        execute(
            """INSERT INTO audit_log
               (action, table_name, record_id, user_name, details)
               VALUES (%s, %s, %s, %s, %s);""",
            (action, table_name, record_id, user, details),
        )
    except Exception:
        pass


# ============================================================
# AUTH
# ============================================================
def verify_password(plain, hashed):
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def hash_password(plain):
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def login_screen():
    st.markdown("""
    <div class="login-box">
        <h1>Uniform Sales</h1>
        <p>Sign in to continue</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("Username", key="login_user")
            password = st.text_input("Password", type="password", key="login_pw")
            submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")

        if submitted:
            row = query(
                "SELECT * FROM users WHERE username = %s AND active = TRUE;",
                (username.strip().lower(),), fetch="one",
            )
            if row and verify_password(password, row["password_hash"]):
                st.session_state.user = {
                    "user_id": row["user_id"],
                    "username": row["username"],
                    "role": row["role"],
                    "name": row["full_name"],
                }
                log_action("LOGIN", "users", row["user_id"], f"{row['username']} signed in")
                st.rerun()
            else:
                log_action("LOGIN_FAILED", "users", None, f"Failed: {username}")
                st.error("Invalid username or password.")


# ============================================================
# SESSION GUARD
# ============================================================
if "user" not in st.session_state or not st.session_state.user:
    login_screen()
    st.stop()

if "user_id" not in st.session_state.user:
    _u = query(
        "SELECT user_id, username, role, full_name FROM users WHERE username = %s AND active = TRUE;",
        (st.session_state.user.get("username", ""),), fetch="one",
    )
    if _u:
        st.session_state.user = {
            "user_id": _u["user_id"],
            "username": _u["username"],
            "role": _u["role"],
            "name": _u["full_name"],
        }
    else:
        st.session_state.user = None
        st.warning("Session expired. Please sign in again.")
        st.stop()


# ============================================================
# SESSION STATE
# ============================================================
def init_state():
    defaults = {
        "cart": [],
        "last_receipt": None,
        "page": "📊 Dashboard",
        "confirm_undo": None,
        "preview_sale": None,
        "scan_input": "",
        "refund_sale": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()
USER = st.session_state.user
IS_ADMIN = USER["role"] == "admin"
IS_MANAGER = USER["role"] in ("admin", "manager")


# ============================================================
# HELPERS
# ============================================================
def current_term_year():
    now = datetime.now()
    m = now.month
    if 1 <= m <= 4:
        term = "Term 1"
    elif 5 <= m <= 8:
        term = "Term 2"
    else:
        term = "Term 3"
    return term, now.year


def cart_total():
    return sum(item["quantity"] * item["unit_price"] for item in st.session_state.cart)


def find_customer_by_phone(phone):
    if not phone:
        return None
    digits = "".join(c for c in phone if c.isdigit())
    if not digits:
        return None
    return query(
        """SELECT * FROM customers
           WHERE REPLACE(REPLACE(REPLACE(phone, ' ', ''), '-', ''), '+', '') ILIKE %s
           LIMIT 1;""",
        (f"%{digits}%",), fetch="one",
    )


def confirm_delete(label, key, summary="This cannot be undone.", cascade_options=None):
    state_key = f"cd_{key}"
    if state_key not in st.session_state:
        st.session_state[state_key] = False

    if not st.session_state[state_key]:
        if st.button("Delete", key=f"ask_{key}"):
            st.session_state[state_key] = True
            st.rerun()
        return False

    st.error(f"Delete **{label}**?\n\n{summary}")
    cascades = []
    if cascade_options:
        st.markdown("**Also do:**")
        for i, act in enumerate(cascade_options):
            if st.checkbox(act["label"], value=True, key=f"cascade_{key}_{i}"):
                cascades.append(act)

    c1, c2, _ = st.columns([1, 1, 3])
    with c1:
        if st.button("Confirm delete", type="primary", key=f"yes_{key}",
                     use_container_width=True):
            for act in cascades:
                try:
                    execute(act["sql"], act.get("params", ()))
                except Exception as e:
                    st.warning(f"Cascade failed: {e}")
            st.session_state[state_key] = False
            return True
    with c2:
        if st.button("Cancel", key=f"no_{key}", use_container_width=True):
            st.session_state[state_key] = False
            st.rerun()
    return False


def build_receipt_html(r):
    item_rows = ""
    for it in r["items"]:
        is_paid = it.get("paid", True)
        is_issued = it.get("issued", True)
        paid_badge = "Paid" if is_paid else "NOT PAID"
        issued_badge = "Issued" if is_issued else "PENDING"
        paid_class = "rc-yes" if is_paid else "rc-no"
        issued_class = "rc-yes" if is_issued else "rc-no"

        item_rows += f"""
        <div class="rc-item">
            <div class="rc-item-line">
                <span class="rc-item-name">{it['product_name']}</span>
                <span class="rc-item-qty">{it['quantity']}×{it['unit_price']:,.0f}</span>
                <span class="rc-item-total">{it['quantity']*it['unit_price']:,.0f}</span>
            </div>
            <div class="rc-flags">
                <span class="rc-flag {paid_class}">{paid_badge}</span>
                <span class="rc-flag {issued_class}">{issued_badge}</span>
            </div>
        </div>
        """

    payments = r.get("payments") or [{"method": r.get("payment_method", "Cash"),
                                       "amount": r["total"]}]
    payment_rows = "".join(
        f'<div class="rc-meta-row"><span>{p["method"]}</span>'
        f'<span>KES {float(p["amount"]):,.0f}</span></div>'
        for p in payments
    )

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Receipt #{r['sale_id']:06d}</title>
<style>
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; font-family: 'Courier New', monospace;
                 background: #f8fafc; color: #000; }}
    .rc {{ max-width: 300px; margin: 20px auto; background: #fff;
          border: 1px solid #e2e8f0; padding: 14px 16px 18px;
          font-size: 12px; line-height: 1.4; }}
    .rc-header {{ text-align: center; padding-bottom: 8px; }}
    .rc-title {{ font-size: 15px; font-weight: bold; letter-spacing: 2px; margin: 0; }}
    .rc-school {{ font-size: 12px; font-weight: bold; margin-top: 3px; }}
    .rc-hr {{ border-top: 1px dashed #000; margin: 8px 0; }}
    .rc-meta {{ font-size: 11px; }}
    .rc-meta-row {{ display: flex; justify-content: space-between; padding: 1px 0; }}
    .rc-item {{ padding: 5px 0; border-bottom: 1px dotted #ccc; }}
    .rc-item:last-child {{ border-bottom: none; }}
    .rc-item-line {{ display: flex; justify-content: space-between; align-items: baseline; }}
    .rc-item-name {{ flex: 1; font-weight: bold; }}
    .rc-item-qty {{ color: #555; font-size: 10px; margin: 0 4px; white-space: nowrap; }}
    .rc-item-total {{ font-weight: bold; white-space: nowrap; }}
    .rc-flags {{ margin-top: 3px; }}
    .rc-flag {{ display: inline-block; font-size: 9px; font-weight: bold;
               padding: 1px 6px; border-radius: 8px; margin-right: 4px; }}
    .rc-yes {{ background: #dcfce7; color: #166534; }}
    .rc-no  {{ background: #fee2e2; color: #991b1b; }}
    .rc-total {{ display: flex; justify-content: space-between; font-size: 14px;
                font-weight: bold; margin: 6px 0 2px; }}
    .rc-footer {{ text-align: center; margin-top: 10px; font-size: 12px; font-weight: bold; }}
    .rc-void {{ background: #dc2626; color: #fff; text-align: center;
               padding: 4px; font-weight: bold; letter-spacing: 2px; margin-bottom: 8px; }}
    .rc-print {{ display: block; width: 100%; margin-top: 14px; padding: 9px;
                background: #1e293b; color: #fff; border: none; border-radius: 6px;
                font-size: 13px; font-weight: bold; cursor: pointer; }}
    .rc-print:hover {{ background: #0f172a; }}
    @media print {{
        body {{ background: #fff; margin: 0; }}
        .rc {{ max-width: 100%; border: none; margin: 0; padding: 0; }}
        .rc-print {{ display: none !important; }}
        @page {{ margin: 4mm; }}
    }}
</style></head><body>
<div class="rc">
    {'<div class="rc-void">*** VOIDED ***</div>' if r.get('voided') else ''}
    <div class="rc-header">
        <div class="rc-title">UNIFORM SALES</div>
        <div class="rc-school">{r['school']}</div>
    </div>
    <div class="rc-hr"></div>
    <div class="rc-meta">
        <div class="rc-meta-row"><span>Receipt</span><span>#{r['sale_id']:06d}</span></div>
        <div class="rc-meta-row"><span>Date</span><span>{r['date'].strftime('%d %b %Y %H:%M')}</span></div>
        <div class="rc-meta-row"><span>Customer</span><span>{r['customer']}</span></div>
        {f'<div class="rc-meta-row"><span>Phone</span><span>{r["phone"]}</span></div>' if r.get("phone") else ''}
    </div>
    <div class="rc-hr"></div>
    <div class="rc-items">{item_rows}</div>
    <div class="rc-hr"></div>
    <div class="rc-total"><span>TOTAL</span><span>KES {r['total']:,.0f}</span></div>
    <div class="rc-meta">{payment_rows}</div>
    <div class="rc-hr"></div>
    <div class="rc-footer">Thank You, Customer!</div>
    <button class="rc-print" onclick="window.print();">Print</button>
</div>
<script>window.focus();</script>
</body></html>"""


# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown(f"""
    <div style="padding: 6px 4px 2px;">
        <div style="font-size: 18px; font-weight: 700; color: #f1f5f9;
                    letter-spacing: -0.3px;">
            Uniform Sales
        </div>
        <div style="font-size: 11px; color: #94a3b8; margin-top: 2px;
                    text-transform: uppercase; letter-spacing: 1px;">
            Point of Sale
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    nav_groups = {
        "Overview": [("📊 Dashboard", "📊 Dashboard")],
        "Sales": [
            ("🛒 Point of Sale", "🛒 Point of Sale"),
            ("📋 Pending Pickup", "📋 Pending Pickup"),
            ("🧑 Customers", "🧑 Customers"),
        ],
        "Inventory": [
            ("📦 Stock", "📦 Stock Management"),
            ("👕 Products", "👕 Products & Prices"),
            ("🏫 Schools", "🏫 Schools"),
        ],
        "Operations": [("✂️ Tailor Production", "✂️ Tailor Production")],
        "Finance": [
            ("💰 Financials", "💰 Financials"),
            ("📈 Reports", "📊 Reports"),
            ("📅 Close Day", "📅 Close Day"),
        ],
        "System": [],
    }

    if IS_ADMIN:
        nav_groups["System"] = [
            ("📜 Audit Log", "📜 Audit Log"),
            ("👥 Users", "👥 Users"),
        ]

    nav_groups = {k: v for k, v in nav_groups.items() if v}

    available_pages = []
    for group_name, items in nav_groups.items():
        for label, page_key in items:
            available_pages.append((group_name, label, page_key))

    valid_page_keys = [p[2] for p in available_pages]
    if st.session_state.page not in valid_page_keys:
        st.session_state.page = "📊 Dashboard"

    for group_name, items in nav_groups.items():
        st.markdown(
            f'<div style="font-size: 10px; font-weight: 600; color: #64748b;'
            f'text-transform: uppercase; letter-spacing: 1.2px;'
            f'padding: 8px 4px 4px;">{group_name}</div>',
            unsafe_allow_html=True,
        )
        for label, page_key in items:
            if st.button(label, key=f"nav_{page_key}", use_container_width=True):
                st.session_state.page = page_key
                st.rerun()

    st.markdown("---")

    st.markdown(f"""
    <div style="padding: 4px;">
        <div style="font-size: 13px; font-weight: 600; color: #f1f5f9;">
            {USER['name']}
        </div>
        <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase;
                    letter-spacing: 0.8px;">
            {USER['role']}
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("Sign Out", key="signout_btn", use_container_width=True):
        log_action("LOGOUT", "users", None, f"{USER['username']} signed out")
        st.session_state.user = None
        st.session_state.cart = []
        st.session_state.last_receipt = None
        st.session_state.preview_sale = None
        st.rerun()


# ============================================================
# PAGE: DASHBOARD
# ============================================================
def page_dashboard():
    term, year = current_term_year()
    today_str = datetime.now().strftime("%A, %d %B %Y")

    st.markdown(f"""
    <div style="display: flex; justify-content: space-between; align-items: baseline;
                margin-bottom: 24px;">
        <div>
            <h1 style="margin: 0;">Dashboard</h1>
            <p style="margin: 4px 0 0; color: #64748b; font-size: 14px;">
                {today_str}
            </p>
        </div>
        <div style="text-align: right;">
            <div style="font-size: 13px; color: #64748b;">{term} · {year}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    today_sales = query(
        """SELECT COALESCE(SUM(total_amount),0) AS total, COUNT(*) AS num
           FROM sales WHERE sale_date::date = %s AND voided = FALSE;""",
        (today,), fetch="one",
    )
    today_total = float(today_sales["total"] if today_sales else 0)
    today_count = int(today_sales["num"] if today_sales else 0)

    yest_sales = query(
        """SELECT COALESCE(SUM(total_amount),0) AS total
           FROM sales WHERE sale_date::date = %s AND voided = FALSE;""",
        (yesterday,), fetch="one",
    )
    yest_total = float(yest_sales["total"] if yest_sales else 0)

    if yest_total > 0:
        pct_change = ((today_total - yest_total) / yest_total) * 100
        change_class = "pos" if pct_change >= 0 else "neg"
        change_text = f"{pct_change:+.1f}% vs yesterday"
    else:
        change_class = ""
        change_text = "No comparison data"

    pending_pickups = query(
        "SELECT COUNT(*) AS c FROM sale_items WHERE paid = TRUE AND issued = FALSE;",
        fetch="one",
    )
    pending_count = int(pending_pickups["c"] if pending_pickups else 0)

    pending_sales_qty = query(
        "SELECT COUNT(DISTINCT sale_id) AS c FROM sale_items WHERE paid = TRUE AND issued = FALSE;",
        fetch="one",
    )
    pending_sales_count = int(pending_sales_qty["c"] if pending_sales_qty else 0)

    cash_today = query(
        """SELECT COALESCE(SUM(sp.amount),0) AS t
           FROM sale_payments sp
           JOIN sales s ON s.sale_id = sp.sale_id
           WHERE s.sale_date::date = %s AND s.voided = FALSE
             AND sp.method = 'Cash';""",
        (today,), fetch="one",
    )
    cash_in = float(cash_today["t"] if cash_today else 0)

    refunds_today = query(
        "SELECT COALESCE(SUM(amount),0) AS t FROM refunds WHERE refund_date::date = %s;",
        (today,), fetch="one",
    )
    refunds_sum = float(refunds_today["t"] if refunds_today else 0)

    expected_cash = cash_in - refunds_sum

    closed_today = query(
        "SELECT closing_id FROM daily_closings WHERE closing_date = %s;",
        (today,), fetch="one",
    )

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Today's Sales</div>
            <div class="kpi-value">KES {today_total:,.0f}</div>
            <div class="kpi-sub {change_class}">{change_text}</div>
        </div>
        """, unsafe_allow_html=True)
    with k2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Transactions</div>
            <div class="kpi-value">{today_count}</div>
            <div class="kpi-sub">sales recorded today</div>
        </div>
        """, unsafe_allow_html=True)
    with k3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Pending Pickup</div>
            <div class="kpi-value">{pending_count}</div>
            <div class="kpi-sub">items · {pending_sales_count} sales</div>
        </div>
        """, unsafe_allow_html=True)
    with k4:
        close_status = "Closed" if closed_today else "Not closed"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Expected Cash</div>
            <div class="kpi-value">KES {expected_cash:,.0f}</div>
            <div class="kpi-sub">{close_status}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    col_trend, col_alerts = st.columns([2, 1])

    with col_trend:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Sales — Last 7 Days</div>',
                    unsafe_allow_html=True)

        trend = query(
            """SELECT sale_date::date AS day, COALESCE(SUM(total_amount),0) AS total
               FROM sales
               WHERE sale_date::date >= %s AND voided = FALSE
               GROUP BY day ORDER BY day;""",
            (today - timedelta(days=6),),
        )

        trend_map = {r["day"]: float(r["total"]) for r in trend}
        days = [today - timedelta(days=i) for i in range(6, -1, -1)]
        chart_data = pd.DataFrame({
            "Day": [d.strftime("%a") for d in days],
            "Sales": [trend_map.get(d, 0) for d in days],
        })

        if any(chart_data["Sales"] > 0):
            st.bar_chart(chart_data.set_index("Day"), height=220, color="#3b82f6")
        else:
            st.info("No sales in the last 7 days.")

        if trend:
            totals = [float(r["total"]) for r in trend]
            avg = sum(totals) / len(totals) if totals else 0
            hi = max(totals) if totals else 0
            lo = min(totals) if totals else 0
            st.caption(f"Average: KES {avg:,.0f} · Highest: KES {hi:,.0f} · Lowest: KES {lo:,.0f}")

        st.markdown('</div>', unsafe_allow_html=True)

    with col_alerts:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Alerts</div>', unsafe_allow_html=True)

        alerts_found = False

        low_stock = query(
            """SELECT p.product_name, s.school_name,
                      COALESCE((SELECT SUM(st.quantity_brought) FROM stock st
                                WHERE st.school_id = s.school_id AND st.product_id = p.product_id),0)
                      -
                      COALESCE((SELECT SUM(si.quantity) FROM sale_items si
                                JOIN sales sa ON sa.sale_id = si.sale_id
                                WHERE sa.school_id = s.school_id AND si.product_id = p.product_id
                                  AND sa.voided = FALSE),0) AS remaining
               FROM products p CROSS JOIN schools s
               WHERE p.active = TRUE
               ORDER BY remaining ASC LIMIT 5;"""
        )

        low_items = [r for r in low_stock if int(r["remaining"]) < 10]
        if low_items:
            alerts_found = True
            st.markdown(
                f'<div class="alert-item">{len(low_items)} product(s) low on stock</div>',
                unsafe_allow_html=True,
            )

        aged = query(
            """SELECT COUNT(*) AS c FROM sale_items si
               JOIN sales s ON s.sale_id = si.sale_id
               WHERE si.paid = TRUE AND si.issued = FALSE
                 AND s.sale_date < NOW() - INTERVAL '7 days';""",
            fetch="one",
        )
        aged_count = int(aged["c"] if aged else 0)
        if aged_count > 0:
            alerts_found = True
            st.markdown(
                f'<div class="alert-item danger">{aged_count} item(s) pending pickup for over 7 days</div>',
                unsafe_allow_html=True,
            )

        last_close = query(
            "SELECT variance, closing_date FROM daily_closings ORDER BY closing_date DESC LIMIT 1;",
            fetch="one",
        )
        if last_close and abs(float(last_close["variance"])) > 1:
            alerts_found = True
            v = float(last_close["variance"])
            st.markdown(
                f'<div class="alert-item danger">Cash variance on '
                f'{last_close["closing_date"].strftime("%d %b")}: '
                f'KES {v:+,.0f}</div>',
                unsafe_allow_html=True,
            )

        unpaid = query(
            "SELECT COUNT(*) AS c FROM sale_items WHERE paid = FALSE AND issued = TRUE;",
            fetch="one",
        )
        unpaid_count = int(unpaid["c"] if unpaid else 0)
        if unpaid_count > 0:
            alerts_found = True
            st.markdown(
                f'<div class="alert-item">{unpaid_count} item(s) issued but not paid</div>',
                unsafe_allow_html=True,
            )

        if not alerts_found:
            st.markdown(
                '<div class="alert-item ok">All clear — no issues</div>',
                unsafe_allow_html=True,
            )

        st.markdown('</div>', unsafe_allow_html=True)

    col_top, col_pay = st.columns([1, 1])

    with col_top:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Top Products — Last 7 Days</div>',
                    unsafe_allow_html=True)

        top_products = query(
            """SELECT p.product_name, SUM(si.quantity) AS qty, SUM(si.line_total) AS revenue
               FROM sale_items si
               JOIN products p ON p.product_id = si.product_id
               JOIN sales s ON s.sale_id = si.sale_id
               WHERE s.sale_date::date >= %s AND s.voided = FALSE
               GROUP BY p.product_name ORDER BY qty DESC LIMIT 5;""",
            (today - timedelta(days=6),),
        )
        if top_products:
            for i, p in enumerate(top_products, 1):
                st.markdown(
                    f"""<div style="display: flex; justify-content: space-between;
                                    padding: 8px 0; border-bottom: 1px solid #f1f5f9;">
                        <div><strong>{i}.</strong> {p['product_name']}</div>
                        <div style="color: #64748b; font-size: 13px;">
                            ×{int(p['qty'])} · KES {float(p['revenue']):,.0f}
                        </div>
                    </div>""",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No sales in the last 7 days.")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_pay:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Today by Payment Method</div>',
                    unsafe_allow_html=True)

        pay_mix = query(
            """SELECT sp.method, SUM(sp.amount) AS total
               FROM sale_payments sp
               JOIN sales s ON s.sale_id = sp.sale_id
               WHERE s.sale_date::date = %s AND s.voided = FALSE
               GROUP BY sp.method ORDER BY total DESC;""",
            (today,),
        )
        if pay_mix:
            total_all = sum(float(p["total"]) for p in pay_mix)
            for p in pay_mix:
                pct = (float(p["total"]) / total_all * 100) if total_all else 0
                st.markdown(
                    f"""<div style="padding: 8px 0;">
                        <div style="display: flex; justify-content: space-between;
                                    margin-bottom: 4px;">
                            <span>{p['method']}</span>
                            <span style="color: #64748b; font-size: 13px;">
                                KES {float(p['total']):,.0f} · {pct:.0f}%
                            </span>
                        </div>
                        <div style="background: #f1f5f9; height: 6px; border-radius: 3px;
                                    overflow: hidden;">
                            <div style="background: #3b82f6; height: 100%; width: {pct}%;"></div>
                        </div>
                    </div>""",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No payments today yet.")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Quick Actions</div>', unsafe_allow_html=True)

    qa = st.columns(5)
    with qa[0]:
        if st.button("New Sale", use_container_width=True, key="qa_pos"):
            st.session_state.page = "🛒 Point of Sale"
            st.rerun()
    with qa[1]:
        if st.button("Pending Pickup", use_container_width=True, key="qa_pickup"):
            st.session_state.page = "📋 Pending Pickup"
            st.rerun()
    with qa[2]:
        if st.button("Add Stock", use_container_width=True, key="qa_stock"):
            st.session_state.page = "📦 Stock Management"
            st.rerun()
    with qa[3]:
        if st.button("Tailor Production", use_container_width=True, key="qa_tailor"):
            st.session_state.page = "✂️ Tailor Production"
            st.rerun()
    with qa[4]:
        if IS_ADMIN:
            if st.button("Close Day", use_container_width=True, key="qa_close"):
                st.session_state.page = "📅 Close Day"
                st.rerun()
        else:
            if st.button("Full Reports", use_container_width=True, key="qa_reports"):
                st.session_state.page = "📊 Reports"
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


# ============================================================
# PAGE: POINT OF SALE — OPTIMIZED
# ============================================================
def page_pos():
    st.markdown("# Point of Sale")
    st.caption("Add items, review the sale, confirm.")

    schools = get_schools()
    products = get_products()
    categories = get_categories()

    if not schools or not products:
        st.warning("Schools or products missing. Please set them up first.")
        return

    # Pre-fetch price overrides for the default school (cached)
    default_school_id = schools[0]["school_id"]
    default_school_name = schools[0]["school_name"]
    price_overrides = get_school_prices_map(default_school_id)

    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.markdown("### Quick Add")

        scan_cols = st.columns([3, 1])
        with scan_cols[0]:
            scan = st.text_input(
                "Scan barcode or type SKU",
                key="scan_field",
                placeholder="Scan or type SKU and press Enter",
            )
        with scan_cols[1]:
            st.write("")
            st.write("")
            do_scan = st.button("Add", key="scan_add_btn", use_container_width=True)

        if scan and (do_scan or scan != st.session_state.get("scan_input", "")):
            st.session_state.scan_input = scan
            matched = query(
                "SELECT * FROM products WHERE sku ILIKE %s AND active = TRUE LIMIT 1;",
                (scan.strip(),), fetch="one",
            )
            if matched:
                price = price_overrides.get(int(matched["product_id"]),
                                            float(matched["price"]))
                found = False
                for item in st.session_state.cart:
                    if (item["product_id"] == matched["product_id"]
                            and item["unit_price"] == float(price)
                            and item.get("issued") and item.get("paid")):
                        item["quantity"] += 1
                        found = True
                        break
                if not found:
                    st.session_state.cart.append({
                        "school_id": default_school_id,
                        "school_name": default_school_name,
                        "product_id": matched["product_id"],
                        "product_name": matched["product_name"],
                        "quantity": 1,
                        "unit_price": float(price),
                        "issued": True,
                        "paid": True,
                    })
                st.success(f"Added {matched['product_name']}")
                st.session_state.scan_input = ""
                st.rerun()
            else:
                st.warning(f"No product with SKU '{scan}'")

        top_sellers = query(
            """SELECT p.product_id, p.product_name, p.price,
                      SUM(si.quantity) AS sold_qty
               FROM sale_items si
               JOIN products p ON p.product_id = si.product_id
               JOIN sales s ON s.sale_id = si.sale_id
               WHERE s.voided = FALSE
               GROUP BY p.product_id, p.product_name, p.price
               ORDER BY sold_qty DESC LIMIT 8;"""
        )
        if top_sellers:
            st.caption("Top sellers")
            quick_cols = st.columns(4)
            for i, prod in enumerate(top_sellers):
                with quick_cols[i % 4]:
                    if st.button(
                        f"+ {prod['product_name']}",
                        key=f"quick_{prod['product_id']}",
                        use_container_width=True,
                    ):
                        price = price_overrides.get(int(prod["product_id"]),
                                                    float(prod["price"]))
                        found = False
                        for item in st.session_state.cart:
                            if (item["product_id"] == prod["product_id"]
                                    and item["unit_price"] == float(price)
                                    and item.get("issued") and item.get("paid")):
                                item["quantity"] += 1
                                found = True
                                break
                        if not found:
                            st.session_state.cart.append({
                                "school_id": default_school_id,
                                "school_name": default_school_name,
                                "product_id": prod["product_id"],
                                "product_name": prod["product_name"],
                                "quantity": 1,
                                "unit_price": float(price),
                                "issued": True,
                                "paid": True,
                            })
                        st.rerun()

        st.markdown("---")
        st.markdown("### Add Items")

        fcol1, fcol2 = st.columns(2)
        with fcol1:
            cat_options = {c["category_name"]: c["category_id"] for c in categories}
            selected_cat = st.selectbox(
                "Category", ["All"] + list(cat_options.keys()), key="pos_cat_select"
            )
        with fcol2:
            st.write("")

        if selected_cat != "All":
            filtered_products = get_products(category_id=cat_options[selected_cat])
        else:
            filtered_products = products

        if not filtered_products:
            st.warning("No products in this category.")
            return

        school_map = {s["school_name"]: s["school_id"] for s in schools}
        selected_school_name = st.selectbox(
            "School", list(school_map.keys()), key="pos_school_select"
        )
        school_id = school_map[selected_school_name]

        product_map = {p["product_name"]: p for p in filtered_products}
        selected_product_name = st.selectbox(
            "Product", list(product_map.keys()), key="pos_product_select"
        )
        product = product_map[selected_product_name]

        # BULK STOCK QUERY (one call, cached) — replaces old per-product lookups
        stock_map = get_all_stock_for_school(school_id)
        stock_avail = stock_map.get(int(product["product_id"]), 0)

        effective_price = price_overrides.get(int(product["product_id"]),
                                              float(product["price"]))
        if school_id != default_school_id:
            # If user picked a different school, use that school's overrides
            school_overrides = get_school_prices_map(school_id)
            effective_price = school_overrides.get(int(product["product_id"]),
                                                   float(product["price"]))

        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            qty = st.number_input("Quantity", min_value=1, value=1, step=1, key="pos_qty")
        with c2:
            unit_price = st.number_input(
                "Unit Price (KES)", min_value=0.0,
                value=float(effective_price), step=10.0, key="pos_unit_price",
            )
        with c3:
            st.metric("Stock Available", stock_avail)

        c_paid, c_issue = st.columns(2)
        with c_paid:
            paid_now = st.checkbox("Paid now", value=True, key="pos_paid_now")
        with c_issue:
            issued_now = st.checkbox("Issued now", value=True, key="pos_issued_now")

        if st.button("Add to Cart", use_container_width=True, key="pos_add_cart",
                     type="primary"):
            if qty > stock_avail:
                st.warning(f"Only {stock_avail} in stock.")
            else:
                found = False
                for item in st.session_state.cart:
                    if (item["school_id"] == school_id
                            and item["product_id"] == product["product_id"]
                            and item["unit_price"] == unit_price
                            and item.get("issued", True) == issued_now
                            and item.get("paid", True) == paid_now):
                        item["quantity"] += qty
                        found = True
                        break
                if not found:
                    st.session_state.cart.append({
                        "school_id": school_id,
                        "school_name": selected_school_name,
                        "product_id": product["product_id"],
                        "product_name": product["product_name"],
                        "quantity": qty,
                        "unit_price": unit_price,
                        "issued": issued_now,
                        "paid": paid_now,
                    })
                st.success(f"Added {qty} × {selected_product_name}")
                st.rerun()

        st.markdown("---")
        st.markdown("### Current Cart")

        if not st.session_state.cart:
            st.info("Cart is empty.")
        else:
            for i, item in enumerate(st.session_state.cart):
                cols = st.columns([4, 1, 1, 1, 1, 1])
                paid_mark = "Paid" if item.get("paid", True) else "Unpaid"
                issued_mark = "Issued" if item.get("issued", True) else "Pending"
                cols[0].write(f"**{item['product_name']}**  \n{item['school_name']}")
                cols[1].write(f"×{item['quantity']}")
                cols[2].write(f"KES {item['unit_price']:,.0f}")
                cols[3].write(f"**KES {item['quantity']*item['unit_price']:,.0f}**")
                cols[4].caption(f"{paid_mark} · {issued_mark}")
                if cols[5].button("Del", key=f"cart_del_{i}"):
                    st.session_state.cart.pop(i)
                    st.rerun()

            bcol1, bcol2 = st.columns(2)
            with bcol1:
                if st.button("Clear Cart", use_container_width=True, key="cart_clear"):
                    st.session_state.cart = []
                    st.rerun()
            with bcol2:
                if st.button("Hold Sale", use_container_width=True, key="cart_hold"):
                    label = f"Hold {datetime.now().strftime('%H:%M')}"
                    execute(
                        """INSERT INTO held_sales (label, cart_json, held_by)
                           VALUES (%s, %s, %s);""",
                        (label, json.dumps(st.session_state.cart), USER["username"]),
                    )
                    st.session_state.cart = []
                    st.success("Sale held. Retrieve it from below.")
                    st.rerun()

        held = query("SELECT * FROM held_sales ORDER BY held_at DESC LIMIT 10;")
        if held:
            with st.expander(f"Held Sales ({len(held)})"):
                for h in held:
                    hc = st.columns([3, 1, 1])
                    hc[0].write(f"**{h['label']}** — {h['held_at'].strftime('%H:%M')}")
                    if hc[1].button("Retrieve", key=f"ret_{h['held_id']}"):
                        st.session_state.cart = json.loads(h["cart_json"])
                        execute("DELETE FROM held_sales WHERE held_id = %s;", (h["held_id"],))
                        st.rerun()
                    if hc[2].button("Del", key=f"delh_{h['held_id']}"):
                        execute("DELETE FROM held_sales WHERE held_id = %s;", (h["held_id"],))
                        st.rerun()

    with col_right:
        st.markdown("### Checkout")
        total = cart_total()
        st.metric("Total", f"KES {total:,.0f}")

        customer_phone = st.text_input("Phone (for lookup)", value="", key="pos_phone")
        existing_customer = find_customer_by_phone(customer_phone) if customer_phone else None

        if existing_customer:
            st.success(f"Found: {existing_customer['customer_name']}")
            default_name = existing_customer["customer_name"]
        else:
            default_name = ""

        customer_name = st.text_input("Customer Name", value=default_name, key="pos_customer_name")

        st.markdown("**Payment Breakdown**")
        payment_methods = ["Cash", "M-Pesa", "Card", "Bank Transfer"]
        n_pay = st.radio(
            "Number of payment methods", [1, 2, 3], index=0, horizontal=True,
            key="pos_n_pay",
        )

        payments = []
        remaining = total
        for i in range(n_pay):
            pc = st.columns([2, 1])
            with pc[0]:
                method = st.selectbox(
                    f"Method {i+1}", payment_methods,
                    index=i if i < len(payment_methods) else 0,
                    key=f"pos_pm_{i}",
                )
            with pc[1]:
                amt = st.number_input(
                    f"Amount {i+1}", min_value=0.0,
                    value=float(remaining) if i == n_pay - 1 else 0.0,
                    step=10.0, key=f"pos_pa_{i}",
                )
            payments.append({"method": method, "amount": amt})
            remaining -= amt

        entered_total = sum(p["amount"] for p in payments)
        diff = entered_total - total

        if abs(diff) < 0.01:
            st.success(f"Balanced: KES {entered_total:,.0f}")
        elif diff > 0:
            st.warning(f"Over by KES {diff:,.0f}")
        else:
            st.warning(f"Short by KES {abs(diff):,.0f}")

        if abs(diff) < 0.01:
            payment_status = "Paid"
        elif entered_total > 0:
            payment_status = "Partial"
        else:
            payment_status = "Pending"

        term, year = current_term_year()
        term_input = st.selectbox(
            "Term", ["Term 1", "Term 2", "Term 3"],
            index=["Term 1", "Term 2", "Term 3"].index(term), key="pos_term",
        )
        year_input = st.number_input(
            "Year", value=year, min_value=2020, max_value=2100, key="pos_year"
        )

        if st.button("Review Sale", type="primary", use_container_width=True, key="pos_review"):
            if not st.session_state.cart:
                st.error("Cart is empty.")
            elif len({it["school_id"] for it in st.session_state.cart}) > 1:
                st.error("Cart has items from multiple schools.")
            else:
                st.session_state.preview_sale = {
                    "cart": list(st.session_state.cart),
                    "total": total,
                    "customer_name": customer_name,
                    "customer_phone": customer_phone,
                    "payments": [p for p in payments if p["amount"] > 0],
                    "payment_status": payment_status,
                    "term": term_input,
                    "year": int(year_input),
                    "existing_customer_id": existing_customer["customer_id"] if existing_customer else None,
                }
                st.rerun()

        if st.session_state.preview_sale:
            p = st.session_state.preview_sale
            st.markdown("---")
            st.warning("Review before saving")
            st.write(f"**Customer:** {p['customer_name'] or 'Walk-in'}")
            for it in p["cart"]:
                st.write(f"- {it['quantity']} × {it['product_name']} @ KES {it['unit_price']:,.0f}")
            st.write(f"**Total:** KES {p['total']:,.0f}")
            if p["payments"]:
                st.write("**Payments:** " + ", ".join(
                    f"{pay['method']} KES {pay['amount']:,.0f}" for pay in p["payments"]
                ))

            cc1, cc2 = st.columns(2)
            with cc1:
                if st.button("Confirm & Save", type="primary",
                             use_container_width=True, key="pos_confirm_sale"):
                    try:
                        customer_id = p.get("existing_customer_id")
                        if not customer_id and (p["customer_name"].strip() or p["customer_phone"].strip()):
                            row = execute_returning(
                                """INSERT INTO customers (customer_name, phone)
                                   VALUES (%s, %s) RETURNING customer_id;""",
                                (p["customer_name"].strip() or "Walk-in",
                                 p["customer_phone"].strip() or None),
                            )
                            customer_id = row["customer_id"]

                        sale_row = execute_returning(
                            """INSERT INTO sales
                               (school_id, customer_id, total_amount, payment_method,
                                payment_status, term, year)
                               VALUES (%s, %s, %s, %s, %s, %s, %s)
                               RETURNING sale_id, sale_date;""",
                            (p["cart"][0]["school_id"], customer_id, p["total"],
                             p["payments"][0]["method"] if p["payments"] else "Cash",
                             p["payment_status"], p["term"], p["year"]),
                        )
                        sale_id = sale_row["sale_id"]

                        for item in p["cart"]:
                            execute(
                                """INSERT INTO sale_items
                                   (sale_id, product_id, quantity, unit_price,
                                    line_total, issued, paid)
                                   VALUES (%s, %s, %s, %s, %s, %s, %s);""",
                                (sale_id, item["product_id"], item["quantity"],
                                 item["unit_price"], item["quantity"] * item["unit_price"],
                                 item.get("issued", True), item.get("paid", True)),
                            )

                        for pay in p["payments"]:
                            execute(
                                "INSERT INTO sale_payments (sale_id, method, amount) VALUES (%s, %s, %s);",
                                (sale_id, pay["method"], pay["amount"]),
                            )

                        log_action("SALE", "sales", sale_id,
                                   f"{len(p['cart'])} items, KES {p['total']:,.0f}")

                        st.session_state.last_receipt = {
                            "sale_id": sale_id,
                            "date": sale_row["sale_date"],
                            "school": p["cart"][0]["school_name"],
                            "customer": p["customer_name"] or "Walk-in",
                            "phone": p["customer_phone"],
                            "items": list(p["cart"]),
                            "total": p["total"],
                            "payment_method": p["payments"][0]["method"] if p["payments"] else "Cash",
                            "payment_status": p["payment_status"],
                            "payments": p["payments"],
                            "term": p["term"],
                            "year": p["year"],
                        }
                        st.session_state.cart = []
                        st.session_state.preview_sale = None
                        invalidate_stock_cache()
                        st.success(f"Sale #{sale_id} saved!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Sale failed: {e}")
            with cc2:
                if st.button("Cancel", use_container_width=True, key="pos_cancel_sale"):
                    st.session_state.preview_sale = None
                    st.rerun()

        if st.session_state.last_receipt:
            r = st.session_state.last_receipt
            st.markdown("---")
            st.markdown("### Last Receipt")

            receipt_html = build_receipt_html(r)
            components.html(receipt_html, height=580, scrolling=True)

            col_a, col_b, col_c = st.columns([1, 1, 2])
            with col_a:
                components.html(
                    f"""<button onclick="
                        var w = window.open('', '_blank', 'width=380,height=720');
                        w.document.write({receipt_html!r});
                        w.document.close(); w.focus();
                        setTimeout(function(){{ w.print(); }}, 400);
                    " style="background:#1e293b;color:#fff;border:none;
                    padding:10px 16px;border-radius:6px;font-weight:600;
                    cursor:pointer;width:100%;font-size:13px;">Print</button>""",
                    height=50,
                )
            with col_b:
                st.download_button(
                    "HTML", data=receipt_html,
                    file_name=f"receipt_{r['sale_id']:06d}.html",
                    mime="text/html", use_container_width=True,
                    key="pos_receipt_dl",
                )
            with col_c:
                if st.button("Undo This Sale", use_container_width=True, key="pos_undo_sale"):
                    st.session_state["confirm_undo"] = r["sale_id"]

            if st.session_state.get("confirm_undo") == r["sale_id"]:
                st.error(f"Delete Sale #{r['sale_id']} (KES {r['total']:,.0f})?")
                c1, c2, _ = st.columns([1, 1, 3])
                with c1:
                    if st.button("Yes, delete", type="primary",
                                 use_container_width=True, key="pos_undo_yes"):
                        execute("DELETE FROM sale_items WHERE sale_id = %s;", (r["sale_id"],))
                        execute("DELETE FROM sales WHERE sale_id = %s;", (r["sale_id"],))
                        log_action("SALE_UNDONE", "sales", r["sale_id"],
                                   f"Undo sale #{r['sale_id']}")
                        st.session_state.last_receipt = None
                        st.session_state["confirm_undo"] = None
                        invalidate_stock_cache()
                        st.success("Sale deleted. Stock restored.")
                        st.rerun()
                with c2:
                    if st.button("Cancel", use_container_width=True, key="pos_undo_no"):
                        st.session_state["confirm_undo"] = None
                        st.rerun()


# ============================================================
# PAGE: PENDING PICKUP
# ============================================================
def page_pending():
    st.markdown("# Pending Pickup")
    st.caption("Items paid for but not yet collected.")

    col1, col2 = st.columns([3, 1])
    with col1:
        search = st.text_input(
            "Search by receipt #, phone, or name",
            placeholder="e.g. 000042 or 0722123456 or Mary",
            key="pending_search",
        ).strip().lower()
    with col2:
        st.write(""); st.write("")
        show_completed = st.checkbox("Show delivered today", value=False,
                                     key="pending_show_completed")

    pending_count = query(
        "SELECT COUNT(*) AS c FROM sale_items WHERE paid = TRUE AND issued = FALSE;",
        fetch="one",
    )
    total_pending = int(pending_count["c"] or 0) if pending_count else 0

    credit_count = query(
        "SELECT COUNT(*) AS c FROM sale_items WHERE paid = FALSE AND issued = TRUE;",
        fetch="one",
    )
    total_credit = int(credit_count["c"] or 0) if credit_count else 0

    today_delivered = query(
        """SELECT COUNT(*) AS c FROM audit_log
           WHERE action = 'ITEM_ISSUED' AND log_time::date = CURRENT_DATE;""",
        fetch="one",
    )
    delivered_today = int(today_delivered["c"] or 0) if today_delivered else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Awaiting Pickup", total_pending)
    m2.metric("Unpaid (credit)", total_credit)
    m3.metric("Delivered Today", delivered_today)
    m4.metric("Today", datetime.now().strftime("%d %b"))

    st.markdown("---")

    sale_filter = ""
    params = []
    if search:
        sale_filter = """
            AND (CAST(s.sale_id AS TEXT) ILIKE %s
                 OR COALESCE(c.customer_name, '') ILIKE %s
                 OR COALESCE(c.phone, '') ILIKE %s)
        """
        like = f"%{search}%"
        params = [like, like, like]

    sales_rows = query(
        f"""
        SELECT DISTINCT s.sale_id, s.sale_date, s.term, s.year,
               sch.school_name,
               COALESCE(c.customer_name, 'Walk-in') AS customer_name,
               c.phone
        FROM sales s
        JOIN schools sch ON sch.school_id = s.school_id
        LEFT JOIN customers c ON c.customer_id = s.customer_id
        JOIN sale_items si ON si.sale_id = s.sale_id
        WHERE si.paid = TRUE AND si.issued = FALSE AND s.voided = FALSE
        {sale_filter}
        ORDER BY s.sale_date DESC LIMIT 50;
        """,
        tuple(params),
    )

    if not sales_rows:
        st.success("No pending pickups.")
    else:
        st.subheader(f"{len(sales_rows)} sale(s) awaiting pickup")

        for sale in sales_rows:
            sid = sale["sale_id"]
            with st.container():
                head = st.columns([2, 2, 2, 2, 1])
                head[0].markdown(f"### Sale #{sid:06d}")
                head[1].markdown(f"**{sale['sale_date'].strftime('%d %b %Y')}**  \n"
                                 f"<span style='color:#888;font-size:12px;'>"
                                 f"{sale['sale_date'].strftime('%H:%M')}</span>",
                                 unsafe_allow_html=True)
                head[2].markdown(f"**{sale['customer_name']}**  \n"
                                 f"<span style='color:#888;font-size:12px;'>"
                                 f"{sale['phone'] or 'no phone'}</span>",
                                 unsafe_allow_html=True)
                head[3].markdown(f"**{sale['school_name']}**")

                items = query(
                    """SELECT si.sale_item_id, si.quantity, si.unit_price, p.product_name
                       FROM sale_items si
                       JOIN products p ON p.product_id = si.product_id
                       WHERE si.sale_id = %s AND si.paid = TRUE AND si.issued = FALSE
                       ORDER BY p.product_name;""",
                    (sid,),
                )

                with head[4]:
                    if st.button("Deliver All", key=f"deliver_all_{sid}",
                                 use_container_width=True, type="primary"):
                        for item in items:
                            execute("UPDATE sale_items SET issued = TRUE WHERE sale_item_id = %s;",
                                    (item["sale_item_id"],))
                            log_action("ITEM_ISSUED", "sale_items", item["sale_item_id"],
                                       f"Issued {item['quantity']} × {item['product_name']} (sale #{sid})")
                        st.success("All delivered.")
                        st.rerun()

                for item in items:
                    ic = st.columns([4, 1, 1, 1])
                    ic[0].write(f"**{item['product_name']}**")
                    ic[1].write(f"Qty: **{item['quantity']}**")
                    ic[2].write(f"KES {float(item['unit_price']):,.0f}")
                    with ic[3]:
                        ticked = st.checkbox("Hand over", key=f"tick_{item['sale_item_id']}")
                        if ticked:
                            execute("UPDATE sale_items SET issued = TRUE WHERE sale_item_id = %s;",
                                    (item["sale_item_id"],))
                            log_action("ITEM_ISSUED", "sale_items", item["sale_item_id"],
                                       f"Issued {item['quantity']} × {item['product_name']}")
                            st.rerun()

                st.markdown("<hr style='margin:10px 0;border:none;border-top:1px solid #e2e8f0;'>",
                            unsafe_allow_html=True)

    if show_completed:
        st.markdown("---")
        st.markdown("### Delivered Today")
        delivered = query(
            """SELECT log_time, details, user_name FROM audit_log
               WHERE action = 'ITEM_ISSUED' AND log_time::date = CURRENT_DATE
               ORDER BY log_time DESC LIMIT 100;"""
        )
        if delivered:
            st.dataframe(pd.DataFrame(delivered), use_container_width=True, hide_index=True)


# ============================================================
# PAGE: STOCK
# ============================================================
def page_stock():
    st.markdown("# Stock")
    st.caption("Add, adjust, and view stock per school.")

    schools = get_schools()
    products = get_products()
    if not schools or not products:
        st.warning("Set up schools and products first.")
        return

    tab1, tab2, tab3 = st.tabs(["Add Stock", "Adjust Stock", "View / Delete"])

    with tab1:
        school_map = {s["school_name"]: s["school_id"] for s in schools}
        school_name = st.selectbox("School", list(school_map.keys()), key="stk_school")
        school_id = school_map[school_name]

        product_map = {p["product_name"]: p for p in products}
        product_name = st.selectbox("Product", list(product_map.keys()), key="stk_product")
        product = product_map[product_name]

        c1, c2, c3 = st.columns(3)
        qty = c1.number_input("Quantity Brought", min_value=1, value=1, step=1, key="stk_qty")
        unit_cost = c2.number_input("Unit Cost", min_value=0.0,
                                    value=float(product["cost_price"] or 0), step=10.0,
                                    key="stk_unit_cost")
        term, year = current_term_year()
        term_in = c3.selectbox("Term", ["Term 1", "Term 2", "Term 3"],
                               index=["Term 1", "Term 2", "Term 3"].index(term),
                               key="stk_term")

        if st.button("Add Stock", use_container_width=True, key="stk_add_btn", type="primary"):
            execute(
                """INSERT INTO stock (school_id, product_id, quantity_brought, term, year, unit_cost)
                   VALUES (%s, %s, %s, %s, %s, %s);""",
                (school_id, product["product_id"], qty, term_in, year, unit_cost),
            )
            log_action("STOCK_ADD", "stock", None, f"{qty} × {product_name} → {school_name}")
            invalidate_stock_cache()
            st.success(f"Added {qty} × {product_name}.")
            st.rerun()

    with tab2:
        st.markdown("### Stock Adjustment")
        school_map = {s["school_name"]: s["school_id"] for s in schools}
        school_name = st.selectbox("School", list(school_map.keys()), key="adj_school")
        school_id = school_map[school_name]

        product_map = {p["product_name"]: p for p in products}
        product_name = st.selectbox("Product", list(product_map.keys()), key="adj_product")
        product = product_map[product_name]

        stock_map = get_all_stock_for_school(school_id)
        current = stock_map.get(int(product["product_id"]), 0)
        st.info(f"Current stock: **{current}**")

        c1, c2 = st.columns(2)
        reason = c1.selectbox("Reason",
                              ["Damaged", "Lost", "Stocktake correction", "Transfer out", "Other"],
                              key="adj_reason")
        adj_qty = c2.number_input("Quantity to REMOVE", min_value=1, value=1, step=1,
                                  key="adj_qty")
        notes = st.text_input("Notes (optional)", key="adj_notes")

        if st.button("Apply Adjustment", key="adj_apply", type="primary"):
            if adj_qty > current:
                st.error(f"Cannot remove more than available ({current}).")
            else:
                term_now, year_now = current_term_year()
                execute(
                    """INSERT INTO stock (school_id, product_id, quantity_brought,
                                         term, year, unit_cost, adjustment_reason, notes)
                       VALUES (%s, %s, %s, %s, %s, 0, %s, %s);""",
                    (school_id, product["product_id"], -adj_qty,
                     term_now, year_now, reason, notes or None),
                )
                log_action("STOCK_ADJUST", "stock", None,
                           f"-{adj_qty} × {product_name} ({reason})")
                invalidate_stock_cache()
                st.success(f"Removed {adj_qty} × {product_name}. Reason: {reason}")
                st.rerun()

    with tab3:
        school_map = {s["school_name"]: s["school_id"] for s in schools}
        school_name = st.selectbox("Filter School", list(school_map.keys()), key="view_stk_school")
        school_id = school_map[school_name]

        entries = query(
            """SELECT st.stock_id, st.date_added, p.product_name, st.quantity_brought,
                      st.term, st.year, st.unit_cost, st.adjustment_reason
               FROM stock st JOIN products p ON p.product_id = st.product_id
               WHERE st.school_id = %s ORDER BY st.date_added DESC LIMIT 200;""",
            (school_id,),
        )

        if entries:
            for e in entries:
                cols = st.columns([2, 2, 1, 1, 1, 1, 1])
                cols[0].write(e["date_added"].strftime("%Y-%m-%d %H:%M"))
                cols[1].write(e["product_name"])
                qty_display = f"+{e['quantity_brought']}" if e["quantity_brought"] > 0 else str(e["quantity_brought"])
                cols[2].write(f"**{qty_display}**")
                cols[3].write(e["term"] or "-")
                cols[4].write(str(e["year"] or "-"))
                cols[5].write(f"KES {float(e['unit_cost'] or 0):,.0f}")

                if IS_MANAGER:
                    with cols[6]:
                        if confirm_delete(
                            f"{e['quantity_brought']} × {e['product_name']}",
                            f"stk_{e['stock_id']}",
                        ):
                            execute("DELETE FROM stock WHERE stock_id = %s;", (e["stock_id"],))
                            log_action("DELETE_STOCK", "stock", e["stock_id"], "Deleted entry")
                            invalidate_stock_cache()
                            st.rerun()

        st.markdown("---")
        st.markdown("### Summary")
        stock_map = get_all_stock_for_school(school_id)
        summary_rows = []
        for p in products:
            brought = query(
                "SELECT COALESCE(SUM(quantity_brought),0) AS q FROM stock WHERE school_id=%s AND product_id=%s;",
                (school_id, p["product_id"]), fetch="one",
            )
            sold = query(
                """SELECT COALESCE(SUM(si.quantity),0) AS q FROM sale_items si
                   JOIN sales s ON s.sale_id = si.sale_id
                   WHERE s.school_id=%s AND si.product_id=%s AND s.voided = FALSE;""",
                (school_id, p["product_id"]), fetch="one",
            )
            summary_rows.append({
                "Product": p["product_name"],
                "Brought": int(brought["q"] or 0),
                "Sold": int(sold["q"] or 0),
                "Remaining": stock_map.get(int(p["product_id"]), 0),
            })
        if summary_rows:
            st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)


# ============================================================
# PAGE: PRODUCTS
# ============================================================
def page_products():
    st.markdown("# Products & Prices")
    st.caption("Manage your catalog, categories, and school-specific prices.")

    tab1, tab2, tab3 = st.tabs(["Products", "Categories", "School Prices"])

    with tab1:
        products = query(
            """SELECT p.product_id, p.product_name, p.sku, p.price, p.cost_price,
                      p.category_id, p.active, c.category_name
               FROM products p
               LEFT JOIN product_categories c ON c.category_id = p.category_id
               ORDER BY p.product_name;"""
        )
        cats = get_categories()
        cat_map = {c["category_id"]: c["category_name"] for c in cats}

        if products:
            for p in products:
                pid = p["product_id"]
                status = "" if p.get("active", True) else " *(inactive)*"
                cols = st.columns([3, 1, 2, 2, 1])
                cols[0].write(f"**{p['product_name']}**{status}")
                cols[1].write(p["sku"] or "—")
                cols[2].write(f"{cat_map.get(p['category_id'], '—')}")
                cols[3].write(f"KES {float(p['price']):,.0f} · cost {float(p['cost_price']):,.0f}")
                if IS_ADMIN:
                    with cols[4]:
                        if confirm_delete(f"product '{p['product_name']}'", f"prod_{pid}"):
                            execute("UPDATE products SET active = FALSE WHERE product_id = %s;", (pid,))
                            clear_caches()
                            log_action("PRODUCT_DEACTIVATE", "products", pid, "Deactivated")
                            st.rerun()
            st.markdown("---")

        st.markdown("### Add / Update Product")
        c1, c2 = st.columns(2)
        with c1:
            prod_name = st.text_input("Product Name", key="prod_form_name")
        with c2:
            prod_sku = st.text_input("SKU / Barcode", key="prod_form_sku")

        c3, c4, c5 = st.columns(3)
        with c3:
            prod_price = st.number_input("Price (KES)", min_value=0.0, step=10.0,
                                         key="prod_form_price")
        with c4:
            prod_cost = st.number_input("Cost (KES)", min_value=0.0, step=10.0,
                                        key="prod_form_cost")
        with c5:
            cat_opts = ["—"] + [c["category_name"] for c in cats]
            prod_cat_choice = st.selectbox("Category", cat_opts, key="prod_form_category")

        prod_cat_id = None
        if prod_cat_choice != "—":
            prod_cat_id = next(
                (c["category_id"] for c in cats if c["category_name"] == prod_cat_choice), None
            )

        if st.button("Save Product", key="prod_form_save", type="primary"):
            if not prod_name.strip():
                st.error("Name required.")
            else:
                execute(
                    """INSERT INTO products
                           (product_name, sku, category_id, price, cost_price, active)
                       VALUES (%s, %s, %s, %s, %s, TRUE)
                       ON CONFLICT (product_name) DO UPDATE
                       SET sku = EXCLUDED.sku,
                           category_id = EXCLUDED.category_id,
                           price = EXCLUDED.price,
                           cost_price = EXCLUDED.cost_price,
                           active = TRUE;""",
                    (prod_name.strip(), prod_sku.strip() or None, prod_cat_id,
                     prod_price, prod_cost),
                )
                clear_caches()
                log_action("PRODUCT_SAVE", "products", None, f"{prod_name}")
                st.success(f"Saved {prod_name}.")
                st.rerun()

    with tab2:
        cats = get_categories()
        for c in cats:
            cols = st.columns([4, 1])
            cols[0].write(c["category_name"])
            if IS_ADMIN:
                with cols[1]:
                    if confirm_delete(f"category '{c['category_name']}'",
                                      f"cat_{c['category_id']}"):
                        execute("UPDATE products SET category_id = NULL WHERE category_id = %s;",
                                (c["category_id"],))
                        execute("DELETE FROM product_categories WHERE category_id = %s;",
                                (c["category_id"],))
                        clear_caches()
                        st.rerun()

        st.markdown("---")
        new_cat = st.text_input("New category name", key="new_cat_name")
        if st.button("Add Category", key="add_cat_btn", type="primary"):
            if new_cat.strip():
                execute(
                    "INSERT INTO product_categories (category_name) VALUES (%s) ON CONFLICT DO NOTHING;",
                    (new_cat.strip(),),
                )
                clear_caches()
                st.rerun()

    with tab3:
        schools = get_schools()
        products = get_products()
        if not schools or not products:
            return

        school_map = {s["school_name"]: s["school_id"] for s in schools}
        prod_map = {p["product_name"]: p["product_id"] for p in products}

        sc = st.selectbox("School", list(school_map.keys()), key="pp_school")
        pc = st.selectbox("Product", list(prod_map.keys()), key="pp_prod")
        spp_category = st.text_input("Category", value="Default", key="pp_category")
        spp_price = st.number_input("Override Price (KES)", min_value=0.0, step=10.0,
                                    key="pp_price")

        if st.button("Save Price Override", key="pp_save", type="primary"):
            execute(
                """INSERT INTO school_product_prices
                       (school_id, category_name, product_id, price)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (school_id, category_name, product_id)
                   DO UPDATE SET price = EXCLUDED.price;""",
                (school_map[sc], spp_category.strip() or "Default",
                 prod_map[pc], spp_price),
            )
            get_school_prices_map.clear()
            st.success("Price saved.")
            st.rerun()

        rows = query(
            """SELECT spp.school_product_price_id AS id, s.school_name,
                      spp.category_name, p.product_name, spp.price
               FROM school_product_prices spp
               JOIN schools s ON s.school_id = spp.school_id
               JOIN products p ON p.product_id = spp.product_id
               ORDER BY s.school_name, p.product_name;"""
        )
        if rows:
            for r in rows:
                cols = st.columns([2, 1, 2, 1, 1])
                cols[0].write(r["school_name"])
                cols[1].write(r["category_name"])
                cols[2].write(r["product_name"])
                cols[3].write(f"KES {float(r['price']):,.0f}")
                if IS_MANAGER:
                    with cols[4]:
                        if confirm_delete("override", f"ovr_{r['id']}"):
                            execute("DELETE FROM school_product_prices WHERE school_product_price_id = %s;",
                                    (r["id"],))
                            get_school_prices_map.clear()
                            st.rerun()


# ============================================================
# PAGE: SCHOOLS
# ============================================================
def page_schools():
    st.markdown("# Schools")
    st.caption("Schools you sell uniforms for.")

    schools = get_schools()
    for s in schools:
        cols = st.columns([4, 1])
        cols[0].write(f"**{s['school_name']}**")
        if IS_ADMIN:
            with cols[1]:
                if confirm_delete(f"school '{s['school_name']}'", f"sch_{s['school_id']}"):
                    execute("DELETE FROM schools WHERE school_id = %s;", (s["school_id"],))
                    clear_caches()
                    log_action("DELETE_SCHOOL", "schools", s["school_id"], "Deleted")
                    st.rerun()

    st.markdown("---")
    st.markdown("### Add School")
    name = st.text_input("School Name", key="new_school_name")
    if st.button("Save School", key="save_school_btn", type="primary"):
        if name.strip():
            execute("INSERT INTO schools (school_name) VALUES (%s) ON CONFLICT DO NOTHING;",
                    (name.strip().upper(),))
            clear_caches()
            st.rerun()


# ============================================================
# PAGE: CUSTOMERS
# ============================================================
def page_customers():
    st.markdown("# Customers")
    st.caption("Everyone who has bought uniforms from you.")

    rows = query(
        """SELECT c.customer_id, c.customer_name, c.phone,
                  (SELECT COUNT(*) FROM sales WHERE customer_id = c.customer_id AND voided = FALSE) AS purchases,
                  COALESCE((SELECT SUM(s.total_amount) FROM sales s
                            WHERE s.customer_id = c.customer_id AND s.voided = FALSE), 0) AS total_spent
           FROM customers c ORDER BY c.customer_name;"""
    )

    if not rows:
        st.info("No customers yet.")
        return

    search = st.text_input("Search by name or phone", key="cust_search").strip().lower()
    filtered = [r for r in rows
                if not search or search in f"{r['customer_name']} {r['phone'] or ''}".lower()]

    st.caption(f"Showing {len(filtered)} of {len(rows)}")

    for r in filtered:
        cols = st.columns([3, 2, 1, 2, 1])
        cols[0].write(f"**{r['customer_name']}**")
        cols[1].write(r["phone"] or "-")
        cols[2].write(f"{r['purchases']}")
        cols[3].write(f"KES {float(r['total_spent']):,.0f}")
        if IS_MANAGER:
            with cols[4]:
                if confirm_delete(f"customer '{r['customer_name']}'", f"cust_{r['customer_id']}"):
                    execute("DELETE FROM customers WHERE customer_id = %s;", (r["customer_id"],))
                    log_action("DELETE_CUSTOMER", "customers", r["customer_id"], "Deleted")
                    st.rerun()


# ============================================================
# PAGE: FINANCIALS
# ============================================================
def page_financials():
    st.markdown("# Financials")
    st.caption("Revenue, costs, investor shares.")

    rev = query("SELECT COALESCE(SUM(total_amount),0) AS t FROM sales WHERE voided = FALSE;",
                fetch="one")
    revenue = float(rev["t"] if rev else 0)

    refunds_total = query("SELECT COALESCE(SUM(amount),0) AS t FROM refunds;", fetch="one")
    refunds_sum = float(refunds_total["t"] if refunds_total else 0)

    cogs = query(
        """SELECT COALESCE(SUM(si.quantity * p.cost_price),0) AS t
           FROM sale_items si
           JOIN sales s ON s.sale_id = si.sale_id
           JOIN products p ON p.product_id = si.product_id
           WHERE s.voided = FALSE;""",
        fetch="one",
    )
    cogs_total = float(cogs["t"] if cogs else 0)

    tailor = query("SELECT COALESCE(SUM(amount_paid),0) AS t FROM tailor_production;", fetch="one")
    tailor_total = float(tailor["t"] if tailor else 0)

    net = revenue - refunds_sum - cogs_total - tailor_total

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Revenue", f"KES {revenue:,.0f}")
    c2.metric("Refunds", f"KES {refunds_sum:,.0f}")
    c3.metric("COGS", f"KES {cogs_total:,.0f}")
    c4.metric("Tailor", f"KES {tailor_total:,.0f}")
    c5.metric("Net", f"KES {net:,.0f}")

    st.markdown("---")
    st.markdown("### Investor Capital & Profit Share")
    inv = query(
        """SELECT i.investor_name, COALESCE(SUM(ft.amount),0) AS capital
           FROM investors i
           LEFT JOIN financial_transactions ft ON ft.investor_id = i.investor_id
             AND ft.transaction_type = 'Capital Contribution'
           WHERE i.active = TRUE
           GROUP BY i.investor_name ORDER BY i.investor_name;"""
    )
    if inv:
        df = pd.DataFrame(inv)
        df["capital"] = df["capital"].astype(float)
        total_cap = df["capital"].sum()
        df["share_%"] = (df["capital"] / total_cap * 100).round(2) if total_cap else 0
        df["profit_share"] = (df["share_%"] / 100 * net).round(2) if total_cap else 0
        st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### Record Transaction")
    with st.form("fin_form", clear_on_submit=True):
        ttype = st.selectbox(
            "Type",
            ["Expense", "Capital Contribution", "Withdrawal", "Other Income"],
            key="fin_type",
        )
        cat = st.text_input("Category", value="General", key="fin_cat")
        desc = st.text_input("Description", key="fin_desc")
        amt = st.number_input("Amount", min_value=0.0, step=100.0, key="fin_amt")
        term, year = current_term_year()
        if st.form_submit_button("Save"):
            execute(
                """INSERT INTO financial_transactions
                   (transaction_type, category, description, amount, term, year)
                   VALUES (%s, %s, %s, %s, %s, %s);""",
                (ttype, cat, desc, amt, term, year),
            )
            log_action("FIN_TXN", "financial_transactions", None, f"{ttype} {amt}")
            st.rerun()


# ============================================================
# PAGE: REPORTS
# ============================================================
def page_reports():
    st.markdown("# Reports")
    st.caption("Filter, analyze, and export sales.")

    tab1, tab2, tab3, tab4 = st.tabs(["Sales", "By School", "By Product", "Refunds"])

    with tab1:
        c1, c2, c3 = st.columns(3)
        start = c1.date_input("From", value=datetime.now() - timedelta(days=30), key="rep_start")
        end = c2.date_input("To", value=datetime.now(), key="rep_end")
        include_voided = c3.checkbox("Include voided", key="rep_voided")

        rows = query(
            f"""SELECT s.sale_id, s.sale_date, sch.school_name,
                       COALESCE(c.customer_name, 'Walk-in') AS customer_name,
                       s.total_amount, s.payment_method, s.payment_status,
                       s.voided, s.term, s.year
                FROM sales s
                JOIN schools sch ON sch.school_id = s.school_id
                LEFT JOIN customers c ON c.customer_id = s.customer_id
                WHERE s.sale_date::date BETWEEN %s AND %s
                {'' if include_voided else 'AND s.voided = FALSE'}
                ORDER BY s.sale_date DESC LIMIT 500;""",
            (start, end),
        )

        if not rows:
            st.info("No sales in range.")
        else:
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)

            dl1, dl2, _ = st.columns([1, 1, 3])
            try:
                buf = io.BytesIO()
                df.to_excel(buf, index=False, engine="openpyxl")
                with dl1:
                    st.download_button(
                        "Excel",
                        data=buf.getvalue(),
                        file_name=f"sales_{start}_{end}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="rep_excel_dl",
                    )
            except Exception:
                pass
            with dl2:
                st.download_button("CSV", df.to_csv(index=False), "sales.csv",
                                   key="rep_csv_dl")

            st.markdown("---")
            st.markdown("### Actions")
            rid = st.selectbox("Sale to manage", [r["sale_id"] for r in rows],
                               key="rep_manage_sale")

            act1, act2, act3 = st.columns(3)
            with act1:
                if st.button("Reprint", key=f"reprint_{rid}"):
                    sale_data = next((r for r in rows if r["sale_id"] == rid), None)
                    if sale_data:
                        items = query(
                            """SELECT si.quantity, si.unit_price, si.issued, si.paid,
                                      p.product_name
                               FROM sale_items si
                               JOIN products p ON p.product_id = si.product_id
                               WHERE si.sale_id = %s;""",
                            (rid,),
                        )
                        st.session_state.last_receipt = {
                            "sale_id": rid,
                            "date": sale_data["sale_date"],
                            "school": sale_data["school_name"],
                            "customer": sale_data["customer_name"],
                            "phone": "",
                            "items": [dict(i) for i in items],
                            "total": float(sale_data["total_amount"]),
                            "payment_method": sale_data["payment_method"],
                            "payment_status": sale_data["payment_status"],
                            "voided": sale_data["voided"],
                        }
                        st.success("Receipt loaded — go to POS to print.")

            with act2:
                if IS_MANAGER and st.button("Refund", key=f"refund_{rid}"):
                    st.session_state["refund_sale"] = rid

            with act3:
                if IS_MANAGER and st.button("Void", key=f"void_{rid}"):
                    execute(
                        """UPDATE sales SET voided = TRUE, voided_at = NOW(),
                                  voided_by = %s WHERE sale_id = %s;""",
                        (USER["username"], rid),
                    )
                    log_action("VOID_SALE", "sales", rid, f"Voided sale #{rid}")
                    invalidate_stock_cache()
                    st.success("Sale voided.")
                    st.rerun()

            if st.session_state.get("refund_sale") == rid:
                st.markdown("---")
                st.markdown(f"### Refund Sale #{rid}")
                sale_items = query(
                    """SELECT si.sale_item_id, si.quantity, si.unit_price, p.product_name
                       FROM sale_items si JOIN products p ON p.product_id = si.product_id
                       WHERE si.sale_id = %s;""",
                    (rid,),
                )
                refund_qty = {}
                for it in sale_items:
                    q = st.number_input(
                        f"{it['product_name']} (max {it['quantity']})",
                        min_value=0, max_value=int(it["quantity"]),
                        value=0, key=f"rq_{it['sale_item_id']}",
                    )
                    refund_qty[it["sale_item_id"]] = q
                reason = st.text_input("Reason", key=f"rr_{rid}")

                if st.button("Confirm Refund", type="primary",
                             key=f"refund_confirm_{rid}"):
                    total_refund = 0
                    refund_items = []
                    for it in sale_items:
                        q = refund_qty[it["sale_item_id"]]
                        if q > 0:
                            total_refund += q * float(it["unit_price"])
                            refund_items.append((it["sale_item_id"], q))

                    if not refund_items:
                        st.warning("Select at least one item.")
                    else:
                        row = execute_returning(
                            """INSERT INTO refunds (sale_id, amount, reason, refunded_by)
                               VALUES (%s, %s, %s, %s) RETURNING refund_id;""",
                            (rid, total_refund, reason or None, USER["username"]),
                        )
                        for item_id, q in refund_items:
                            execute(
                                """INSERT INTO refund_items (refund_id, sale_item_id, quantity)
                                   VALUES (%s, %s, %s);""",
                                (row["refund_id"], item_id, q),
                            )
                        log_action("REFUND", "refunds", row["refund_id"],
                                   f"Refunded KES {total_refund:,.0f} on sale #{rid}")
                        invalidate_stock_cache()
                        st.success(f"Refunded KES {total_refund:,.0f}")
                        st.session_state["refund_sale"] = None
                        st.rerun()

    with tab2:
        rows = query(
            """SELECT sch.school_name, COUNT(s.sale_id) AS num,
                      COALESCE(SUM(s.total_amount),0) AS revenue
               FROM schools sch LEFT JOIN sales s ON s.school_id = sch.school_id AND s.voided = FALSE
               GROUP BY sch.school_name ORDER BY revenue DESC;"""
        )
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with tab3:
        rows = query(
            """SELECT p.product_name, SUM(si.quantity) AS qty, SUM(si.line_total) AS revenue
               FROM sale_items si
               JOIN products p ON p.product_id = si.product_id
               JOIN sales s ON s.sale_id = si.sale_id
               WHERE s.voided = FALSE
               GROUP BY p.product_name ORDER BY revenue DESC;"""
        )
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with tab4:
        rows = query(
            """SELECT r.refund_id, r.refund_date, r.amount, r.reason, r.refunded_by,
                      s.sale_id, COALESCE(c.customer_name, 'Walk-in') AS customer
               FROM refunds r
               JOIN sales s ON s.sale_id = r.sale_id
               LEFT JOIN customers c ON c.customer_id = s.customer_id
               ORDER BY r.refund_date DESC LIMIT 200;"""
        )
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ============================================================
# PAGE: CLOSE DAY
# ============================================================
def page_close_day():
    st.markdown("# Close Day")
    st.caption("Reconcile cash at end of day.")

    close_date = st.date_input("Date to close", value=datetime.now().date(), key="close_date")

    sales_data = query(
        """SELECT COALESCE(SUM(total_amount),0) AS total, COUNT(*) AS num_sales
           FROM sales WHERE sale_date::date = %s AND voided = FALSE;""",
        (close_date,), fetch="one",
    )
    total_sales = float(sales_data["total"] if sales_data else 0)
    num_sales = int(sales_data["num_sales"] if sales_data else 0)

    payments_breakdown = query(
        """SELECT method, SUM(amount) AS total
           FROM sale_payments sp
           JOIN sales s ON s.sale_id = sp.sale_id
           WHERE s.sale_date::date = %s AND s.voided = FALSE
           GROUP BY method;""",
        (close_date,),
    )

    refunds_data = query(
        "SELECT COALESCE(SUM(amount),0) AS total FROM refunds WHERE refund_date::date = %s;",
        (close_date,), fetch="one",
    )
    total_refunds = float(refunds_data["total"] if refunds_data else 0)

    cash_in = 0
    payment_rows = []
    for p in payments_breakdown:
        method = p["method"]
        amt = float(p["total"])
        payment_rows.append({"Method": method, "Amount": amt})
        if method == "Cash":
            cash_in = amt

    expected_cash = cash_in - total_refunds

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sales", f"{num_sales}")
    c2.metric("Total", f"KES {total_sales:,.0f}")
    c3.metric("Refunds", f"KES {total_refunds:,.0f}")
    c4.metric("Expected Cash", f"KES {expected_cash:,.0f}")

    st.markdown("### Payment Breakdown")
    if payment_rows:
        st.dataframe(pd.DataFrame(payment_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No payments recorded.")

    st.markdown("---")
    st.markdown("### Cash Reconciliation")
    counted_cash = st.number_input(
        "Actual cash counted (KES)",
        min_value=0.0, value=float(expected_cash), step=10.0,
        key="close_counted_cash",
    )
    variance = counted_cash - expected_cash

    if abs(variance) < 0.01:
        st.success("Cash matches exactly.")
    elif variance > 0:
        st.warning(f"Over by KES {variance:,.0f}")
    else:
        st.error(f"Short by KES {abs(variance):,.0f}")

    notes = st.text_area("Notes", key="close_notes")

    existing = query("SELECT * FROM daily_closings WHERE closing_date = %s;",
                     (close_date,), fetch="one")
    if existing:
        st.info(f"Day already closed by **{existing['closed_by']}** at "
                f"{existing['closed_at'].strftime('%d %b %Y %H:%M')}.")

    if st.button("Close Day", type="primary", key="close_day_btn"):
        try:
            if existing:
                execute(
                    """UPDATE daily_closings
                       SET expected_cash = %s, counted_cash = %s, variance = %s,
                           total_sales = %s, total_refunds = %s, notes = %s,
                           closed_by = %s, closed_at = NOW()
                       WHERE closing_date = %s;""",
                    (expected_cash, counted_cash, variance, total_sales,
                     total_refunds, notes, USER["username"], close_date),
                )
            else:
                execute(
                    """INSERT INTO daily_closings
                       (closing_date, expected_cash, counted_cash, variance,
                        total_sales, total_refunds, notes, closed_by)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s);""",
                    (close_date, expected_cash, counted_cash, variance,
                     total_sales, total_refunds, notes, USER["username"]),
                )
            log_action("CLOSE_DAY", "daily_closings", None,
                       f"Closed {close_date} variance {variance:,.0f}")
            st.success("Day closed.")
            st.rerun()
        except Exception as e:
            st.error(f"Failed: {e}")

    st.markdown("---")
    st.markdown("### Past Closings")
    past = query(
        """SELECT closing_date, total_sales, total_refunds, expected_cash,
                  counted_cash, variance, closed_by, closed_at
           FROM daily_closings ORDER BY closing_date DESC LIMIT 30;"""
    )
    if past:
        st.dataframe(pd.DataFrame(past), use_container_width=True, hide_index=True)


# ============================================================
# PAGE: TAILOR
# ============================================================
def page_tailor():
    st.markdown("# Tailor Production")
    st.caption("Record production runs. Stock updates automatically.")

    schools = get_schools()
    products = get_products()
    if not schools or not products:
        return

    school_map = {s["school_name"]: s["school_id"] for s in schools}
    prod_map = {p["product_name"]: p["product_id"] for p in products}

    with st.expander("Record New Production", expanded=False):
        with st.form("tailor_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            school = c1.selectbox("School", list(school_map.keys()), key="tl_school")
            product = c2.selectbox("Product", list(prod_map.keys()), key="tl_product")
            c3, c4 = st.columns(2)
            tailor = c3.text_input("Tailor Name", key="tl_tailor")
            qty = c4.number_input("Qty Produced", min_value=1, value=1, step=1, key="tl_qty")
            c5, c6 = st.columns(2)
            cost = c5.number_input("Cost/Item", min_value=0.0, step=10.0, key="tl_cost")
            paid = c6.number_input("Amount Paid", min_value=0.0, step=100.0, key="tl_paid")
            notes = st.text_input("Notes", key="tl_notes")
            term, year = current_term_year()
            if st.form_submit_button("Save"):
                if tailor.strip():
                    execute(
                        """INSERT INTO tailor_production
                           (school_id, product_id, tailor_name, quantity_produced,
                            cost_per_item, amount_paid, term, year, notes)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);""",
                        (school_map[school], prod_map[product], tailor.strip(),
                         qty, cost, paid, term, year, notes or None),
                    )
                    execute(
                        """INSERT INTO stock (school_id, product_id, quantity_brought,
                                             term, year, unit_cost)
                           VALUES (%s, %s, %s, %s, %s, %s);""",
                        (school_map[school], prod_map[product], qty, term, year, cost),
                    )
                    log_action("TAILOR_PROD", "tailor_production", None, f"{qty} × {product}")
                    invalidate_stock_cache()
                    st.rerun()

    st.markdown("---")
    rows = query(
        """SELECT tp.production_id, tp.production_date, tp.school_id, tp.product_id,
                  s.school_name, p.product_name, tp.tailor_name, tp.quantity_produced,
                  tp.cost_per_item, tp.amount_paid, tp.notes
           FROM tailor_production tp
           JOIN schools s ON s.school_id = tp.school_id
           JOIN products p ON p.product_id = tp.product_id
           ORDER BY tp.production_date DESC LIMIT 100;"""
    )
    for r in rows:
        cols = st.columns([2, 2, 2, 1, 2, 2, 1])
        cols[0].write(r["production_date"].strftime("%Y-%m-%d"))
        cols[1].write(r["tailor_name"])
        cols[2].write(r["product_name"])
        cols[3].write(f"×{r['quantity_produced']}")
        cols[4].write(f"Cost: {float(r['cost_per_item']):,.0f}")
        cols[5].write(f"Paid: {float(r['amount_paid']):,.0f}")
        if IS_MANAGER:
            with cols[6]:
                if confirm_delete(f"production #{r['production_id']}",
                                  f"tal_{r['production_id']}"):
                    execute("DELETE FROM tailor_production WHERE production_id = %s;",
                            (r["production_id"],))
                    log_action("DELETE_TAILOR", "tailor_production",
                               r["production_id"], "Deleted")
                    invalidate_stock_cache()
                    st.rerun()


# ============================================================
# PAGE: AUDIT
# ============================================================
def page_audit():
    st.markdown("# Audit Log")
    st.caption("Every action recorded with user, timestamp, details.")

    rows = query(
        """SELECT log_id, log_time, user_name, action, table_name, details
           FROM audit_log ORDER BY log_time DESC LIMIT 300;"""
    )

    if not rows:
        st.info("No activity.")
        return

    c1, c2 = st.columns([2, 1])
    search = c1.text_input("Search", key="audit_search").strip().lower()
    action_filter = c2.selectbox(
        "Action",
        ["All"] + sorted({r["action"] for r in rows}),
        key="audit_action_filter",
    )

    filtered = [r for r in rows
                if (action_filter == "All" or r["action"] == action_filter)
                and (not search or search in f"{r['user_name']} {r['action']} {r['details'] or ''}".lower())]

    st.caption(f"Showing {len(filtered)} of {len(rows)}")

    for r in filtered:
        cols = st.columns([2, 2, 2, 5, 1])
        cols[0].write(r["log_time"].strftime("%Y-%m-%d %H:%M"))
        cols[1].write(f"**{r['user_name']}**")
        cols[2].write(f"`{r['action']}`")
        cols[3].write(r["details"] or "-")
        if IS_ADMIN:
            with cols[4]:
                if confirm_delete(f"log #{r['log_id']}", f"log_{r['log_id']}"):
                    execute("DELETE FROM audit_log WHERE log_id = %s;", (r["log_id"],))
                    st.rerun()

    st.download_button("CSV", pd.DataFrame(filtered).to_csv(index=False),
                       "audit.csv", key="audit_csv_dl")


# ============================================================
# PAGE: USERS
# ============================================================
def page_users():
    st.markdown("# Users")
    st.caption("Manage cashiers, managers, admins.")

    users = query("SELECT user_id, username, full_name, role, active FROM users ORDER BY username;")

    st.markdown("### Existing Users")
    for u in users:
        cols = st.columns([2, 3, 2, 1, 1])
        cols[0].write(f"**{u['username']}**")
        cols[1].write(u["full_name"])
        cols[2].write(f"`{u['role']}`")
        cols[3].write("Active" if u["active"] else "Inactive")
        with cols[4]:
            if u["username"] != USER["username"]:
                if st.button("Del", key=f"deluser_{u['user_id']}"):
                    execute("UPDATE users SET active = FALSE WHERE user_id = %s;", (u["user_id"],))
                    log_action("USER_DEACTIVATE", "users", u["user_id"], "Deactivated")
                    st.rerun()

    st.markdown("---")
    st.markdown("### Add User")
    with st.form("add_user_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        new_username = c1.text_input("Username", key="new_user_name")
        new_full_name = c2.text_input("Full Name", key="new_user_fullname")
        c3, c4 = st.columns(2)
        new_password = c3.text_input("Password", type="password", key="new_user_pw")
        new_role = c4.selectbox("Role", ["cashier", "manager", "admin"], key="new_user_role")
        create_submitted = st.form_submit_button("Create")

    if create_submitted:
        if not new_username.strip() or not new_password:
            st.error("Username and password required.")
        elif len(new_password) < 6:
            st.error("Password must be at least 6 characters.")
        else:
            existing = query("SELECT user_id FROM users WHERE username = %s;",
                             (new_username.strip().lower(),), fetch="one")
            if existing:
                st.error("Username already exists.")
            else:
                execute(
                    """INSERT INTO users (username, password_hash, full_name, role, active)
                       VALUES (%s, %s, %s, %s, TRUE);""",
                    (new_username.strip().lower(), hash_password(new_password),
                     new_full_name.strip() or new_username.strip(), new_role),
                )
                log_action("USER_CREATE", "users", None, f"Created {new_username} ({new_role})")
                st.success(f"User {new_username} created.")
                st.rerun()

    st.markdown("---")
    st.markdown("### Change My Password")
    with st.form("change_password_form", clear_on_submit=True):
        current_password = st.text_input("Current password", type="password", key="chg_current")
        new_password_1 = st.text_input("New password", type="password", key="chg_new1")
        new_password_2 = st.text_input("Confirm new password", type="password", key="chg_new2")
        change_submitted = st.form_submit_button("Change Password")

    if change_submitted:
        if not current_password or not new_password_1 or not new_password_2:
            st.error("All fields required.")
        elif new_password_1 != new_password_2:
            st.error("New passwords do not match.")
        elif len(new_password_1) < 6:
            st.error("Password must be at least 6 characters.")
        else:
            db_row = query("SELECT password_hash FROM users WHERE user_id = %s;",
                           (USER["user_id"],), fetch="one")
            if not db_row:
                st.error("Account not found. Please log out and back in.")
            elif not verify_password(current_password, db_row["password_hash"]):
                st.error("Current password is incorrect.")
                log_action("PASSWORD_CHANGE_FAILED", "users", USER["user_id"], "Wrong current")
            else:
                execute("UPDATE users SET password_hash = %s WHERE user_id = %s;",
                        (hash_password(new_password_1), USER["user_id"]))
                log_action("PASSWORD_CHANGE", "users", USER["user_id"], "Password changed")
                st.success("Password changed.")

    if IS_ADMIN:
        st.markdown("---")
        st.markdown("### Reset Another User's Password")
        other_users = [u for u in users if u["username"] != USER["username"] and u["active"]]
        if not other_users:
            st.info("No other active users.")
        else:
            user_options = {f"{u['username']} ({u['full_name']})": u["user_id"] for u in other_users}
            with st.form("admin_reset_form", clear_on_submit=True):
                target_label = st.selectbox("User", list(user_options.keys()),
                                            key="admin_reset_target")
                admin_new_pw = st.text_input("New password", type="password",
                                             key="admin_reset_pw")
                admin_reset_submitted = st.form_submit_button("Reset")
            if admin_reset_submitted:
                if len(admin_new_pw) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    target_id = user_options[target_label]
                    execute("UPDATE users SET password_hash = %s WHERE user_id = %s;",
                            (hash_password(admin_new_pw), target_id))
                    log_action("PASSWORD_RESET_BY_ADMIN", "users", target_id,
                               f"Reset for {target_label}")
                    st.success(f"Password reset for {target_label}.")


# ============================================================
# ROUTER
# ============================================================
PAGES = {
    "📊 Dashboard": page_dashboard,
    "🛒 Point of Sale": page_pos,
    "📋 Pending Pickup": page_pending,
    "🧑 Customers": page_customers,
    "📦 Stock Management": page_stock,
    "👕 Products & Prices": page_products,
    "🏫 Schools": page_schools,
    "✂️ Tailor Production": page_tailor,
    "💰 Financials": page_financials,
    "📊 Reports": page_reports,
    "📅 Close Day": page_close_day,
    "📜 Audit Log": page_audit,
    "👥 Users": page_users,
}

PAGES[st.session_state.page]()
