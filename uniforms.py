# ============================================================
# UNIFORM SALES POS — FULL SYSTEM
# ============================================================
import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components
from contextlib import contextmanager

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
    @media print {
        [data-testid="stSidebar"],
        [data-testid="stHeader"],
        .stButton,
        .stDownloadButton,
        [data-testid="stToolbar"],
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
# SETUP DATABASE (RUNS ONCE)
# ============================================================
@st.cache_resource(show_spinner="Setting up database...")
def setup_database():
    conn = get_connection()
    if conn is None:
        return False
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schools (
                school_id SERIAL PRIMARY KEY,
                school_name VARCHAR(100) NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS products (
                product_id SERIAL PRIMARY KEY,
                product_name VARCHAR(100) NOT NULL UNIQUE,
                price NUMERIC(10,2) NOT NULL DEFAULT 0,
                cost_price NUMERIC(10,2) NOT NULL DEFAULT 0
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
                year INT
            );
            CREATE TABLE IF NOT EXISTS sale_items (
                sale_item_id SERIAL PRIMARY KEY,
                sale_id INT NOT NULL REFERENCES sales(sale_id),
                product_id INT NOT NULL REFERENCES products(product_id),
                quantity INT NOT NULL,
                unit_price NUMERIC(10,2) NOT NULL,
                line_total NUMERIC(10,2) NOT NULL,
                issued BOOLEAN DEFAULT TRUE
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
                unit_cost NUMERIC(10,2) DEFAULT 0
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
        """)

        for stmt in [
            "ALTER TABLE products ADD COLUMN IF NOT EXISTS cost_price NUMERIC(10,2) NOT NULL DEFAULT 0;",
            "ALTER TABLE sales ADD COLUMN IF NOT EXISTS term VARCHAR(20);",
            "ALTER TABLE sales ADD COLUMN IF NOT EXISTS year INT;",
            "ALTER TABLE sale_items ADD COLUMN IF NOT EXISTS issued BOOLEAN DEFAULT TRUE;",
            "ALTER TABLE stock ADD COLUMN IF NOT EXISTS term VARCHAR(20);",
            "ALTER TABLE stock ADD COLUMN IF NOT EXISTS year INT;",
            "ALTER TABLE stock ADD COLUMN IF NOT EXISTS unit_cost NUMERIC(10,2) DEFAULT 0;",
        ]:
            cur.execute(stmt)

        for s in ["LOVING BLOOMS SCHOOL", "WARIDI UTAWALA SCHOOL"]:
            cur.execute(
                "INSERT INTO schools (school_name) VALUES (%s) ON CONFLICT (school_name) DO NOTHING;",
                (s,),
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
# AUTHENTICATION
# ============================================================
def get_users():
    return {
        "admin":   {"password": "admin2026",   "role": "admin",   "name": "Administrator"},
        "cashier": {"password": "cashier2026", "role": "cashier", "name": "Cashier"},
        "manager": {"password": "manager2026", "role": "manager", "name": "Manager"},
    }


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
            users = get_users()
            if username in users and users[username]["password"] == password:
                st.session_state.user = {
                    "username": username,
                    "role": users[username]["role"],
                    "name": users[username]["name"],
                }
                log_action("LOGIN", "users", None, f"{username} signed in")
                st.rerun()
            else:
                st.error("Invalid username or password.")

        st.caption("Default: admin / admin2026")


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


def get_products():
    return query("SELECT product_id, product_name, price, cost_price FROM products ORDER BY product_name;")


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
           WHERE s.school_id=%s AND si.product_id=%s;""",
        (school_id, product_id), fetch="one",
    )
    return int(brought["q"] or 0) - int(sold["q"] or 0)


def cart_total():
    return sum(item["quantity"] * item["unit_price"] for item in st.session_state.cart)


def confirm_delete(
    label,
    key,
    summary="This cannot be undone.",
    cascade_options=None,
    cascade_default=True,
):
    """
    Universal delete confirmation with optional cascades.

    cascade_options: list of dicts:
        [{"label": "Also remove linked stock entry",
          "sql": "DELETE FROM stock WHERE ...",
          "params": (id,)}]
    """
    state_key = f"cd_{key}"

    if state_key not in st.session_state:
        st.session_state[state_key] = False

    # ---- Trigger ----
    if not st.session_state[state_key]:
        if st.button("🗑 Delete", key=f"ask_{key}"):
            st.session_state[state_key] = True
            st.rerun()
        return False

    # ---- Confirmation panel ----
    st.error(f"⚠️ Delete **{label}**?\n\n{summary}")

    cascades_to_run = []
    if cascade_options:
        st.markdown("**Also do:**")
        for i, act in enumerate(cascade_options):
            checked = st.checkbox(
                act["label"],
                value=cascade_default,
                key=f"cascade_{key}_{i}",
            )
            if checked:
                cascades_to_run.append(act)

    c1, c2, _ = st.columns([1, 1, 3])
    with c1:
        if st.button("✅ Yes, delete", type="primary",
                     key=f"yes_{key}", use_container_width=True):
            for act in cascades_to_run:
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
        pages += ["💰 Financials", "📊 Reports", "✂️ Tailor Production", "📜 Audit Log"]

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
    if not schools or not products:
        st.warning("Schools or products missing. Please set them up first.")
        return

    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("Add Items")
        school_map = {s["school_name"]: s["school_id"] for s in schools}
        selected_school_name = st.selectbox("School", list(school_map.keys()))
        school_id = school_map[selected_school_name]

        product_map = {p["product_name"]: p for p in products}
        selected_product_name = st.selectbox("Product", list(product_map.keys()))
        product = product_map[selected_product_name]

        effective_price = get_school_price(school_id, product["product_id"], product["price"])
        stock_avail = get_stock_available(school_id, product["product_id"])

        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            qty = st.number_input("Quantity", min_value=1, value=1, step=1)
        with c2:
            unit_price = st.number_input(
                "Unit Price (KES)", min_value=0.0,
                value=float(effective_price), step=10.0,
            )
        with c3:
            st.metric("Stock Available", stock_avail)

        issued_now = st.checkbox(
            "✓ Issue items now (uncheck if customer will collect later)",
            value=True,
        )

        if st.button("➕ Add to Cart", use_container_width=True):
            if qty > stock_avail:
                st.warning(
                    f"Only {stock_avail} in stock for {selected_school_name}. "
                    "Adjust quantity or add stock first."
                )
            else:
                found = False
                for item in st.session_state.cart:
                    if (item["school_id"] == school_id
                            and item["product_id"] == product["product_id"]
                            and item["unit_price"] == unit_price
                            and item.get("issued", True) == issued_now):
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
                    })
                st.success(f"Added {qty} × {selected_product_name}")
                st.rerun()

        st.markdown("---")
        st.subheader("Current Cart")

        if not st.session_state.cart:
            st.info("Cart is empty. Add items above.")
        else:
            for i, item in enumerate(st.session_state.cart):
                cols = st.columns([4, 1, 1, 1, 1, 1])
                badge = "✓ Issued" if item.get("issued", True) else "✗ Pending"
                cols[0].write(f"**{item['product_name']}**  \n{item['school_name']}")
                cols[1].write(f"×{item['quantity']}")
                cols[2].write(f"KES {item['unit_price']:,.0f}")
                cols[3].write(f"**KES {item['quantity']*item['unit_price']:,.0f}**")
                cols[4].caption(badge)
                if cols[5].button("🗑", key=f"del_{i}"):
                    st.session_state.cart.pop(i)
                    st.rerun()

            if st.button("🗑 Clear Cart"):
                st.session_state.cart = []
                st.rerun()

    with col_right:
        st.subheader("Checkout")
        total = cart_total()
        st.metric("Total", f"KES {total:,.0f}")

        customer_name = st.text_input("Customer Name", value="")
        customer_phone = st.text_input("Phone (optional)", value="")
        payment_method = st.selectbox("Payment Method", ["Cash", "M-Pesa", "Card", "Bank Transfer"])
        payment_status = st.selectbox("Payment Status", ["Paid", "Pending", "Partial"])

        term, year = current_term_year()
        term_input = st.selectbox("Term", ["Term 1", "Term 2", "Term 3"],
                                  index=["Term 1", "Term 2", "Term 3"].index(term))
        year_input = st.number_input("Year", value=year, min_value=2020, max_value=2100)

        if st.button("✅ Complete Sale", type="primary", use_container_width=True):
            if not st.session_state.cart:
                st.error("Cart is empty.")
                return

            for item in st.session_state.cart:
                avail = get_stock_available(item["school_id"], item["product_id"])
                if item["quantity"] > avail:
                    st.error(
                        f"Insufficient stock for {item['product_name']} "
                        f"({item['school_name']}): need {item['quantity']}, have {avail}."
                    )
                    return

            try:
                customer_id = None
                if customer_name.strip():
                    row = execute_returning(
                        """INSERT INTO customers (customer_name, phone)
                           VALUES (%s, %s) RETURNING customer_id;""",
                        (customer_name.strip(), customer_phone.strip() or None),
                    )
                    customer_id = row["customer_id"]

                school_ids = {it["school_id"] for it in st.session_state.cart}
                if len(school_ids) > 1:
                    st.error("Cart contains items from multiple schools. Please complete them separately.")
                    return

                sale_row = execute_returning(
                    """INSERT INTO sales
                       (school_id, customer_id, total_amount, payment_method,
                        payment_status, term, year)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)
                       RETURNING sale_id, sale_date;""",
                    (list(school_ids)[0], customer_id, total, payment_method,
                     payment_status, term_input, int(year_input)),
                )
                sale_id = sale_row["sale_id"]

                for item in st.session_state.cart:
                    execute(
                        """INSERT INTO sale_items
                           (sale_id, product_id, quantity, unit_price, line_total, issued)
                           VALUES (%s, %s, %s, %s, %s, %s);""",
                        (sale_id, item["product_id"], item["quantity"],
                         item["unit_price"], item["quantity"] * item["unit_price"],
                         item.get("issued", True)),
                    )

                log_action("SALE", "sales", sale_id,
                           f"{len(st.session_state.cart)} items, KES {total:,.0f}")

                st.session_state.last_receipt = {
                    "sale_id": sale_id,
                    "date": sale_row["sale_date"],
                    "school": st.session_state.cart[0]["school_name"],
                    "customer": customer_name or "Walk-in",
                    "phone": customer_phone,
                    "items": list(st.session_state.cart),
                    "total": total,
                    "payment_method": payment_method,
                    "payment_status": payment_status,
                    "term": term_input,
                    "year": int(year_input),
                }
                st.session_state.cart = []
                st.success(f"Sale #{sale_id} recorded!")
                st.rerun()
            except Exception as e:
                st.error(f"Sale failed: {e}")

        # ---- RECEIPT ----
        if st.session_state.last_receipt:
            r = st.session_state.last_receipt
            st.markdown("---")
            st.subheader("🧾 Last Receipt")

            # Build items
            item_rows = ""
            for it in r["items"]:
                is_issued = it.get("issued", True)
                issued_line = (
                    '<div class="rc-issued rc-yes">✓ Issued</div>'
                    if is_issued
                    else '<div class="rc-issued rc-no">✗ Not Issued</div>'
                )
                item_rows += f"""
                <div class="rc-item">
                    <div class="rc-item-line">
                        <span class="rc-item-name">{it['product_name']}</span>
                        <span class="rc-item-qty">{it['quantity']} × {it['unit_price']:,.0f}</span>
                        <span class="rc-item-total">{it['quantity']*it['unit_price']:,.0f}</span>
                    </div>
                    {issued_line}
                </div>
                """

            receipt_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Receipt #{r['sale_id']:06d}</title>
