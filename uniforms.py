
import os
import uuid
import base64
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st
import psycopg2

st.set_page_config(
    page_title="Uniform Sales Manager",
    page_icon="🧵",
    layout="wide",
)

SCHOOLS = ["LOVING BLOOMS SCHOOL", "WARIDI UTAWALA SCHOOL"]
LOGOS = {
    "LOVING BLOOMS SCHOOL": "loving_blooms_logo.png",
    "WARIDI UTAWALA SCHOOL": "waridi_logo.png",
}
PRODUCTS = [
    ("Skirt", 650),
    ("Blouse", 500),
    ("Socks", 200),
    ("Tracksuit Playgroup-PP2", 1600),
    ("Tracksuit G1-G6", 1800),
    ("Sweater", 1000),
    ("Tie/Bow Tie", 150),
    ("Short", 400),
    ("Halfcoat", 600),
    ("Fleece", 2500),
    ("Trouser", 650),
    ("T-shirt", 500),
    ("Wrap Skirt", 500),
    ("Half Sweater", 800),
]


# ---------------- DATABASE ----------------

def db():
    try:
        cfg = dict(st.secrets["postgres"])
    except Exception:
        cfg = {}

    host = cfg.get("host") or os.getenv("PGHOST")
    database = cfg.get("dbname") or cfg.get("database") or os.getenv("PGDATABASE")
    user = cfg.get("user") or os.getenv("PGUSER")
    password = cfg.get("password") or os.getenv("PGPASSWORD")
    port = cfg.get("port") or os.getenv("PGPORT", "5432")
    sslmode = cfg.get("sslmode") or os.getenv("PGSSLMODE", "prefer")

    if not all([host, database, user, password]):
        st.error(
            "Database credentials are missing. Configure host, dbname, user, "
            "password, and port under Streamlit Cloud → Settings → Secrets."
        )
        st.stop()

    return psycopg2.connect(
        host=host,
        dbname=database,
        user=user,
        password=password,
        port=int(port),
        sslmode=sslmode,
        connect_timeout=10,
    )


def read(sql, params=None):
    conn = db()
    try:
        return pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()


