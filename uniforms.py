import os, textwrap

code = r'''import os
from datetime import date, datetime
from decimal import Decimal

import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import streamlit as st
import streamlit.components.v1 as components

# ============================================================
# UNIFORM SALES & BUSINESS MANAGER
# Existing PostgreSQL database: uniforms_sales
# ============================================================

st.set_page_config(
    page_title="Uniforms | Business Manager",
    page_icon="🧵",
    layout="wide",
    initial_sidebar_state="expanded",
)

NAVY = "#142B4A"
BLUE = "#2364AA"
PALE = "#F3F7FC"
ORANGE = "#F28C28"
GREEN = "#16845B"
RED = "#C23B3B"

st.markdown(
    f"""
    <style>
    .stApp {{ background: {PALE}; }}
    [data-testid="stSidebar"] {{ background: {NAVY}; }}
    [data-testid="stSidebar"] * {{ color: white !important; }}
    .block-container {{ padding-top: 1.5rem; padding-bottom: 2.5rem; }}
    div[data-testid="stMetric"] {{
        background: white; border: 1px solid #E1E8F0;
        padding: 16px 18px; border-radius: 14px;
        box-shadow: 0 2px 8px rgba(20,43,74,.04);
    }}
    div.stButton > button[kind="primary"] {{
        background: {BLUE}; border: 0; border-radius: 9px;
        color: white; font-weight: 600;
    }}
    .hero {{
        background: linear-gradient(110deg, {NAVY}, {BLUE});
        padding: 24px 28px; border-radius: 16px; color: white;
        margin-bottom: 18px;
    }}
    .hero h1 {{ color: white; margin: 0; }}
    .hero p {{ color: #E4EDF8; margin-bottom: 0; }}
    .small-muted {{ color: #65758B; font-size: .9rem; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------- DATABASE CONNECTION --------------------

def get_connection():
    """Uses Streamlit secrets first, then environment variables, then local defaults."""
    cfg = {}
    try:
        cfg = dict(st.secrets.get("postgres", {}))
    except Exception:
        cfg = {}

    params = {
        "host": cfg.get("host", os.getenv("PGHOST", "127.0.0.1")),
        "port": int(cfg.get("port", os.getenv("PGPORT", "5432"))),
        "dbname": cfg.get("database", cfg.get("dbname", os.getenv("PGDATABASE", "uniforms_sales"))),
        "user": cfg.get("user", os.getenv("PGUSER", "postgres")),
        "password": cfg.get("password", os.getenv("PGPASSWORD", "")),
    }
    sslmode = cfg.get("sslmode", os.getenv("PGSSLMODE", "prefer"))
    if sslmode:
        params["sslmode"] = sslmode
    return psycopg2.connect(**params)


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


def table_columns(cur, table):
    cur.execute(
        """SELECT column_name FROM information_schema.columns
           WHERE table_schema='public' AND table_name=%s""",
        (table,),
    )
    return {r[0] for r in cur.fetchall()}


def setup_database():
    """Create missing tables and safely add new columns without dropping existing data."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS schools (
                    id SERIAL PRIMARY KEY,
                    school_name TEXT UNIQUE NOT NULL
                );
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    product_name TEXT UNIQUE NOT NULL,
                    category TEXT DEFAULT 'Uniform'
                );
                CREATE TABLE IF NOT EXISTS customers (
                    id SERIAL PRIMARY KEY,
                    customer_name TEXT NOT NULL,
                    phone TEXT
                );
                CREATE TABLE IF NOT EXISTS sales (
                    id SERIAL PRIMARY KEY,
                    sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    school_id INTEGER REFERENCES schools(id),
                    customer_id INTEGER REFERENCES customers(id),
                    total_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
                    payment_method TEXT DEFAULT 'Cash',
                    payment_status TEXT DEFAULT 'Unpaid',
                    term TEXT DEFAULT 'Term 1',
                    year INTEGER DEFAULT EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER
                );
                CREATE TABLE IF NOT EXISTS sale_items (
                    id SERIAL PRIMARY KEY,
                    sale_id INTEGER REFERENCES sales(id) ON DELETE CASCADE,
                    product_id INTEGER REFERENCES products(id),
                    quantity INTEGER NOT NULL DEFAULT 1,
                    unit_price NUMERIC(12,2) NOT NULL DEFAULT 0,
                    line_total NUMERIC(12,2) NOT NULL DEFAULT 0,
                    issued BOOLEAN DEFAULT FALSE
                );
                CREATE TABLE IF NOT EXISTS school_product_prices (
                    id SERIAL PRIMARY KEY,
                    school_id INTEGER REFERENCES schools(id) ON DELETE CASCADE,
                    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
                    price NUMERIC(12,2) NOT NULL DEFAULT 0,
                    category TEXT DEFAULT 'Primary',
                    UNIQUE(school_id, product_id, category)
                );
                CREATE TABLE IF NOT EXISTS stock (
                    id SERIAL PRIMARY KEY,
                    school_id INTEGER REFERENCES schools(id),
                    product_id INTEGER REFERENCES products(id),
                    quantity_brought INTEGER NOT NULL DEFAULT 0,
                    term TEXT DEFAULT 'Term 1',
                    year INTEGER DEFAULT EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER,
                    unit_cost NUMERIC(12,2) DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS financial_transactions (
                    id SERIAL PRIMARY KEY,
                    transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    transaction_type TEXT NOT NULL DEFAULT 'Expense',
                    category TEXT DEFAULT 'General',
                    amount NUMERIC(12,2) NOT NULL DEFAULT 0,
                    description TEXT,
                    school_id INTEGER REFERENCES schools(id),
                    investor_name TEXT
                );
                CREATE TABLE IF NOT EXISTS investors (
                    id SERIAL PRIMARY KEY,
                    investor_name TEXT UNIQUE NOT NULL
                );
                CREATE TABLE IF NOT EXISTS tailor_production (
                    id SERIAL PRIMARY KEY,
                    production_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    school_id INTEGER REFERENCES schools(id),
                    product_id INTEGER REFERENCES products(id),
                    quantity INTEGER NOT NULL DEFAULT 0,
                    cost_per_item NUMERIC(12,2) DEFAULT 0,
                    total_cost NUMERIC(12,2) DEFAULT 0,
                    tailor_name TEXT,
                    notes TEXT,
                    term TEXT DEFAULT 'Term 1',
                    year INTEGER DEFAULT EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER
                );
            """)

            # Safe migrations for existing installations.
            migrations = {
                "sales": [
                    ("amount_paid", "NUMERIC(12,2) NOT NULL DEFAULT 0"),
                    ("balance_due", "NUMERIC(12,2) NOT NULL DEFAULT 0"),
                    ("receipt_number", "TEXT"),
                    ("class_name", "TEXT"),
                ],
                "sale_items": [
                    ("issued", "BOOLEAN DEFAULT FALSE"),
                ],
                "products": [
                    ("category", "TEXT DEFAULT 'Uniform'"),
                ],
                "school_product_prices": [
                    ("category", "TEXT DEFAULT 'Primary'"),
                ],
                "stock": [
                    ("unit_cost", "NUMERIC(12,2) DEFAULT 0"),
                    ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
                ],
                "financial_transactions": [
                    ("transaction_date", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
                    ("transaction_type", "TEXT DEFAULT 'Expense'"),
                    ("category", "TEXT DEFAULT 'General'"),
                    ("description", "TEXT"),
                    ("school_id", "INTEGER"),
                    ("investor_name", "TEXT"),
                ],
                "tailor_production": [
                    ("production_date", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
                    ("cost_per_item", "NUMERIC(12,2) DEFAULT 0"),
                    ("total_cost", "NUMERIC(12,2) DEFAULT 0"),
                    ("tailor_name", "TEXT"),
                    ("notes", "TEXT"),
                    ("term", "TEXT DEFAULT 'Term 1'"),
                    ("year", "INTEGER DEFAULT EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER"),
                ],
            }
            for table, cols in migrations.items():
                existing = table_columns(cur, table)
                for col, definition in cols:
                    if col not in existing:
                        cur.execute(f'ALTER TABLE "{table}" ADD COLUMN "{col}" {definition}')

            # Make sure receipt numbers are unique when present.
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS sales_receipt_number_uq ON sales(receipt_number) WHERE receipt_number IS NOT NULL")

            cur.execute("""
                INSERT INTO schools (school_name) VALUES
                ('LOVING BLOOMS SCHOOL'), ('WARIDI UTAWALA SCHOOL')
                ON CONFLICT (school_name) DO NOTHING
            """)

            defaults = [
                ("Skirt", "Uniform", 650),
                ("Blouse", "Uniform", 500),
                ("Socks", "Accessories", 200),
                ("Tracksuit Playgroup-PP2", "Sportswear", 1600),
                ("Tracksuit G1-G6", "Sportswear", 1800),
                ("Sweater", "Uniform", 1000),
                ("Tie / Bow Tie", "Accessories", 150),
                ("Short", "Uniform", 400),
                ("Halfcoat", "Uniform", 600),
                ("Fleece", "Outerwear", 2500),
                ("Trouser", "Uniform", 650),
                ("T-Shirt", "Sportswear", 500),
                ("Wrap Skirt", "Uniform", 500),
                ("Half Sweater", "Uniform", 800),
            ]
            for name, category, price in defaults:
                cur.execute(
                    """INSERT INTO products(product_name, category) VALUES (%s,%s)
                       ON CONFLICT (product_name) DO NOTHING""",
                    (name, category),
                )

            # Add default price records only where a matching school/product/category
            # price does not already exist. Existing custom prices are not overwritten.
            cur.execute("SELECT id FROM schools")
            school_ids = [r[0] for r in cur.fetchall()]
            cur.execute("SELECT id, product_name FROM products")
            products = cur.fetchall()
            for sid in school_ids:
                for pid, pname in products:
                    if pname == "Skirt":
                        price = 700 if sid == 2 else 650
                    elif pname == "Blouse":
                        price = 700 if sid == 2 else 500
                    elif pname == "Tracksuit G1-G6":
                        price = 1800
                    elif pname == "Tracksuit Playgroup-PP2":
                        price = 1600
                    elif pname == "Half Sweater":
                        price = 800
                    elif pname == "Sweater":
                        price = 1000
                    elif pname == "Wrap Skirt":
                        price = 500
                    else:
                        price = next((p[2] for p in defaults if p[0] == pname), 500)
                    cur.execute(
                        """INSERT INTO school_product_prices(school_id, product_id, price, category)
                           VALUES (%s,%s,%s,'Primary')
                           ON CONFLICT DO NOTHING""",
                        (sid, pid, price),
                    )
        conn.commit()


# -------------------- HELPERS --------------------

def money(value):
    try:
        return f"KSh {float(value or 0):,.2f}"
    except (TypeError, ValueError):
        return "KSh 0.00"


def get_schools():
    return query_df("SELECT id, school_name FROM schools ORDER BY school_name")


def get_products_for_school(school_id, category):
    return query_df(
        """SELECT p.id, p.product_name, p.category, spp.price
           FROM school_product_prices spp
           JOIN products p ON p.id=spp.product_id
           WHERE spp.school_id=%s AND COALESCE(spp.category,'Primary')=%s
           ORDER BY p.product_name""",
        (int(school_id), category),
    )


def current_stock(school_id, product_id, term=None, year=None):
    sql = """
        SELECT
          COALESCE((SELECT SUM(quantity_brought) FROM stock
                    WHERE school_id=%s AND product_id=%s),0)
          + COALESCE((SELECT SUM(quantity) FROM tailor_production
                      WHERE school_id=%s AND product_id=%s),0)
          - COALESCE((SELECT SUM(si.quantity) FROM sale_items si
                      JOIN sales s ON s.id=si.sale_id
                      WHERE s.school_id=%s AND si.product_id=%s),0) AS qty
    """
    row = execute(sql, (school_id, product_id, school_id, product_id, school_id, product_id), True)
    return int(row[0] or 0)


def refresh_data():
    for key in ("cart", "last_receipt"):
        if key not in st.session_state:
            st.session_state[key] = [] if key == "cart" else None


def get_receipt(sale_id):
    sales = query_df(
        """SELECT s.*, sc.school_name, c.customer_name, c.phone
           FROM sales s
           JOIN schools sc ON sc.id=s.school_id
           LEFT JOIN customers c ON c.id=s.customer_id
           WHERE s.id=%s""",
        (int(sale_id),),
    )
    if sales.empty:
        return None, pd.DataFrame()
    items = query_df(
        """SELECT p.product_name, si.quantity, si.unit_price, si.line_total, si.issued
           FROM sale_items si JOIN products p ON p.id=si.product_id
           WHERE si.sale_id=%s ORDER BY si.id""",
        (int(sale_id),),
    )
    return sales.iloc[0], items


def receipt_html(sale, items):
    school_name = str(sale.get("school_name", "Uniform Sales"))
    logo_path = ""
    if "LOVING BLOOMS" in school_name.upper():
        logo_path = os.getenv("LOVING_BLOOMS_LOGO", r"C:\Users\awuor\loving_blooms_logo.png")
    elif "WARIDI" in school_name.upper():
        logo_path = os.getenv("WARIDI_LOGO", r"C:\Users\awuor\waridi_logo.png")

    logo_html = ""
    if logo_path and os.path.exists(logo_path):
        import base64
        ext = os.path.splitext(logo_path)[1].lower()
        mime = "image/png" if ext == ".png" else "image/jpeg"
        with open(logo_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
        logo_html = f'<img src="data:{mime};base64,{encoded}" style="max-width:95px;max-height:70px;object-fit:contain;margin-bottom:8px;">'

    rows = ""
    for _, item in items.iterrows():
        status = "ISSUED" if bool(item["issued"]) else "NOT ISSUED"
        rows += f"""
        <tr>
          <td>{item['product_name']}</td><td style="text-align:center">{int(item['quantity'])}</td>
          <td style="text-align:right">{float(item['unit_price']):,.2f}</td>
          <td style="text-align:right">{float(item['line_total']):,.2f}</td>
          <td style="text-align:center">{status}</td>
        </tr>"""
    receipt_no = sale.get("receipt_number") or f"UNI-{int(sale['id']):06d}"
    paid = float(sale.get("amount_paid") or 0)
    balance = float(sale.get("balance_due") or (float(sale.get("total_amount") or 0) - paid))
    return f"""
    <html><head><meta charset="utf-8"><title>Receipt {receipt_no}</title>
    <style>
      body{{font-family:Arial,sans-serif;color:#1c2733;margin:0;padding:20px}}
      .receipt{{max-width:760px;margin:auto;border:1px solid #d7dee8;padding:26px;border-radius:8px}}
      .top{{text-align:center;border-bottom:2px solid #142b4a;padding-bottom:14px}}
      h2{{margin:4px 0;color:#142b4a}} .muted{{color:#617085;font-size:12px}}
      .details{{display:flex;justify-content:space-between;gap:20px;margin:18px 0}}
      table{{width:100%;border-collapse:collapse;font-size:12px}}
      th{{background:#142b4a;color:white;text-align:left}}
      th,td{{padding:9px 7px;border-bottom:1px solid #e1e7ef}}
      .totals{{margin:18px 0 0 auto;width:280px}}
      .totals div{{display:flex;justify-content:space-between;padding:5px 0}}
      .balance{{font-weight:bold;color:#b23b3b;border-top:1px solid #ddd;padding-top:8px}}
      .footer{{text-align:center;margin-top:22px;font-size:12px;color:#617085}}
      @media print{{body{{padding:0}} .receipt{{border:0}}}}
    </style></head><body><div class="receipt">
    <div class="top">{logo_html}<h2>{school_name}</h2>
    <div class="muted">UNIFORM SALES RECEIPT</div>
    <h3>{receipt_no}</h3></div>
    <div class="details">
      <div><b>Customer:</b> {sale.get('customer_name') or 'Walk-in customer'}<br>
      <b>Phone:</b> {sale.get('phone') or '—'}<br><b>Class:</b> {sale.get('class_name') or '—'}</div>
      <div><b>Date:</b> {pd.to_datetime(sale.get('sale_date')).strftime('%d %b %Y, %I:%M %p')}<br>
      <b>Term / Year:</b> {sale.get('term') or '—'} / {sale.get('year') or '—'}<br>
      <b>Payment:</b> {sale.get('payment_method') or '—'}</div>
    </div>
    <table><thead><tr><th>Item</th><th>Qty</th><th>Unit (KSh)</th><th>Total (KSh)</th><th>Issue status</th></tr></thead>
    <tbody>{rows}</tbody></table>
    <div class="totals">
      <div><span>Total</span><b>KSh {float(sale.get('total_amount') or 0):,.2f}</b></div>
      <div><span>Amount paid</span><b>KSh {paid:,.2f}</b></div>
      <div class="balance"><span>Balance due</span><span>KSh {balance:,.2f}</span></div>
    </div>
    <div class="footer">Thank you. Please keep this receipt for your records.</div>
    </div></body></html>"""


# -------------------- INITIALISE --------------------

try:
    setup_database()
    refresh_data()
except Exception as e:
    st.error("Could not connect to PostgreSQL or prepare the database.")
    st.info("Check your PostgreSQL service, database name, username and password. The app does not delete existing data.")
    st.code(str(e))
    st.stop()

# -------------------- SIDEBAR --------------------

st.sidebar.markdown("## 🧵 Uniforms")
st.sidebar.caption("Sales • Stock • Finance")
page = st.sidebar.radio(
    "WORKSPACE",
    [
        "Dashboard",
        "New Sale / POS",
        "Receipts & Issuing",
        "Price Management",
        "Inventory",
        "Business Finance",
        "Sales Reports",
        "Tailor & Production",
    ],
)
st.sidebar.divider()
st.sidebar.caption(f"Today: {date.today().strftime('%d %b %Y')}")
st.sidebar.caption("Database: uniforms_sales")

schools = get_schools()
if schools.empty:
    st.error("No schools found in the database.")
    st.stop()
school_options = dict(zip(schools["school_name"], schools["id"]))

# -------------------- DASHBOARD --------------------

if page == "Dashboard":
    st.markdown(
        '<div class="hero"><h1>Business Dashboard</h1><p>Track sales, collections, stock and business performance in one place.</p></div>',
        unsafe_allow_html=True,
    )
    f1, f2, f3 = st.columns([2, 1, 1])
    selected_school_name = f1.selectbox("School", list(school_options), key="dash_school")
    period = f2.selectbox("Period", ["This month", "This term", "This year", "All time"], key="dash_period")
    dash_year = f3.selectbox("Year", list(range(date.today().year, date.today().year - 5, -1)), key="dash_year")

    where = ["s.school_id=%s"]
    params = [school_options[selected_school_name]]
    if period == "This month":
        where.append("DATE_TRUNC('month',s.sale_date)=DATE_TRUNC('month',CURRENT_DATE)")
    elif period == "This term":
        where.append("s.term=(SELECT term FROM sales WHERE school_id=%s ORDER BY sale_date DESC LIMIT 1)")
        params.append(school_options[selected_school_name])
        where.append("s.year=%s")
        params.append(dash_year)
    elif period == "This year":
        where.append("s.year=%s")
        params.append(dash_year)
    where_sql = " AND ".join(where)

    metrics = query_df(
        f"""SELECT COUNT(*) AS sales_count,
                   COALESCE(SUM(s.total_amount),0) AS sales_total,
                   COALESCE(SUM(COALESCE(s.amount_paid, CASE WHEN s.payment_status='Paid' THEN s.total_amount ELSE 0 END)),0) AS collected,
                   COALESCE(SUM(COALESCE(s.balance_due, GREATEST(s.total_amount-COALESCE(s.amount_paid,0),0))),0) AS outstanding
            FROM sales s WHERE {where_sql}""",
        params,
    ).iloc[0]
    # Estimate gross profit from sold items less stock purchase/production cost where available.
    profit = query_df(
        f"""SELECT COALESCE(SUM(si.line_total),0) AS revenue,
                   COALESCE(SUM(si.quantity * COALESCE(
                     (SELECT st.unit_cost FROM stock st WHERE st.school_id=s.school_id
                      AND st.product_id=si.product_id AND st.unit_cost>0
                      ORDER BY st.created_at DESC LIMIT 1),0)),0) AS estimated_cost
            FROM sales s JOIN sale_items si ON si.sale_id=s.id WHERE {where_sql}""",
        params,
    ).iloc[0]
    estimated_profit = float(profit["revenue"] or 0) - float(profit["estimated_cost"] or 0)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Sales value", money(metrics["sales_total"]))
    c2.metric("Cash collected", money(metrics["collected"]))
    c3.metric("Outstanding", money(metrics["outstanding"]))
    c4.metric("Transactions", f"{int(metrics['sales_count']):,}")
    c5.metric("Est. gross profit", money(estimated_profit), help="Approximation using the most recent recorded stock unit cost; enter accurate costs for better estimates.")

    st.divider()
    left, right = st.columns([1.5, 1])
    with left:
        st.subheader("Sales trend")
        trend = query_df(
            f"""SELECT DATE(s.sale_date) AS sale_day,
                       SUM(s.total_amount) AS sales,
                       SUM(COALESCE(s.amount_paid,0)) AS collected
                FROM sales s WHERE {where_sql}
                GROUP BY DATE(s.sale_date) ORDER BY sale_day""",
            params,
        )
        if not trend.empty:
            st.line_chart(trend.set_index("sale_day")[["sales", "collected"]])
        else:
            st.info("No sales for the selected filters yet.")
    with right:
        st.subheader("Top-selling items")
        top = query_df(
            f"""SELECT p.product_name, SUM(si.quantity) AS units,
                       SUM(si.line_total) AS revenue
                FROM sales s JOIN sale_items si ON si.sale_id=s.id
                JOIN products p ON p.id=si.product_id
                WHERE {where_sql}
                GROUP BY p.product_name ORDER BY units DESC LIMIT 8""",
            params,
        )
        if top.empty:
            st.info("Items will appear here after sales are recorded.")
        else:
            st.dataframe(top, use_container_width=True, hide_index=True)
    st.subheader("Recent transactions")
    recent = query_df(
        """SELECT s.id, s.receipt_number, s.sale_date, sc.school_name,
                  c.customer_name, s.total_amount, s.amount_paid, s.balance_due,
                  s.payment_status
           FROM sales s JOIN schools sc ON sc.id=s.school_id
           LEFT JOIN customers c ON c.id=s.customer_id
           ORDER BY s.sale_date DESC LIMIT 10"""
    )
    if not recent.empty:
        st.dataframe(recent, use_container_width=True, hide_index=True)
    st.caption("Estimated profit is indicative, not a substitute for complete accounting records.")

# -------------------- NEW SALE / POS --------------------

elif page == "New Sale / POS":
    st.markdown('<div class="hero"><h1>New Sale / POS</h1><p>Create an itemised sale, accept full or partial payment, and save a permanent receipt.</p></div>', unsafe_allow_html=True)
    with st.form("sale_details"):
        a, b, c = st.columns(3)
        school_name = a.selectbox("School", list(school_options), key="pos_school")
        category = b.selectbox("Category / section", ["Primary", "JSS", "Other"], key="pos_category")
        term = c.selectbox("Term", ["Term 1", "Term 2", "Term 3"], key="pos_term")
        d, e, f = st.columns(3)
        customer_name = d.text_input("Parent / customer name", key="pos_customer")
        phone = e.text_input("Phone number", key="pos_phone")
        class_name = f.text_input("Class / grade", placeholder="e.g. Grade 4")
        year = st.selectbox("Academic year", list(range(date.today().year, date.today().year - 5, -1)), key="pos_year")
        submitted = st.form_submit_button("Save customer details", type="primary")
    if submitted:
        st.session_state["pos_customer_saved"] = {
            "school_name": school_name, "category": category, "term": term,
            "customer_name": customer_name.strip(), "phone": phone.strip(),
            "class_name": class_name.strip(), "year": int(year),
        }
        st.success("Customer and sale details saved for this sale.")

    details = st.session_state.get("pos_customer_saved")
    if not details:
        st.info("Enter the sale details above and click **Save customer details** to load the product list.")
    else:
        st.caption(f"Preparing sale for {details['customer_name'] or 'Walk-in customer'} • {details['school_name']} • {details['term']} {details['year']}")
        products = get_products_for_school(school_options[details["school_name"]], details["category"])
        if products.empty:
            st.warning("No prices are assigned for this school and category. Open Price Management to assign prices.")
        else:
            pmap = {f"{r.product_name} — {money(r.price)}": r for r in products.itertuples(index=False)}
            with st.form("add_item_form"):
                pcol, qcol = st.columns([3, 1])
                chosen = pcol.selectbox("Uniform item", list(pmap))
                qty = qcol.number_input("Quantity", min_value=1, max_value=500, value=1, step=1)
                add_item = st.form_submit_button("＋ Add item to cart")
            if add_item:
                r = pmap[chosen]
                found = False
                for item in st.session_state.cart:
                    if item["product_id"] == int(r.id):
                        item["quantity"] += int(qty)
                        found = True
                        break
                if not found:
                    st.session_state.cart.append({
                        "product_id": int(r.id), "product_name": r.product_name,
                        "quantity": int(qty), "unit_price": float(r.price),
                    })
                st.rerun()

        if st.session_state.cart:
            st.subheader("Current cart")
            cart_df = pd.DataFrame(st.session_state.cart)
            cart_df["line_total"] = cart_df["quantity"] * cart_df["unit_price"]
            st.dataframe(
                cart_df[["product_name", "quantity", "unit_price", "line_total"]].rename(
                    columns={"product_name":"Item","quantity":"Qty","unit_price":"Unit price","line_total":"Line total"}
                ),
                use_container_width=True, hide_index=True,
                column_config={
                    "Unit price": st.column_config.NumberColumn(format="KSh %.2f"),
                    "Line total": st.column_config.NumberColumn(format="KSh %.2f"),
                },
            )
            total = sum(i["quantity"] * i["unit_price"] for i in st.session_state.cart)
            x, y, z = st.columns([1, 1, 1])
            x.metric("Sale total", money(total))
            amount_paid = y.number_input("Amount paid (KSh)", min_value=0.0, max_value=float(total), value=float(total), step=100.0)
            payment_method = z.selectbox("Payment method", ["Cash", "M-Pesa", "Bank", "Mixed", "Other"])
            st.caption(f"Balance due: **{money(total - amount_paid)}**")
            col1, col2 = st.columns(2)
            if col1.button("Complete sale & create receipt", type="primary", use_container_width=True):
                try:
                    with get_connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute("SELECT id FROM customers WHERE customer_name=%s AND COALESCE(phone,'')=%s ORDER BY id LIMIT 1",
                                        (details["customer_name"] or "Walk-in customer", details["phone"]))
                            row = cur.fetchone()
                            if row:
                                customer_id = row[0]
                            else:
                                cur.execute("INSERT INTO customers(customer_name, phone) VALUES (%s,%s) RETURNING id",
                                            (details["customer_name"] or "Walk-in customer", details["phone"]))
                                customer_id = cur.fetchone()[0]
                            receipt_number = f"UNI-{datetime.now().strftime('%y%m%d')}-{datetime.now().strftime('%H%M%S')}"
                            balance = round(float(total) - float(amount_paid), 2)
                            status = "Paid" if balance <= 0 else ("Partially Paid" if amount_paid > 0 else "Unpaid")
                            cur.execute(
                                """INSERT INTO sales(school_id, customer_id, total_amount, payment_method,
                                    payment_status, term, year, amount_paid, balance_due, receipt_number, class_name)
                                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                                (school_options[details["school_name"]], customer_id, total, payment_method,
                                 status, details["term"], details["year"], amount_paid, balance,
                                 receipt_number, details["class_name"]),
                            )
                            sale_id = cur.fetchone()[0]
                            for item in st.session_state.cart:
                                cur.execute(
                                    """INSERT INTO sale_items(sale_id, product_id, quantity, unit_price, line_total, issued)
                                       VALUES (%s,%s,%s,%s,%s,FALSE)""",
                                    (sale_id, item["product_id"], item["quantity"], item["unit_price"],
                                     item["quantity"] * item["unit_price"]),
                                )
                            if amount_paid > 0:
                                cur.execute(
                                    """INSERT INTO financial_transactions(transaction_type, category, amount,
                                       description, school_id, investor_name)
                                       VALUES ('Income','Uniform sales',%s,%s,%s,NULL)""",
                                    (amount_paid, f"Receipt {receipt_number}", school_options[details["school_name"]]),
                                )
                        conn.commit()
                    st.session_state.last_receipt_id = sale_id
                    st.session_state.cart = []
                    st.session_state.pop("pos_customer_saved", None)
                    st.success(f"Sale saved successfully. Receipt: {receipt_number}")
                    st.rerun()
                except Exception as e:
                    st.error("The sale could not be saved. No items were removed from your cart.")
                    st.code(str(e))
            if col2.button("Clear cart", use_container_width=True):
                st.session_state.cart = []
                st.rerun()

# -------------------- RECEIPTS & ISSUING --------------------

elif page == "Receipts & Issuing":
    st.markdown('<div class="hero"><h1>Receipts & Issuing</h1><p>Find previous receipts, print them again, and track which items have been handed over.</p></div>', unsafe_allow_html=True)
    search = st.text_input("Search by receipt number, customer, or phone")
    receipts = query_df(
        """SELECT s.id, s.receipt_number, s.sale_date, sc.school_name, c.customer_name,
                  c.phone, s.total_amount, s.amount_paid, s.balance_due, s.payment_status
           FROM sales s JOIN schools sc ON sc.id=s.school_id
           LEFT JOIN customers c ON c.id=s.customer_id
           WHERE (%s='' OR COALESCE(s.receipt_number,'') ILIKE %s OR COALESCE(c.customer_name,'') ILIKE %s OR COALESCE(c.phone,'') ILIKE %s)
           ORDER BY s.sale_date DESC LIMIT 250""",
        (search, f"%{search}%", f"%{search}%", f"%{search}%"),
    )
    if receipts.empty:
        st.info("No matching receipts found.")
    else:
        st.dataframe(receipts.drop(columns=["id"]), use_container_width=True, hide_index=True)
        choices = {
            f"{r.receipt_number or ('UNI-'+str(r.id))} | {r.customer_name or 'Walk-in'} | {pd.to_datetime(r.sale_date).strftime('%d %b %Y')}": int(r.id)
            for r in receipts.itertuples(index=False)
        }
        chosen_receipt = st.selectbox("Open receipt", list(choices))
        sale_id = choices[chosen_receipt]
        sale, items = get_receipt(sale_id)
        if sale is not None:
            st.subheader(f"Receipt {sale.get('receipt_number') or sale_id}")
            st.dataframe(items, use_container_width=True, hide_index=True)
            a, b, c = st.columns(3)
            a.metric("Total", money(sale["total_amount"]))
            a.metric("Paid", money(sale.get("amount_paid", 0)))
            b.metric("Balance", money(sale.get("balance_due", 0)))
            c.metric("Payment status", sale.get("payment_status", "—"))
            st.markdown("**Mark items as issued**")
            for idx, item in items.iterrows():
                key = f"issued_{sale_id}_{idx}"
                checked = st.checkbox(
                    f"{item['product_name']} × {int(item['quantity'])}",
                    value=bool(item["issued"]),
                    key=key,
                )
                if checked != bool(item["issued"]):
                    # Save the status using the sale id and product; the row id is safest.
                    execute(
                        """UPDATE sale_items SET issued=%s
                           WHERE id=(SELECT si.id FROM sale_items si JOIN products p ON p.id=si.product_id
                                     WHERE si.sale_id=%s AND p.product_name=%s ORDER BY si.id OFFSET %s LIMIT 1)""",
                        (checked, sale_id, item["product_name"], int(idx)),
                    )
            sale, items = get_receipt(sale_id)
            html = receipt_html(sale, items)
            components.html(html, height=620, scrolling=True)
            st.download_button(
                "Download receipt as HTML",
                data=html,
                file_name=f"{sale.get('receipt_number') or 'receipt-'+str(sale_id)}.html",
                mime="text/html",
                use_container_width=True,
            )
            if st.button("Print receipt", type="primary"):
                components.html(
                    f"<script>const w=window.open('','_blank');w.document.write({repr(html)});w.document.close();w.focus();w.print();</script>",
                    height=0,
                )

# -------------------- PRICE MANAGEMENT --------------------

elif page == "Price Management":
    st.markdown('<div class="hero"><h1>Price Management</h1><p>Maintain separate prices for each school and section without changing past receipts.</p></div>', unsafe_allow_html=True)
    school_name = st.selectbox("School", list(school_options), key="price_school")
    category = st.selectbox("Section", ["Primary", "JSS", "Other"], key="price_category")
    sid = school_options[school_name]
    price_df = get_products_for_school(sid, category)
    if not price_df.empty:
        edited = st.data_editor(
            price_df[["id", "product_name", "category", "price"]].rename(columns={"id":"product_id"}),
            hide_index=True, use_container_width=True, num_rows="fixed",
            disabled=["product_id", "product_name", "category"],
            column_config={"price": st.column_config.NumberColumn("Selling price (KSh)", min_value=0, step=50, format="KSh %.2f")},
            key="price_editor",
        )
        if st.button("Save price changes", type="primary"):
            try:
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        for _, r in edited.iterrows():
                            cur.execute(
                                """UPDATE school_product_prices SET price=%s
                                   WHERE school_id=%s AND product_id=%s AND COALESCE(category,'Primary')=%s""",
                                (float(r["price"]), sid, int(r["product_id"]), category),
                            )
                    conn.commit()
                st.success("Prices updated. Existing sale receipts remain unchanged.")
                st.rerun()
            except Exception as e:
                st.error(str(e))
    else:
        st.info("No products assigned to this school and section yet.")

    st.divider()
    st.subheader("Add a product and price")
    with st.form("new_product"):
        name = st.text_input("Product name")
        product_category = st.selectbox("Product type", ["Uniform", "Sportswear", "Accessories", "Outerwear", "Other"])
        price = st.number_input("Selling price (KSh)", min_value=0.0, value=500.0, step=50.0)
        section = st.selectbox("Assign to section", ["Primary", "JSS", "Other"], key="new_prod_section")
        save_product = st.form_submit_button("Create / assign product")
    if save_product:
        if not name.strip():
            st.warning("Enter a product name.")
        else:
            try:
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "INSERT INTO products(product_name,category) VALUES (%s,%s) ON CONFLICT(product_name) DO UPDATE SET category=EXCLUDED.category RETURNING id",
                            (name.strip(), product_category),
                        )
                        pid = cur.fetchone()[0]
                        cur.execute(
                            """INSERT INTO school_product_prices(school_id,product_id,price,category)
                               VALUES (%s,%s,%s,%s)
                               ON CONFLICT(school_id,product_id,category) DO UPDATE SET price=EXCLUDED.price""",
                            (sid, pid, price, section),
                        )
                    conn.commit()
                st.success("Product and price saved.")
                st.rerun()
            except Exception as e:
                st.error("Could not save product. Check your database schema.")
                st.code(str(e))

# -------------------- INVENTORY --------------------

elif page == "Inventory":
    st.markdown('<div class="hero"><h1>Inventory</h1><p>Record stock purchases and monitor estimated stock remaining.</p></div>', unsafe_allow_html=True)
    a, b, c = st.columns(3)
    school_name = a.selectbox("School", list(school_options), key="stock_school")
    term = b.selectbox("Term", ["Term 1", "Term 2", "Term 3"], key="stock_term")
    year = c.selectbox("Year", list(range(date.today().year, date.today().year - 5, -1)), key="stock_year")
    products = query_df("SELECT id, product_name FROM products ORDER BY product_name")
    if not products.empty:
        product_map = dict(zip(products.product_name, products.id))
        st.subheader("Receive stock")
        with st.form("receive_stock"):
            p = st.selectbox("Product", list(product_map))
            qty = st.number_input("Quantity received", min_value=1, value=1, step=1)
            unit_cost = st.number_input("Cost per item (KSh)", min_value=0.0, value=0.0, step=25.0)
            vendor = st.text_input("Supplier / notes")
            receive = st.form_submit_button("Record stock purchase", type="primary")
        if receive:
            total_cost = float(qty) * float(unit_cost)
            try:
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """INSERT INTO stock(school_id,product_id,quantity_brought,term,year,unit_cost)
                               VALUES (%s,%s,%s,%s,%s,%s)""",
                            (school_options[school_name], product_map[p], qty, term, year, unit_cost),
                        )
                        if total_cost > 0:
                            cur.execute(
                                """INSERT INTO financial_transactions(transaction_type,category,amount,description,school_id)
                                   VALUES ('Expense','Stock purchase',%s,%s,%s)""",
                                (total_cost, f"{p}: {qty} units. {vendor}".strip(), school_options[school_name]),
                            )
                    conn.commit()
                st.success("Stock purchase recorded.")
                st.rerun()
            except Exception as e:
                st.error(str(e))

        st.divider()
        st.subheader("Stock on hand")
        stock_df = query_df(
            """SELECT p.id, p.product_name,
                COALESCE(st.received,0) AS received,
                COALESCE(tp.produced,0) AS produced,
                COALESCE(si.sold,0) AS sold,
                COALESCE(st.received,0)+COALESCE(tp.produced,0)-COALESCE(si.sold,0) AS estimated_on_hand
             FROM products p
             LEFT JOIN (SELECT product_id, SUM(quantity_brought) received FROM stock WHERE school_id=%s GROUP BY product_id) st ON st.product_id=p.id
             LEFT JOIN (SELECT product_id, SUM(quantity) produced FROM tailor_production WHERE school_id=%s GROUP BY product_id) tp ON tp.product_id=p.id
             LEFT JOIN (SELECT si.product_id, SUM(si.quantity) sold FROM sale_items si JOIN sales s ON s.id=si.sale_id WHERE s.school_id=%s GROUP BY si.product_id) si ON si.product_id=p.id
             ORDER BY p.product_name""",
            (school_options[school_name], school_options[school_name], school_options[school_name]),
        )
        stock_df = stock_df[stock_df[["received", "produced", "sold"]].sum(axis=1) > 0]
        if not stock_df.empty:
            stock_df["Status"] = stock_df["estimated_on_hand"].apply(lambda x: "LOW / REORDER" if x <= 5 else "OK")
            st.dataframe(stock_df.drop(columns=["id"]), use_container_width=True, hide_index=True)
            low = stock_df[stock_df["estimated_on_hand"] <= 5]
            if not low.empty:
                st.warning("Low stock: " + ", ".join(low["product_name"].astype(str).tolist()))
        else:
            st.info("No stock or sales movements recorded for this school yet.")

# -------------------- BUSINESS FINANCE --------------------

elif page == "Business Finance":
    st.markdown('<div class="hero"><h1>Business Finance</h1><p>Review income, expenses, investments and the cash position.</p></div>', unsafe_allow_html=True)
    a, b = st.columns(2)
    school_name = a.selectbox("School", ["All schools"] + list(school_options), key="finance_school")
    year = b.selectbox("Year", list(range(date.today().year, date.today().year - 5, -1)), key="finance_year")
    school_filter = "" if school_name == "All schools" else " AND school_id=%s"
    params = [year]
    if school_name != "All schools":
        params.append(school_options[school_name])
    tx = query_df(
        f"""SELECT transaction_date, transaction_type, category, amount, description, investor_name
            FROM financial_transactions
            WHERE EXTRACT(YEAR FROM transaction_date)=%s {school_filter}
            ORDER BY transaction_date DESC""",
        params,
    )
    # Sales payments are also shown separately because legacy records may not have transactions.
    sale_filter = "" if school_name == "All schools" else " AND s.school_id=%s"
    sale_params = [year] + ([] if school_name == "All schools" else [school_options[school_name]])
    sales_summary = query_df(
        f"""SELECT COALESCE(SUM(COALESCE(s.amount_paid,0)),0) AS collected,
                   COALESCE(SUM(s.total_amount),0) AS invoiced,
                   COALESCE(SUM(COALESCE(s.balance_due,0)),0) AS balance
            FROM sales s WHERE s.year=%s {sale_filter}""",
        sale_params,
    ).iloc[0]
    income = float(tx.loc[tx["transaction_type"].str.lower().isin(["income","investment","capital"]), "amount"].sum()) if not tx.empty else 0
    expenses = float(tx.loc[tx["transaction_type"].str.lower().isin(["expense","withdrawal"]), "amount"].sum()) if not tx.empty else 0
    investments = float(tx.loc[tx["transaction_type"].str.lower().isin(["investment","capital"]), "amount"].sum()) if not tx.empty else 0
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Sales collected", money(sales_summary["collected"]))
    m2.metric("Sales outstanding", money(sales_summary["balance"]))
    m3.metric("Recorded expenses", money(expenses))
    m4.metric("Recorded investments", money(investments))
    st.caption("Sales collected are calculated from sales records. The transaction ledger is displayed separately to help avoid confusing invoiced sales with cash received.")
    st.subheader("Add a financial transaction")
    with st.form("finance_tx"):
        x, y, z = st.columns(3)
        tx_type = x.selectbox("Transaction type", ["Income", "Expense", "Investment", "Withdrawal"])
        tx_category = y.text_input("Category", value="General")
        tx_amount = z.number_input("Amount (KSh)", min_value=0.0, step=100.0)
        tx_description = st.text_input("Description / reference")
        tx_school = st.selectbox("School allocation", ["All / shared"] + list(school_options), key="tx_school")
        tx_investor = st.text_input("Investor name (optional)")
        add_tx = st.form_submit_button("Save transaction", type="primary")
    if add_tx:
        if tx_amount <= 0:
            st.warning("Enter an amount greater than zero.")
        else:
            sid = None if tx_school == "All / shared" else school_options[tx_school]
            try:
                execute(
                    """INSERT INTO financial_transactions(transaction_type,category,amount,description,school_id,investor_name)
                       VALUES (%s,%s,%s,%s,%s,%s)""",
                    (tx_type, tx_category or "General", tx_amount, tx_description, sid, tx_investor or None),
                )
                st.success("Transaction saved.")
                st.rerun()
            except Exception as e:
                st.error(str(e))
    st.subheader("Transaction ledger")
    if tx.empty:
        st.info("No ledger entries for this filter.")
    else:
        st.dataframe(tx, use_container_width=True, hide_index=True)
        st.download_button("Export ledger CSV", tx.to_csv(index=False).encode("utf-8"), "finance_ledger.csv", "text/csv")

# -------------------- SALES REPORTS --------------------

elif page == "Sales Reports":
    st.markdown('<div class="hero"><h1>Sales Reports</h1><p>Search and export sales records for bookkeeping and analysis.</p></div>', unsafe_allow_html=True)
    a, b, c = st.columns(3)
    school_name = a.selectbox("School", ["All schools"] + list(school_options), key="report_school")
    year = b.selectbox("Year", list(range(date.today().year, date.today().year - 5, -1)), key="report_year")
    term = c.selectbox("Term", ["All terms", "Term 1", "Term 2", "Term 3"], key="report_term")
    clauses = ["s.year=%s"]
    params = [year]
    if school_name != "All schools":
        clauses.append("s.school_id=%s")
        params.append(school_options[school_name])
    if term != "All terms":
        clauses.append("s.term=%s")
        params.append(term)
    report = query_df(
        f"""SELECT s.id, s.receipt_number, s.sale_date, sc.school_name, c.customer_name,
                   c.phone, s.class_name, s.term, s.year, s.total_amount, s.amount_paid,
                   s.balance_due, s.payment_method, s.payment_status
            FROM sales s JOIN schools sc ON sc.id=s.school_id
            LEFT JOIN customers c ON c.id=s.customer_id
            WHERE {' AND '.join(clauses)} ORDER BY s.sale_date DESC""",
        params,
    )
    if report.empty:
        st.info("No sales match these filters.")
    else:
        m1, m2, m3 = st.columns(3)
        m1.metric("Sales", len(report))
        m2.metric("Total invoiced", money(report["total_amount"].sum()))
        m3.metric("Total outstanding", money(report["balance_due"].fillna(0).sum()))
        st.dataframe(report.drop(columns=["id"]), use_container_width=True, hide_index=True)
        st.download_button("Download sales CSV", report.to_csv(index=False).encode("utf-8"), "uniform_sales_report.csv", "text/csv", type="primary")
        receipt_map = {f"{r.receipt_number or ('UNI-'+str(r.id))} — {r.customer_name or 'Walk-in'}": int(r.id) for r in report.itertuples(index=False)}
        selected = st.selectbox("Open a receipt from this report", list(receipt_map))
        if st.button("Open selected receipt"):
            st.session_state.last_receipt_id = receipt_map[selected]
            st.session_state["open_receipt_from_report"] = True
            st.info("Open Receipts & Issuing from the sidebar and select this receipt.")

# -------------------- TAILOR & PRODUCTION --------------------

elif page == "Tailor & Production":
    st.markdown('<div class="hero"><h1>Tailor & Production</h1><p>Record finished uniforms and tailor costs. Production is included in estimated stock.</p></div>', unsafe_allow_html=True)
    with st.form("production_form"):
        a, b, c = st.columns(3)
        school_name = a.selectbox("School", list(school_options), key="prod_school")
        product_df = query_df("SELECT id, product_name FROM products ORDER BY product_name")
        product_map = dict(zip(product_df.product_name, product_df.id))
        product_name = b.selectbox("Product made", list(product_map))
        quantity = c.number_input("Quantity produced", min_value=1, value=1, step=1)
        d, e, f = st.columns(3)
        cost = d.number_input("Cost per item (KSh)", min_value=0.0, value=0.0, step=25.0)
        tailor = e.text_input("Tailor / workshop")
        term = f.selectbox("Term", ["Term 1", "Term 2", "Term 3"], key="prod_term")
        year = st.selectbox("Year", list(range(date.today().year, date.today().year - 5, -1)), key="prod_year")
        notes = st.text_input("Notes")
        submit_prod = st.form_submit_button("Save production record", type="primary")
    if submit_prod:
        try:
            execute(
                """INSERT INTO tailor_production(school_id,product_id,quantity,cost_per_item,total_cost,tailor_name,notes,term,year)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (school_options[school_name], product_map[product_name], quantity, cost,
                 quantity * cost, tailor, notes, term, year),
            )
            if quantity * cost > 0:
                execute(
                    """INSERT INTO financial_transactions(transaction_type,category,amount,description,school_id)
                       VALUES ('Expense','Tailoring / production',%s,%s,%s)""",
                    (quantity * cost, f"{quantity} × {product_name}; {tailor}".strip(), school_options[school_name]),
                )
            st.success("Production record saved.")
            st.rerun()
        except Exception as e:
            st.error(str(e))
    production = query_df(
        """SELECT tp.production_date, sc.school_name, p.product_name, tp.quantity,
                  tp.cost_per_item, tp.total_cost, tp.tailor_name, tp.notes, tp.term, tp.year
           FROM tailor_production tp JOIN schools sc ON sc.id=tp.school_id
           JOIN products p ON p.id=tp.product_id ORDER BY tp.production_date DESC LIMIT 300"""
    )
    st.subheader("Recent production")
    if production.empty:
        st.info("No production records yet.")
    else:
        st.dataframe(production, use_container_width=True, hide_index=True)
        st.download_button("Export production CSV", production.to_csv(index=False).encode("utf-8"), "tailor_production.csv", "text/csv")

'''
path = "/mnt/data/uniforms_improved.py"
with open(path, "w", encoding="utf-8") as f:
    f.write(code)
print(f"Created {path} ({len(code.splitlines())} lines)")
