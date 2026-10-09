import os, textwrap

code = r'''import os
import base64
from datetime import date, datetime

import pandas as pd
import psycopg2
import streamlit as st
import streamlit.components.v1 as components

# ============================================================
# UNIFORM SALES POS - STREAMLIT + POSTGRESQL
# Designed for local PostgreSQL or Streamlit Community Cloud.
# Existing records are preserved; this app does not drop tables.
# ============================================================

st.set_page_config(
    page_title="Uniform Sales Business Manager",
    page_icon="🧵",
    layout="wide",
    initial_sidebar_state="expanded",
)

NAVY = "#142B4A"
BLUE = "#2364AA"
PALE = "#F3F7FC"

st.markdown(
    f"""
    <style>
      .stApp {{ background: {PALE}; }}
      [data-testid="stSidebar"] {{ background: {NAVY}; }}
      [data-testid="stSidebar"] * {{ color: white !important; }}
      .block-container {{ padding-top: 1.5rem; }}
      [data-testid="stMetric"] {{
        background: white; border: 1px solid #E2E8F0;
        padding: 14px 16px; border-radius: 12px;
      }}
      .hero {{
        background: linear-gradient(110deg, {NAVY}, {BLUE});
        color: white; border-radius: 15px; padding: 22px 26px;
        margin-bottom: 18px;
      }}
      .hero h1 {{ color: white; margin: 0; }}
      .hero p {{ color: #E7EEF8; margin: 5px 0 0; }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------- DATABASE ----------------------

def get_connection():
    """Read Streamlit secrets first, then environment variables, then local defaults."""
    cfg = {}
    try:
        cfg = dict(st.secrets.get("postgres", {}))
    except Exception:
        pass

    host = cfg.get("host", os.getenv("PGHOST", "127.0.0.1"))
    port = int(cfg.get("port", os.getenv("PGPORT", "5432")))
    dbname = cfg.get("database", cfg.get("dbname", os.getenv("PGDATABASE", "uniforms_sales")))
    user = cfg.get("user", os.getenv("PGUSER", "postgres"))
    password = cfg.get("password", os.getenv("PGPASSWORD", ""))
    sslmode = cfg.get("sslmode", os.getenv("PGSSLMODE", "prefer"))

    args = dict(host=host, port=port, dbname=dbname, user=user, password=password)
    if sslmode:
        args["sslmode"] = sslmode
    return psycopg2.connect(**args)


def read_df(sql, params=None):
    with get_connection() as conn:
        return pd.read_sql_query(sql, conn, params=params)


def run_sql(sql, params=None, returning=False):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            result = cur.fetchone() if returning else None
        conn.commit()
        return result


def existing_columns(cur, table):
    cur.execute(
        """SELECT column_name FROM information_schema.columns
           WHERE table_schema='public' AND table_name=%s""",
        (table,),
    )
    return {row[0] for row in cur.fetchall()}


def setup_database():
    """Create missing tables and add columns safely. No table is dropped."""
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

                CREATE TABLE IF NOT EXISTS investors (
                    id SERIAL PRIMARY KEY,
                    investor_name TEXT UNIQUE NOT NULL
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

            # Safe upgrades for databases created by earlier versions.
            upgrades = {
                "sales": [
                    ("amount_paid", "NUMERIC(12,2) NOT NULL DEFAULT 0"),
                    ("balance_due", "NUMERIC(12,2) NOT NULL DEFAULT 0"),
                    ("receipt_number", "TEXT"),
                    ("class_name", "TEXT"),
                ],
                "products": [("category", "TEXT DEFAULT 'Uniform'")],
                "sale_items": [("issued", "BOOLEAN DEFAULT FALSE")],
                "school_product_prices": [("category", "TEXT DEFAULT 'Primary'")],
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
            for table, definitions in upgrades.items():
                columns = existing_columns(cur, table)
                for col, definition in definitions:
                    if col not in columns:
                        cur.execute(f'ALTER TABLE "{table}" ADD COLUMN "{col}" {definition}')

            cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS sales_receipt_number_uq
                ON sales(receipt_number) WHERE receipt_number IS NOT NULL
            """)

            cur.execute("""
                INSERT INTO schools(school_name) VALUES
                ('LOVING BLOOMS SCHOOL'), ('WARIDI UTAWALA SCHOOL')
                ON CONFLICT(school_name) DO NOTHING
            """)

            product_defaults = [
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
            for name, category, _ in product_defaults:
                cur.execute(
                    """INSERT INTO products(product_name, category) VALUES (%s,%s)
                       ON CONFLICT(product_name) DO NOTHING""",
                    (name, category),
                )

            cur.execute("SELECT id FROM schools")
            school_ids = [row[0] for row in cur.fetchall()]
            cur.execute("SELECT id, product_name FROM products")
            products = cur.fetchall()
            default_prices = {name: price for name, _, price in product_defaults}

            for school_id in school_ids:
                for product_id, product_name in products:
                    price = default_prices.get(product_name, 500)
                    # Waridi JSS defaults; Primary defaults remain separately editable.
                    if school_id == 2 and product_name in ("Skirt", "Blouse"):
                        price = 700
                    cur.execute(
                        """INSERT INTO school_product_prices(school_id,product_id,price,category)
                           VALUES (%s,%s,%s,'Primary') ON CONFLICT DO NOTHING""",
                        (school_id, product_id, price),
                    )
        conn.commit()


# ---------------------- HELPERS ----------------------

def money(value):
    try:
        return f"KSh {float(value or 0):,.2f}"
    except (TypeError, ValueError):
        return "KSh 0.00"


def schools_dict():
    df = read_df("SELECT id, school_name FROM schools ORDER BY school_name")
    return dict(zip(df["school_name"], df["id"]))


def products_for(school_id, section):
    return read_df(
        """SELECT p.id, p.product_name, p.category, spp.price
           FROM school_product_prices spp
           JOIN products p ON p.id=spp.product_id
           WHERE spp.school_id=%s AND COALESCE(spp.category,'Primary')=%s
           ORDER BY p.product_name""",
        (int(school_id), section),
    )


def get_receipt(sale_id):
    sale_df = read_df(
        """SELECT s.*, sc.school_name, c.customer_name, c.phone
           FROM sales s JOIN schools sc ON sc.id=s.school_id
           LEFT JOIN customers c ON c.id=s.customer_id WHERE s.id=%s""",
        (int(sale_id),),
    )
    if sale_df.empty:
        return None, pd.DataFrame()
    items = read_df(
        """SELECT si.id AS item_id, p.product_name, si.quantity, si.unit_price,
                  si.line_total, COALESCE(si.issued,FALSE) AS issued
           FROM sale_items si JOIN products p ON p.id=si.product_id
           WHERE si.sale_id=%s ORDER BY si.id""",
        (int(sale_id),),
    )
    return sale_df.iloc[0].to_dict(), items


def make_receipt_html(sale, items):
    school_name = str(sale.get("school_name") or "Uniform Sales")
    logo_path = ""
    if "LOVING BLOOMS" in school_name.upper():
        logo_path = os.getenv("LOVING_BLOOMS_LOGO", "loving_blooms_logo.png")
    elif "WARIDI" in school_name.upper():
        logo_path = os.getenv("WARIDI_LOGO", "waridi_logo.png")

    logo = ""
    if logo_path and os.path.isfile(logo_path):
        ext = os.path.splitext(logo_path)[1].lower()
        mime = "image/png" if ext == ".png" else "image/jpeg"
        with open(logo_path, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode("utf-8")
        logo = f'<img src="data:{mime};base64,{encoded}" style="max-width:90px;max-height:65px;margin-bottom:8px">'

    rows = []
    for _, item in items.iterrows():
        status = "ISSUED" if bool(item["issued"]) else "NOT ISSUED"
        rows.append(
            "<tr>"
            f"<td>{item['product_name']}</td>"
            f"<td class='center'>{int(item['quantity'])}</td>"
            f"<td class='right'>{float(item['unit_price']):,.2f}</td>"
            f"<td class='right'>{float(item['line_total']):,.2f}</td>"
            f"<td class='center'>{status}</td>"
            "</tr>"
        )

    total = float(sale.get("total_amount") or 0)
    paid = float(sale.get("amount_paid") or 0)
    balance = float(sale.get("balance_due") or max(total - paid, 0))
    receipt_no = sale.get("receipt_number") or f"UNI-{int(sale['id']):06d}"
    sale_date = pd.to_datetime(sale.get("sale_date")).strftime("%d %b %Y, %I:%M %p")

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Receipt {receipt_no}</title>
<style>
body{{font-family:Arial,sans-serif;color:#172536;margin:0;padding:20px}}
.receipt{{max-width:800px;margin:auto;padding:24px;border:1px solid #dce3ed;border-radius:10px}}
.header{{text-align:center;border-bottom:2px solid #142b4a;padding-bottom:14px}}
h2{{color:#142b4a;margin:5px}}.muted{{color:#65758b;font-size:12px}}
.details{{display:flex;justify-content:space-between;gap:20px;margin:18px 0;line-height:1.8}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{background:#142b4a;color:white}}th,td{{padding:9px 7px;border-bottom:1px solid #e1e7ef;text-align:left}}
.center{{text-align:center}}.right{{text-align:right}}
.totals{{width:300px;margin:18px 0 0 auto}}.totals div{{display:flex;justify-content:space-between;padding:6px 0}}
.balance{{border-top:1px solid #ccd4df;font-weight:bold;color:#b42318}}
.footer{{text-align:center;color:#65758b;font-size:12px;margin-top:22px}}
@media print{{body{{padding:0}}.receipt{{border:0}}}}
</style></head><body><div class="receipt">
<div class="header">{logo}<h2>{school_name}</h2><div class="muted">UNIFORM SALES RECEIPT</div><h3>{receipt_no}</h3></div>
<div class="details">
<div><b>Customer:</b> {sale.get('customer_name') or 'Walk-in customer'}<br>
<b>Phone:</b> {sale.get('phone') or '—'}<br><b>Class:</b> {sale.get('class_name') or '—'}</div>
<div><b>Date:</b> {sale_date}<br><b>Term / Year:</b> {sale.get('term') or '—'} / {sale.get('year') or '—'}<br>
<b>Payment method:</b> {sale.get('payment_method') or '—'}<br><b>Status:</b> {sale.get('payment_status') or '—'}</div>
</div>
<table><thead><tr><th>Item</th><th>Qty</th><th>Unit price (KSh)</th><th>Total (KSh)</th><th>Issuing status</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
<div class="totals">
<div><span>Total</span><b>KSh {total:,.2f}</b></div>
<div><span>Amount paid</span><b>KSh {paid:,.2f}</b></div>
<div class="balance"><span>Balance due</span><b>KSh {balance:,.2f}</b></div>
</div>
<div class="footer">Thank you. Please keep this receipt for your records.</div>
</div></body></html>"""


def show_hero(title, subtitle):
    st.markdown(
        f'<div class="hero"><h1>{title}</h1><p>{subtitle}</p></div>',
        unsafe_allow_html=True,
    )


# ---------------------- STARTUP ----------------------

try:
    setup_database()
except Exception as exc:
    st.error("Unable to connect to PostgreSQL or prepare the database.")
    st.markdown(
        "Check your database connection settings. For Streamlit Cloud, add a "
        "`postgres` section under **App → Settings → Secrets**. For local use, "
        "set `PGHOST`, `PGDATABASE`, `PGUSER`, and `PGPASSWORD` environment variables."
    )
    st.code(str(exc))
    st.stop()

if "cart" not in st.session_state:
    st.session_state.cart = []
if "sale_details" not in st.session_state:
    st.session_state.sale_details = None
if "last_sale_id" not in st.session_state:
    st.session_state.last_sale_id = None

school_map = schools_dict()
if not school_map:
    st.error("No schools are configured.")
    st.stop()

st.sidebar.markdown("# 🧵 Uniforms")
st.sidebar.caption("Sales • Inventory • Finance")
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
st.sidebar.caption(f"Today: {date.today():%d %b %Y}")
st.sidebar.caption("Database: uniforms_sales")


# ---------------------- DASHBOARD ----------------------

if page == "Dashboard":
    show_hero("Business Dashboard", "Your sales, collections, stock and business performance at a glance.")
    col1, col2, col3 = st.columns([2, 1, 1])
    school_name = col1.selectbox("School", list(school_map), key="dashboard_school")
    period = col2.selectbox("Period", ["This month", "This year", "All time"], key="dashboard_period")
    year = col3.selectbox("Year", list(range(date.today().year, date.today().year - 5, -1)), key="dashboard_year")

    clauses = ["s.school_id=%s"]
    params = [school_map[school_name]]
    if period == "This month":
        clauses.append("DATE_TRUNC('month',s.sale_date)=DATE_TRUNC('month',CURRENT_DATE)")
    elif period == "This year":
        clauses.append("s.year=%s")
        params.append(year)
    where = " AND ".join(clauses)

    stats = read_df(
        f"""SELECT COUNT(*) AS transactions,
                   COALESCE(SUM(s.total_amount),0) AS sales_value,
                   COALESCE(SUM(COALESCE(s.amount_paid,0)),0) AS cash_received,
                   COALESCE(SUM(COALESCE(s.balance_due,GREATEST(s.total_amount-COALESCE(s.amount_paid,0),0))),0) AS outstanding
            FROM sales s WHERE {where}""",
        params,
    ).iloc[0]

    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Sales value", money(stats["sales_value"]))
    d2.metric("Cash received", money(stats["cash_received"]))
    d3.metric("Outstanding", money(stats["outstanding"]))
    d4.metric("Transactions", f"{int(stats['transactions']):,}")

    left, right = st.columns([1.5, 1])
    with left:
        st.subheader("Sales trend")
        trend = read_df(
            f"""SELECT DATE(s.sale_date) AS day, SUM(s.total_amount) AS sales,
                       SUM(COALESCE(s.amount_paid,0)) AS received
                FROM sales s WHERE {where}
                GROUP BY DATE(s.sale_date) ORDER BY day""",
            params,
        )
        if trend.empty:
            st.info("No sales found for this filter.")
        else:
            st.line_chart(trend.set_index("day")[["sales", "received"]])
    with right:
        st.subheader("Top-selling products")
        top = read_df(
            f"""SELECT p.product_name, SUM(si.quantity) AS units,
                       SUM(si.line_total) AS revenue
                FROM sales s JOIN sale_items si ON si.sale_id=s.id
                JOIN products p ON p.id=si.product_id
                WHERE {where} GROUP BY p.product_name
                ORDER BY units DESC LIMIT 8""",
            params,
        )
        if top.empty:
            st.info("Products appear here after the first sale.")
        else:
            st.dataframe(top, use_container_width=True, hide_index=True)

    st.subheader("Recent sales")
    recent = read_df(
        """SELECT s.receipt_number, s.sale_date, sc.school_name, c.customer_name,
                  s.total_amount, s.amount_paid, s.balance_due, s.payment_status
           FROM sales s JOIN schools sc ON sc.id=s.school_id
           LEFT JOIN customers c ON c.id=s.customer_id
           ORDER BY s.sale_date DESC LIMIT 10"""
    )
    if recent.empty:
        st.info("No sales recorded yet.")
    else:
        st.dataframe(recent, use_container_width=True, hide_index=True)
    st.caption("Outstanding balances are based on payment data saved with each sale.")


# ---------------------- NEW SALE ----------------------

elif page == "New Sale / POS":
    show_hero("New Sale / POS", "Build a multi-item cart, record a payment and create a permanent receipt.")

    with st.form("sale_details_form"):
        a, b, c = st.columns(3)
        school_name = a.selectbox("School", list(school_map), key="sale_school")
        section = b.selectbox("Section", ["Primary", "JSS", "Other"], key="sale_section")
        term = c.selectbox("Term", ["Term 1", "Term 2", "Term 3"], key="sale_term")
        d, e, f = st.columns(3)
        customer_name = d.text_input("Parent / customer name")
        phone = e.text_input("Phone number")
        class_name = f.text_input("Class / grade", placeholder="e.g. Grade 4")
        year = st.selectbox("Academic year", list(range(date.today().year, date.today().year - 5, -1)), key="sale_year")
        save_details = st.form_submit_button("Continue to products", type="primary")

    if save_details:
        st.session_state.sale_details = {
            "school_name": school_name,
            "school_id": school_map[school_name],
            "section": section,
            "term": term,
            "year": int(year),
            "customer_name": customer_name.strip(),
            "phone": phone.strip(),
            "class_name": class_name.strip(),
        }
        st.session_state.cart = []
        st.rerun()

    details = st.session_state.sale_details
    if details:
        st.info(
            f"Sale for **{details['customer_name'] or 'Walk-in customer'}** · "
            f"{details['school_name']} · {details['section']} · "
            f"{details['term']} {details['year']}"
        )
        product_df = products_for(details["school_id"], details["section"])
        if product_df.empty:
            st.warning("There are no products assigned to this school and section. Use Price Management to assign products and prices.")
        else:
            product_choices = {
                f"{row.product_name} — {money(row.price)}": row
                for row in product_df.itertuples(index=False)
            }
            with st.form("add_cart_item_form"):
                a, b = st.columns([3, 1])
                chosen = a.selectbox("Uniform item", list(product_choices))
                quantity = b.number_input("Quantity", min_value=1, max_value=500, value=1, step=1)
                add_item = st.form_submit_button("Add item to cart")
            if add_item:
                product = product_choices[chosen]
                existing = next((x for x in st.session_state.cart if x["product_id"] == int(product.id)), None)
                if existing:
                    existing["quantity"] += int(quantity)
                else:
                    st.session_state.cart.append({
                        "product_id": int(product.id),
                        "product_name": product.product_name,
                        "quantity": int(quantity),
                        "unit_price": float(product.price),
                    })
                st.rerun()

        if st.session_state.cart:
            st.subheader("Cart")
            cart_df = pd.DataFrame(st.session_state.cart)
            cart_df["line_total"] = cart_df["quantity"] * cart_df["unit_price"]
            st.dataframe(
                cart_df.rename(columns={
                    "product_name": "Item", "quantity": "Quantity",
                    "unit_price": "Unit price (KSh)", "line_total": "Line total (KSh)"
                }),
                use_container_width=True, hide_index=True,
                column_config={
                    "Unit price (KSh)": st.column_config.NumberColumn(format="KSh %.2f"),
                    "Line total (KSh)": st.column_config.NumberColumn(format="KSh %.2f"),
                },
            )
            total = round(sum(item["quantity"] * item["unit_price"] for item in st.session_state.cart), 2)
            p1, p2, p3 = st.columns(3)
            p1.metric("Total", money(total))
            amount_paid = p2.number_input("Amount paid (KSh)", min_value=0.0, max_value=float(total), value=float(total), step=100.0, key="amount_paid")
            payment_method = p3.selectbox("Payment method", ["Cash", "M-Pesa", "Bank", "Mixed", "Other"])
            st.metric("Balance due", money(max(total - amount_paid, 0)))

            col1, col2 = st.columns(2)
            if col1.button("Complete sale & save receipt", type="primary", use_container_width=True):
                try:
                    balance = round(max(total - float(amount_paid), 0), 2)
                    payment_status = "Paid" if balance == 0 else ("Partially Paid" if amount_paid > 0 else "Unpaid")
                    receipt_number = f"UNI-{datetime.now():%y%m%d-%H%M%S}"
                    with get_connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                """SELECT id FROM customers
                                   WHERE customer_name=%s AND COALESCE(phone,'')=%s
                                   ORDER BY id LIMIT 1""",
                                (details["customer_name"] or "Walk-in customer", details["phone"]),
                            )
                            customer = cur.fetchone()
                            if customer:
                                customer_id = customer[0]
                            else:
                                cur.execute(
                                    "INSERT INTO customers(customer_name,phone) VALUES (%s,%s) RETURNING id",
                                    (details["customer_name"] or "Walk-in customer", details["phone"]),
                                )
                                customer_id = cur.fetchone()[0]

                            cur.execute(
                                """INSERT INTO sales(
                                    school_id,customer_id,total_amount,payment_method,payment_status,
                                    term,year,amount_paid,balance_due,receipt_number,class_name
                                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                                (
                                    details["school_id"], customer_id, total, payment_method,
                                    payment_status, details["term"], details["year"],
                                    float(amount_paid), balance, receipt_number, details["class_name"],
                                ),
                            )
                            sale_id = cur.fetchone()[0]

                            for item in st.session_state.cart:
                                cur.execute(
                                    """INSERT INTO sale_items(sale_id,product_id,quantity,unit_price,line_total,issued)
                                       VALUES (%s,%s,%s,%s,%s,FALSE)""",
                                    (
                                        sale_id, item["product_id"], item["quantity"],
                                        item["unit_price"], item["quantity"] * item["unit_price"],
                                    ),
                                )

                            if amount_paid > 0:
                                cur.execute(
                                    """INSERT INTO financial_transactions(
                                        transaction_type,category,amount,description,school_id
                                    ) VALUES ('Income','Uniform sales',%s,%s,%s)""",
                                    (amount_paid, f"Receipt {receipt_number}", details["school_id"]),
                                )
                        conn.commit()

                    st.session_state.last_sale_id = sale_id
                    st.session_state.cart = []
                    st.session_state.sale_details = None
                    st.success(f"Sale saved. Receipt number: {receipt_number}")
                    st.rerun()
                except Exception as exc:
                    st.error("Could not save the sale. Your cart has been kept so you can retry.")
                    st.code(str(exc))

            if col2.button("Clear cart", use_container_width=True):
                st.session_state.cart = []
                st.rerun()

    if st.session_state.last_sale_id:
        st.divider()
        st.success("Latest saved receipt")
        sale, items = get_receipt(st.session_state.last_sale_id)
        if sale:
            html = make_receipt_html(sale, items)
            components.html(html, height=600, scrolling=True)
            st.download_button(
                "Download latest receipt (HTML)",
                data=html,
                file_name=f"{sale.get('receipt_number') or 'receipt'}.html",
                mime="text/html",
            )


# ---------------------- RECEIPTS & ISSUING ----------------------

elif page == "Receipts & Issuing":
    show_hero("Receipts & Issuing", "Search saved receipts, reprint them, and mark each item issued.")

    search = st.text_input("Search by receipt number, customer name or phone")
    receipts = read_df(
        """SELECT s.id, COALESCE(s.receipt_number,'UNI-'||LPAD(s.id::text,6,'0')) AS receipt,
                  s.sale_date, sc.school_name, c.customer_name, c.phone,
                  s.total_amount, s.amount_paid, s.balance_due, s.payment_status
           FROM sales s JOIN schools sc ON sc.id=s.school_id
           LEFT JOIN customers c ON c.id=s.customer_id
           WHERE (%s='' OR COALESCE(s.receipt_number,'') ILIKE %s
                  OR COALESCE(c.customer_name,'') ILIKE %s
                  OR COALESCE(c.phone,'') ILIKE %s)
           ORDER BY s.sale_date DESC LIMIT 300""",
        (search, f"%{search}%", f"%{search}%", f"%{search}%"),
    )

    if receipts.empty:
        st.info("No receipts found.")
    else:
        st.dataframe(receipts.drop(columns=["id"]), use_container_width=True, hide_index=True)
        choices = {
            f"{row.receipt} · {row.customer_name or 'Walk-in'} · {pd.to_datetime(row.sale_date):%d %b %Y}": int(row.id)
            for row in receipts.itertuples(index=False)
        }
        choice = st.selectbox("Select receipt to open", list(choices))
        sale_id = choices[choice]
        sale, items = get_receipt(sale_id)

        if sale:
            st.subheader(f"Receipt: {sale.get('receipt_number') or sale_id}")
            st.dataframe(items.drop(columns=["item_id"]), use_container_width=True, hide_index=True)
            st.subheader("Update issuing status")
            changed = False
            for _, item in items.iterrows():
                new_issued = st.checkbox(
                    f"{item['product_name']} × {int(item['quantity'])} — "
                    f"{'Issued' if item['issued'] else 'Not issued'}",
                    value=bool(item["issued"]),
                    key=f"issue_{sale_id}_{int(item['item_id'])}",
                )
                if new_issued != bool(item["issued"]):
                    run_sql("UPDATE sale_items SET issued=%s WHERE id=%s", (new_issued, int(item["item_id"])))
                    changed = True
            if changed:
                st.success("Issuing status saved. Refresh this receipt to see the updated print view.")
                st.rerun()

            sale, items = get_receipt(sale_id)
            html = make_receipt_html(sale, items)
            components.html(html, height=650, scrolling=True)
            st.download_button(
                "Download receipt (HTML)",
                data=html,
                file_name=f"{sale.get('receipt_number') or 'receipt-'+str(sale_id)}.html",
                mime="text/html",
                use_container_width=True,
            )
            st.caption("Open the downloaded HTML receipt in your browser and use Ctrl+P to print or save as PDF.")


# ---------------------- PRICE MANAGEMENT ----------------------

elif page == "Price Management":
    show_hero("Price Management", "Set prices by school and section. Past sales retain their original prices.")
    a, b = st.columns(2)
    school_name = a.selectbox("School", list(school_map), key="prices_school")
    section = b.selectbox("Section", ["Primary", "JSS", "Other"], key="prices_section")
    school_id = school_map[school_name]
    prices = products_for(school_id, section)

    if not prices.empty:
        editable = st.data_editor(
            prices[["id", "product_name", "price"]].rename(columns={"id": "product_id"}),
            disabled=["product_id", "product_name"],
            hide_index=True, use_container_width=True,
            column_config={"price": st.column_config.NumberColumn("Selling price (KSh)", min_value=0, step=50, format="KSh %.2f")},
            key="prices_editor",
        )
        if st.button("Save price changes", type="primary"):
            try:
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        for _, row in editable.iterrows():
                            cur.execute(
                                """UPDATE school_product_prices SET price=%s
                                   WHERE school_id=%s AND product_id=%s AND COALESCE(category,'Primary')=%s""",
                                (float(row["price"]), school_id, int(row["product_id"]), section),
                            )
                    conn.commit()
                st.success("Prices updated successfully.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    else:
        st.warning("No products are assigned to this school and section yet.")

    st.divider()
    st.subheader("Create or assign a product")
    with st.form("assign_product_form"):
        name = st.text_input("Product name")
        kind = st.selectbox("Product type", ["Uniform", "Sportswear", "Accessories", "Outerwear", "Other"])
        new_price = st.number_input("Selling price (KSh)", min_value=0.0, value=500.0, step=50.0)
        assign_section = st.selectbox("Section to assign", ["Primary", "JSS", "Other"], key="assign_section")
        save_product = st.form_submit_button("Create / assign product", type="primary")
    if save_product:
        if not name.strip():
            st.warning("Enter a product name.")
        else:
            try:
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """INSERT INTO products(product_name,category) VALUES (%s,%s)
                               ON CONFLICT(product_name) DO UPDATE SET category=EXCLUDED.category
                               RETURNING id""",
                            (name.strip(), kind),
                        )
                        product_id = cur.fetchone()[0]
                        cur.execute(
                            """INSERT INTO school_product_prices(school_id,product_id,price,category)
                               VALUES (%s,%s,%s,%s)
                               ON CONFLICT(school_id,product_id,category)
                               DO UPDATE SET price=EXCLUDED.price""",
                            (school_id, product_id, new_price, assign_section),
                        )
                    conn.commit()
                st.success("Product and price saved.")
                st.rerun()
            except Exception as exc:
                st.error("Could not save the product.")
                st.code(str(exc))


# ---------------------- INVENTORY ----------------------

elif page == "Inventory":
    show_hero("Inventory", "Receive stock, track stock levels and flag items that need reordering.")
    a, b, c = st.columns(3)
    school_name = a.selectbox("School", list(school_map), key="inventory_school")
    term = b.selectbox("Term", ["Term 1", "Term 2", "Term 3"], key="inventory_term")
    year = c.selectbox("Year", list(range(date.today().year, date.today().year - 5, -1)), key="inventory_year")

    product_df = read_df("SELECT id,product_name FROM products ORDER BY product_name")
    product_map = dict(zip(product_df["product_name"], product_df["id"]))
    st.subheader("Receive stock")
    with st.form("receive_stock_form"):
        product_name = st.selectbox("Product", list(product_map))
        quantity = st.number_input("Quantity received", min_value=1, value=1, step=1)
        unit_cost = st.number_input("Cost per item (KSh)", min_value=0.0, value=0.0, step=25.0)
        supplier = st.text_input("Supplier / reference")
        save_stock = st.form_submit_button("Record stock purchase", type="primary")
    if save_stock:
        try:
            school_id = school_map[school_name]
            total_cost = quantity * unit_cost
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO stock(school_id,product_id,quantity_brought,term,year,unit_cost)
                           VALUES (%s,%s,%s,%s,%s,%s)""",
                        (school_id, product_map[product_name], quantity, term, year, unit_cost),
                    )
                    if total_cost > 0:
                        cur.execute(
                            """INSERT INTO financial_transactions(transaction_type,category,amount,description,school_id)
                               VALUES ('Expense','Stock purchase',%s,%s,%s)""",
                            (total_cost, f"{product_name}: {quantity} units. {supplier}".strip(), school_id),
                        )
                conn.commit()
            st.success("Stock purchase recorded.")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))

    st.divider()
    st.subheader("Estimated stock on hand")
    stock = read_df(
        """SELECT p.product_name,
             COALESCE(st.qty,0) AS received,
             COALESCE(tp.qty,0) AS produced,
             COALESCE(si.qty,0) AS sold,
             COALESCE(st.qty,0)+COALESCE(tp.qty,0)-COALESCE(si.qty,0) AS on_hand
           FROM products p
           LEFT JOIN (SELECT product_id,SUM(quantity_brought) qty FROM stock WHERE school_id=%s GROUP BY product_id) st ON st.product_id=p.id
           LEFT JOIN (SELECT product_id,SUM(quantity) qty FROM tailor_production WHERE school_id=%s GROUP BY product_id) tp ON tp.product_id=p.id
           LEFT JOIN (SELECT si.product_id,SUM(si.quantity) qty FROM sale_items si JOIN sales s ON s.id=si.sale_id WHERE s.school_id=%s GROUP BY si.product_id) si ON si.product_id=p.id
           ORDER BY p.product_name""",
        (school_map[school_name], school_map[school_name], school_map[school_name]),
    )
    stock = stock[(stock[["received", "produced", "sold"]].sum(axis=1) > 0)]
    if stock.empty:
        st.info("No stock movements or sales recorded for this school yet.")
    else:
        stock["Status"] = stock["on_hand"].apply(lambda value: "REORDER" if value <= 5 else "OK")
        st.dataframe(stock, use_container_width=True, hide_index=True)
        low = stock[stock["on_hand"] <= 5]
        if not low.empty:
            st.warning("Low stock: " + ", ".join(low["product_name"].astype(str)))


# ---------------------- BUSINESS FINANCE ----------------------

elif page == "Business Finance":
    show_hero("Business Finance", "Record transactions and review collections, expenses and investments.")
    a, b = st.columns(2)
    school_name = a.selectbox("School", ["All schools"] + list(school_map), key="finance_school")
    year = b.selectbox("Year", list(range(date.today().year, date.today().year - 5, -1)), key="finance_year")
    school_clause = "" if school_name == "All schools" else " AND school_id=%s"
    params = [year] + ([] if school_name == "All schools" else [school_map[school_name]])
    ledger = read_df(
        f"""SELECT transaction_date,transaction_type,category,amount,description,school_id,investor_name
            FROM financial_transactions
            WHERE EXTRACT(YEAR FROM transaction_date)=%s {school_clause}
            ORDER BY transaction_date DESC""",
        params,
    )

    sales_clause = "" if school_name == "All schools" else " AND school_id=%s"
    sales_params = [year] + ([] if school_name == "All schools" else [school_map[school_name]])
    sales_totals = read_df(
        f"""SELECT COALESCE(SUM(total_amount),0) invoiced,
                   COALESCE(SUM(amount_paid),0) collected,
                   COALESCE(SUM(balance_due),0) outstanding
            FROM sales WHERE year=%s {sales_clause}""",
        sales_params,
    ).iloc[0]

    income = float(ledger.loc[ledger["transaction_type"].str.lower().eq("income"), "amount"].sum()) if not ledger.empty else 0
    expenses = float(ledger.loc[ledger["transaction_type"].str.lower().eq("expense"), "amount"].sum()) if not ledger.empty else 0
    investments = float(ledger.loc[ledger["transaction_type"].str.lower().eq("investment"), "amount"].sum()) if not ledger.empty else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Sales invoiced", money(sales_totals["invoiced"]))
    m2.metric("Cash collected", money(sales_totals["collected"]))
    m3.metric("Outstanding", money(sales_totals["outstanding"]))
    m4.metric("Recorded expenses", money(expenses))
    st.caption("Sales totals come from the sales table. The ledger lists recorded financial transactions separately; avoid entering the same income or expense twice.")

    st.subheader("Add transaction")
    with st.form("add_finance_transaction"):
        x, y, z = st.columns(3)
        tx_type = x.selectbox("Type", ["Income", "Expense", "Investment", "Withdrawal"])
        category = y.text_input("Category", value="General")
        amount = z.number_input("Amount (KSh)", min_value=0.0, step=100.0)
        description = st.text_input("Description / reference")
        tx_school_name = st.selectbox("School allocation", ["Shared / all schools"] + list(school_map), key="finance_tx_school")
        investor = st.text_input("Investor name (optional)")
        submit_tx = st.form_submit_button("Save transaction", type="primary")
    if submit_tx:
        if amount <= 0:
            st.warning("Enter an amount greater than zero.")
        else:
            tx_school_id = None if tx_school_name == "Shared / all schools" else school_map[tx_school_name]
            try:
                run_sql(
                    """INSERT INTO financial_transactions(transaction_type,category,amount,description,school_id,investor_name)
                       VALUES (%s,%s,%s,%s,%s,%s)""",
                    (tx_type, category or "General", amount, description, tx_school_id, investor or None),
                )
                st.success("Transaction saved.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    st.subheader("Transaction ledger")
    if ledger.empty:
        st.info("No transactions for the selected year and school.")
    else:
        st.dataframe(ledger, use_container_width=True, hide_index=True)
        st.download_button("Export ledger CSV", ledger.to_csv(index=False).encode("utf-8"), "finance_ledger.csv", "text/csv")


# ---------------------- SALES REPORTS ----------------------

elif page == "Sales Reports":
    show_hero("Sales Reports", "Filter sales, review payment balances and export records.")
    a, b, c = st.columns(3)
    school_name = a.selectbox("School", ["All schools"] + list(school_map), key="report_school")
    year = b.selectbox("Year", list(range(date.today().year, date.today().year - 5, -1)), key="report_year")
    term = c.selectbox("Term", ["All terms", "Term 1", "Term 2", "Term 3"], key="report_term")
    clauses = ["s.year=%s"]
    params = [year]
    if school_name != "All schools":
        clauses.append("s.school_id=%s")
        params.append(school_map[school_name])
    if term != "All terms":
        clauses.append("s.term=%s")
        params.append(term)
    report = read_df(
        f"""SELECT s.id,s.receipt_number,s.sale_date,sc.school_name,c.customer_name,c.phone,
                   s.class_name,s.term,s.year,s.total_amount,s.amount_paid,s.balance_due,
                   s.payment_method,s.payment_status
            FROM sales s JOIN schools sc ON sc.id=s.school_id
            LEFT JOIN customers c ON c.id=s.customer_id
            WHERE {' AND '.join(clauses)} ORDER BY s.sale_date DESC""",
        params,
    )
    if report.empty:
        st.info("No sales match the selected filters.")
    else:
        x, y, z = st.columns(3)
        x.metric("Transactions", f"{len(report):,}")
        y.metric("Total invoiced", money(report["total_amount"].sum()))
        z.metric("Outstanding", money(report["balance_due"].fillna(0).sum()))
        st.dataframe(report.drop(columns=["id"]), use_container_width=True, hide_index=True)
        st.download_button(
            "Download sales report CSV",
            report.to_csv(index=False).encode("utf-8"),
            "uniform_sales_report.csv",
            "text/csv",
            type="primary",
        )


# ---------------------- TAILOR & PRODUCTION ----------------------

elif page == "Tailor & Production":
    show_hero("Tailor & Production", "Record finished garments and production costs.")
    product_df = read_df("SELECT id,product_name FROM products ORDER BY product_name")
    product_map = dict(zip(product_df["product_name"], product_df["id"]))
    with st.form("production_form"):
        a, b, c = st.columns(3)
        school_name = a.selectbox("School", list(school_map), key="production_school")
        product_name = b.selectbox("Product produced", list(product_map))
        quantity = c.number_input("Quantity produced", min_value=1, value=1, step=1)
        d, e, f = st.columns(3)
        cost = d.number_input("Cost per item (KSh)", min_value=0.0, step=25.0)
        tailor_name = e.text_input("Tailor / workshop")
        term = f.selectbox("Term", ["Term 1", "Term 2", "Term 3"], key="production_term")
        year = st.selectbox("Year", list(range(date.today().year, date.today().year - 5, -1)), key="production_year")
        notes = st.text_input("Notes")
        save_production = st.form_submit_button("Save production record", type="primary")
    if save_production:
        school_id = school_map[school_name]
        total_cost = float(quantity) * float(cost)
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO tailor_production(
                             school_id,product_id,quantity,cost_per_item,total_cost,tailor_name,notes,term,year
                           ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (school_id, product_map[product_name], quantity, cost, total_cost, tailor_name, notes, term, year),
                    )
                    if total_cost > 0:
                        cur.execute(
                            """INSERT INTO financial_transactions(transaction_type,category,amount,description,school_id)
                               VALUES ('Expense','Tailoring / production',%s,%s,%s)""",
                            (total_cost, f"{quantity} × {product_name}; {tailor_name}".strip(), school_id),
                        )
                conn.commit()
            st.success("Production record saved.")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))

    production = read_df(
        """SELECT tp.production_date,sc.school_name,p.product_name,tp.quantity,tp.cost_per_item,
                  tp.total_cost,tp.tailor_name,tp.notes,tp.term,tp.year
           FROM tailor_production tp JOIN schools sc ON sc.id=tp.school_id
           JOIN products p ON p.id=tp.product_id
           ORDER BY tp.production_date DESC LIMIT 300"""
    )
    st.subheader("Recent production records")
    if production.empty:
        st.info("No production records yet.")
    else:
        st.dataframe(production, use_container_width=True, hide_index=True)
        st.download_button(
            "Export production CSV",
            production.to_csv(index=False).encode("utf-8"),
            "tailor_production.csv",
            "text/csv",
        )
'''
path = "/mnt/data/uniforms.py"
with open(path, "w", encoding="utf-8") as f:
    f.write(code)

# Basic syntax validation before presenting the file.
compile(code, path, "exec")
print(f"Created and syntax-checked {path} ({len(code.splitlines())} lines).")