def write(sql, params=None, returning=False):
    conn = db()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            result = cur.fetchone() if returning else None
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def setup():
    statements = [
        """CREATE TABLE IF NOT EXISTS schools (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            default_price NUMERIC(12,2) NOT NULL DEFAULT 0,
            active BOOLEAN NOT NULL DEFAULT TRUE
        )""",
        """CREATE TABLE IF NOT EXISTS customers (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            phone TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS sales (
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
            notes TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS sale_items (
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
        )""",
        """CREATE TABLE IF NOT EXISTS school_product_prices (
            id SERIAL PRIMARY KEY,
            school_id INTEGER NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
            product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
            category TEXT NOT NULL DEFAULT 'Primary',
            class_name TEXT NOT NULL DEFAULT 'All',
            term TEXT NOT NULL DEFAULT 'All',
            year INTEGER NOT NULL DEFAULT 2026,
            price NUMERIC(12,2) NOT NULL DEFAULT 0,
            UNIQUE(school_id, product_id, category, class_name, term, year)
        )""",
        """CREATE TABLE IF NOT EXISTS stock (
            id SERIAL PRIMARY KEY,
            school_id INTEGER NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
            product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
            quantity INTEGER NOT NULL DEFAULT 0,
            reorder_level INTEGER NOT NULL DEFAULT 5,
            UNIQUE(school_id, product_id)
        )""",
        """CREATE TABLE IF NOT EXISTS investors (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            capital NUMERIC(12,2) NOT NULL DEFAULT 0,
            notes TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS financial_transactions (
            id SERIAL PRIMARY KEY,
            transaction_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            school_id INTEGER REFERENCES schools(id),
            transaction_type TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            amount NUMERIC(12,2) NOT NULL DEFAULT 0,
            payment_method TEXT DEFAULT 'Cash'
        )""",
        """CREATE TABLE IF NOT EXISTS tailor_production (
            id SERIAL PRIMARY KEY,
            school_id INTEGER REFERENCES schools(id),
            product_id INTEGER REFERENCES products(id),
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'Pending',
            tailor_name TEXT,
            cost_per_item NUMERIC(12,2) NOT NULL DEFAULT 0,
            order_date DATE NOT NULL DEFAULT CURRENT_DATE,
            due_date DATE,
            notes TEXT
        )""",
    ]

    conn = db()
    try:
        with conn.cursor() as cur:
            for statement in statements:
                cur.execute(statement)

            # Add missing columns to compatible older versions of sales.
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

            cur.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_receipt_number "
                "ON sales(receipt_number) WHERE receipt_number IS NOT NULL"
            )

            for school in SCHOOLS:
                cur.execute(
                    "INSERT INTO schools(name) VALUES (%s) ON CONFLICT(name) DO NOTHING",
                    (school,),
                )

            for name, price in PRODUCTS:
                cur.execute(
                    """INSERT INTO products(name, default_price)
                       VALUES (%s,%s) ON CONFLICT(name) DO NOTHING""",
                    (name, price),
                )

            cur.execute("SELECT id FROM schools")
            school_ids = [row[0] for row in cur.fetchall()]
            cur.execute("SELECT id, default_price FROM products WHERE active=TRUE")
            products = cur.fetchall()

            for school_id in school_ids:
                for product_id, price in products:
                    cur.execute(
                        """INSERT INTO school_product_prices
                           (school_id, product_id, category, class_name, term, year, price)
                           VALUES (%s,%s,'Primary','All','All',2026,%s)
                           ON CONFLICT(school_id, product_id, category, class_name, term, year)
                           DO NOTHING""",
                        (school_id, product_id, price),
                    )

            cur.execute(
                "INSERT INTO investors(name,capital) VALUES ('Gift',150000) "
                "ON CONFLICT(name) DO NOTHING"
            )
            cur.execute(
                "INSERT INTO investors(name,capital) VALUES ('Ken',100000) "
                "ON CONFLICT(name) DO NOTHING"
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def money(value):
    return f"KSh {float(value or 0):,.2f}"


def clear_cache():
    st.cache_data.clear()


def get_prices(school_id, category, class_name, term, year):
    return read(
        """SELECT p.id AS product_id, p.name,
           COALESCE((
             SELECT sp.price FROM school_product_prices sp
             WHERE sp.school_id=%s AND sp.product_id=p.id
               AND sp.category=%s
               AND sp.class_name IN (%s,'All')
               AND sp.term IN (%s,'All')
               AND sp.year IN (%s,2026)
             ORDER BY (sp.class_name=%s) DESC,
                      (sp.term=%s) DESC, (sp.year=%s) DESC
             LIMIT 1
           ),p.default_price) AS price
           FROM products p WHERE p.active=TRUE ORDER BY p.name""",
        [school_id, category, class_name, term, year,
         class_name, term, year],
    )


def get_logo_html(school_name):
    path = LOGOS.get(school_name)
    if not path or not os.path.exists(path):
        return ""
    with open(path, "rb") as logo_file:
        encoded = base64.b64encode(logo_file.read()).decode("utf-8")
    return f'<img src="data:image/png;base64,{encoded}" style="max-height:70px;">'


def save_sale(school_id, header, cart, discount, amount_paid, payment_method):
    subtotal = round(sum(float(x["price"]) * int(x["quantity"]) for x in cart), 2)
    total = max(0, round(subtotal - float(discount), 2))
    paid = min(max(0, float(amount_paid)), total)
    balance = round(total - paid, 2)
    receipt = (
        "UNI-" + datetime.now().strftime("%Y%m%d-%H%M%S")
        + "-" + uuid.uuid4().hex[:5].upper()
    )

    conn = db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO customers(name,phone) VALUES (%s,%s) RETURNING id",
                (header["customer_name"].strip(), header["customer_phone"].strip() or None),
            )
            customer_id = cur.fetchone()[0]

            cur.execute(
                """INSERT INTO sales
                   (receipt_number,school_id,customer_id,customer_name,customer_phone,
                    sale_date,term,year,class_name,subtotal,discount,total_amount,
                    amount_paid,balance_due,payment_method,notes)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   RETURNING id""",
                (
                    receipt, school_id, customer_id,
                    header["customer_name"].strip(),
                    header["customer_phone"].strip() or None,
                    datetime.combine(header["sale_date"], datetime.min.time()),
                    header["term"], header["year"], header["class_name"],
                    subtotal, float(discount), total, paid, balance,
                    payment_method, header["notes"].strip() or None,
                ),
            )
            sale_id = cur.fetchone()[0]

            for item in cart:
                qty = int(item["quantity"])
                price = float(item["price"])
                cur.execute(
                    """INSERT INTO sale_items
                       (sale_id,product_id,product_name,quantity,unit_price,line_total)
                       VALUES (%s,%s,%s,%s,%s,%s)""",
                    (sale_id, item["product_id"], item["name"],
                     qty, price, round(qty * price, 2)),
                )

            cur.execute(
                """INSERT INTO financial_transactions
                   (transaction_date,school_id,transaction_type,category,
                    description,amount,payment_method)
                   VALUES (%s,%s,'Income','Uniform sales',%s,%s,%s)""",
                (
                    datetime.combine(header["sale_date"], datetime.min.time()),
                    school_id, f"Payment for {receipt}", paid, payment_method,
                ),
            )
        conn.commit()
        return sale_id, receipt
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------- START APPLICATION ----------------

