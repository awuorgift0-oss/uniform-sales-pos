# ============================================================
# UNIFORM SALES POS — COMPLETE PRODUCTION SYSTEM
# ============================================================
import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from datetime import datetime, timedelta
import streamlit.components.v1 as components
from contextlib import contextmanager
import bcrypt
import io

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Uniform Sales POS",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# STYLING
# ============================================================
st.markdown("""
<style>
    .stApp { background-color: #eef6fb; }
    [data-testid="stSidebar"] { background-color: #0b1f3a; }
    [data-testid="stSidebar"] * { color: white; }
    [data-testid="stSidebar"] .stButton > button {
        background-color: #1f3a5f; color: white;
        border: 1px solid #2c5282;
    }
    h1, h2, h3 { color: #0b1f3a; }
    .stButton > button {
        background-color: #f28c28; color: white;
        border: none; border-radius: 7px; font-weight: bold;
    }
    .stButton > button:hover { background-color: #d97618; color: white; }
    div[data-testid="stMetric"] {
        background-color: white; border-radius: 10px; padding: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    .login-box {
        max-width: 400px; margin: 80px auto; padding: 40px;
        background: white; border-radius: 14px;
        box-shadow: 0 6px 24px rgba(11,31,58,0.15);
    }
    .login-box h1 { text-align: center; margin-bottom: 4px; }
    .login-box p { text-align: center; color: #666; margin-bottom: 24px; }
    .void-tag {
        background: #fdecea; color: #c0392b;
        padding: 1px 8px; border-radius: 8px;
        font-size: 11px; font-weight: bold;
    }
    @media print {
        [data-testid="stSidebar"],
        [data-testid="stHeader"],
        .stButton, .stDownloadButton,
        [data-testid="stToolbar"], footer { display: none !important; }
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
# SETUP DATABASE
# ============================================================
@st.cache_resource(show_spinner="Setting up database...")
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

        # Safe column additions
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

        # Seed categories
        for cat in ["Uniform", "Sports", "Accessories", "Footwear", "Other"]:
            cur.execute(
                "INSERT INTO product_categories (category_name) VALUES (%s) ON CONFLICT (category_name) DO NOTHING;",
                (cat,),
            )

        # Seed schools
        for s in ["LOVING BLOOMS SCHOOL", "WARIDI UTAWALA SCHOOL"]:
            cur.execute(
                "INSERT INTO schools (school_name) VALUES (%s) ON CONFLICT (school_name) DO NOTHING;",
                (s,),
            )

        # Seed default admin user (only if no users exist)
        cur.execute("SELECT COUNT(*) FROM users;")
        if cur.fetchone()[0] == 0:
            default_hash = bcrypt.hashpw(b"admin2026", bcrypt.gensalt()).decode()
            cur.execute(
                """INSERT INTO users (username, password_hash, full_name, role)
                   VALUES ('admin', %s, 'Administrator', 'admin')""",
                (default_hash,),
            )

        # Seed products
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

        # Seed investors
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
# AUTHENTICATION (bcrypt)
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
        <h1>🧾 Uniform Sales POS</h1>
        <p>Please sign in to continue</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("🔐 Sign In", use_container_width=True)

        if submitted:
            row = query(
                "SELECT * FROM users WHERE username = %s AND active = TRUE;",
                (username.strip().lower(),),
                fetch="one",
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
                log_action("LOGIN_FAILED", "users", None, f"Failed login: {username}")
                st.error("Invalid username or password.")

        st.caption("Default: **admin** / **admin2026** — change it after first login.")


if "user" not in st.session_state or not st.session_state.user:
    login_screen()
    st.stop()


# ============================================================
# SESSION STATE
# ============================================================
def init_state():
    defaults = {
        "cart": [],
        "last_receipt": None,
        "page": "🛒 Point of Sale",
        "confirm_undo": None,
        "preview_sale": None,
        "scan_input": "",
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


def get_schools():
    return query("SELECT school_id, school_name FROM schools ORDER BY school_name;")


def get_categories():
    return query("SELECT category_id, category_name FROM product_categories ORDER BY category_name;")


def get_products(category_id=None, active_only=True):
    sql = """SELECT p.product_id, p.product_name, p.sku, p.price, p.cost_price,
                    p.category_id, c.category_name
             FROM products p
             LEFT JOIN product_categories c ON c.category_id = p.category_id
             WHERE 1=1"""
    params = []
    if active_only:
        sql += " AND p.active = TRUE"
    if category_id:
        sql += " AND p.category_id = %s"
        params.append(category_id)
    sql += " ORDER BY p.product_name;"
    return query(sql, tuple(params))


def get_school_price(school_id, product_id, default_price):
    row = query(
        """SELECT price FROM school_product_prices
           WHERE school_id = %s AND product_id = %s
           ORDER BY category_name LIMIT 1;""",
        (school_id, product_id), fetch="one",
    )
    return float(row["price"]) if row else float(default_price)


def get_stock_available(school_id, product_id):
    brought = query(
        "SELECT COALESCE(SUM(quantity_brought),0) AS q FROM stock WHERE school_id=%s AND product_id=%s;",
        (school_id, product_id), fetch="one",
    )
    sold = query(
        """SELECT COALESCE(SUM(si.quantity),0) AS q FROM sale_items si
           JOIN sales s ON s.sale_id = si.sale_id
           WHERE s.school_id=%s AND si.product_id=%s AND s.voided = FALSE;""",
        (school_id, product_id), fetch="one",
    )
    refunded = query(
        """SELECT COALESCE(SUM(ri.quantity),0) AS q FROM refund_items ri
           JOIN refunds r ON r.refund_id = ri.refund_id
           JOIN sale_items si ON si.sale_item_id = ri.sale_item_id
           JOIN sales s ON s.sale_id = si.sale_id
           WHERE s.school_id=%s AND si.product_id=%s;""",
        (school_id, product_id), fetch="one",
    )
    return int(brought["q"] or 0) - int(sold["q"] or 0) + int(refunded["q"] or 0)


def cart_total():
    return sum(item["quantity"] * item["unit_price"] for item in st.session_state.cart)


def find_customer_by_phone(phone):
    if not phone:
        return None
    digits = "".join(c for c in phone if c.isdigit())
    return query(
        """SELECT * FROM customers
           WHERE REPLACE(REPLACE(REPLACE(phone, ' ', ''), '-', ''), '+', '') ILIKE %s
           LIMIT 1;""",
        (f"%{digits}%",),
        fetch="one",
    )


def confirm_delete(label, key, summary="This cannot be undone.", cascade_options=None,
                   cascade_default=True, confirm_text="Delete"):
    state_key = f"cd_{key}"
    if state_key not in st.session_state:
        st.session_state[state_key] = False

    if not st.session_state[state_key]:
        if st.button("🗑 Delete", key=f"ask_{key}"):
            st.session_state[state_key] = True
            st.rerun()
        return False

    st.error(f"⚠️ Delete **{label}**?\n\n{summary}")

    cascades = []
    if cascade_options:
        st.markdown("**Also do:**")
        for i, act in enumerate(cascade_options):
            if st.checkbox(act["label"], value=cascade_default, key=f"cascade_{key}_{i}"):
                cascades.append(act)

    c1, c2, _ = st.columns([1, 1, 3])
    with c1:
        if st.button("✅ Yes, delete", type="primary", key=f"yes_{key}", use_container_width=True):
            for act in cascades:
                try:
                    execute(act["sql"], act.get("params", ()))
                except Exception as e:
                    st.warning(f"Cascade failed: {e}")
            st.session_state[state_key] = False
            return True
    with c2:
        if st.button("❌ Cancel", key=f"no_{key}", use_container_width=True):
            st.session_state[state_key] = False
            st.rerun()
    return False


def build_receipt_html(r, thermal=False):
    """Generate receipt HTML. thermal=True → 58mm layout."""
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

    payments = r.get("payments") or [{"method": r["payment_method"], "amount": r["total"]}]
    payment_rows = "".join(
        f'<div class="rc-meta-row"><span>{p["method"]}</span>'
        f'<span>KES {float(p["amount"]):,.0f}</span></div>'
        for p in payments
    )

    width = "220px" if thermal else "300px"

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Receipt #{r['sale_id']:06d}</title>
<style>
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; font-family: 'Courier New', monospace;
                 background: #eef2f7; color: #000; }}
    .rc {{ max-width: {width}; margin: 20px auto; background: #fff;
          border: 1px solid #ccc; padding: 14px 16px 18px; font-size: 12px; line-height: 1.4; }}
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
    .rc-yes {{ background: #e6f7ee; color: #0a8f3c; }}
    .rc-no  {{ background: #fdecea; color: #c0392b; }}
    .rc-total {{ display: flex; justify-content: space-between; font-size: 14px;
                font-weight: bold; margin: 6px 0 2px; }}
    .rc-footer {{ text-align: center; margin-top: 10px; font-size: 12px; font-weight: bold; }}
    .rc-void {{ background: #c0392b; color: #fff; text-align: center;
               padding: 4px; font-weight: bold; letter-spacing: 2px; margin-bottom: 8px; }}
    .rc-print {{ display: block; width: 100%; margin-top: 14px; padding: 9px;
                background: #f28c28; color: #fff; border: none; border-radius: 6px;
                font-size: 13px; font-weight: bold; cursor: pointer; }}
    .rc-print:hover {{ background: #d97618; }}
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
    <button class="rc-print" onclick="window.print();">🖨 Print</button>
</div>
<script>window.focus();</script>
</body></html>"""


# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("## 🧾 Uniform POS")
    st.caption(f"👤 {USER['name']} · `{USER['role']}`")
    st.markdown("---")

    pages = ["🛒 Point of Sale", "📋 Pending Pickup", "📦 Stock Management"]
    if IS_MANAGER:
        pages += ["👕 Products & Prices", "🏫 Schools", "🧑 Customers"]
    if IS_ADMIN:
        pages += [
            "💰 Financials", "📊 Reports", "📅 Close Day",
            "✂️ Tailor Production", "📜 Audit Log", "👥 Users"
        ]

    if st.session_state.page not in pages:
        st.session_state.page = pages[0]

    st.session_state.page = st.radio(
        "Navigate", pages, index=pages.index(st.session_state.page)
    )

    st.markdown("---")
    term, year = current_term_year()
    st.caption(f"📅 {term} · {year}")
    st.caption(f"🛒 Cart: {len(st.session_state.cart)} items")

    if st.button("🚪 Sign Out", use_container_width=True):
        log_action("LOGOUT", "users", None, f"{USER['username']} signed out")
        st.session_state.user = None
        st.session_state.cart = []
        st.session_state.last_receipt = None
        st.rerun()


# ============================================================
# PAGE: POINT OF SALE
# ============================================================
def page_pos():
    st.title("🛒 Point of Sale")

    schools = get_schools()
    products = get_products()
    categories = get_categories()

    if not schools or not products:
        st.warning("Schools or products missing. Please set them up first.")
        return

    col_left, col_right = st.columns([2, 1])

    with col_left:
        # ============================================================
        # SCAN / QUICK ADD
        # ============================================================
        st.subheader("⚡ Quick Add")

        # Barcode scan
        scan_cols = st.columns([3, 1])
        with scan_cols[0]:
            scan = st.text_input(
                "🔖 Scan barcode or type SKU",
                key="scan_field",
                placeholder="Scan or type SKU and press Enter",
            )
        with scan_cols[1]:
            st.write("")
            st.write("")
            do_scan = st.button("Add", key="scan_add", use_container_width=True)

        if scan and (do_scan or scan != st.session_state.get("scan_input", "")):
            st.session_state.scan_input = scan
            matched = query(
                "SELECT * FROM products WHERE sku ILIKE %s AND active = TRUE LIMIT 1;",
                (scan.strip(),),
                fetch="one",
            )
            if matched:
                school_id = schools[0]["school_id"]  # default to first school
                price = get_school_price(school_id, matched["product_id"], matched["price"])
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
                        "school_id": school_id,
                        "school_name": schools[0]["school_name"],
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

        # Top 8 sellers as quick buttons
        top_sellers = query(
            """SELECT p.product_id, p.product_name, p.price,
                      SUM(si.quantity) AS sold
