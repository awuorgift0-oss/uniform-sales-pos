import os, textwrap, pathlib

code = r'''import os
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

import pandas as pd
import streamlit as st

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None
    RealDictCursor = None

st.set_page_config(
    page_title="Uniform Sales & Business Manager",
    page_icon="🧵",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------------
APP_TITLE = "Uniform Sales & Business Manager"
LOGO_PATHS = {
    "LOVING BLOOMS SCHOOL": "loving_blooms_logo.png",
    "WARIDI UTAWALA SCHOOL": "waridi_logo.png",
}

DEFAULT_SCHOOLS = ["LOVING BLOOMS SCHOOL", "WARIDI UTAWALA SCHOOL"]
DEFAULT_PRODUCTS = [
    ("Skirt", 650), ("Blouse", 500), ("Socks", 200),
    ("Tracksuit Playgroup-PP2", 1600), ("Tracksuit G1-G6", 1800),
    ("Sweater", 1000), ("Tie/Bow Tie", 150), ("Short", 400),
    ("Halfcoat", 600), ("Fleece", 2500), ("Trouser", 650),
    ("T-shirt", 500), ("Wrap Skirt", 500), ("Half Sweater", 800),
]

# -------------------------------------------------------------------
# DATABASE HELPERS
# -------------------------------------------------------------------
def get_connection():
    """Connect using Streamlit Cloud secrets or environment variables."""
    if psycopg2 is None:
        st.error("Database driver missing. Add psycopg2-binary to requirements.txt.")
        st.stop()

    cfg = {}
    try:
        if "postgres" in st.secrets:
            cfg = dict(st.secrets["postgres"])
        elif "database" in st.secrets:
            cfg = dict(st.secrets["database"])
    except Exception:
        cfg = {}

    host = cfg.get("host") or os.getenv("PGHOST") or os.getenv("DB_HOST")
    dbname = cfg.get("dbname") or cfg.get("database") or os.getenv("PGDATABASE") or os.getenv("DB_NAME")
    user = cfg.get("user") or os.getenv("PGUSER") or os.getenv("DB_USER")
    password = cfg.get("password") or os.getenv("PGPASSWORD") or os.getenv("DB_PASSWORD")
    port = cfg.get("port") or os.getenv("PGPORT") or os.getenv("DB_PORT") or 5432
    sslmode = cfg.get("sslmode") or os.getenv("PGSSLMODE") or "prefer"

    if not all([host, dbname, user, password]):
        st.error(
            "Database credentials are missing. In Streamlit Cloud, add a [postgres] "
            "section under App settings → Secrets with host, dbname, user, password, port."
        )
        st.stop()

    return psycopg2.connect(
        host=host, dbname=dbname, user=user, password=password,
        port=int(port), sslmode=sslmode, connect_timeout=10
    )


def query_df(sql, params=None):
    with get_connection() as conn:
        return pd.read_sql_query(sql, conn, params=params)


def execute(sql, params=None, returning=False):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            result = cur.fetchone() if returning else None
        conn.commit()
        return result


def setup_database():
    """Create missing tables and add newer columns without deleting existing data."""
    ddl = """
    CREATE TABLE IF NOT EXISTS schools (
        id SERIAL PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        default_price NUMERIC(12,2) NOT NULL DEFAULT 0,
        active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS customers (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        phone TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS school_product_prices (
        id SERIAL PRIMARY KEY,
        school_id INTEGER NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
        product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
        category TEXT NOT NULL DEFAULT 'Primary',
        class_name TEXT NOT NULL DEFAULT 'All',
        term TEXT NOT NULL DEFAULT 'All',
        year INTEGER NOT NULL DEFAULT 2026,
        price NUMERIC(12,2) NOT NULL DEFAULT 0,
        UNIQUE (school_id, product_id, category, class_name, term, year)
    );

    CREATE TABLE IF NOT EXISTS sales (
        id SERIAL PRIMARY KEY,
        receipt_number TEXT UNIQUE,
        school_id INTEGER REFERENCES schools(id),
        customer_id INTEGER REFERENCES customers(id),
        customer_name TEXT NOT NULL DEFAULT 'Walk-in customer',
        customer_phone TEXT,
        sale_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        term TEXT NOT NULL DEFAULT 'Term 1',
        year INTEGER NOT NULL DEFAULT 2026,
        class_name TEXT NOT NULL DEFAULT 'Not specified',
        subtotal NUMERIC(12,2) NOT NULL DEFAULT 0,
        discount NUMERIC(12,2) NOT NULL DEFAULT 0,
        total_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
        amount_paid NUMERIC(12,2) NOT NULL DEFAULT 0,
        balance_due NUMERIC(12,2) NOT NULL DEFAULT 0,
        payment_method TEXT NOT NULL DEFAULT 'Cash',
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS sale_items (
        id SERIAL PRIMARY KEY,
        sale_id INTEGER NOT NULL REFERENCES sales(id) ON DELETE CASCADE,
        product_id INTEGER REFERENCES products(id),
        product_name TEXT NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1,
        unit_price NUMERIC(12,2) NOT NULL DEFAULT 0,
        line_total NUMERIC(12,2) NOT NULL DEFAULT 0,
        issued BOOLEAN NOT NULL DEFAULT FALSE,
        issued_at TIMESTAMP,
        notes TEXT
    );

    CREATE TABLE IF NOT EXISTS stock (
        id SERIAL PRIMARY KEY,
        school_id INTEGER NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
        product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
        quantity INTEGER NOT NULL DEFAULT 0,
        reorder_level INTEGER NOT NULL DEFAULT 5,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(school_id, product_id)
    );

    CREATE TABLE IF NOT EXISTS investors (
        id SERIAL PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        capital NUMERIC(12,2) NOT NULL DEFAULT 0,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS financial_transactions (
        id SERIAL PRIMARY KEY,
        transaction_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        school_id INTEGER REFERENCES schools(id),
        transaction_type TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT,
        amount NUMERIC(12,2) NOT NULL DEFAULT 0,
        payment_method TEXT DEFAULT 'Cash',
        investor_id INTEGER REFERENCES investors(id),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS tailor_production (
        id SERIAL PRIMARY KEY,
        school_id INTEGER REFERENCES schools(id),
        product_id INTEGER REFERENCES products(id),
        product_name TEXT NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'Pending',
        tailor_name TEXT,
        cost_per_item NUMERIC(12,2) NOT NULL DEFAULT 0,
        order_date DATE NOT NULL DEFAULT CURRENT_DATE,
        due_date DATE,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(ddl)
            # Compatibility upgrades for an older database.
            upgrades = [
                "ALTER TABLE sales ADD COLUMN IF NOT EXISTS receipt_number TEXT",
                "ALTER TABLE sales ADD COLUMN IF NOT EXISTS customer_name TEXT NOT NULL DEFAULT 'Walk-in customer'",
                "ALTER TABLE sales ADD COLUMN IF NOT EXISTS customer_phone TEXT",
                "ALTER TABLE sales ADD COLUMN IF NOT EXISTS term TEXT NOT NULL DEFAULT 'Term 1'",
                "ALTER TABLE sales ADD COLUMN IF NOT EXISTS year INTEGER NOT NULL DEFAULT 2026",
                "ALTER TABLE sales ADD COLUMN IF NOT EXISTS class_name TEXT NOT NULL DEFAULT 'Not specified'",
                "ALTER TABLE sales ADD COLUMN IF NOT EXISTS subtotal NUMERIC(12,2) NOT NULL DEFAULT 0",
                "ALTER TABLE sales ADD COLUMN IF NOT EXISTS discount NUMERIC(12,2) NOT NULL DEFAULT 0",
                "ALTER TABLE sales ADD COLUMN IF NOT EXISTS total_amount NUMERIC(12,2) NOT NULL DEFAULT 0",
                "ALTER TABLE sales ADD COLUMN IF NOT EXISTS amount_paid NUMERIC(12,2) NOT NULL DEFAULT 0",
                "ALTER TABLE sales ADD COLUMN IF NOT EXISTS balance_due NUMERIC(12,2) NOT NULL DEFAULT 0",
                "ALTER TABLE sales ADD COLUMN IF NOT EXISTS payment_method TEXT NOT NULL DEFAULT 'Cash'",
                "ALTER TABLE sales ADD COLUMN IF NOT EXISTS notes TEXT",
                "ALTER TABLE sale_items ADD COLUMN IF NOT EXISTS product_name TEXT NOT NULL DEFAULT 'Item'",
                "ALTER TABLE sale_items ADD COLUMN IF NOT EXISTS quantity INTEGER NOT NULL DEFAULT 1",
                "ALTER TABLE sale_items ADD COLUMN IF NOT EXISTS unit_price NUMERIC(12,2) NOT NULL DEFAULT 0",
                "ALTER TABLE sale_items ADD COLUMN IF NOT EXISTS line_total NUMERIC(12,2) NOT NULL DEFAULT 0",
                "ALTER TABLE sale_items ADD COLUMN IF NOT EXISTS issued BOOLEAN NOT NULL DEFAULT FALSE",
                "ALTER TABLE sale_items ADD COLUMN IF NOT EXISTS issued_at TIMESTAMP",
                "ALTER TABLE sale_items ADD COLUMN IF NOT EXISTS notes TEXT",
            ]
            for statement in upgrades:
                cur.execute(statement)
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_sales_receipt_number ON sales(receipt_number) WHERE receipt_number IS NOT NULL")
            # Seed schools and default products.
            for school in DEFAULT_SCHOOLS:
                cur.execute(
                    "INSERT INTO schools(name) VALUES (%s) ON CONFLICT(name) DO NOTHING",
                    (school,)
                )
            for name, price in DEFAULT_PRODUCTS:
                cur.execute(
                    "INSERT INTO products(name, default_price) VALUES (%s, %s) "
                    "ON CONFLICT(name) DO NOTHING", (name, price)
                )
            # Seed a baseline price for each school/product; users can edit later.
            cur.execute("SELECT id FROM schools")
            school_rows = cur.fetchall()
            cur.execute("SELECT id, default_price FROM products WHERE active=TRUE")
            product_rows = cur.fetchall()
            for school_row in school_rows:
                for product_row in product_rows:
                    cur.execute(
                        """INSERT INTO school_product_prices
                           (school_id, product_id, category, class_name, term, year, price)
                           VALUES (%s, %s, 'Primary', 'All', 'All', 2026, %s)
                           ON CONFLICT(school_id, product_id, category, class_name, term, year) DO NOTHING""",
                        (school_row[0], product_row[0], product_row[1])
                    )
            cur.execute("INSERT INTO investors(name, capital) VALUES ('Gift', 150000) ON CONFLICT(name) DO NOTHING")
            cur.execute("INSERT INTO investors(name, capital) VALUES ('Ken', 100000) ON CONFLICT(name) DO NOTHING")
        conn.commit()


@st.cache_data(ttl=30)
def get_schools():
    return query_df("SELECT id, name FROM schools ORDER BY name")


@st.cache_data(ttl=30)
def get_products(active_only=True):
    where = "WHERE active=TRUE" if active_only else ""
    return query_df(f"SELECT id, name, default_price, active FROM products {where} ORDER BY name")


@st.cache_data(ttl=30)
def get_prices(school_id, category, class_name, term, year):
    sql = """
        SELECT p.id AS product_id, p.name, p.default_price,
               COALESCE((
                 SELECT spp.price FROM school_product_prices spp
                 WHERE spp.school_id=%s AND spp.product_id=p.id
                   AND spp.category=%s AND spp.class_name IN (%s, 'All')
                   AND spp.term IN (%s, 'All') AND spp.year IN (%s, 2026)
                 ORDER BY (spp.class_name=%s) DESC, (spp.term=%s) DESC,
                          (spp.year=%s) DESC
                 LIMIT 1
               ), p.default_price) AS price
        FROM products p WHERE p.active=TRUE ORDER BY p.name
    """
    return query_df(sql, [school_id, category, class_name, term, year, class_name, term, year])


def clear_caches():
    get_schools.clear()
    get_products.clear()
    get_prices.clear()


def money(value):
    try:
        return f"KSh {float(value):,.2f}"
    except (TypeError, ValueError):
        return "KSh 0.00"


def school_id_by_name(name):
    row = execute("SELECT id FROM schools WHERE name=%s", (name,), returning=True)
    return row[0] if row else None


def receipt_html(sale, items, school_name):
    logo = LOGO_PATHS.get(school_name, "")
    logo_html = ""
    if logo and os.path.exists(logo):
        import base64
        with open(logo, "rb") as logo_file:
            encoded = base64.b64encode(logo_file.read()).decode("utf-8")
        logo_html = f'<img src="data:image/png;base64,{encoded}" style="max-height:75px;max-width:140px;">'
    item_rows = ""
    for _, item in items.iterrows():
        status = "ISSUED" if bool(item["issued"]) else "NOT ISSUED"
        item_rows += (
            "<tr>"
            f"<td>{str(item['product_name'])}</td>"
            f"<td style='text-align:center'>{int(item['quantity'])}</td>"
            f"<td style='text-align:right'>{float(item['unit_price']):,.2f}</td>"
            f"<td style='text-align:right'>{float(item['line_total']):,.2f}</td>"
            f"<td>{status}</td></tr>"
        )
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
    <style>
    body{{font-family:Arial,sans-serif;color:#172033;max-width:850px;margin:20px auto;padding:20px}}
    .head{{display:flex;align-items:center;justify-content:space-between;border-bottom:2px solid #15284b;padding-bottom:12px}}
    h1{{font-size:22px;margin:0;color:#15284b}} .muted{{color:#606a7b;font-size:12px}}
    table{{width:100%;border-collapse:collapse;margin-top:18px}}th,td{{border:1px solid #d8deea;padding:9px;font-size:12px}}
    th{{background:#eef2f8;text-align:left}} .totals{{margin-left:auto;width:300px;margin-top:16px}}
    .totals div{{display:flex;justify-content:space-between;padding:5px}} .grand{{font-weight:bold;border-top:2px solid #15284b}}
    @media print{{button{{display:none}} body{{margin:0}}}}
    </style></head><body>
    <div class="head"><div>{logo_html}</div><div><h1>{school_name}</h1>
    <div class="muted">UNIFORM SALES RECEIPT</div></div><div style="text-align:right">
    <b>{sale.get('receipt_number','')}</b><br><span class="muted">{sale.get('sale_date','')}</span></div></div>
    <p><b>Customer:</b> {sale.get('customer_name','')}<br>
    <b>Phone:</b> {sale.get('customer_phone','') or '—'}<br>
    <b>Class:</b> {sale.get('class_name','')} &nbsp; <b>Term:</b> {sale.get('term','')} &nbsp; <b>Year:</b> {sale.get('year','')}</p>
    <table><thead><tr><th>Item</th><th>Qty</th><th>Unit price (KSh)</th><th>Total (KSh)</th><th>Issue status</th></tr></thead>
    <tbody>{item_rows}</tbody></table>
    <div class="totals">
    <div><span>Subtotal</span><span>{float(sale.get('subtotal',0)):,.2f}</span></div>
    <div><span>Discount</span><span>{float(sale.get('discount',0)):,.2f}</span></div>
    <div class="grand"><span>Total</span><span>{float(sale.get('total_amount',0)):,.2f}</span></div>
    <div><span>Paid</span><span>{float(sale.get('amount_paid',0)):,.2f}</span></div>
    <div><span>Balance due</span><span>{float(sale.get('balance_due',0)):,.2f}</span></div>
    </div>
    <p><b>Payment method:</b> {sale.get('payment_method','Cash')}</p>
    <p class="muted">Thank you. Keep this receipt for reference.</p>
    <button onclick="window.print()">Print receipt</button></body></html>"""


def save_sale(school_id, customer_name, customer_phone, sale_date, term, year,
              class_name, cart, discount, amount_paid, payment_method, notes):
    subtotal = round(sum(float(x["price"]) * int(x["quantity"]) for x in cart), 2)
    total = max(0, round(subtotal - float(discount), 2))
    paid = min(max(0, float(amount_paid)), total)
    balance = round(total - paid, 2)
    receipt_number = "UNI-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4].upper()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO customers(name, phone) VALUES (%s,%s) RETURNING id""",
                (customer_name.strip() or "Walk-in customer", customer_phone.strip() or None)
            )
            customer_id = cur.fetchone()[0]
            cur.execute(
                """INSERT INTO sales
                   (receipt_number, school_id, customer_id, customer_name, customer_phone,
                    sale_date, term, year, class_name, subtotal, discount, total_amount,
                    amount_paid, balance_due, payment_method, notes)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   RETURNING id""",
                (receipt_number, school_id, customer_id, customer_name.strip() or "Walk-in customer",
                 customer_phone.strip() or None, datetime.combine(sale_date, datetime.min.time()),
                 term, int(year), class_name, subtotal, float(discount), total, paid, balance,
                 payment_method, notes.strip() or None)
            )
            sale_id = cur.fetchone()[0]
            for item in cart:
                qty = int(item["quantity"])
                price = float(item["price"])
                cur.execute(
                    """INSERT INTO sale_items
                       (sale_id, product_id, product_name, quantity, unit_price, line_total, issued)
                       VALUES (%s,%s,%s,%s,%s,%s,FALSE)""",
                    (sale_id, int(item["product_id"]), item["name"], qty, price, round(qty * price, 2))
                )
            # Record sale income as a financial transaction; the full sale value is tracked,
            # while payment balance remains on the receipt.
            cur.execute(
                """INSERT INTO financial_transactions
                   (transaction_date, school_id, transaction_type, category, description, amount, payment_method)
                   VALUES (%s,%s,'Income','Uniform sales',%s,%s,%s)""",
                (datetime.combine(sale_date, datetime.min.time()), school_id,
                 f"Receipt {receipt_number}", paid, payment_method)
            )
        conn.commit()
    return sale_id, receipt_number


# -------------------------------------------------------------------
# APP INITIALIZATION
# -------------------------------------------------------------------
st.title("🧵 " + APP_TITLE)
st.caption("Sales • Receipts • Stock • Pricing • Finance • Reports")

try:
    setup_database()
except Exception as exc:
    st.error("Could not connect to or prepare the database.")
    st.code(str(exc))
    st.info("Check your Streamlit Cloud Secrets and database connection details.")
    st.stop()

schools_df = get_schools()
if schools_df.empty:
    st.error("No schools found in the database.")
    st.stop()

with st.sidebar:
    st.header("Workspace")
    school_names = schools_df["name"].tolist()
    selected_school_name = st.selectbox("School", school_names)
    selected_school_id = int(schools_df.loc[schools_df["name"] == selected_school_name, "id"].iloc[0])
    st.divider()
    page = st.radio(
        "Navigate",
        ["Dashboard", "New Sale / POS", "Receipts & Issuing", "Price Management",
         "Inventory", "Business Finance", "Sales Reports", "Tailor & Production", "Settings"],
    )
    st.divider()
    st.caption("Data is stored in PostgreSQL.")
    logo_path = LOGO_PATHS.get(selected_school_name, "")
    if logo_path and os.path.exists(logo_path):
        st.image(logo_path, use_container_width=True)

# -------------------------------------------------------------------
# DASHBOARD
# -------------------------------------------------------------------
if page == "Dashboard":
    st.subheader(f"Dashboard — {selected_school_name}")
    col1, col2, col3, col4 = st.columns(4)
    today = date.today()
    month_start = today.replace(day=1)
    metrics = query_df(
        """SELECT
            COALESCE(SUM(CASE WHEN sale_date::date=%s THEN total_amount END),0) AS today_sales,
            COALESCE(SUM(CASE WHEN sale_date::date >= %s THEN total_amount END),0) AS month_sales,
            COALESCE(SUM(CASE WHEN sale_date::date >= %s THEN amount_paid END),0) AS month_paid,
            COALESCE(SUM(CASE WHEN sale_date::date >= %s THEN balance_due END),0) AS outstanding
           FROM sales WHERE school_id=%s""",
        [today, month_start, month_start, month_start, selected_school_id]
    ).iloc[0]
    total_sales = query_df("SELECT COALESCE(SUM(total_amount),0) AS total FROM sales WHERE school_id=%s",
                           [selected_school_id]).iloc[0]["total"]
    col1.metric("Sales today", money(metrics["today_sales"]))
    col2.metric("Sales this month", money(metrics["month_sales"]))
    col3.metric("Collected this month", money(metrics["month_paid"]))
    col4.metric("Outstanding balance", money(metrics["outstanding"]))
    st.divider()
    left, right = st.columns(2)
    with left:
        st.markdown("#### Sales trend (last 30 days)")
        trend = query_df(
            """SELECT sale_date::date AS day, SUM(total_amount) AS sales
               FROM sales WHERE school_id=%s AND sale_date >= CURRENT_DATE - INTERVAL '29 days'
               GROUP BY sale_date::date ORDER BY day""", [selected_school_id])
        if not trend.empty:
            st.line_chart(trend.set_index("day")["sales"])
        else:
            st.info("Sales will appear here after the first transaction.")
    with right:
        st.markdown("#### Best-selling products")
        top = query_df(
            """SELECT si.product_name, SUM(si.quantity) AS units, SUM(si.line_total) AS revenue
               FROM sale_items si JOIN sales s ON s.id=si.sale_id
               WHERE s.school_id=%s GROUP BY si.product_name ORDER BY units DESC LIMIT 8""",
            [selected_school_id])
        if not top.empty:
            st.bar_chart(top.set_index("product_name")["units"])
            st.dataframe(top, use_container_width=True, hide_index=True)
        else:
            st.info("No product sales recorded yet.")
    st.markdown("#### Recent sales")
    recent = query_df(
        """SELECT s.receipt_number, s.sale_date, s.customer_name, s.class_name,
                  s.total_amount, s.amount_paid, s.balance_due
           FROM sales s WHERE s.school_id=%s ORDER BY s.sale_date DESC LIMIT 10""",
        [selected_school_id])
    if recent.empty:
        st.info("No sales recorded yet.")
    else:
        st.dataframe(recent, use_container_width=True, hide_index=True)
    st.caption(f"All-time recorded sales: {money(total_sales)}")

# -------------------------------------------------------------------
# POINT OF SALE
# -------------------------------------------------------------------
elif page == "New Sale / POS":
    st.subheader("New sale")
    st.write("Add several uniform items to one receipt. Prices can be adjusted in Price Management.")
    with st.form("sale_header"):
        c1, c2, c3 = st.columns(3)
        customer_name = c1.text_input("Customer / parent name", placeholder="Customer name")
        customer_phone = c2.text_input("Phone number", placeholder="07xx xxx xxx")
        sale_date = c3.date_input("Sale date", value=date.today())
        c4, c5, c6 = st.columns(3)
        class_name = c4.text_input("Class / grade", value="Not specified")
        term = c5.selectbox("Term", ["Term 1", "Term 2", "Term 3"])
        year = c6.number_input("Year", min_value=2020, max_value=2100, value=date.today().year, step=1)
        category = st.selectbox("Price category", ["Primary", "JSS", "Other"])
        notes = st.text_input("Notes (optional)")
        submitted_header = st.form_submit_button("Use these sale details")
    if submitted_header:
        st.session_state["sale_header_data"] = {
            "customer_name": customer_name, "customer_phone": customer_phone,
            "sale_date": sale_date, "class_name": class_name, "term": term,
            "year": int(year), "category": category, "notes": notes
        }
    header = st.session_state.get("sale_header_data", {
        "customer_name": "", "customer_phone": "", "sale_date": date.today(),
        "class_name": "Not specified", "term": "Term 1", "year": date.today().year,
        "category": "Primary", "notes": ""
    })
    st.caption(f"Current cart category: {header['category']} · Class: {header['class_name']} · {header['term']} {header['year']}")
    price_df = get_prices(selected_school_id, header["category"], header["class_name"],
                          header["term"], header["year"])
    if price_df.empty:
        st.warning("No active products are available. Add products in Settings.")
    else:
        names = price_df["name"].tolist()
        with st.form("add_to_cart"):
            a, b, c = st.columns([3, 1, 1])
            chosen_name = a.selectbox("Uniform item", names)
            selected_row = price_df.loc[price_df["name"] == chosen_name].iloc[0]
            unit_price = b.number_input("Unit price (KSh)", min_value=0.0,
                                        value=float(selected_row["price"]), step=50.0)
            quantity = c.number_input("Quantity", min_value=1, max_value=500, value=1, step=1)
            add_item = st.form_submit_button("Add item to cart")
        if add_item:
            cart = st.session_state.get("uniform_cart", [])
            found = next((x for x in cart if x["product_id"] == int(selected_row["product_id"]) and x["price"] == float(unit_price)), None)
            if found:
                found["quantity"] += int(quantity)
            else:
                cart.append({
                    "product_id": int(selected_row["product_id"]), "name": chosen_name,
                    "price": float(unit_price), "quantity": int(quantity)
                })
            st.session_state["uniform_cart"] = cart
            st.success(f"Added {quantity} × {chosen_name}.")
    cart = st.session_state.get("uniform_cart", [])
    st.markdown("#### Current cart")
    if not cart:
        st.info("Your cart is empty. Add an item above.")
    else:
        cart_df = pd.DataFrame(cart)
        cart_df["line_total"] = cart_df["price"] * cart_df["quantity"]
        st.dataframe(cart_df.rename(columns={
            "name": "Item", "price": "Unit price", "quantity": "Quantity", "line_total": "Line total"
        }), use_container_width=True, hide_index=True)
        subtotal = float(cart_df["line_total"].sum())
        d1, d2, d3 = st.columns(3)
        d1.metric("Subtotal", money(subtotal))
        discount = d2.number_input("Discount (KSh)", min_value=0.0, max_value=subtotal,
                                   value=0.0, step=50.0, key="sale_discount")
        total = max(0, subtotal - discount)
        d3.metric("Total due", money(total))
        amount_paid = st.number_input("Amount paid now (KSh)", min_value=0.0,
                                      max_value=float(total), value=float(total), step=100.0,
                                      key="sale_paid")
        payment_method = st.selectbox("Payment method", ["Cash", "M-Pesa", "Bank", "Card", "Other"])
        p1, p2 = st.columns(2)
        if p1.button("Complete sale and save receipt", type="primary", use_container_width=True):
            if not header["customer_name"].strip():
                st.error("Enter the customer or parent name in the sale details above.")
            else:
                try:
                    sale_id, receipt_no = save_sale(
                        selected_school_id, header["customer_name"], header["customer_phone"],
                        header["sale_date"], header["term"], header["year"], header["class_name"],
                        cart, discount, amount_paid, payment_method, header["notes"]
                    )
                    st.session_state["last_sale_id"] = sale_id
                    st.session_state["last_receipt_no"] = receipt_no
                    st.session_state["uniform_cart"] = []
                    st.session_state.pop("sale_discount", None)
                    st.session_state.pop("sale_paid", None)
                    clear_caches()
                    st.success(f"Sale saved successfully. Receipt: {receipt_no}")
                    st.rerun()
                except Exception as exc:
                    st.error("The sale could not be saved.")
                    st.code(str(exc))
        if p2.button("Clear cart", use_container_width=True):
            st.session_state["uniform_cart"] = []
            st.rerun()
    if st.session_state.get("last_receipt_no"):
        st.success(f"Last saved receipt: {st.session_state['last_receipt_no']}. Open Receipts & Issuing to print it.")

# -------------------------------------------------------------------
# RECEIPTS AND ISSUING
# -------------------------------------------------------------------
elif page == "Receipts & Issuing":
    st.subheader("Receipts & uniform issuing")
    search = st.text_input("Search by receipt number, customer, or phone")
    params = [selected_school_id]
    sql = """SELECT id, receipt_number, sale_date, customer_name, customer_phone,
                    class_name, term, year, total_amount, amount_paid, balance_due
             FROM sales WHERE school_id=%s"""
    if search.strip():
        sql += " AND (COALESCE(receipt_number,'') ILIKE %s OR customer_name ILIKE %s OR COALESCE(customer_phone,'') ILIKE %s)"
        params += [f"%{search.strip()}%"] * 3
    sql += " ORDER BY sale_date DESC LIMIT 100"
    sales_df = query_df(sql, params)
    if sales_df.empty:
        st.info("No matching receipts.")
    else:
        st.dataframe(sales_df.drop(columns=["id"]), use_container_width=True, hide_index=True)
        options = {f"{r['receipt_number']} — {r['customer_name']} — {money(r['total_amount'])}": int(r["id"])
                   for _, r in sales_df.iterrows()}
        selected_label = st.selectbox("Open receipt", list(options.keys()))
        sale_id = options[selected_label]
        sale_df = query_df(
            """SELECT s.*, sc.name AS school_name FROM sales s
               LEFT JOIN schools sc ON sc.id=s.school_id WHERE s.id=%s""", [sale_id])
        items = query_df(
            """SELECT id, product_name, quantity, unit_price, line_total, issued, issued_at, notes
               FROM sale_items WHERE sale_id=%s ORDER BY id""", [sale_id])
        sale = sale_df.iloc[0].to_dict()
        st.markdown("#### Items and issuing status")
        edited_items = st.data_editor(
            items[["id", "product_name", "quantity", "unit_price", "line_total", "issued", "notes"]],
            use_container_width=True, hide_index=True, disabled=["id", "product_name", "quantity", "unit_price", "line_total"],
            column_config={
                "issued": st.column_config.CheckboxColumn("Issued to customer"),
                "notes": st.column_config.TextColumn("Issue notes")
            },
            key=f"issue_editor_{sale_id}"
        )
        if st.button("Save issuing updates", type="primary"):
            with get_connection() as conn:
                with conn.cursor() as cur:
                    for _, item in edited_items.iterrows():
                        cur.execute(
                            """UPDATE sale_items SET issued=%s, issued_at=CASE
                               WHEN %s=TRUE AND issued_at IS NULL THEN CURRENT_TIMESTAMP
                               WHEN %s=FALSE THEN NULL ELSE issued_at END,
                               notes=%s WHERE id=%s AND sale_id=%s""",
                            (bool(item["issued"]), bool(item["issued"]), bool(item["issued"]),
                             item["notes"] if pd.notna(item["notes"]) else None, int(item["id"]), sale_id)
                        )
                conn.commit()
            st.success("Issuing status updated.")
            st.rerun()
        st.markdown("#### Receipt")
        html = receipt_html(sale, items, sale.get("school_name") or selected_school_name)
        st.components.v1.html(html, height=640, scrolling=True)
        st.download_button("Download receipt as HTML", data=html,
                           file_name=f"{sale.get('receipt_number','receipt')}.html",
                           mime="text/html")

# -------------------------------------------------------------------
# PRICE MANAGEMENT
# -------------------------------------------------------------------
elif page == "Price Management":
    st.subheader("Price management")
    st.write("Set school-specific prices by category, class, term and year. Use class `All` and term `All` as defaults.")
    product_df = get_products()
    with st.form("price_form"):
        c1, c2, c3 = st.columns(3)
        product_name = c1.selectbox("Product", product_df["name"].tolist())
        category = c2.selectbox("Category", ["Primary", "JSS", "Other"])
        class_value = c3.text_input("Class (or All)", value="All")
        c4, c5, c6 = st.columns(3)
        term_value = c4.selectbox("Term (or All)", ["All", "Term 1", "Term 2", "Term 3"])
        year_value = c5.number_input("Year", min_value=2020, max_value=2100, value=date.today().year, step=1)
        current_default = float(product_df.loc[product_df["name"] == product_name, "default_price"].iloc[0])
        price_value = c6.number_input("Price (KSh)", min_value=0.0, value=current_default, step=50.0)
        update_price = st.form_submit_button("Save price")
    if update_price:
        pid = int(product_df.loc[product_df["name"] == product_name, "id"].iloc[0])
        execute(
            """INSERT INTO school_product_prices(school_id,product_id,category,class_name,term,year,price)
               VALUES (%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT(school_id,product_id,category,class_name,term,year)
               DO UPDATE SET price=EXCLUDED.price""",
            (selected_school_id, pid, category, class_value.strip() or "All",
             term_value, int(year_value), float(price_value))
        )
        clear_caches()
        st.success("Price saved.")
    prices = query_df(
        """SELECT p.name AS product, spp.category, spp.class_name, spp.term, spp.year, spp.price
           FROM school_product_prices spp JOIN products p ON p.id=spp.product_id
           WHERE spp.school_id=%s ORDER BY p.name, spp.category, spp.class_name, spp.term, spp.year""",
        [selected_school_id])
    st.markdown("#### Existing prices")
    st.dataframe(prices, use_container_width=True, hide_index=True)
    st.download_button("Download price list CSV", prices.to_csv(index=False),
                       file_name=f"{selected_school_name.lower().replace(' ','_')}_prices.csv",
                       mime="text/csv")

# -------------------------------------------------------------------
# INVENTORY
# -------------------------------------------------------------------
elif page == "Inventory":
    st.subheader("Inventory")
    products_df = get_products()
    with st.form("stock_form"):
        c1, c2, c3 = st.columns(3)
        stock_product = c1.selectbox("Product", products_df["name"].tolist())
        quantity_on_hand = c2.number_input("Quantity on hand", min_value=0, max_value=100000, value=0, step=1)
        reorder_level = c3.number_input("Reorder alert level", min_value=0, max_value=100000, value=5, step=1)
        save_stock = st.form_submit_button("Save stock level")
    if save_stock:
        product_id = int(products_df.loc[products_df["name"] == stock_product, "id"].iloc[0])
        execute(
            """INSERT INTO stock(school_id,product_id,quantity,reorder_level,updated_at)
               VALUES (%s,%s,%s,%s,CURRENT_TIMESTAMP)
               ON CONFLICT(school_id,product_id)
               DO UPDATE SET quantity=EXCLUDED.quantity,reorder_level=EXCLUDED.reorder_level,updated_at=CURRENT_TIMESTAMP""",
            (selected_school_id, product_id, int(quantity_on_hand), int(reorder_level))
        )
        st.success("Stock level saved.")
    stock_df = query_df(
        """SELECT p.name AS product, COALESCE(st.quantity,0) AS quantity_on_hand,
                  COALESCE(st.reorder_level,5) AS reorder_level,
                  COALESCE(SUM(CASE WHEN si.issued=FALSE THEN si.quantity ELSE 0 END),0) AS sold_not_issued,
                  COALESCE(st.quantity,0)-COALESCE(SUM(CASE WHEN si.issued=TRUE THEN si.quantity ELSE 0 END),0) AS indicative_available
           FROM products p
           LEFT JOIN stock st ON st.product_id=p.id AND st.school_id=%s
           LEFT JOIN sale_items si ON si.product_id=p.id
           LEFT JOIN sales s ON s.id=si.sale_id AND s.school_id=%s
           WHERE p.active=TRUE GROUP BY p.name,st.quantity,st.reorder_level ORDER BY p.name""",
        [selected_school_id, selected_school_id])
    if not stock_df.empty:
        stock_df["status"] = stock_df.apply(lambda r: "LOW STOCK" if r["quantity_on_hand"] <= r["reorder_level"] else "OK", axis=1)
        st.dataframe(stock_df, use_container_width=True, hide_index=True)
        low = stock_df[stock_df["status"] == "LOW STOCK"]
        if not low.empty:
            st.warning("Low stock items: " + ", ".join(low["product"].tolist()))
    st.caption("Stock quantities are manually maintained. Sales do not automatically deduct stock; use the issue status and stock records together.")

# -------------------------------------------------------------------
# BUSINESS FINANCE
# -------------------------------------------------------------------
elif page == "Business Finance":
    st.subheader("Business finance")
    tab1, tab2, tab3 = st.tabs(["Record transaction", "Transactions", "Investors"])
    with tab1:
        with st.form("finance_form"):
            c1, c2, c3 = st.columns(3)
            trans_type = c1.selectbox("Type", ["Expense", "Income", "Capital contribution", "Withdrawal"])
            trans_category = c2.selectbox("Category", ["Rent", "Salaries", "Transport", "Materials", "Tailoring",
                                                       "Utilities", "Uniform sales", "Capital", "Loan", "Other"])
            trans_amount = c3.number_input("Amount (KSh)", min_value=0.0, value=0.0, step=100.0)
            trans_desc = st.text_input("Description")
            c4, c5 = st.columns(2)
            trans_date = c4.date_input("Transaction date", value=date.today())
            trans_method = c5.selectbox("Payment method", ["Cash", "M-Pesa", "Bank", "Card", "Other"])
            record_trans = st.form_submit_button("Record transaction")
        if record_trans:
            if trans_amount <= 0:
                st.error("Enter an amount greater than zero.")
            else:
                execute(
                    """INSERT INTO financial_transactions
                       (transaction_date,school_id,transaction_type,category,description,amount,payment_method)
                       VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                    (datetime.combine(trans_date, datetime.min.time()), selected_school_id,
                     trans_type, trans_category, trans_desc, float(trans_amount), trans_method)
                )
                st.success("Transaction recorded.")
    with tab2:
        transactions = query_df(
            """SELECT transaction_date,transaction_type,category,description,amount,payment_method
               FROM financial_transactions WHERE school_id=%s ORDER BY transaction_date DESC LIMIT 500""",
            [selected_school_id])
        if transactions.empty:
            st.info("No transactions yet.")
        else:
            st.dataframe(transactions, use_container_width=True, hide_index=True)
            st.download_button("Download transactions CSV", transactions.to_csv(index=False),
                               file_name="financial_transactions.csv", mime="text/csv")
    with tab3:
        investors = query_df("SELECT id,name,capital,notes FROM investors ORDER BY name")
        st.dataframe(investors, use_container_width=True, hide_index=True)
        with st.form("investor_form"):
            inv_name = st.text_input("Investor name")
            inv_capital = st.number_input("Capital invested (KSh)", min_value=0.0, value=0.0, step=1000.0)
            inv_notes = st.text_input("Notes")
            save_investor = st.form_submit_button("Add / update investor")
        if save_investor:
            if not inv_name.strip():
                st.error("Enter an investor name.")
            else:
                execute(
                    """INSERT INTO investors(name,capital,notes) VALUES (%s,%s,%s)
                       ON CONFLICT(name) DO UPDATE SET capital=investors.capital+EXCLUDED.capital,
                       notes=COALESCE(EXCLUDED.notes,investors.notes)""",
                    (inv_name.strip(), float(inv_capital), inv_notes.strip() or None)
                )
                st.success("Investor saved.")

# -------------------------------------------------------------------
# REPORTS
# -------------------------------------------------------------------
elif page == "Sales Reports":
    st.subheader("Sales reports")
    c1, c2 = st.columns(2)
    start_date = c1.date_input("From", value=date.today().replace(day=1), key="report_from")
    end_date = c2.date_input("To", value=date.today(), key="report_to")
    if start_date > end_date:
        st.error("The start date must be on or before the end date.")
    else:
        report = query_df(
            """SELECT s.receipt_number,s.sale_date,s.customer_name,s.customer_phone,s.class_name,
                      s.term,s.year,s.subtotal,s.discount,s.total_amount,s.amount_paid,s.balance_due,
                      s.payment_method
               FROM sales s WHERE s.school_id=%s AND s.sale_date::date BETWEEN %s AND %s
               ORDER BY s.sale_date DESC""",
            [selected_school_id, start_date, end_date])
        total = float(report["total_amount"].sum()) if not report.empty else 0
        paid = float(report["amount_paid"].sum()) if not report.empty else 0
        outstanding = float(report["balance_due"].sum()) if not report.empty else 0
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Receipts", len(report))
        c2.metric("Sales", money(total))
        c3.metric("Collected", money(paid))
        c4.metric("Outstanding", money(outstanding))
        st.dataframe(report, use_container_width=True, hide_index=True)
        st.download_button("Download sales report CSV", report.to_csv(index=False),
                           file_name="sales_report.csv", mime="text/csv")
        item_report = query_df(
            """SELECT si.product_name,SUM(si.quantity) AS units,SUM(si.line_total) AS revenue
               FROM sale_items si JOIN sales s ON s.id=si.sale_id
               WHERE s.school_id=%s AND s.sale_date::date BETWEEN %s AND %s
               GROUP BY si.product_name ORDER BY revenue DESC""",
            [selected_school_id, start_date, end_date])
        st.markdown("#### Product performance")
        if not item_report.empty:
            st.dataframe(item_report, use_container_width=True, hide_index=True)
            st.bar_chart(item_report.set_index("product_name")["revenue"])
        else:
            st.info("No sales for this period.")

# -------------------------------------------------------------------
# TAILOR / PRODUCTION
# -------------------------------------------------------------------
elif page == "Tailor & Production":
    st.subheader("Tailor and production tracking")
    products_df = get_products()
    with st.form("production_form"):
        c1, c2, c3 = st.columns(3)
        prod_name = c1.selectbox("Product", products_df["name"].tolist())
        prod_qty = c2.number_input("Quantity ordered", min_value=1, max_value=100000, value=1)
        tailor_name = c3.text_input("Tailor / supplier")
        c4, c5, c6 = st.columns(3)
        prod_status = c4.selectbox("Status", ["Pending", "In progress", "Completed", "Collected", "Cancelled"])
        cost_item = c5.number_input("Cost per item (KSh)", min_value=0.0, value=0.0, step=50.0)
        due_date = c6.date_input("Expected date", value=date.today() + timedelta(days=7))
        prod_notes = st.text_input("Production notes")
        add_prod = st.form_submit_button("Save production order")
    if add_prod:
        pid = int(products_df.loc[products_df["name"] == prod_name, "id"].iloc[0])
        execute(
            """INSERT INTO tailor_production
               (school_id,product_id,product_name,quantity,status,tailor_name,cost_per_item,due_date,notes)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (selected_school_id, pid, prod_name, int(prod_qty), prod_status, tailor_name,
             float(cost_item), due_date, prod_notes)
        )
        st.success("Production order saved.")
    production = query_df(
        """SELECT id,product_name,quantity,status,tailor_name,cost_per_item,order_date,due_date,notes
           FROM tailor_production WHERE school_id=%s ORDER BY created_at DESC LIMIT 300""",
        [selected_school_id])
    if not production.empty:
        st.dataframe(production, use_container_width=True, hide_index=True)
        st.caption("To change an existing production status, use the update controls below.")
        prod_ids = production["id"].astype(int).tolist()
        chosen_prod_id = st.selectbox("Production order ID", prod_ids)
        new_status = st.selectbox("Update status", ["Pending", "In progress", "Completed", "Collected", "Cancelled"], key="production_status")
        if st.button("Update production status"):
            execute("UPDATE tailor_production SET status=%s WHERE id=%s AND school_id=%s",
                    (new_status, int(chosen_prod_id), selected_school_id))
            st.success("Production status updated.")
            st.rerun()
    else:
        st.info("No production orders yet.")

# -------------------------------------------------------------------
# SETTINGS
# -------------------------------------------------------------------
elif page == "Settings":
    st.subheader("Settings and product catalogue")
    st.markdown("#### Add a school")
    with st.form("school_form"):
        new_school = st.text_input("School name")
        add_school = st.form_submit_button("Add school")
    if add_school:
        if not new_school.strip():
            st.error("Enter a school name.")
        else:
            try:
                execute("INSERT INTO schools(name) VALUES (%s) ON CONFLICT(name) DO NOTHING", (new_school.strip().upper(),))
                clear_caches()
                st.success("School saved.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    st.divider()
    st.markdown("#### Add a product")
    with st.form("product_form"):
        new_product = st.text_input("Product name")
        new_price = st.number_input("Default price (KSh)", min_value=0.0, value=0.0, step=50.0)
        add_product = st.form_submit_button("Add product")
    if add_product:
        if not new_product.strip():
            st.error("Enter a product name.")
        else:
            try:
                execute("INSERT INTO products(name,default_price) VALUES (%s,%s) ON CONFLICT(name) DO NOTHING",
                        (new_product.strip(), float(new_price)))
                pid_row = execute("SELECT id FROM products WHERE name=%s", (new_product.strip(),), returning=True)
                if pid_row:
                    execute(
                        """INSERT INTO school_product_prices(school_id,product_id,category,class_name,term,year,price)
                           VALUES (%s,%s,'Primary','All','All',%s,%s)
                           ON CONFLICT(school_id,product_id,category,class_name,term,year) DO NOTHING""",
                        (selected_school_id, pid_row[0], date.today().year, float(new_price))
                    )
                clear_caches()
                st.success("Product saved.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    st.divider()
    st.markdown("#### Product catalogue")
    products = query_df("SELECT id,name,default_price,active,created_at FROM products ORDER BY name")
    st.dataframe(products, use_container_width=True, hide_index=True)
    st.caption("This app creates missing tables and adds compatible columns. It does not drop your existing sales data.")
    st.warning("Before major database changes, keep a backup of your PostgreSQL database.")
'''
path = "/mnt/data/uniforms.py"
with open(path, "w", encoding="utf-8") as f:
    f.write(code)
# Validate syntax before exposing the file.
compile(code, path, "exec")

requirements = """streamlit>=1.40
pandas>=2.0
psycopg2-binary>=2.9
"""
with open("/mnt/data/requirements.txt", "w", encoding="utf-8") as f:
    f.write(requirements)

print("Created and syntax-checked uniforms.py and requirements.txt.")