st.title("🧵 Uniform Sales & Business Manager")
st.caption("Point of sale • Receipts • Pricing • Stock • Finance • Reports")

try:
    setup()
except Exception as exc:
    st.error("Database setup failed. Check your PostgreSQL credentials and table compatibility.")
    st.code(str(exc))
    st.stop()

schools_df = read("SELECT id,name FROM schools ORDER BY name")
if schools_df.empty:
    st.error("No schools are configured.")
    st.stop()

with st.sidebar:
    st.header("Workspace")
    selected_school = st.selectbox("School", schools_df["name"].tolist())
    school_id = int(schools_df.loc[schools_df["name"] == selected_school, "id"].iloc[0])
    logo_path = LOGOS.get(selected_school, "")
    if logo_path and os.path.exists(logo_path):
        st.image(logo_path, use_container_width=True)
    page = st.radio(
        "Menu",
        [
            "Dashboard", "New Sale / POS", "Receipts & Issuing",
            "Price Management", "Inventory", "Business Finance",
            "Sales Reports", "Tailor & Production", "Settings",
        ],
    )

# ---------------- DASHBOARD ----------------

if page == "Dashboard":
    st.subheader(f"Dashboard — {selected_school}")
    today = date.today()
    month_start = today.replace(day=1)

    metrics = read(
        """SELECT
           COALESCE(SUM(total_amount) FILTER (WHERE sale_date::date=%s),0) AS today_sales,
           COALESCE(SUM(total_amount) FILTER (WHERE sale_date::date >= %s),0) AS month_sales,
           COALESCE(SUM(amount_paid) FILTER (WHERE sale_date::date >= %s),0) AS month_paid,
           COALESCE(SUM(balance_due),0) AS outstanding
           FROM sales WHERE school_id=%s""",
        [today, month_start, month_start, school_id],
    ).iloc[0]

    a, b, c, d = st.columns(4)
    a.metric("Sales today", money(metrics["today_sales"]))
    b.metric("Sales this month", money(metrics["month_sales"]))
    c.metric("Collected this month", money(metrics["month_paid"]))
    d.metric("Outstanding balance", money(metrics["outstanding"]))

    left, right = st.columns(2)
    with left:
        st.markdown("#### Sales trend — 30 days")
        trend = read(
            """SELECT sale_date::date AS day,SUM(total_amount) AS sales
               FROM sales WHERE school_id=%s
               AND sale_date >= CURRENT_DATE - INTERVAL '29 days'
               GROUP BY sale_date::date ORDER BY day""",
            [school_id],
        )
        if trend.empty:
            st.info("Sales will appear here after transactions are recorded.")
        else:
            st.line_chart(trend.set_index("day")["sales"])

    with right:
        st.markdown("#### Best-selling items")
        top = read(
            """SELECT si.product_name,SUM(si.quantity) AS units,
                      SUM(si.line_total) AS revenue
               FROM sale_items si JOIN sales s ON s.id=si.sale_id
               WHERE s.school_id=%s GROUP BY si.product_name
               ORDER BY units DESC LIMIT 10""",
            [school_id],
        )
        if top.empty:
            st.info("No product sales recorded yet.")
        else:
            st.bar_chart(top.set_index("product_name")["units"])
            st.dataframe(top, use_container_width=True, hide_index=True)

    st.markdown("#### Recent sales")
    recent = read(
        """SELECT receipt_number,sale_date,customer_name,class_name,
                  total_amount,amount_paid,balance_due
           FROM sales WHERE school_id=%s ORDER BY sale_date DESC LIMIT 10""",
        [school_id],
    )
    st.dataframe(recent, use_container_width=True, hide_index=True)

# ---------------- POS ----------------

