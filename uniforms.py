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
    .receipt-box {
        background: white; padding: 25px; border-radius: 10px;
        border: 1px solid #ddd; font-family: 'Courier New', monospace;
        max-width: 420px; margin: 0 auto;
    }
    .receipt-box h3 { text-align: center; margin-bottom: 4px; }
    .receipt-line {
        display: flex; justify-content: space-between;
        padding: 2px 0; font-size: 14px;
    }
    .receipt-divider { border-top: 1px dashed #999; margin: 8px 0; }
    .login-box {
        max-width: 400px; margin: 80px auto; padding: 40px;
        background: white; border-radius: 14px;
        box-shadow: 0 6px 24px rgba(11,31,58,0.15);
    }
    .login-box h1 { text-align: center; margin-bottom: 4px; }
    .login-box p { text-align: center; color: #666; margin-bottom: 24px; }
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
# SETUP (RUNS ONCE)
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
        "admin":    {"password": "admin2026",  "role": "admin",   "name": "Administrator"},
        "cashier":  {"password": "cashier2026","role": "cashier", "name": "Cashier"},
        "manager":  {"password": "manager2026","role": "manager", "name": "Manager"},
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
           WHERE s.school_id=%s AND si.product_id=%s AND si.issued=TRUE;""",
        (school_id, product_id), fetch="one",
    )
    return int(brought["q"] or 0) - int(sold["q"] or 0)


def cart_total():
    return sum(item["quantity"] * item["unit_price"] for item in st.session_state.cart)


# ============================================================
# SIDEBAR NAV
# ============================================================
with st.sidebar:
    st.markdown(f"## 🧾 Uniform POS")
    st.caption(f"👤 {USER['name']} · `{USER['role']}`")
    st.markdown("---")

    pages = ["🛒 Point of Sale", "📦 Stock Management"]
    if IS_MANAGER:
        pages += ["👕 Products & Prices", "🏫 Schools"]
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
                            and item["unit_price"] == unit_price):
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
                    })
                st.success(f"Added {qty} × {selected_product_name}")
                st.rerun()

        st.markdown("---")
        st.subheader("Current Cart")

        if not st.session_state.cart:
            st.info("Cart is empty. Add items above.")
        else:
            for i, item in enumerate(st.session_state.cart):
                cols = st.columns([4, 1, 1, 1, 1])
                cols[0].write(f"**{item['product_name']}**  \n{item['school_name']}")
                cols[1].write(f"×{item['quantity']}")
                cols[2].write(f"KES {item['unit_price']:,.0f}")
                cols[3].write(f"**KES {item['quantity']*item['unit_price']:,.0f}**")
                if cols[4].button("🗑", key=f"del_{i}"):
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
                         item["unit_price"], item["quantity"] * item["unit_price"], True),
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

        if st.session_state.last_receipt:
            r = st.session_state.last_receipt
            st.markdown("---")
            st.subheader("🧾 Last Receipt")
            receipt_html = f"""
            <div class="receipt-box">
                <h3>UNIFORM SALES</h3>
                <div style="text-align:center;font-size:12px;">{r['school']}</div>
                <div class="receipt-divider"></div>
                <div class="receipt-line"><span>Sale #</span><span>{r['sale_id']}</span></div>
                <div class="receipt-line"><span>Date</span><span>{r['date'].strftime('%Y-%m-%d %H:%M')}</span></div>
                <div class="receipt-line"><span>Customer</span><span>{r['customer']}</span></div>
                <div class="receipt-divider"></div>
            """
            for it in r["items"]:
                receipt_html += (
                    f'<div class="receipt-line"><span>{it["product_name"]} ×{it["quantity"]}</span>'
                    f'<span>{it["quantity"]*it["unit_price"]:,.0f}</span></div>'
                )
            receipt_html += f"""
                <div class="receipt-divider"></div>
                <div class="receipt-line"><b>TOTAL</b><b>KES {r['total']:,.0f}</b></div>
                <div class="receipt-line"><span>Payment</span><span>{r['payment_method']} ({r['payment_status']})</span></div>
                <div class="receipt-divider"></div>
                <div style="text-align:center;font-size:12px;">{r['term']} · {r['year']}</div>
                <div style="text-align:center;font-size:11px;margin-top:6px;">Thank you!</div>
            </div>
            """
            components.html(receipt_html, height=520, scrolling=True)


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

    tab1, tab2 = st.tabs(["Add Stock", "View Stock"])

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
            log_action("STOCK_ADD", "stock", None,
                       f"{qty} × {product_name} → {school_name}")
            st.success(f"Added {qty} × {product_name} to {school_name}.")
            st.rerun()

    with tab2:
        school_map = {s["school_name"]: s["school_id"] for s in schools}
        school_name = st.selectbox("Filter School", list(school_map.keys()), key="view_stock_school")
        school_id = school_map[school_name]

        rows = query(
            """SELECT p.product_name,
                      COALESCE(SUM(st.quantity_brought),0) AS brought,
                      COALESCE((
                        SELECT SUM(si.quantity) FROM sale_items si
                        JOIN sales s ON s.sale_id = si.sale_id
                        WHERE s.school_id = %s AND si.product_id = p.product_id AND si.issued = TRUE
                      ),0) AS sold
               FROM products p
               LEFT JOIN stock st ON st.product_id = p.product_id AND st.school_id = %s
               GROUP BY p.product_id, p.product_name
               ORDER BY p.product_name;""",
            (school_id, school_id),
        )
        if rows:
            df = pd.DataFrame([{
                "Product": r["product_name"],
                "Brought": int(r["brought"]),
                "Sold": int(r["sold"]),
                "Remaining": int(r["brought"]) - int(r["sold"]),
            } for r in rows])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No stock records yet.")


# ============================================================
# PAGE: PRODUCTS
# ============================================================
def page_products():
    st.title("👕 Products & Prices")

    tab1, tab2 = st.tabs(["Products", "School-Specific Prices"])

    with tab1:
        products = get_products()
        if products:
            df = pd.DataFrame([{
                "ID": p["product_id"],
                "Product": p["product_name"],
                "Default Price": float(p["price"]),
                "Cost Price": float(p["cost_price"]),
            } for p in products])
            st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown("### Add / Update Product")
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
            log_action("PRICE_OVERRIDE", "school_product_prices", None,
                       f"{pc} @ {sc} = {pr}")
            st.success("Price saved.")
            st.rerun()

        rows = query(
            """SELECT s.school_name, spp.category_name, p.product_name, spp.price
               FROM school_product_prices spp
               JOIN schools s ON s.school_id = spp.school_id
               JOIN products p ON p.product_id = spp.product_id
               ORDER BY s.school_name, p.product_name;"""
        )
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ============================================================
# PAGE: SCHOOLS
# ============================================================
def page_schools():
    st.title("🏫 Schools")
    schools = get_schools()
    if schools:
        st.dataframe(pd.DataFrame(schools), use_container_width=True, hide_index=True)

    st.markdown("### Add School")
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
        """SELECT transaction_date, transaction_type, category, description, amount
           FROM financial_transactions
           ORDER BY transaction_date DESC LIMIT 25;"""
    )
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ============================================================
# PAGE: REPORTS
# ============================================================
def page_reports():
    st.title("📊 Reports")

    tab1, tab2, tab3 = st.tabs(["Sales", "By School", "By Product"])

    with tab1:
        rows = query(
            """SELECT s.sale_id, s.sale_date, sch.school_name, c.customer_name,
                      s.total_amount, s.payment_method, s.payment_status, s.term, s.year
               FROM sales s
               JOIN schools sch ON sch.school_id = s.school_id
               LEFT JOIN customers c ON c.customer_id = s.customer_id
               ORDER BY s.sale_date DESC LIMIT 100;"""
        )
        if rows:
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.download_button("⬇ Download CSV", df.to_csv(index=False), "sales.csv")
        else:
            st.info("No sales yet.")

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
    st.subheader("Recent Production")
    rows = query(
        """SELECT tp.production_date, s.school_name, p.product_name,
                  tp.tailor_name, tp.quantity_produced, tp.cost_per_item,
                  tp.amount_paid, tp.notes
           FROM tailor_production tp
           JOIN schools s ON s.school_id = tp.school_id
           JOIN products p ON p.product_id = tp.product_id
           ORDER BY tp.production_date DESC LIMIT 50;"""
    )
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ============================================================
# PAGE: AUDIT LOG
# ============================================================
def page_audit():
    st.title("📜 Audit Log")
    st.caption("Every action is recorded with user, timestamp, and details.")

    rows = query(
        """SELECT log_time, user_name, action, table_name, record_id, details
           FROM audit_log
           ORDER BY log_time DESC LIMIT 200;"""
    )
    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("⬇ Download CSV", df.to_csv(index=False), "audit_log.csv")
    else:
        st.info("No activity yet.")


# ============================================================
# ROUTER
# ============================================================
PAGES = {
    "🛒 Point of Sale": page_pos,
    "📦 Stock Management": page_stock,
    "👕 Products & Prices": page_products,
    "🏫 Schools": page_schools,
    "💰 Financials": page_financials,
    "📊 Reports": page_reports,
    "✂️ Tailor Production": page_tailor,
    "📜 Audit Log": page_audit,
}

PAGES[st.session_state.page]()