<style>
    * {{ box-sizing: border-box; }}
    html, body {{
        margin: 0; padding: 0;
        font-family: 'Courier New', monospace;
        background: #eef2f7; color: #000;
    }}
    .rc {{
        max-width: 300px; margin: 20px auto;
        background: #fff; border: 1px solid #ccc;
        padding: 14px 16px 18px; font-size: 12px; line-height: 1.4;
    }}
    .rc-header {{ text-align: center; padding-bottom: 8px; }}
    .rc-title {{ font-size: 15px; font-weight: bold; letter-spacing: 2px; margin: 0; }}
    .rc-school {{ font-size: 12px; font-weight: bold; margin-top: 3px; }}
    .rc-hr {{ border-top: 1px dashed #000; margin: 8px 0; }}
    .rc-meta {{ font-size: 11px; }}
    .rc-meta-row {{ display: flex; justify-content: space-between; padding: 1px 0; }}
    .rc-items {{ margin: 2px 0; }}
    .rc-item {{ padding: 5px 0; border-bottom: 1px dotted #ccc; }}
    .rc-item:last-child {{ border-bottom: none; }}
    .rc-item-line {{ display: flex; justify-content: space-between; align-items: baseline; }}
    .rc-item-name {{ flex: 1; font-weight: bold; }}
    .rc-item-qty {{ color: #555; font-size: 11px; margin: 0 6px; white-space: nowrap; }}
    .rc-item-total {{ font-weight: bold; white-space: nowrap; }}
    .rc-issued {{ font-size: 10px; font-weight: bold; margin-top: 2px; letter-spacing: 0.5px; }}
    .rc-yes {{ color: #0a8f3c; }}
    .rc-no  {{ color: #c0392b; }}
    .rc-total {{ display: flex; justify-content: space-between; font-size: 14px; font-weight: bold; margin: 4px 0; }}
    .rc-pay {{ display: flex; justify-content: space-between; font-size: 11px; }}
    .rc-footer {{ text-align: center; margin-top: 10px; font-size: 12px; font-weight: bold; }}
    .rc-print {{
        display: block; width: 100%; margin-top: 14px; padding: 9px;
        background: #f28c28; color: #fff; border: none; border-radius: 6px;
        font-size: 13px; font-weight: bold; cursor: pointer;
    }}
    .rc-print:hover {{ background: #d97618; }}
    @media print {{
        body {{ background: #fff; margin: 0; }}
        .rc {{ max-width: 100%; border: none; margin: 0; padding: 0; }}
        .rc-print {{ display: none !important; }}
        @page {{ margin: 6mm; }}
    }}
</style>
</head>
<body>
<div class="rc">
    <div class="rc-header">
        <div class="rc-title">UNIFORM SALES</div>
        <div class="rc-school">{r['school']}</div>
    </div>
    <div class="rc-hr"></div>
    <div class="rc-meta">
        <div class="rc-meta-row"><span>Receipt</span><span>#{r['sale_id']:06d}</span></div>
        <div class="rc-meta-row"><span>Date</span><span>{r['date'].strftime('%d %b %Y  %H:%M')}</span></div>
        <div class="rc-meta-row"><span>Customer</span><span>{r['customer']}</span></div>
    </div>
    <div class="rc-hr"></div>
    <div class="rc-items">
        {item_rows}
    </div>
    <div class="rc-hr"></div>
    <div class="rc-total">
        <span>TOTAL</span>
        <span>KES {r['total']:,.0f}</span>
    </div>
    <div class="rc-pay">
        <span>{r['payment_method']}</span>
        <span>{r['payment_status']}</span>
    </div>
    <div class="rc-hr"></div>
    <div class="rc-footer">
        Thank You, Customer!
    </div>
    <button class="rc-print" onclick="window.print();">🖨 Print Receipt</button>
</div>
<script>window.focus();</script>
</body>
</html>"""

            components.html(receipt_html, height=560, scrolling=True)

            col_a, col_b, col_c = st.columns([1, 1, 2])
            with col_a:
                components.html(
                    f"""
                    <button onclick="
                        var w = window.open('', '_blank', 'width=380,height=720');
                        w.document.write({receipt_html!r});
                        w.document.close();
                        w.focus();
                        setTimeout(function(){{ w.print(); }}, 400);
                    " style="
                        background:#f28c28;color:#fff;border:none;
                        padding:10px 16px;border-radius:7px;font-weight:bold;
                        cursor:pointer;width:100%;font-size:13px;
                    ">🖨 Print (New Window)</button>
                    """,
                    height=50,
                )
            with col_b:
                st.download_button(
                    "⬇ Download HTML",
                    data=receipt_html,
                    file_name=f"receipt_{r['sale_id']:06d}.html",
                    mime="text/html",
                    use_container_width=True,
                )

            # ---- UNDO LAST SALE ----
            st.markdown("---")
            undo_col, info_col = st.columns([1, 2])

            with undo_col:
                if st.button(
                    "↩️ Undo This Sale",
                    type="primary",
                    use_container_width=True,
                    key="undo_last_sale",
                ):
                    st.session_state["confirm_undo"] = r["sale_id"]

            with info_col:
                st.caption(
                    f"This will delete sale **#{r['sale_id']}** and "
                    f"restore the {len(r['items'])} item(s) back to stock."
                )

            if st.session_state.get("confirm_undo") == r["sale_id"]:
                st.error(
                    f"⚠️ Are you sure you want to **delete Sale #{r['sale_id']}** "
                    f"(KES {r['total']:,.0f})? This cannot be undone."
                )
                c1, c2, _ = st.columns([1, 1, 3])
                with c1:
                    if st.button("✅ Yes, delete it", type="primary",
                                 use_container_width=True, key="confirm_undo_yes"):
                        try:
                            execute("DELETE FROM sale_items WHERE sale_id = %s;",
                                    (r["sale_id"],))
                            execute("DELETE FROM sales WHERE sale_id = %s;",
                                    (r["sale_id"],))
                            log_action(
                                "SALE_UNDONE", "sales", r["sale_id"],
                                f"Undo sale #{r['sale_id']} (KES {r['total']:,.0f})",
                            )
                            st.session_state.last_receipt = None
                            st.session_state["confirm_undo"] = None
                            st.success(f"✅ Sale #{r['sale_id']} deleted. Stock restored.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Could not delete sale: {e}")
                with c2:
                    if st.button("❌ Cancel", use_container_width=True,
                                 key="confirm_undo_no"):
                        st.session_state["confirm_undo"] = None
                        st.rerun()


# ============================================================
# PAGE: PENDING PICKUP
# ============================================================
def page_pending():
    st.title("📋 Pending Pickup")
    st.caption("Search a customer, tick items as you hand them over, then mark the sale as delivered.")

    col1, col2 = st.columns([3, 1])
    with col1:
        search = st.text_input(
            "🔎 Search by receipt #, phone, or customer name",
            placeholder="e.g.  000042  or  0722123456  or  Mary",
            key="pending_search",
        ).strip().lower()
    with col2:
        st.write("")
        st.write("")
        show_completed = st.checkbox("Show delivered today", value=False)

    # Summary
    pending_count = query("SELECT COUNT(*) AS c FROM sale_items WHERE issued = FALSE;", fetch="one")
    total_pending = int(pending_count["c"] or 0) if pending_count else 0

    today_delivered = query(
        """SELECT COUNT(*) AS c FROM audit_log
           WHERE action = 'ITEM_ISSUED'
             AND log_time::date = CURRENT_DATE;""",
        fetch="one",
    )
    delivered_today = int(today_delivered["c"] or 0) if today_delivered else 0

    m1, m2, m3 = st.columns(3)
    m1.metric("📦 Total Pending Items", total_pending)
    m2.metric("✅ Delivered Today", delivered_today)
    m3.metric("🕐 Today", datetime.now().strftime("%d %b %Y"))

    st.markdown("---")

    sale_filter = ""
    params = []
    if search:
        sale_filter = """
            AND (
                CAST(s.sale_id AS TEXT) ILIKE %s
                OR COALESCE(c.customer_name, '') ILIKE %s
                OR COALESCE(c.phone, '') ILIKE %s
            )
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
        WHERE si.issued = FALSE
        {sale_filter}
        ORDER BY s.sale_date DESC
        LIMIT 50;
        """,
        tuple(params),
    )

    if not sales_rows:
        if search:
            st.info(f"No pending sales match **'{search}'**.")
        else:
            st.success("🎉 No pending items — everything has been delivered.")
    else:
        st.subheader(f"📦 {len(sales_rows)} sale(s) with pending items")

        for sale in sales_rows:
            sid = sale["sale_id"]
            with st.container():
                head_cols = st.columns([2, 2, 2, 2, 1])
                head_cols[0].markdown(f"### Sale #{sid:06d}")
                head_cols[1].markdown(
                    f"**{sale['sale_date'].strftime('%d %b %Y')}**  \n"
                    f"<span style='color:#888;font-size:12px;'>"
                    f"{sale['sale_date'].strftime('%H:%M')}</span>",
                    unsafe_allow_html=True,
                )
                head_cols[2].markdown(
                    f"**{sale['customer_name']}**  \n"
                    f"<span style='color:#888;font-size:12px;'>"
                    f"{sale['phone'] or 'no phone'}</span>",
                    unsafe_allow_html=True,
                )
                head_cols[3].markdown(f"**{sale['school_name']}**")

                items = query(
                    """SELECT si.sale_item_id, si.quantity, si.unit_price,
                              p.product_name
                       FROM sale_items si
                       JOIN products p ON p.product_id = si.product_id
                       WHERE si.sale_id = %s AND si.issued = FALSE
                       ORDER BY p.product_name;""",
                    (sid,),
                )

                pending_total_qty = sum(int(i["quantity"]) for i in items)

                with head_cols[4]:
                    if st.button(
                        "✅ Deliver All",
                        key=f"deliver_all_{sid}",
                        use_container_width=True,
                        type="primary",
                    ):
                        for item in items:
                            execute(
                                "UPDATE sale_items SET issued = TRUE WHERE sale_item_id = %s;",
                                (item["sale_item_id"],),
                            )
                            log_action(
                                "ITEM_ISSUED", "sale_items", item["sale_item_id"],
                                f"Issued {item['quantity']} × {item['product_name']} on sale #{sid}",
                            )
                        st.success(f"✅ Sale #{sid} fully delivered.")
                        st.rerun()

                st.caption(
                    f"Pending: **{pending_total_qty}** item(s) · "
                    f"Term {sale['term'] or '-'} · {sale['year'] or '-'}"
                )

                for item in items:
                    item_cols = st.columns([4, 1, 1, 1])
                    item_cols[0].write(f"**{item['product_name']}**")
                    item_cols[1].write(f"Qty: **{item['quantity']}**")
                    item_cols[2].write(f"KES {float(item['unit_price']):,.0f}")

                    with item_cols[3]:
                        ticked = st.checkbox(
                            "Issued",
                            key=f"tick_{item['sale_item_id']}",
                            value=False,
                        )
                        if ticked:
                            already = query(
                                "SELECT issued FROM sale_items WHERE sale_item_id = %s;",
                                (item["sale_item_id"],),
                                fetch="one",
                            )
                            if already and not already["issued"]:
                                execute(
                                    "UPDATE sale_items SET issued = TRUE WHERE sale_item_id = %s;",
                                    (item["sale_item_id"],),
                                )
                                log_action(
                                    "ITEM_ISSUED", "sale_items", item["sale_item_id"],
                                    f"Issued {item['quantity']} × {item['product_name']} on sale #{sid}",
                                )
                                st.rerun()

                st.markdown(
                    "<hr style='margin:14px 0 4px;border:none;"
                    "border-top:1px solid #e5e9f0;'>",
                    unsafe_allow_html=True,
                )

    if show_completed:
        st.markdown("---")
        st.subheader("✅ Delivered Today")
        delivered = query(
            """SELECT al.log_time, al.details, al.user_name
               FROM audit_log al
               WHERE al.action = 'ITEM_ISSUED'
                 AND al.log_time::date = CURRENT_DATE
               ORDER BY al.log_time DESC
               LIMIT 100;"""
        )
        if delivered:
            df = pd.DataFrame(delivered)
            df.columns = ["Time", "Details", "By"]
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Nothing delivered today yet.")

    st.markdown("---")
    all_pending = query(
        """SELECT si.sale_item_id, s.sale_id, s.sale_date,
                  sch.school_name, c.customer_name, c.phone,
                  p.product_name, si.quantity, si.unit_price,
                  si.line_total
           FROM sale_items si
           JOIN sales s ON s.sale_id = si.sale_id
           JOIN schools sch ON sch.school_id = s.school_id
           LEFT JOIN customers c ON c.customer_id = s.customer_id
           JOIN products p ON p.product_id = si.product_id
           WHERE si.issued = FALSE
           ORDER BY s.sale_date DESC;"""
    )
    if all_pending:
        st.download_button(
            "⬇ Download All Pending (CSV)",
            data=pd.DataFrame(all_pending).to_csv(index=False),
            file_name="pending_pickup.csv",
        )


# ============================================================
# PAGE: STOCK
# ============================================================
def page_stock():
    st.title("📦 Stock Management")

    schools = get_schools()
    products = get_products()
    if not schools or not products:
        st.warning("Set up schools and products first.")
        return

    tab1, tab2 = st.tabs(["Add Stock", "View / Delete Stock"])

    with tab1:
        school_map = {s["school_name"]: s["school_id"] for s in schools}
        school_name = st.selectbox("School", list(school_map.keys()), key="stock_school")
        school_id = school_map[school_name]

        product_map = {p["product_name"]: p for p in products}
        product_name = st.selectbox("Product", list(product_map.keys()), key="stock_product")
        product = product_map[product_name]

        c1, c2, c3 = st.columns(3)
        qty = c1.number_input("Quantity Brought", min_value=1, value=1, step=1)
        unit_cost = c2.number_input("Unit Cost (KES)", min_value=0.0,
                                    value=float(product["cost_price"] or 0), step=10.0)
        term, year = current_term_year()
        term_in = c3.selectbox("Term", ["Term 1", "Term 2", "Term 3"],
                               index=["Term 1", "Term 2", "Term 3"].index(term))

        if st.button("➕ Add Stock", use_container_width=True):
            execute(
                """INSERT INTO stock (school_id, product_id, quantity_brought, term, year, unit_cost)
                   VALUES (%s, %s, %s, %s, %s, %s);""",
                (school_id, product["product_id"], qty, term_in, year, unit_cost),
            )
            log_action("STOCK_ADD", "stock", None, f"{qty} × {product_name} → {school_name}")
            st.success(f"Added {qty} × {product_name} to {school_name}.")
            st.rerun()

    with tab2:
        st.subheader("Stock Entries")
        school_map = {s["school_name"]: s["school_id"] for s in schools}
        school_name = st.selectbox("Filter School", list(school_map.keys()), key="view_stock_school")
        school_id = school_map[school_name]

        entries = query(
            """SELECT st.stock_id, st.date_added, p.product_name,
                      st.quantity_brought, st.term, st.year, st.unit_cost
               FROM stock st
               JOIN products p ON p.product_id = st.product_id
               WHERE st.school_id = %s
               ORDER BY st.date_added DESC LIMIT 200;""",
            (school_id,),
        )

        if entries:
            for e in entries:
                sid = e["stock_id"]
                cols = st.columns([2, 2, 1, 1, 1, 1, 1])
                cols[0].write(e["date_added"].strftime("%Y-%m-%d %H:%M"))
                cols[1].write(e["product_name"])
                cols[2].write(f"×{e['quantity_brought']}")
                cols[3].write(e["term"] or "-")
                cols[4].write(str(e["year"] or "-"))
                cols[5].write(f"Cost: {float(e['unit_cost'] or 0):,.0f}")

                if IS_MANAGER:
                    with cols[6]:
                        if confirm_delete(
                            f"{e['quantity_brought']} × {e['product_name']}",
                            f"stock_{sid}",
                            summary=(
                                f"{e['quantity_brought']} × {e['product_name']} "
                                f"on {e['date_added'].strftime('%d %b %Y')}"
                            ),
                        ):
                            execute("DELETE FROM stock WHERE stock_id = %s;", (sid,))
                            log_action("DELETE_STOCK", "stock", sid,
                                       f"Deleted {e['quantity_brought']} × {e['product_name']}")
                            st.success("Stock entry deleted.")
                            st.rerun()

        st.markdown("---")
        st.subheader("Summary")
        summary = query(
            """SELECT p.product_name,
                      COALESCE(SUM(st.quantity_brought),0) AS brought,
                      COALESCE((
                        SELECT SUM(si.quantity) FROM sale_items si
                        JOIN sales s ON s.sale_id = si.sale_id
                        WHERE s.school_id = %s AND si.product_id = p.product_id
                      ),0) AS sold
               FROM products p
               LEFT JOIN stock st ON st.product_id = p.product_id AND st.school_id = %s
               GROUP BY p.product_id, p.product_name
               ORDER BY p.product_name;""",
            (school_id, school_id),
        )
        if summary:
            df = pd.DataFrame([{
                "Product": r["product_name"],
                "Brought": int(r["brought"]),
                "Sold": int(r["sold"]),
                "Remaining": int(r["brought"]) - int(r["sold"]),
            } for r in summary])
            st.dataframe(df, use_container_width=True, hide_index=True)


# ============================================================
# PAGE: PRODUCTS
# ============================================================
def page_products():
    st.title("👕 Products & Prices")

    tab1, tab2 = st.tabs(["Products", "School-Specific Prices"])

    with tab1:
        products = get_products()
        if products:
            st.subheader("Product List")
            for p in products:
                pid = p["product_id"]
                cols = st.columns([3, 2, 2, 1])
                cols[0].write(f"**{p['product_name']}**")
                cols[1].write(f"Price: KES {float(p['price']):,.0f}")
                cols[2].write(f"Cost: KES {float(p['cost_price']):,.0f}")
                if IS_ADMIN:
                    with cols[3]:
                        linked = query(
                            """SELECT
                                 (SELECT COUNT(*) FROM sale_items WHERE product_id = %s) AS sales,
                                 (SELECT COUNT(*) FROM stock WHERE product_id = %s) AS stock,
                                 (SELECT COUNT(*) FROM school_product_prices WHERE product_id = %s) AS prices;""",
                            (pid, pid, pid), fetch="one",
                        )

                        cascade_opts = []
                        if linked and int(linked["sales"]) > 0:
                            cascade_opts.append({
                                "label": f"⚠️ Also delete {int(linked['sales'])} linked sale item(s)",
                                "sql": "DELETE FROM sale_items WHERE product_id = %s;",
                                "params": (pid,),
                            })
                        if linked and int(linked["stock"]) > 0:
                            cascade_opts.append({
                                "label": f"Also delete {int(linked['stock'])} stock entry(ies)",
                                "sql": "DELETE FROM stock WHERE product_id = %s;",
                                "params": (pid,),
                            })
                        if linked and int(linked["prices"]) > 0:
                            cascade_opts.append({
                                "label": f"Also delete {int(linked['prices'])} price override(s)",
                                "sql": "DELETE FROM school_product_prices WHERE product_id = %s;",
                                "params": (pid,),
                            })

                        linked_summary = ""
                        if linked:
                            linked_summary = (
                                f"Linked — sales: {int(linked['sales'])}, "
                                f"stock: {int(linked['stock'])}, "
                                f"prices: {int(linked['prices'])}"
                            )

                        if confirm_delete(
                            f"product '{p['product_name']}'",
                            f"prod_{pid}",
                            summary=linked_summary,
                            cascade_options=cascade_opts,
                        ):
                            execute("DELETE FROM products WHERE product_id = %s;", (pid,))
                            log_action("DELETE_PRODUCT", "products", pid,
                                       f"Deleted product {p['product_name']}")
                            st.success("Product deleted.")
                            st.rerun()
            st.markdown("---")

        st.subheader("Add / Update Product")
        c1, c2, c3 = st.columns(3)
        name = c1.text_input("Product Name")
        price = c2.number_input("Default Price", min_value=0.0, step=10.0)
        cost = c3.number_input("Cost Price", min_value=0.0, step=10.0)
        if st.button("💾 Save Product"):
            if not name.strip():
                st.error("Product name is required.")
            else:
                execute(
                    """INSERT INTO products (product_name, price, cost_price)
                       VALUES (%s, %s, %s)
                       ON CONFLICT (product_name) DO UPDATE
                       SET price = EXCLUDED.price, cost_price = EXCLUDED.cost_price;""",
                    (name.strip(), price, cost),
                )
                log_action("PRODUCT_SAVE", "products", None, f"{name} @ {price}")
                st.success(f"Saved {name}.")
                st.rerun()

    with tab2:
        schools = get_schools()
        products = get_products()
        if not schools or not products:
            return
        school_map = {s["school_name"]: s["school_id"] for s in schools}
        prod_map = {p["product_name"]: p["product_id"] for p in products}

        sc = st.selectbox("School", list(school_map.keys()), key="pp_school")
        pc = st.selectbox("Product", list(prod_map.keys()), key="pp_prod")
        cat = st.text_input("Category", value="Default")
        pr = st.number_input("Price", min_value=0.0, step=10.0)

        if st.button("💾 Save Price Override"):
            execute(
                """INSERT INTO school_product_prices
                   (school_id, category_name, product_id, price)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (school_id, category_name, product_id)
                   DO UPDATE SET price = EXCLUDED.price;""",
                (school_map[sc], cat.strip() or "Default", prod_map[pc], pr),
            )
            log_action("PRICE_OVERRIDE", "school_product_prices", None, f"{pc} @ {sc} = {pr}")
            st.success("Price saved.")
            st.rerun()

        st.markdown("---")
        st.subheader("Existing Overrides")
        rows = query(
            """SELECT spp.school_product_price_id AS id,
                      s.school_name, spp.category_name, p.product_name, spp.price
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
                        if confirm_delete(
                            f"{r['product_name']} @ {r['school_name']}",
                            f"ovr_{r['id']}",
                            summary=f"KES {float(r['price']):,.0f} for {r['product_name']}",
                        ):
                            execute("DELETE FROM school_product_prices WHERE school_product_price_id = %s;",
                                    (r["id"],))
                            log_action("DELETE_OVERRIDE", "school_product_prices", r["id"],
                                       f"Deleted override {r['product_name']} @ {r['school_name']}")
                            st.success("Override deleted.")
                            st.rerun()


# ============================================================
# PAGE: SCHOOLS
# ============================================================
def page_schools():
    st.title("🏫 Schools")

    schools = get_schools()
    if schools:
        st.subheader("School List")
        for s in schools:
            sid = s["school_id"]
            cols = st.columns([4, 1])
            cols[0].write(f"**{s['school_name']}**")
            if IS_ADMIN:
                with cols[1]:
                    linked = query(
                        """SELECT
                             (SELECT COUNT(*) FROM sales WHERE school_id = %s) AS sales,
                             (SELECT COUNT(*) FROM stock WHERE school_id = %s) AS stock,
                             (SELECT COUNT(*) FROM school_product_prices WHERE school_id = %s) AS prices,
                             (SELECT COUNT(*) FROM tailor_production WHERE school_id = %s) AS tailors;""",
                        (sid, sid, sid, sid), fetch="one",
                    )

                    cascade_opts = []
                    if linked and int(linked["sales"]) > 0:
                        cascade_opts.append({
                            "label": f"⚠️ Also delete {int(linked['sales'])} sale(s) and their items",
                            "sql": """DELETE FROM sale_items WHERE sale_id IN
                                     (SELECT sale_id FROM sales WHERE school_id = %s);""",
                            "params": (sid,),
                        })
                        cascade_opts.append({
                            "label": f"Also delete {int(linked['sales'])} sale header(s)",
                            "sql": "DELETE FROM sales WHERE school_id = %s;",
                            "params": (sid,),
                        })
                    if linked and int(linked["stock"]) > 0:
                        cascade_opts.append({
                            "label": f"Also delete {int(linked['stock'])} stock entry(ies)",
                            "sql": "DELETE FROM stock WHERE school_id = %s;",
                            "params": (sid,),
                        })
                    if linked and int(linked["prices"]) > 0:
                        cascade_opts.append({
                            "label": f"Also delete {int(linked['prices'])} price override(s)",
                            "sql": "DELETE FROM school_product_prices WHERE school_id = %s;",
                            "params": (sid,),
                        })
                    if linked and int(linked["tailors"]) > 0:
                        cascade_opts.append({
                            "label": f"Also delete {int(linked['tailors'])} tailor record(s)",
                            "sql": "DELETE FROM tailor_production WHERE school_id = %s;",
                            "params": (sid,),
                        })

                    linked_summary = ""
                    if linked:
                        linked_summary = (
                            f"Linked — sales: {int(linked['sales'])}, "
                            f"stock: {int(linked['stock'])}, "
                            f"prices: {int(linked['prices'])}, "
                            f"tailor: {int(linked['tailors'])}"
                        )

                    if confirm_delete(
                        f"school '{s['school_name']}'",
                        f"school_{sid}",
                        summary=linked_summary,
                        cascade_options=cascade_opts,
                    ):
                        execute("DELETE FROM schools WHERE school_id = %s;", (sid,))
                        log_action("DELETE_SCHOOL", "schools", sid,
                                   f"Deleted school {s['school_name']}")
                        st.success("School deleted.")
                        st.rerun()
        st.markdown("---")

    st.subheader("Add School")
    name = st.text_input("School Name")
    if st.button("💾 Save School"):
        if not name.strip():
            st.error("Name required.")
        else:
            execute(
                "INSERT INTO schools (school_name) VALUES (%s) ON CONFLICT (school_name) DO NOTHING;",
                (name.strip().upper(),),
            )
            log_action("SCHOOL_ADD", "schools", None, name.strip())
            st.success("School saved.")
            st.rerun()


# ============================================================
# PAGE: CUSTOMERS
# ============================================================
def page_customers():
    st.title("🧑 Customers")

    rows = query(
        """SELECT c.customer_id, c.customer_name, c.phone,
                  (SELECT COUNT(*) FROM sales WHERE customer_id = c.customer_id) AS purchases
           FROM customers c
           ORDER BY c.customer_name;"""
    )

    if not rows:
        st.info("No customers yet.")
        return

    search = st.text_input("🔎 Search by name or phone",
                           key="cust_search").strip().lower()

    filtered = []
    for r in rows:
        haystack = f"{r['customer_name']} {r['phone'] or ''}".lower()
        if search and search not in haystack:
            continue
        filtered.append(r)

    st.caption(f"Showing {len(filtered)} of {len(rows)} customers.")

    for r in filtered:
        cols = st.columns([3, 2, 2, 1])
        cols[0].write(f"**{r['customer_name']}**")
        cols[1].write(r["phone"] or "-")
        cols[2].write(f"{r['purchases']} purchase(s)")

        if IS_MANAGER:
            with cols[3]:
                cascade = []
                if int(r["purchases"]) > 0:
                    cascade.append({
                        "label": f"⚠️ Also delete {int(r['purchases'])} linked sale(s) and items",
                        "sql": """DELETE FROM sale_items WHERE sale_id IN
                                 (SELECT sale_id FROM sales WHERE customer_id = %s);""",
                        "params": (r["customer_id"],),
                    })
                    cascade.append({
                        "label": "Also delete the sale header(s)",
                        "sql": "DELETE FROM sales WHERE customer_id = %s;",
                        "params": (r["customer_id"],),
                    })

                if confirm_delete(
                    f"customer '{r['customer_name']}'",
                    f"cust_{r['customer_id']}",
                    summary=f"{r['purchases']} linked purchase(s)",
                    cascade_options=cascade,
                ):
                    execute("DELETE FROM customers WHERE customer_id = %s;",
                            (r["customer_id"],))
                    log_action("DELETE_CUSTOMER", "customers", r["customer_id"],
                               f"Deleted customer {r['customer_name']}")
                    st.success("Customer deleted.")
                    st.rerun()


# ============================================================
# PAGE: FINANCIALS
# ============================================================
def page_financials():
    st.title("💰 Financials")

    rev = query(
        "SELECT COALESCE(SUM(total_amount),0) AS total FROM sales WHERE payment_status = 'Paid';",
        fetch="one",
    )
    revenue = float(rev["total"] if rev else 0)

    cogs = query(
        """SELECT COALESCE(SUM(si.quantity * p.cost_price),0) AS total
           FROM sale_items si
           JOIN sales s ON s.sale_id = si.sale_id
           JOIN products p ON p.product_id = si.product_id
           WHERE s.payment_status = 'Paid';""",
        fetch="one",
    )
    cogs_total = float(cogs["total"] if cogs else 0)

    tailor = query(
        "SELECT COALESCE(SUM(amount_paid),0) AS total FROM tailor_production;",
        fetch="one",
    )
    tailor_total = float(tailor["total"] if tailor else 0)

    cap = query(
        """SELECT COALESCE(SUM(amount),0) AS total FROM financial_transactions
           WHERE transaction_type = 'Capital Contribution';""",
        fetch="one",
    )
    capital = float(cap["total"] if cap else 0)

    gross_profit = revenue - cogs_total
    net_profit = gross_profit - tailor_total

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Revenue", f"KES {revenue:,.0f}")
    c2.metric("COGS", f"KES {cogs_total:,.0f}")
    c3.metric("Gross Profit", f"KES {gross_profit:,.0f}")
    c4.metric("Net Profit", f"KES {net_profit:,.0f}")

    st.markdown("---")
    st.subheader("Investor Capital & Profit Share")
    inv = query(
        """SELECT i.investor_name,
                  COALESCE(SUM(ft.amount),0) AS capital
           FROM investors i
           LEFT JOIN financial_transactions ft
             ON ft.investor_id = i.investor_id
             AND ft.transaction_type = 'Capital Contribution'
           WHERE i.active = TRUE
           GROUP BY i.investor_name
           ORDER BY i.investor_name;"""
    )
    if inv:
        df = pd.DataFrame(inv)
        df["capital"] = df["capital"].astype(float)
        total_cap = df["capital"].sum()
        df["share_%"] = (df["capital"] / total_cap * 100).round(2) if total_cap else 0
        df["profit_share"] = (df["share_%"] / 100 * net_profit).round(2) if total_cap else 0
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"Total Capital: KES {total_cap:,.0f}")

    st.markdown("---")
    st.subheader("Record Transaction")
    with st.form("fin_form", clear_on_submit=True):
        ttype = st.selectbox("Type", ["Expense", "Capital Contribution", "Withdrawal", "Other Income"])
        category = st.text_input("Category", value="General")
        desc = st.text_input("Description")
        amount = st.number_input("Amount", min_value=0.0, step=100.0)
        investor_options = query("SELECT investor_id, investor_name FROM investors WHERE active=TRUE;")
        inv_map = {i["investor_name"]: i["investor_id"] for i in investor_options} if investor_options else {}
        inv_choice = st.selectbox("Investor (optional)", ["None"] + list(inv_map.keys()))
        term, year = current_term_year()
        submitted = st.form_submit_button("💾 Save")
        if submitted:
            execute(
                """INSERT INTO financial_transactions
                   (transaction_type, category, description, amount, investor_id, term, year)
                   VALUES (%s, %s, %s, %s, %s, %s, %s);""",
                (ttype, category, desc, amount, inv_map.get(inv_choice), term, year),
            )
            log_action("FIN_TXN", "financial_transactions", None, f"{ttype} {amount}")
            st.success("Transaction recorded.")
            st.rerun()

    st.markdown("---")
    st.subheader("Recent Transactions")
    rows = query(
        """SELECT transaction_id AS id, transaction_date, transaction_type,
                  category, description, amount
           FROM financial_transactions
           ORDER BY transaction_date DESC LIMIT 100;"""
    )
    if rows:
        for r in rows:
            cols = st.columns([2, 2, 3, 2, 1])
            cols[0].write(r["transaction_date"].strftime("%Y-%m-%d"))
            cols[1].write(r["transaction_type"])
            cols[2].write(r["description"] or r["category"])
            cols[3].write(f"KES {float(r['amount']):,.0f}")
            if IS_ADMIN:
                with cols[4]:
                    warning = ""
                    if r["transaction_type"] == "Capital Contribution":
                        warning = ("⚠️ This is a capital entry. Deleting it will affect "
                                   "investor share calculations.")
                    summary = (
                        f"**{r['transaction_type']}** — KES {float(r['amount']):,.0f}"
                        + (f"\n\n_{warning}_" if warning else "")
                    )
                    if confirm_delete(
                        f"transaction #{r['id']}",
                        f"fin_{r['id']}",
                        summary=summary,
                    ):
                        execute("DELETE FROM financial_transactions WHERE transaction_id = %s;",
                                (r["id"],))
                        log_action("DELETE_FIN", "financial_transactions", r["id"],
                                   f"Deleted {r['transaction_type']} KES {float(r['amount']):,.0f}")
                        st.success("Transaction deleted.")
                        st.rerun()
    else:
        st.info("No transactions yet.")


# ============================================================
# PAGE: REPORTS
# ============================================================
def page_reports():
    st.title("📊 Reports")

    tab1, tab2, tab3 = st.tabs(["Sales", "By School", "By Product"])

    with tab1:
        st.subheader("Sales History")
        if not IS_MANAGER:
            st.caption("View only — deletion requires manager or admin.")

        rows = query(
            """SELECT s.sale_id, s.sale_date, sch.school_name, c.customer_name,
                      s.total_amount, s.payment_method, s.payment_status,
                      s.term, s.year
               FROM sales s
               JOIN schools sch ON sch.school_id = s.school_id
               LEFT JOIN customers c ON c.customer_id = s.customer_id
               ORDER BY s.sale_date DESC LIMIT 200;"""
        )

        if not rows:
            st.info("No sales yet.")
        else:
            search = st.text_input("🔎 Filter by customer, school, or sale #",
                                   key="sales_filter").strip().lower()

            for r in rows:
                rid = r["sale_id"]
                haystack = f"{rid} {r['customer_name'] or ''} {r['school_name']}".lower()
                if search and search not in haystack:
                    continue

                cols = st.columns([1, 2, 2, 2, 1, 1, 1, 1])
                cols[0].write(f"**#{rid}**")
                cols[1].write(r["sale_date"].strftime("%Y-%m-%d %H:%M"))
                cols[2].write(r["school_name"])
                cols[3].write(r["customer_name"] or "Walk-in")
                cols[4].write(f"KES {float(r['total_amount']):,.0f}")
                cols[5].write(r["payment_method"] or "-")
                cols[6].write(r["payment_status"])

                if IS_MANAGER:
                    with cols[7]:
                        if confirm_delete(
                            f"Sale #{rid}",
                            f"sale_{rid}",
                            summary=(
                                f"**KES {float(r['total_amount']):,.0f}** — "
                                f"{r['customer_name'] or 'Walk-in'} on "
                                f"{r['sale_date'].strftime('%d %b %Y')}"
                            ),
                            cascade_options=[{
                                "label": "Also remove sale line items (restores stock)",
                                "sql": "DELETE FROM sale_items WHERE sale_id = %s;",
                                "params": (rid,),
                            }],
                        ):
                            execute("DELETE FROM sales WHERE sale_id = %s;", (rid,))
                            log_action("DELETE_SALE", "sales", rid,
                                       f"Deleted sale #{rid} (KES {float(r['total_amount']):,.0f})")
                            st.success(f"Sale #{rid} deleted. Stock restored.")
                            st.rerun()

            st.markdown("---")
            df = pd.DataFrame(rows)
            st.download_button("⬇ Download CSV", df.to_csv(index=False), "sales.csv")

    with tab2:
        rows = query(
            """SELECT sch.school_name,
                      COUNT(s.sale_id) AS num_sales,
                      COALESCE(SUM(s.total_amount),0) AS revenue
               FROM schools sch
               LEFT JOIN sales s ON s.school_id = sch.school_id
               GROUP BY sch.school_name
               ORDER BY revenue DESC;"""
        )
        if rows:
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.bar_chart(df.set_index("school_name")["revenue"])

    with tab3:
        rows = query(
            """SELECT p.product_name,
                      SUM(si.quantity) AS qty_sold,
                      SUM(si.line_total) AS revenue
               FROM sale_items si
               JOIN products p ON p.product_id = si.product_id
               GROUP BY p.product_name
               ORDER BY revenue DESC;"""
        )
        if rows:
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.bar_chart(df.set_index("product_name")["revenue"])


# ============================================================
# PAGE: TAILOR PRODUCTION
# ============================================================
def page_tailor():
    st.title("✂️ Tailor Production")

    schools = get_schools()
    products = get_products()
    if not schools or not products:
        return

    school_map = {s["school_name"]: s["school_id"] for s in schools}
    prod_map = {p["product_name"]: p["product_id"] for p in products}

    with st.expander("➕ Record New Production", expanded=False):
        with st.form("tailor_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            school = c1.selectbox("School", list(school_map.keys()))
            product = c2.selectbox("Product", list(prod_map.keys()))
            c3, c4 = st.columns(2)
            tailor = c3.text_input("Tailor Name")
            qty = c4.number_input("Quantity Produced", min_value=1, value=1, step=1)
            c5, c6 = st.columns(2)
            cost_item = c5.number_input("Cost per Item", min_value=0.0, step=10.0)
            paid = c6.number_input("Amount Paid", min_value=0.0, step=100.0)
            notes = st.text_input("Notes")
            term, year = current_term_year()
            submitted = st.form_submit_button("💾 Save Production")
            if submitted:
                if not tailor.strip():
                    st.error("Tailor name required.")
                else:
                    execute(
                        """INSERT INTO tailor_production
                           (school_id, product_id, tailor_name, quantity_produced,
                            cost_per_item, amount_paid, term, year, notes)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);""",
                        (school_map[school], prod_map[product], tailor.strip(),
                         qty, cost_item, paid, term, year, notes or None),
                    )
                    execute(
                        """INSERT INTO stock (school_id, product_id, quantity_brought, term, year, unit_cost)
                           VALUES (%s, %s, %s, %s, %s, %s);""",
                        (school_map[school], prod_map[product], qty, term, year, cost_item),
                    )
                    log_action("TAILOR_PROD", "tailor_production", None,
                               f"{qty} × {product} by {tailor}")
                    st.success("Production recorded and stock updated.")
                    st.rerun()

    st.markdown("---")
    st.subheader("Production History")

    rows = query(
        """SELECT tp.production_id AS id, tp.production_date, tp.school_id,
                  tp.product_id, s.school_name,
                  p.product_name, tp.tailor_name, tp.quantity_produced,
                  tp.cost_per_item, tp.amount_paid, tp.notes
           FROM tailor_production tp
           JOIN schools s ON s.school_id = tp.school_id
           JOIN products p ON p.product_id = tp.product_id
           ORDER BY tp.production_date DESC LIMIT 100;"""
    )

    if not rows:
        st.info("No production records yet.")
        return

    search = st.text_input(
        "🔎 Filter by tailor, product, or school",
        key="tailor_filter",
    ).strip().lower()

    for r in rows:
        haystack = f"{r['tailor_name']} {r['product_name']} {r['school_name']}".lower()
        if search and search not in haystack:
            continue

        cols = st.columns([2, 2, 2, 1, 2, 2, 1])
        cols[0].write(r["production_date"].strftime("%Y-%m-%d"))
        cols[1].write(r["tailor_name"])
        cols[2].write(r["product_name"])
        cols[3].write(f"×{r['quantity_produced']}")
        cols[4].write(f"Cost/Item: {float(r['cost_per_item']):,.0f}")
        cols[5].write(f"Paid: {float(r['amount_paid']):,.0f}")

        stock_entry = query(
            """SELECT stock_id, quantity_brought FROM stock
               WHERE school_id = %s AND product_id = %s
                 AND quantity_brought = %s AND unit_cost = %s
               ORDER BY date_added DESC LIMIT 1;""",
            (r["school_id"], r["product_id"],
             r["quantity_produced"], r["cost_per_item"]),
            fetch="one",
        )

        with cols[6]:
            if IS_MANAGER:
                cascade = []
                if stock_entry:
                    cascade.append({
                        "label": f"Also delete linked stock entry ({stock_entry['quantity_brought']} units)",
                        "sql": "DELETE FROM stock WHERE stock_id = %s;",
                        "params": (stock_entry["stock_id"],),
                    })

                if confirm_delete(
                    f"production #{r['id']}",
                    f"tailor_{r['id']}",
                    summary=(
                        f"**{r['quantity_produced']} × {r['product_name']}** "
                        f"by **{r['tailor_name']}** on "
                        f"{r['production_date'].strftime('%d %b %Y')}"
                    ),
                    cascade_options=cascade,
                ):
                    execute(
                        "DELETE FROM tailor_production WHERE production_id = %s;",
                        (r["id"],),
                    )
                    log_action(
                        "DELETE_TAILOR", "tailor_production", r["id"],
                        f"Deleted production #{r['id']} ({r['quantity_produced']} × {r['product_name']})",
                    )
                    st.success("Production record deleted.")
                    st.rerun()

        st.markdown(
            "<hr style='margin:4px 0;border:none;border-top:1px solid #f0f0f0;'>",
            unsafe_allow_html=True,
        )


# ============================================================
# PAGE: AUDIT LOG
# ============================================================
def page_audit():
    st.title("📜 Audit Log")
    st.caption("Every action is recorded with user, timestamp, and details.")

    rows = query(
        """SELECT log_id, log_time, user_name, action, table_name,
                  record_id, details
           FROM audit_log
           ORDER BY log_time DESC LIMIT 200;"""
    )

    if not rows:
        st.info("No activity yet.")
        return

    c1, c2, c3 = st.columns([2, 2, 1])
    search = c1.text_input("🔎 Search", key="audit_search").strip().lower()
    action_filter = c2.selectbox(
        "Action",
        ["All"] + sorted({r["action"] for r in rows}),
        key="audit_action",
    )
    c3.write("")
    c3.write("")
    if IS_ADMIN and c3.button("🗑 Clear Old (>90 days)"):
        execute("DELETE FROM audit_log WHERE log_time < NOW() - INTERVAL '90 days';")
        log_action("AUDIT_CLEANUP", "audit_log", None, "Cleared logs older than 90 days")
        st.success("Old logs cleared.")
        st.rerun()

    filtered = []
    for r in rows:
        if action_filter != "All" and r["action"] != action_filter:
            continue
        haystack = f"{r['user_name']} {r['action']} {r['details'] or ''}".lower()
        if search and search not in haystack:
            continue
        filtered.append(r)

    st.caption(f"Showing {len(filtered)} of {len(rows)} recent entries.")

    for r in filtered:
        cols = st.columns([2, 2, 2, 4, 1])
        cols[0].write(r["log_time"].strftime("%Y-%m-%d %H:%M"))
        cols[1].write(f"**{r['user_name']}**")
        cols[2].write(f"`{r['action']}`")
        cols[3].write(r["details"] or "-")

        if IS_ADMIN:
            with cols[4]:
                if confirm_delete(
                    f"log entry #{r['log_id']}",
                    f"log_{r['log_id']}",
                    summary=f"`{r['action']}` by {r['user_name']}",
                ):
                    execute("DELETE FROM audit_log WHERE log_id = %s;", (r["log_id"],))
                    st.success("Log entry deleted.")
                    st.rerun()

    st.markdown("---")
    df = pd.DataFrame(filtered)
    st.download_button("⬇ Download CSV", df.to_csv(index=False), "audit_log.csv")


# ============================================================
# ROUTER
# ============================================================
PAGES = {
    "🛒 Point of Sale": page_pos,
    "📋 Pending Pickup": page_pending,
    "📦 Stock Management": page_stock,
    "👕 Products & Prices": page_products,
    "🏫 Schools": page_schools,
    "🧑 Customers": page_customers,
    "💰 Financials": page_financials,
    "📊 Reports": page_reports,
    "✂️ Tailor Production": page_tailor,
    "📜 Audit Log": page_audit,
}

PAGES[st.session_state.page]()