elif page == "New Sale / POS":
    st.subheader("New sale")

    with st.form("sale_details"):
        a, b, c = st.columns(3)
        customer_name = a.text_input("Customer / parent name")
        customer_phone = b.text_input("Phone number")
        sale_date = c.date_input("Sale date", value=date.today())

        d, e, f = st.columns(3)
        class_name = d.text_input("Class / grade", value="Not specified")
        term = e.selectbox("Term", ["Term 1", "Term 2", "Term 3"])
        year = f.number_input("Year", min_value=2020, max_value=2100,
                              value=date.today().year, step=1)
        category = st.selectbox("Price category", ["Primary", "JSS", "Other"])
        notes = st.text_input("Notes")
        if st.form_submit_button("Save sale details"):
            st.session_state["sale_header"] = {
                "customer_name": customer_name,
                "customer_phone": customer_phone,
                "sale_date": sale_date,
                "class_name": class_name,
                "term": term,
                "year": int(year),
                "category": category,
                "notes": notes,
            }

    header = st.session_state.get("sale_header", {
        "customer_name": "", "customer_phone": "", "sale_date": date.today(),
        "class_name": "Not specified", "term": "Term 1",
        "year": date.today().year, "category": "Primary", "notes": "",
    })

    st.caption(
        f"Current customer: {header['customer_name'] or 'Not entered'} · "
        f"{header['class_name']} · {header['term']} {header['year']}"
    )

    price_df = get_prices(
        school_id, header["category"], header["class_name"],
        header["term"], header["year"],
    )

    with st.form("add_item"):
        a, b, c = st.columns([3, 1, 1])
        item_name = a.selectbox("Uniform item", price_df["name"].tolist())
        item_row = price_df.loc[price_df["name"] == item_name].iloc[0]
        unit_price = b.number_input(
            "Unit price (KSh)", min_value=0.0,
            value=float(item_row["price"]), step=50.0,
        )
        quantity = c.number_input("Quantity", min_value=1, value=1, step=1)
        add = st.form_submit_button("Add to cart")

    if add:
        cart = st.session_state.get("cart", [])
        existing = next(
            (x for x in cart if x["product_id"] == int(item_row["product_id"])
             and x["price"] == float(unit_price)),
            None,
        )
        if existing:
            existing["quantity"] += int(quantity)
        else:
            cart.append({
                "product_id": int(item_row["product_id"]),
                "name": item_name, "price": float(unit_price),
                "quantity": int(quantity),
            })
        st.session_state["cart"] = cart

    cart = st.session_state.get("cart", [])
    if not cart:
        st.info("The cart is empty. Add uniform items above.")
    else:
        cart_df = pd.DataFrame(cart)
        cart_df["line_total"] = cart_df["price"] * cart_df["quantity"]
        st.dataframe(
            cart_df.rename(columns={
                "name": "Item", "price": "Unit price",
                "quantity": "Quantity", "line_total": "Line total",
            }),
            use_container_width=True, hide_index=True,
        )

        subtotal = float(cart_df["line_total"].sum())
        a, b, c = st.columns(3)
        a.metric("Subtotal", money(subtotal))
        discount = b.number_input(
            "Discount (KSh)", min_value=0.0, max_value=subtotal,
            value=0.0, step=50.0,
        )
        total = max(0, subtotal - discount)
        c.metric("Total due", money(total))

        amount_paid = st.number_input(
            "Amount paid now (KSh)", min_value=0.0,
            max_value=float(total), value=float(total), step=100.0,
        )
        payment_method = st.selectbox(
            "Payment method", ["Cash", "M-Pesa", "Bank", "Card", "Other"]
        )

        a, b = st.columns(2)
        if a.button("Complete sale and save receipt", type="primary",
                    use_container_width=True):
            if not header["customer_name"].strip():
                st.error("Enter the customer name in Sale Details above.")
            else:
                try:
                    sale_id, receipt = save_sale(
                        school_id, header, cart, discount,
                        amount_paid, payment_method,
                    )
                    st.session_state["cart"] = []
                    st.session_state["last_receipt"] = receipt
                    clear_cache()
                    st.success(f"Sale saved. Receipt number: {receipt}")
                    st.rerun()
                except Exception as exc:
                    st.error("Could not save the sale.")
                    st.code(str(exc))

        if b.button("Clear cart", use_container_width=True):
            st.session_state["cart"] = []
            st.rerun()

    if st.session_state.get("last_receipt"):
        st.info(f"Last saved receipt: {st.session_state['last_receipt']}")

# ---------------- RECEIPTS AND ISSUING ----------------

elif page == "Receipts & Issuing":
    st.subheader("Receipts and uniform issuing")
    search = st.text_input("Search receipt, customer or phone")
    sql = """SELECT id,receipt_number,sale_date,customer_name,customer_phone,
                    class_name,term,year,total_amount,amount_paid,balance_due
             FROM sales WHERE school_id=%s"""
    params = [school_id]
    if search.strip():
        sql += """ AND (COALESCE(receipt_number,'') ILIKE %s
                    OR customer_name ILIKE %s
                    OR COALESCE(customer_phone,'') ILIKE %s)"""
        params.extend([f"%{search.strip()}%"] * 3)
    sql += " ORDER BY sale_date DESC LIMIT 200"
    sales = read(sql, params)

    if sales.empty:
        st.info("No matching receipts.")
    else:
        st.dataframe(sales.drop(columns=["id"]), use_container_width=True,
                     hide_index=True)
        options = {
            f"{r.receipt_number} — {r.customer_name} — {money(r.total_amount)}": int(r.id)
            for r in sales.itertuples()
        }
        chosen = st.selectbox("Open receipt", list(options))
        sale_id = options[chosen]

        sale_df = read(
            """SELECT s.*,sc.name AS school_name FROM sales s
               JOIN schools sc ON sc.id=s.school_id WHERE s.id=%s""",
            [sale_id],
        )
        items = read(
            """SELECT id,product_name,quantity,unit_price,line_total,issued,notes
               FROM sale_items WHERE sale_id=%s ORDER BY id""",
            [sale_id],
        )
        sale = sale_df.iloc[0].to_dict()

        edited = st.data_editor(
            items, use_container_width=True, hide_index=True,
            disabled=["id", "product_name", "quantity", "unit_price", "line_total"],
            column_config={
                "issued": st.column_config.CheckboxColumn("Issued to customer"),
                "notes": st.column_config.TextColumn("Issue notes"),
            },
            key=f"issue_{sale_id}",
        )

        if st.button("Save issuing updates"):
            conn = db()
            try:
                with conn.cursor() as cur:
                    for _, item in edited.iterrows():
                        cur.execute(
                            """UPDATE sale_items SET issued=%s,
                               issued_at=CASE
                                 WHEN %s AND issued_at IS NULL THEN CURRENT_TIMESTAMP
                                 WHEN NOT %s THEN NULL ELSE issued_at END,
                               notes=%s WHERE id=%s AND sale_id=%s""",
                            (
                                bool(item["issued"]), bool(item["issued"]),
                                bool(item["issued"]),
                                item["notes"] if pd.notna(item["notes"]) else None,
                                int(item["id"]), sale_id,
                            ),
                        )
                conn.commit()
                st.success("Issuing status saved.")
                st.rerun()
            except Exception as exc:
                conn.rollback()
                st.error(str(exc))
            finally:
                conn.close()

        st.markdown("#### Receipt preview")
        logo = get_logo_html(sale["school_name"])
        rows = ""
        for item in items.itertuples():
            status = "ISSUED" if bool(item.issued) else "NOT ISSUED"
            rows += (
                f"<tr><td>{item.product_name}</td><td>{item.quantity}</td>"
                f"<td>{float(item.unit_price):,.2f}</td>"
                f"<td>{float(item.line_total):,.2f}</td><td>{status}</td></tr>"
            )

        html = f"""<!doctype html><html><head><meta charset="utf-8">
        <style>
        body{{font-family:Arial,sans-serif;margin:25px;color:#172033}}
        .header{{display:flex;justify-content:space-between;align-items:center;
        border-bottom:2px solid #15284b;padding-bottom:12px}}
        h2{{color:#15284b}} table{{width:100%;border-collapse:collapse;margin-top:20px}}
        th,td{{border:1px solid #ddd;padding:9px;text-align:left}}
        th{{background:#eef2f8}} .totals{{margin:20px 0 0 auto;width:300px}}
        .totals p{{display:flex;justify-content:space-between}}
        @media print{{button{{display:none}}}}
        </style></head><body>
        <div class="header"><div>{logo}</div><div><h2>{sale['school_name']}</h2>
        <b>UNIFORM SALES RECEIPT</b></div><div>{sale['receipt_number']}<br>
        {sale['sale_date']}</div></div>
        <p><b>Customer:</b> {sale['customer_name']}<br>
        <b>Phone:</b> {sale.get('customer_phone') or '—'}<br>
        <b>Class:</b> {sale['class_name']} | <b>Term:</b> {sale['term']}
        | <b>Year:</b> {sale['year']}</p>
        <table><tr><th>Item</th><th>Qty</th><th>Unit price</th>
        <th>Total</th><th>Issue status</th></tr>{rows}</table>
        <div class="totals">
        <p><span>Subtotal</span><span>{money(sale['subtotal'])}</span></p>
        <p><span>Discount</span><span>{money(sale['discount'])}</span></p>
        <p><b>Total</b><b>{money(sale['total_amount'])}</b></p>
        <p><span>Paid</span><span>{money(sale['amount_paid'])}</span></p>
        <p><b>Balance due</b><b>{money(sale['balance_due'])}</b></p>
        </div><p>Payment method: {sale['payment_method']}</p>
        <button onclick="window.print()">Print receipt</button>
        </body></html>"""
        st.components.v1.html(html, height=650, scrolling=True)
        st.download_button(
            "Download receipt HTML", html,
            file_name=f"{sale['receipt_number']}.html",
            mime="text/html",
        )

# ---------------- PRICE MANAGEMENT ----------------

elif page == "Price Management":
    st.subheader("School-specific prices")
    products = read("SELECT id,name,default_price FROM products WHERE active=TRUE ORDER BY name")

    with st.form("price_form"):
        a, b, c = st.columns(3)
        product_name = a.selectbox("Product", products["name"].tolist())
        category = b.selectbox("Category", ["Primary", "JSS", "Other"])
        class_name = c.text_input("Class (use All for default)", value="All")
        d, e, f = st.columns(3)
        term = d.selectbox("Term", ["All", "Term 1", "Term 2", "Term 3"])
        year = e.number_input("Year", min_value=2020, max_value=2100,
                              value=date.today().year)
        default = float(products.loc[products.name == product_name, "default_price"].iloc[0])
        price = f.number_input("Price (KSh)", min_value=0.0,
                               value=default, step=50.0)
        save = st.form_submit_button("Save price")

    if save:
        pid = int(products.loc[products.name == product_name, "id"].iloc[0])
        write(
            """INSERT INTO school_product_prices
               (school_id,product_id,category,class_name,term,year,price)
               VALUES (%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT(school_id,product_id,category,class_name,term,year)
               DO UPDATE SET price=EXCLUDED.price""",
            (school_id, pid, category, class_name.strip() or "All",
             term, int(year), float(price)),
        )
        clear_cache()
        st.success("Price saved.")

    prices = read(
        """SELECT p.name AS product,sp.category,sp.class_name,sp.term,sp.year,sp.price
           FROM school_product_prices sp JOIN products p ON p.id=sp.product_id
           WHERE sp.school_id=%s ORDER BY p.name,sp.category,sp.class_name,sp.term,sp.year""",
        [school_id],
    )
    st.dataframe(prices, use_container_width=True, hide_index=True)
    st.download_button("Download price list CSV", prices.to_csv(index=False),
                       "price_list.csv", "text/csv")

# ---------------- INVENTORY ----------------

elif page == "Inventory":
    st.subheader("Inventory")
    products = read("SELECT id,name FROM products WHERE active=TRUE ORDER BY name")
    with st.form("stock_form"):
        product_name = st.selectbox("Product", products["name"].tolist())
        quantity = st.number_input("Quantity on hand", min_value=0, value=0)
        reorder = st.number_input("Low-stock alert level", min_value=0, value=5)
        save = st.form_submit_button("Save stock")
    if save:
        pid = int(products.loc[products.name == product_name, "id"].iloc[0])
        write(
            """INSERT INTO stock(school_id,product_id,quantity,reorder_level)
               VALUES (%s,%s,%s,%s)
               ON CONFLICT(school_id,product_id)
               DO UPDATE SET quantity=EXCLUDED.quantity,reorder_level=EXCLUDED.reorder_level""",
            (school_id, pid, int(quantity), int(reorder)),
        )
        st.success("Stock saved.")

    stock = read(
        """SELECT p.name AS product,COALESCE(s.quantity,0) AS quantity,
                  COALESCE(s.reorder_level,5) AS reorder_level
           FROM products p LEFT JOIN stock s
             ON s.product_id=p.id AND s.school_id=%s
           WHERE p.active=TRUE ORDER BY p.name""",
        [school_id],
    )
    if not stock.empty:
        stock["status"] = stock.apply(
            lambda r: "LOW STOCK" if r.quantity <= r.reorder_level else "OK",
            axis=1,
        )
        st.dataframe(stock, use_container_width=True, hide_index=True)
        low = stock.loc[stock.status == "LOW STOCK", "product"].tolist()
        if low:
            st.warning("Low stock: " + ", ".join(low))
    st.caption("Stock is manually updated. This version does not automatically deduct stock when items are sold.")

# ---------------- FINANCE ----------------

elif page == "Business Finance":
    st.subheader("Business finance")
    tab1, tab2, tab3 = st.tabs(["Record transaction", "Transactions", "Investors"])

    with tab1:
        with st.form("transaction_form"):
            a, b, c = st.columns(3)
            kind = a.selectbox("Transaction type", ["Income", "Expense", "Capital contribution", "Withdrawal"])
            category = b.selectbox("Category", [
                "Uniform sales", "Rent", "Salaries", "Materials",
                "Tailoring", "Transport", "Utilities", "Capital", "Other",
            ])
            amount = c.number_input("Amount (KSh)", min_value=0.0, value=0.0, step=100.0)
            description = st.text_input("Description")
            d, e = st.columns(2)
            trans_date = d.date_input("Date", value=date.today())
            method = e.selectbox("Payment method", ["Cash", "M-Pesa", "Bank", "Card", "Other"])
            save = st.form_submit_button("Record transaction")
        if save:
            if amount <= 0:
                st.error("Enter an amount greater than zero.")
            else:
                write(
                    """INSERT INTO financial_transactions
                       (transaction_date,school_id,transaction_type,category,description,amount,payment_method)
                       VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                    (datetime.combine(trans_date, datetime.min.time()),
                     school_id, kind, category, description, float(amount), method),
                )
                st.success("Transaction recorded.")

    with tab2:
        transactions = read(
            """SELECT transaction_date,transaction_type,category,description,amount,payment_method
               FROM financial_transactions WHERE school_id=%s
               ORDER BY transaction_date DESC LIMIT 500""",
            [school_id],
        )
        st.dataframe(transactions, use_container_width=True, hide_index=True)
        st.download_button("Download transactions CSV",
                           transactions.to_csv(index=False),
                           "transactions.csv", "text/csv")

    with tab3:
        investors = read("SELECT name,capital,notes FROM investors ORDER BY name")
        st.dataframe(investors, use_container_width=True, hide_index=True)
        with st.form("investor_form"):
            name = st.text_input("Investor name")
            capital = st.number_input("Capital amount (KSh)", min_value=0.0, value=0.0)
            notes = st.text_input("Notes")
            save = st.form_submit_button("Add capital")
        if save:
            if not name.strip():
                st.error("Enter an investor name.")
            else:
                write(
                    """INSERT INTO investors(name,capital,notes) VALUES (%s,%s,%s)
                       ON CONFLICT(name) DO UPDATE SET capital=investors.capital+EXCLUDED.capital,
                       notes=COALESCE(EXCLUDED.notes,investors.notes)""",
                    (name.strip(), float(capital), notes.strip() or None),
                )
                st.success("Investor saved.")

# ---------------- REPORTS ----------------

elif page == "Sales Reports":
    st.subheader("Sales reports")
    a, b = st.columns(2)
    start = a.date_input("From", value=date.today().replace(day=1))
    end = b.date_input("To", value=date.today())

    if start > end:
        st.error("The start date must be before or equal to the end date.")
    else:
        report = read(
            """SELECT receipt_number,sale_date,customer_name,customer_phone,class_name,
                      term,year,subtotal,discount,total_amount,amount_paid,balance_due,payment_method
               FROM sales WHERE school_id=%s AND sale_date::date BETWEEN %s AND %s
               ORDER BY sale_date DESC""",
            [school_id, start, end],
        )
        a, b, c, d = st.columns(4)
        a.metric("Receipts", len(report))
        b.metric("Sales", money(report.total_amount.sum() if not report.empty else 0))
        c.metric("Collected", money(report.amount_paid.sum() if not report.empty else 0))
        d.metric("Outstanding", money(report.balance_due.sum() if not report.empty else 0))
        st.dataframe(report, use_container_width=True, hide_index=True)
        st.download_button("Download sales report", report.to_csv(index=False),
                           "sales_report.csv", "text/csv")

        items = read(
            """SELECT si.product_name,SUM(si.quantity) AS units,
                      SUM(si.line_total) AS revenue
               FROM sale_items si JOIN sales s ON s.id=si.sale_id
               WHERE s.school_id=%s AND s.sale_date::date BETWEEN %s AND %s
               GROUP BY si.product_name ORDER BY revenue DESC""",
            [school_id, start, end],
        )
        st.markdown("#### Product performance")
        if not items.empty:
            st.dataframe(items, use_container_width=True, hide_index=True)
            st.bar_chart(items.set_index("product_name")["revenue"])

# ---------------- TAILOR / PRODUCTION ----------------

elif page == "Tailor & Production":
    st.subheader("Tailor and production orders")
    products = read("SELECT id,name FROM products WHERE active=TRUE ORDER BY name")

    with st.form("production_form"):
        a, b, c = st.columns(3)
        product_name = a.selectbox("Product", products["name"].tolist())
        quantity = b.number_input("Quantity", min_value=1, value=1)
        tailor = c.text_input("Tailor / supplier")
        d, e, f = st.columns(3)
        status = d.selectbox("Status", ["Pending", "In progress", "Completed", "Collected", "Cancelled"])
        cost = e.number_input("Cost per item (KSh)", min_value=0.0, value=0.0)
        due = f.date_input("Expected completion", value=date.today() + timedelta(days=7))
        notes = st.text_input("Notes")
        save = st.form_submit_button("Save production order")

    if save:
        pid = int(products.loc[products.name == product_name, "id"].iloc[0])
        write(
            """INSERT INTO tailor_production
               (school_id,product_id,product_name,quantity,status,tailor_name,cost_per_item,due_date,notes)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (school_id, pid, product_name, int(quantity), status,
             tailor, float(cost), due, notes),
        )
        st.success("Production order saved.")

    orders = read(
        """SELECT id,product_name,quantity,status,tailor_name,cost_per_item,
                  order_date,due_date,notes FROM tailor_production
           WHERE school_id=%s ORDER BY id DESC LIMIT 300""",
        [school_id],
    )
    st.dataframe(orders, use_container_width=True, hide_index=True)

    if not orders.empty:
        selected_id = st.selectbox("Production order ID", orders.id.astype(int).tolist())
        new_status = st.selectbox(
            "Update status",
            ["Pending", "In progress", "Completed", "Collected", "Cancelled"],
        )
        if st.button("Update order status"):
            write(
                "UPDATE tailor_production SET status=%s WHERE id=%s AND school_id=%s",
                (new_status, int(selected_id), school_id),
            )
            st.success("Status updated.")
            st.rerun()

# ---------------- SETTINGS ----------------

elif page == "Settings":
    st.subheader("Schools and products")

    st.markdown("#### Add school")
    with st.form("add_school"):
        new_school = st.text_input("School name")
        add = st.form_submit_button("Add school")
    if add:
        if not new_school.strip():
            st.error("Enter a school name.")
        else:
            write(
                "INSERT INTO schools(name) VALUES (%s) ON CONFLICT(name) DO NOTHING",
                (new_school.strip().upper(),),
            )
            clear_cache()
            st.success("School saved.")

    st.divider()
    st.markdown("#### Add product")
    with st.form("add_product"):
        product_name = st.text_input("Product name")
        default_price = st.number_input("Default price (KSh)", min_value=0.0, value=0.0)
        add = st.form_submit_button("Add product")
    if add:
        if not product_name.strip():
            st.error("Enter a product name.")
        else:
            write(
                """INSERT INTO products(name,default_price) VALUES (%s,%s)
                   ON CONFLICT(name) DO NOTHING""",
                (product_name.strip(), float(default_price)),
            )
            row = write(
                "SELECT id FROM products WHERE name=%s",
                (product_name.strip(),), returning=True,
            )
            if row:
                write(
                    """INSERT INTO school_product_prices
                       (school_id,product_id,category,class_name,term,year,price)
                       VALUES (%s,%s,'Primary','All','All',%s,%s)
                       ON CONFLICT(school_id,product_id,category,class_name,term,year)
                       DO NOTHING""",
                    (school_id, row[0], date.today().year, float(default_price)),
                )
            clear_cache()
            st.success("Product saved.")

    st.markdown("#### Current catalogue")
    catalogue = read("SELECT id,name,default_price,active FROM products ORDER BY name")
    st.dataframe(catalogue, use_container_width=True, hide_index=True)

    st.caption("Missing tables are created automatically. Existing records are not intentionally deleted.")
    st.warning("Back up your PostgreSQL database before making major changes.")
