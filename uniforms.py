import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components
from decimal import Decimal


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Uniform Business Management System",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =========================================================
# CSS — MAKE STREAMLIT LOOK LIKE AN ACTUAL APPLICATION
# =========================================================

st.markdown("""
<style>

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
[data-testid="stToolbar"] {visibility: hidden;}

.stApp {
    background: #eef4f8;
}

[data-testid="stSidebar"] {
    background: #0b1f3a;
}

[data-testid="stSidebar"] * {
    color: white !important;
}

.main-title {
    font-size: 28px;
    font-weight: 800;
    color: #0b1f3a;
    margin-bottom: 5px;
}

.subtitle {
    color: #64748b;
    font-size: 14px;
    margin-bottom: 25px;
}

.app-header {
    background: linear-gradient(135deg, #0b1f3a, #163b68);
    padding: 22px 28px;
    border-radius: 14px;
    color: white;
    margin-bottom: 25px;
}

.app-header h1 {
    color: white;
    margin: 0;
    font-size: 27px;
}

.app-header p {
    margin: 5px 0 0 0;
    color: #dbeafe;
}

.metric-card {
    background: white;
    padding: 20px;
    border-radius: 14px;
    box-shadow: 0 3px 12px rgba(0,0,0,0.06);
    border: 1px solid #e2e8f0;
}

.metric-title {
    color: #64748b;
    font-size: 13px;
    font-weight: 600;
}

.metric-value {
    color: #0b1f3a;
    font-size: 26px;
    font-weight: 800;
    margin-top: 5px;
}

.section-card {
    background: white;
    padding: 20px;
    border-radius: 14px;
    box-shadow: 0 3px 12px rgba(0,0,0,0.05);
    border: 1px solid #e2e8f0;
    margin-bottom: 20px;
}

.receipt-box {
    background: white;
    padding: 25px;
    border-radius: 10px;
    border: 1px solid #ddd;
}

button[kind="primary"] {
    background: #f28c28;
    border-color: #f28c28;
}

button[kind="primary"]:hover {
    background: #d97706;
    border-color: #d97706;
}

.low-stock {
    color: #dc2626;
    font-weight: 700;
}

.good-stock {
    color: #15803d;
    font-weight: 700;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_connection():
    try:
        db = st.secrets["postgres"]

        return psycopg2.connect(
            host=db["host"],
            port=db["port"],
            database=db["database"],
            user=db["user"],
            password=db["password"],
            sslmode=db.get("sslmode", "require")
        )

    except Exception as e:
        st.error(f"Database connection failed: {e}")
        st.stop()


# =========================================================
# DATABASE HELPERS
# =========================================================

def execute_query(query, params=None, fetch=False):
    conn = get_connection()

    try:
        cur = conn.cursor()
        cur.execute(query, params or ())

        if fetch:
            result = cur.fetchall()
        else:
            result = None

        conn.commit()
        cur.close()

        return result

    except Exception as e:
        conn.rollback()
        st.error(f"Database error: {e}")
        return None

    finally:
        conn.close()


def fetch_dataframe(query, params=None):
    conn = get_connection()

    try:
        return pd.read_sql_query(query, conn, params=params)

    except Exception as e:
        st.error(f"Database error: {e}")
        return pd.DataFrame()

    finally:
        conn.close()


def money(value):
    try:
        return f"KSh {float(value):,.2f}"
    except Exception:
        return "KSh 0.00"


# =========================================================
# DATABASE SETUP
# =========================================================

def setup_database():

    conn = get_connection()

    try:
        cur = conn.cursor()

        # -------------------------------------------------
        # SCHOOLS
        # -------------------------------------------------

        cur.execute("""
            CREATE TABLE IF NOT EXISTS schools (
                school_id SERIAL PRIMARY KEY,
                school_name VARCHAR(100) UNIQUE NOT NULL
            );
        """)

        # -------------------------------------------------
        # PRODUCTS
        # -------------------------------------------------

        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                product_id SERIAL PRIMARY KEY,
                product_name VARCHAR(100) UNIQUE NOT NULL,
                price NUMERIC(12,2) DEFAULT 0,
                cost_price NUMERIC(12,2) DEFAULT 0
            );
        """)

        # -------------------------------------------------
        # CUSTOMERS
        # -------------------------------------------------

        cur.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                customer_id SERIAL PRIMARY KEY,
                customer_name VARCHAR(150),
                phone VARCHAR(30)
            );
        """)

        # -------------------------------------------------
        # SALES
        # -------------------------------------------------

        cur.execute("""
            CREATE TABLE IF NOT EXISTS sales (
                sale_id SERIAL PRIMARY KEY,
                sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                school_id INT REFERENCES schools(school_id),
                customer_id INT REFERENCES customers(customer_id),
                class_name VARCHAR(50),
                total_amount NUMERIC(12,2) DEFAULT 0,
                payment_method VARCHAR(50),
                payment_status VARCHAR(30) DEFAULT 'Paid',
                term VARCHAR(30),
                year INT
            );
        """)

        # -------------------------------------------------
        # SALE ITEMS
        # -------------------------------------------------

        cur.execute("""
            CREATE TABLE IF NOT EXISTS sale_items (
                sale_item_id SERIAL PRIMARY KEY,
                sale_id INT REFERENCES sales(sale_id) ON DELETE CASCADE,
                product_id INT REFERENCES products(product_id),
                quantity INT,
                unit_price NUMERIC(12,2),
                line_total NUMERIC(12,2),
                issued BOOLEAN DEFAULT TRUE
            );
        """)

        # -------------------------------------------------
        # SCHOOL PRODUCT PRICES
        # -------------------------------------------------

        cur.execute("""
            CREATE TABLE IF NOT EXISTS school_product_prices (
                school_product_price_id SERIAL PRIMARY KEY,
                school_id INT REFERENCES schools(school_id) ON DELETE CASCADE,
                category_name VARCHAR(100),
                product_id INT REFERENCES products(product_id) ON DELETE CASCADE,
                price NUMERIC(12,2),
                UNIQUE(school_id, category_name, product_id)
            );
        """)

        # -------------------------------------------------
        # STOCK
        # -------------------------------------------------

        cur.execute("""
            CREATE TABLE IF NOT EXISTS stock (
                stock_id SERIAL PRIMARY KEY,
                school_id INT REFERENCES schools(school_id),
                product_id INT REFERENCES products(product_id),
                quantity_brought INT,
                date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                term VARCHAR(30),
                year INT,
                unit_cost NUMERIC(12,2)
            );
        """)

        # -------------------------------------------------
        # UNIFORM SETS
        # -------------------------------------------------

        cur.execute("""
            CREATE TABLE IF NOT EXISTS uniform_sets (
                set_id SERIAL PRIMARY KEY,
                school_id INT REFERENCES schools(school_id) ON DELETE CASCADE,
                set_name VARCHAR(100)
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS set_items (
                set_item_id SERIAL PRIMARY KEY,
                set_id INT REFERENCES uniform_sets(set_id) ON DELETE CASCADE,
                product_id INT REFERENCES products(product_id),
                quantity INT
            );
        """)

        # -------------------------------------------------
        # INVESTORS
        # -------------------------------------------------

        cur.execute("""
            CREATE TABLE IF NOT EXISTS investors (
                investor_id SERIAL PRIMARY KEY,
                investor_name VARCHAR(100) UNIQUE NOT NULL,
                active BOOLEAN DEFAULT TRUE
            );
        """)

        # -------------------------------------------------
        # FINANCIAL TRANSACTIONS
        # -------------------------------------------------

        cur.execute("""
            CREATE TABLE IF NOT EXISTS financial_transactions (
                transaction_id SERIAL PRIMARY KEY,
                transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                transaction_type VARCHAR(50),
                category VARCHAR(100),
                description TEXT,
                amount NUMERIC(12,2),
                investor_id INT REFERENCES investors(investor_id),
                term VARCHAR(30),
                year INT
            );
        """)

        # Add source references to finance table
        cur.execute("""
            ALTER TABLE financial_transactions
            ADD COLUMN IF NOT EXISTS sale_id INT
            REFERENCES sales(sale_id) ON DELETE CASCADE;
        """)

        cur.execute("""
            ALTER TABLE financial_transactions
            ADD COLUMN IF NOT EXISTS stock_id INT
            REFERENCES stock(stock_id) ON DELETE CASCADE;
        """)

        cur.execute("""
            ALTER TABLE financial_transactions
            ADD COLUMN IF NOT EXISTS production_id INT
            REFERENCES tailor_production(production_id) ON DELETE CASCADE;
        """)

        # -------------------------------------------------
        # TAILOR PRODUCTION
        # -------------------------------------------------

        cur.execute("""
            CREATE TABLE IF NOT EXISTS tailor_production (
                production_id SERIAL PRIMARY KEY,
                school_id INT REFERENCES schools(school_id),
                product_id INT REFERENCES products(product_id),
                tailor_name VARCHAR(150),
                quantity_produced INT,
                cost_per_item NUMERIC(12,2),
                amount_paid NUMERIC(12,2),
                production_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                term VARCHAR(30),
                year INT,
                notes TEXT
            );
        """)

        # The FK above can fail if production table doesn't exist yet.
        # Ensure source reference exists after table creation.
        cur.execute("""
            ALTER TABLE financial_transactions
            ADD COLUMN IF NOT EXISTS production_id INT
            REFERENCES tailor_production(production_id) ON DELETE CASCADE;
        """)

        # -------------------------------------------------
        # ENSURE CLASS COLUMN EXISTS FOR OLD DATABASES
        # -------------------------------------------------

        cur.execute("""
            ALTER TABLE sales
            ADD COLUMN IF NOT EXISTS class_name VARCHAR(50);
        """)

        # -------------------------------------------------
        # REAL SCHOOLS
        # -------------------------------------------------

        cur.execute("""
            INSERT INTO schools (school_name)
            VALUES
                ('LOVING BLOOMS SCHOOL'),
                ('WARIDI UTAWALA SCHOOL')
            ON CONFLICT (school_name) DO NOTHING;
        """)

        # -------------------------------------------------
        # REAL INVESTORS
        # -------------------------------------------------

        cur.execute("""
            INSERT INTO investors (investor_name, active)
            VALUES
                ('Gift', TRUE),
                ('Ken', TRUE)
            ON CONFLICT (investor_name)
            DO UPDATE SET active = TRUE;
        """)

        # -------------------------------------------------
        # INITIAL CAPITAL
        # Only insert if investor has no capital contribution.
        # -------------------------------------------------

        cur.execute("""
            SELECT investor_id, investor_name
            FROM investors
            WHERE investor_name IN ('Gift', 'Ken');
        """)

        investors = cur.fetchall()

        capital = {
            "Gift": 150000,
            "Ken": 100000
        }

        for investor_id, investor_name in investors:

            cur.execute("""
                SELECT COUNT(*)
                FROM financial_transactions
                WHERE investor_id = %s
                  AND transaction_type = 'Capital Contribution';
            """, (investor_id,))

            count = cur.fetchone()[0]

            if count == 0:
                cur.execute("""
                    INSERT INTO financial_transactions
                    (
                        transaction_type,
                        category,
                        description,
                        amount,
                        investor_id
                    )
                    VALUES
                    (
                        'Capital Contribution',
                        'Owner Capital',
                        'Initial capital contribution',
                        %s,
                        %s
                    );
                """, (capital[investor_name], investor_id))

        # -------------------------------------------------
        # PRODUCTS
        # -------------------------------------------------

        products = [
            ("Skirt", 650),
            ("Blouse", 500),
            ("Socks", 200),
            ("Tracksuit Playgroup-PP2", 1600),
            ("Tracksuit G1-G6", 1800),
            ("Sweater", 1000),
            ("Tie", 150),
            ("Bow Tie", 150),
            ("Short", 400),
            ("Halfcoat", 600),
            ("Fleece", 2500),
            ("Trouser", 650),
            ("T-Shirt", 500),
            ("Wrap Skirt", 500),
            ("Half Sweater", 800)
        ]

        for name, price in products:

            cur.execute("""
                INSERT INTO products
                (product_name, price, cost_price)
                VALUES (%s, %s, 0)
                ON CONFLICT (product_name)
                DO NOTHING;
            """, (name, price))

        conn.commit()
        cur.close()

    except Exception as e:
        conn.rollback()
        st.error(f"Database setup error: {e}")

    finally:
        conn.close()


# =========================================================
# SESSION STATE
# =========================================================

if "cart" not in st.session_state:
    st.session_state.cart = []

if "last_receipt" not in st.session_state:
    st.session_state.last_receipt = None

if "page" not in st.session_state:
    st.session_state.page = "Dashboard"


# =========================================================
# RUN DATABASE SETUP
# =========================================================

setup_database()


# =========================================================
# RECEIPT FUNCTIONS
# =========================================================

def get_receipt(sale_id):

    sale = fetch_dataframe("""
        SELECT
            s.sale_id,
            s.sale_date,
            s.class_name,
            s.total_amount,
            s.payment_method,
            s.payment_status,
            s.term,
            s.year,
            sc.school_name,
            c.customer_name,
            c.phone
        FROM sales s
        LEFT JOIN schools sc
            ON s.school_id = sc.school_id
        LEFT JOIN customers c
            ON s.customer_id = c.customer_id
        WHERE s.sale_id = %s
    """, (sale_id,))

    if sale.empty:
        return None

    items = fetch_dataframe("""
        SELECT
            p.product_name,
            si.quantity,
            si.unit_price,
            si.line_total,
            si.issued
        FROM sale_items si
        JOIN products p
            ON si.product_id = p.product_id
        WHERE si.sale_id = %s
        ORDER BY si.sale_item_id
    """, (sale_id,))

    return {
        "header": sale.iloc[0].to_dict(),
        "items": items
    }


def render_receipt(receipt):

    if not receipt:
        st.warning("Receipt not found.")
        return

    h = receipt["header"]
    items = receipt["items"]

    item_rows = ""

    for _, row in items.iterrows():

        item_rows += f"""
        <tr>
            <td>{row['product_name']}</td>
            <td>{int(row['quantity'])}</td>
            <td>KSh {float(row['unit_price']):,.2f}</td>
            <td>KSh {float(row['line_total']):,.2f}</td>
        </tr>
        """

    sale_date = h["sale_date"]

    if hasattr(sale_date, "strftime"):
        sale_date = sale_date.strftime("%d %b %Y, %I:%M %p")

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>

    <style>

    body {{
        font-family: Arial, sans-serif;
        background: #f3f4f6;
        padding: 20px;
    }}

    .receipt {{
        width: 600px;
        max-width: 100%;
        margin: auto;
        background: white;
        padding: 30px;
        border-radius: 8px;
    }}

    .header {{
        text-align: center;
        border-bottom: 2px solid #111827;
        padding-bottom: 15px;
        margin-bottom: 15px;
    }}

    .header h2 {{
        margin: 0;
        color: #0b1f3a;
    }}

    .details {{
        margin-bottom: 20px;
        line-height: 1.7;
    }}

    table {{
        width: 100%;
        border-collapse: collapse;
    }}

    th, td {{
        border-bottom: 1px solid #ddd;
        padding: 8px;
        text-align: left;
    }}

    th {{
        background: #f3f4f6;
    }}

    .total {{
        text-align: right;
        font-size: 20px;
        font-weight: bold;
        margin-top: 20px;
    }}

    .footer {{
        text-align: center;
        margin-top: 25px;
        color: #555;
    }}

    .print-button {{
        display: block;
        margin: 20px auto;
        padding: 12px 25px;
        background: #0b1f3a;
        color: white;
        border: none;
        border-radius: 6px;
        cursor: pointer;
        font-size: 15px;
    }}

    @media print {{

        body {{
            background: white;
            padding: 0;
        }}

        .receipt {{
            width: 100%;
            padding: 10px;
        }}

        .print-button {{
            display: none;
        }}

    }}

    </style>

    </head>

    <body>

    <div class="receipt">

        <div class="header">

            <h2>UNIFORM BUSINESS</h2>

            <p>{h.get('school_name') or ''}</p>

            <strong>SALES RECEIPT</strong>

        </div>

        <div class="details">

            <strong>Receipt No:</strong> {h.get('sale_id')}<br>

            <strong>Date:</strong> {sale_date}<br>

            <strong>Customer/Student:</strong>
            {h.get('customer_name') or ''}<br>

            <strong>Phone:</strong>
            {h.get('phone') or ''}<br>

            <strong>Class/Grade:</strong>
            {h.get('class_name') or ''}<br>

            <strong>Term:</strong>
            {h.get('term') or ''}<br>

            <strong>Year:</strong>
            {h.get('year') or ''}<br>

            <strong>Payment:</strong>
            {h.get('payment_method') or ''}

        </div>

        <table>

            <thead>

                <tr>
                    <th>Item</th>
                    <th>Qty</th>
                    <th>Price</th>
                    <th>Total</th>
                </tr>

            </thead>

            <tbody>

                {item_rows}

            </tbody>

        </table>

        <div class="total">
            TOTAL: KSh {float(h.get('total_amount') or 0):,.2f}
        </div>

        <div class="footer">
            Thank you for your business.
        </div>

        <button class="print-button" onclick="window.print()">
            🖨️ Print Receipt
        </button>

    </div>

    </body>
    </html>
    """

    components.html(
        html,
        height=700,
        scrolling=True
    )


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.markdown("""
    <div style="
        text-align:center;
        padding:10px 0 20px 0;
        font-size:20px;
        font-weight:800;
    ">
        🏫 UNIFORM BUSINESS
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 🏠 MAIN")

    page = st.radio(
        "Navigation",
        [
            "Dashboard",
            "New Sale",
            "Sales History",
            "Stock Management",
            "Price Management",
            "Tailor & Production",
            "Business Finance",
            "ML & Forecasting",
            "System Management"
        ],
        index=[
            "Dashboard",
            "New Sale",
            "Sales History",
            "Stock Management",
            "Price Management",
            "Tailor & Production",
            "Business Finance",
            "ML & Forecasting",
            "System Management"
        ].index(st.session_state.page),
        label_visibility="collapsed",
        key="navigation"
    )

    st.session_state.page = page

    st.markdown("---")

    st.caption("Uniform Business Management System")
    st.caption("PostgreSQL + Python + Streamlit")


# =========================================================
# APP HEADER
# =========================================================

st.markdown("""
<div class="app-header">

    <h1>🏫 UNIFORM BUSINESS MANAGEMENT SYSTEM</h1>

    <p>
        Sales • Inventory • Production • Finance • Reports
    </p>

</div>
""", unsafe_allow_html=True)


# =========================================================
# DASHBOARD
# =========================================================

if page == "Dashboard":

    st.markdown(
        '<div class="main-title">Dashboard</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitle">Business overview and daily performance</div>',
        unsafe_allow_html=True
    )

    # -----------------------------------------------------
    # KPIs
    # -----------------------------------------------------

    today_sales = fetch_dataframe("""
        SELECT COALESCE(SUM(total_amount),0) AS value
        FROM sales
        WHERE DATE(sale_date) = CURRENT_DATE
    """)

    month_sales = fetch_dataframe("""
        SELECT COALESCE(SUM(total_amount),0) AS value
        FROM sales
        WHERE sale_date >= DATE_TRUNC('month', CURRENT_DATE)
    """)

    transactions = fetch_dataframe("""
        SELECT COUNT(*) AS value
        FROM sales
        WHERE DATE(sale_date) = CURRENT_DATE
    """)

    items = fetch_dataframe("""
        SELECT COALESCE(SUM(si.quantity),0) AS value
        FROM sale_items si
        JOIN sales s ON si.sale_id = s.sale_id
        WHERE DATE(s.sale_date) = CURRENT_DATE
          AND si.issued = TRUE
    """)

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        value = today_sales.iloc[0]["value"]
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">TODAY'S SALES</div>
            <div class="metric-value">{money(value)}</div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        value = month_sales.iloc[0]["value"]
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">THIS MONTH</div>
            <div class="metric-value">{money(value)}</div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        value = transactions.iloc[0]["value"]
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">TODAY'S TRANSACTIONS</div>
            <div class="metric-value">{int(value)}</div>
        </div>
        """, unsafe_allow_html=True)

    with c4:
        value = items.iloc[0]["value"]
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">ITEMS SOLD TODAY</div>
            <div class="metric-value">{int(value)}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("")

    # -----------------------------------------------------
    # QUICK ACTIONS
    # -----------------------------------------------------

    st.markdown("### ⚡ Quick Actions")

    q1, q2, q3, q4 = st.columns(4)

    with q1:
        if st.button("➕ New Sale", use_container_width=True):
            st.session_state.page = "New Sale"
            st.rerun()

    with q2:
        if st.button("📦 Add Stock", use_container_width=True):
            st.session_state.page = "Stock Management"
            st.rerun()

    with q3:
        if st.button("💰 Manage Prices", use_container_width=True):
            st.session_state.page = "Price Management"
            st.rerun()

    with q4:
        if st.button("📜 Sales History", use_container_width=True):
            st.session_state.page = "Sales History"
            st.rerun()

    st.markdown("---")

    # -----------------------------------------------------
    # SALES TREND
    # -----------------------------------------------------

    left, right = st.columns(2)

    with left:

        st.markdown("### 📈 Sales Trend")

        trend = fetch_dataframe("""
            SELECT
                DATE(sale_date) AS sale_day,
                SUM(total_amount) AS revenue
            FROM sales
            WHERE sale_date >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY DATE(sale_date)
            ORDER BY sale_day;
        """)

        if not trend.empty:
            trend["sale_day"] = pd.to_datetime(trend["sale_day"])
            trend = trend.set_index("sale_day")
            st.line_chart(trend["revenue"])
        else:
            st.info("No sales recorded yet.")

    # -----------------------------------------------------
    # SALES BY SCHOOL
    # -----------------------------------------------------

    with right:

        st.markdown("### 🏫 Sales by School")

        school_sales = fetch_dataframe("""
            SELECT
                sc.school_name,
                COALESCE(SUM(s.total_amount),0) AS revenue
            FROM schools sc
            LEFT JOIN sales s
                ON sc.school_id = s.school_id
            GROUP BY sc.school_name
            ORDER BY revenue DESC;
        """)

        if not school_sales.empty:

            chart = school_sales.set_index("school_name")

            st.bar_chart(chart["revenue"])

        else:
            st.info("No sales recorded yet.")

    st.markdown("---")

    # -----------------------------------------------------
    # STOCK + TOP PRODUCTS
    # -----------------------------------------------------

    left, right = st.columns(2)

    with left:

        st.markdown("### 📦 Stock Status")

        stock_df = fetch_dataframe("""
            SELECT
                sc.school_name,
                p.product_name,
                COALESCE(SUM(st.quantity_brought),0)
                -
                COALESCE((
                    SELECT SUM(si.quantity)
                    FROM sale_items si
                    JOIN sales s
                        ON si.sale_id = s.sale_id
                    WHERE s.school_id = st.school_id
                      AND si.product_id = st.product_id
                      AND si.issued = TRUE
                ),0) AS remaining
            FROM stock st
            JOIN schools sc
                ON st.school_id = sc.school_id
            JOIN products p
                ON st.product_id = p.product_id
            GROUP BY
                sc.school_name,
                p.product_name,
                st.school_id,
                st.product_id
            ORDER BY remaining ASC;
        """)

        if stock_df.empty:

            st.info("No stock records yet.")

        else:

            display_stock = stock_df.copy()

            display_stock["Status"] = display_stock["remaining"].apply(
                lambda x: "LOW" if x <= 5 else "OK"
            )

            display_stock.columns = [
                "School",
                "Product",
                "Remaining",
                "Status"
            ]

            st.dataframe(
                display_stock,
                use_container_width=True,
                hide_index=True
            )

    with right:

        st.markdown("### 🏆 Top-Selling Products")

        top_products = fetch_dataframe("""
            SELECT
                p.product_name,
                SUM(si.quantity) AS quantity_sold,
                SUM(si.line_total) AS revenue
            FROM sale_items si
            JOIN products p
                ON si.product_id = p.product_id
            JOIN sales s
                ON si.sale_id = s.sale_id
            WHERE si.issued = TRUE
            GROUP BY p.product_name
            ORDER BY quantity_sold DESC
            LIMIT 10;
        """)

        if top_products.empty:
            st.info("No sales recorded yet.")
        else:
            st.dataframe(
                top_products,
                use_container_width=True,
                hide_index=True
            )

    # -----------------------------------------------------
    # RECENT SALES
    # -----------------------------------------------------

    st.markdown("### 🧾 Recent Sales")

    recent = fetch_dataframe("""
        SELECT
            s.sale_id AS "Receipt",
            s.sale_date AS "Date",
            sc.school_name AS "School",
            c.customer_name AS "Customer",
            s.class_name AS "Class",
            s.total_amount AS "Amount",
            s.payment_method AS "Payment"
        FROM sales s
        LEFT JOIN schools sc
            ON s.school_id = sc.school_id
        LEFT JOIN customers c
            ON s.customer_id = c.customer_id
        ORDER BY s.sale_date DESC
        LIMIT 10;
    """)

    if recent.empty:
        st.info("No sales recorded yet.")
    else:
        st.dataframe(
            recent,
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# NEW SALE
# =========================================================

elif page == "New Sale":

    st.markdown("## 🧾 New Sale")
    st.markdown(
        "Create a sale, add items to the cart and issue a receipt."
    )

    schools = fetch_dataframe("""
        SELECT school_id, school_name
        FROM schools
        ORDER BY school_name
    """)

    if schools.empty:
        st.warning("No schools found.")
        st.stop()

    school_name = st.selectbox(
        "School",
        schools["school_name"].tolist()
    )

    school_id = int(
        schools.loc[
            schools["school_name"] == school_name,
            "school_id"
        ].iloc[0]
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        term = st.selectbox(
            "Term",
            ["Term 1", "Term 2", "Term 3"]
        )

    with c2:
        year = st.number_input(
            "Year",
            min_value=2020,
            max_value=2100,
            value=datetime.now().year
        )

    with c3:
        category = st.selectbox(
            "Category",
            ["Primary", "Junior Secondary"]
        )

    c1, c2 = st.columns(2)

    with c1:
        customer_name = st.text_input(
            "Student / Customer Name"
        )

    with c2:
        phone = st.text_input(
            "Phone Number"
        )

    class_name = st.text_input(
        "Class / Grade"
    )

    st.markdown("---")

    st.markdown("### 🛒 Add Items")

    available = fetch_dataframe("""
        SELECT
            spp.product_id,
            p.product_name,
            spp.price
        FROM school_product_prices spp
        JOIN products p
            ON spp.product_id = p.product_id
        WHERE spp.school_id = %s
          AND spp.category_name = %s
        ORDER BY p.product_name;
    """, (school_id, category))

    if available.empty:

        st.warning(
            "No prices have been assigned to this school/category. "
            "Go to Price Management first."
        )

    else:

        product_name = st.selectbox(
            "Product",
            available["product_name"].tolist()
        )

        selected = available[
            available["product_name"] == product_name
        ].iloc[0]

        unit_price = float(selected["price"])

        st.info(f"Unit price: {money(unit_price)}")

        c1, c2 = st.columns(2)

        with c1:
            quantity = st.number_input(
                "Quantity",
                min_value=1,
                value=1,
                step=1
            )

        with c2:
            issued = st.checkbox(
                "Issued to customer",
                value=True
            )

        if st.button(
            "➕ Add to Cart",
            type="primary",
            use_container_width=True
        ):

            st.session_state.cart.append({
                "product_id": int(selected["product_id"]),
                "product": product_name,
                "quantity": int(quantity),
                "unit_price": unit_price,
                "line_total": unit_price * quantity,
                "issued": issued
            })

            st.success("Item added to cart.")

    # -----------------------------------------------------
    # CART
    # -----------------------------------------------------

    st.markdown("### 🛒 Cart")

    if st.session_state.cart:

        cart_df = pd.DataFrame(st.session_state.cart)

        st.dataframe(
            cart_df[
                [
                    "product",
                    "quantity",
                    "unit_price",
                    "line_total",
                    "issued"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

        total = sum(
            item["line_total"]
            for item in st.session_state.cart
        )

        st.markdown(
            f"## Total: {money(total)}"
        )

        c1, c2 = st.columns(2)

        with c1:

            if st.button(
                "🗑️ Clear Cart",
                use_container_width=True
            ):
                st.session_state.cart = []
                st.rerun()

        with c2:

            payment_method = st.selectbox(
                "Payment Method",
                ["Cash", "M-Pesa", "Bank", "Other"]
            )

            if st.button(
                "✅ Complete Sale",
                type="primary",
                use_container_width=True
            ):

                if not customer_name.strip():
                    st.error("Enter the student/customer name.")

                else:

                    conn = get_connection()

                    try:

                        cur = conn.cursor()

                        # CUSTOMER
                        cur.execute("""
                            INSERT INTO customers
                            (customer_name, phone)
                            VALUES (%s, %s)
                            RETURNING customer_id;
                        """, (
                            customer_name.strip(),
                            phone.strip()
                        ))

                        customer_id = cur.fetchone()[0]

                        # SALE
                        cur.execute("""
                            INSERT INTO sales
                            (
                                school_id,
                                customer_id,
                                class_name,
                                total_amount,
                                payment_method,
                                payment_status,
                                term,
                                year
                            )
                            VALUES
                            (%s,%s,%s,%s,%s,'Paid',%s,%s)
                            RETURNING sale_id;
                        """, (
                            school_id,
                            customer_id,
                            class_name.strip(),
                            total,
                            payment_method,
                            term,
                            year
                        ))

                        sale_id = cur.fetchone()[0]

                        # SALE ITEMS
                        for item in st.session_state.cart:

                            cur.execute("""
                                INSERT INTO sale_items
                                (
                                    sale_id,
                                    product_id,
                                    quantity,
                                    unit_price,
                                    line_total,
                                    issued
                                )
                                VALUES
                                (%s,%s,%s,%s,%s,%s);
                            """, (
                                sale_id,
                                item["product_id"],
                                item["quantity"],
                                item["unit_price"],
                                item["line_total"],
                                item["issued"]
                            ))

                        # FINANCE
                        cur.execute("""
                            INSERT INTO financial_transactions
                            (
                                transaction_type,
                                category,
                                description,
                                amount,
                                term,
                                year,
                                sale_id
                            )
                            VALUES
                            (
                                'Sales Income',
                                'Sales',
                                %s,
                                %s,
                                %s,
                                %s,
                                %s
                            );
                        """, (
                            f"Sale #{sale_id}",
                            total,
                            term,
                            year,
                            sale_id
                        ))

                        conn.commit()

                        cur.close()
                        conn.close()

                        st.session_state.last_receipt = sale_id
                        st.session_state.cart = []

                        st.success(
                            f"Sale #{sale_id} completed successfully."
                        )

                    except Exception as e:

                        conn.rollback()
                        conn.close()

                        st.error(
                            f"Sale could not be completed: {e}"
                        )

    else:

        st.info("Your cart is empty.")


# =========================================================
# DISPLAY LAST RECEIPT
# =========================================================

if page == "New Sale" and st.session_state.last_receipt:

    st.markdown("---")

    st.markdown("## 🧾 Receipt")

    receipt = get_receipt(
        st.session_state.last_receipt
    )

    render_receipt(receipt)

    if st.button("Close Receipt"):
        st.session_state.last_receipt = None
        st.rerun()


# =========================================================
# SALES HISTORY
# =========================================================

elif page == "Sales History":

    st.markdown("## 📜 Sales History")

    sales = fetch_dataframe("""
        SELECT
            s.sale_id,
            s.sale_date,
            sc.school_name,
            c.customer_name,
            c.phone,
            s.class_name,
            s.term,
            s.year,
            s.total_amount,
            s.payment_method,
            s.payment_status
        FROM sales s
        LEFT JOIN schools sc
            ON s.school_id = sc.school_id
        LEFT JOIN customers c
            ON s.customer_id = c.customer_id
        ORDER BY s.sale_date DESC;
    """)

    if sales.empty:

        st.info("No sales have been recorded yet.")

    else:

        st.dataframe(
            sales,
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "⬇️ Download Sales CSV",
            sales.to_csv(index=False),
            file_name="sales_history.csv",
            mime="text/csv"
        )

        st.markdown("---")

        sale_id = st.number_input(
            "Receipt number to view / print",
            min_value=1,
            step=1
        )

        if st.button(
            "🧾 View / Print Receipt",
            type="primary"
        ):

            receipt = get_receipt(int(sale_id))

            if receipt:
                render_receipt(receipt)
            else:
                st.error("Receipt not found.")


# =========================================================
# PRICE MANAGEMENT
# =========================================================

elif page == "Price Management":

    st.markdown("## 💰 Price Management")

    schools = fetch_dataframe("""
        SELECT school_id, school_name
        FROM schools
        ORDER BY school_name
    """)

    school_name = st.selectbox(
        "School",
        schools["school_name"].tolist()
    )

    school_id = int(
        schools.loc[
            schools["school_name"] == school_name,
            "school_id"
        ].iloc[0]
    )

    category = st.selectbox(
        "Category",
        ["Primary", "Junior Secondary"]
    )

    st.markdown("### Existing Prices")

    prices = fetch_dataframe("""
        SELECT
            spp.school_product_price_id,
            p.product_name,
            spp.price
        FROM school_product_prices spp
        JOIN products p
            ON spp.product_id = p.product_id
        WHERE spp.school_id = %s
          AND spp.category_name = %s
        ORDER BY p.product_name;
    """, (school_id, category))

    if prices.empty:

        st.info("No prices assigned yet.")

    else:

        for _, row in prices.iterrows():

            c1, c2, c3 = st.columns([4, 2, 1])

            with c1:
                st.write(row["product_name"])

            with c2:

                new_price = st.number_input(
                    f"Price {row['school_product_price_id']}",
                    min_value=0.0,
                    value=float(row["price"]),
                    step=50.0,
                    key=f"price_{row['school_product_price_id']}",
                    label_visibility="collapsed"
                )

            with c3:

                if st.button(
                    "Save",
                    key=f"save_price_{row['school_product_price_id']}"
                ):

                    execute_query("""
                        UPDATE school_product_prices
                        SET price = %s
                        WHERE school_product_price_id = %s
                    """, (
                        new_price,
                        row["school_product_price_id"]
                    ))

                    st.success("Price updated.")
                    st.rerun()

    st.markdown("---")

    st.markdown("### ➕ Assign Product")

    products = fetch_dataframe("""
        SELECT product_id, product_name, price
        FROM products
        ORDER BY product_name
    """)

    assigned = fetch_dataframe("""
        SELECT product_id
        FROM school_product_prices
        WHERE school_id = %s
          AND category_name = %s
    """, (school_id, category))

    assigned_ids = set(
        assigned["product_id"].tolist()
    ) if not assigned.empty else set()

    unassigned = products[
        ~products["product_id"].isin(assigned_ids)
    ]

    if unassigned.empty:

        st.success(
            "All products have been assigned."
        )

    else:

        product_name = st.selectbox(
            "Product to assign",
            unassigned["product_name"].tolist()
        )

        product = unassigned[
            unassigned["product_name"] == product_name
        ].iloc[0]

        price = st.number_input(
            "Selling Price",
            min_value=0.0,
            value=float(product["price"]),
            step=50.0
        )

        if st.button(
            "Assign Product",
            type="primary"
        ):

            execute_query("""
                INSERT INTO school_product_prices
                (
                    school_id,
                    category_name,
                    product_id,
                    price
                )
                VALUES (%s,%s,%s,%s)
            """, (
                school_id,
                category,
                int(product["product_id"]),
                price
            ))

            st.success("Product assigned.")
            st.rerun()

    st.markdown("---")

    st.markdown("### ➕ Create New Product")

    c1, c2 = st.columns(2)

    with c1:
        new_product = st.text_input(
            "Product Name"
        )

    with c2:
        selling_price = st.number_input(
            "Selling Price",
            min_value=0.0,
            step=50.0
        )

    cost_price = st.number_input(
        "Cost Price",
        min_value=0.0,
        step=50.0
    )

    if st.button(
        "Create Product",
        type="primary"
    ):

        if not new_product.strip():

            st.error("Enter product name.")

        else:

            try:

                execute_query("""
                    INSERT INTO products
                    (
                        product_name,
                        price,
                        cost_price
                    )
                    VALUES (%s,%s,%s)
                """, (
                    new_product.strip(),
                    selling_price,
                    cost_price
                ))

                st.success("Product created.")

            except Exception as e:
                st.error(f"Could not create product: {e}")


# =========================================================
# STOCK MANAGEMENT
# =========================================================

elif page == "Stock Management":

    st.markdown("## 📦 Stock Management")

    schools = fetch_dataframe("""
        SELECT school_id, school_name
        FROM schools
        ORDER BY school_name
    """)

    products = fetch_dataframe("""
        SELECT product_id, product_name
        FROM products
        ORDER BY product_name
    """)

    c1, c2 = st.columns(2)

    with c1:

        school_name = st.selectbox(
            "School",
            schools["school_name"].tolist()
        )

        school_id = int(
            schools.loc[
                schools["school_name"] == school_name,
                "school_id"
            ].iloc[0]
        )

    with c2:

        product_name = st.selectbox(
            "Product",
            products["product_name"].tolist()
        )

        product_id = int(
            products.loc[
                products["product_name"] == product_name,
                "product_id"
            ].iloc[0]
        )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        quantity = st.number_input(
            "Quantity",
            min_value=1,
            step=1
        )

    with c2:
        unit_cost = st.number_input(
            "Unit Cost",
            min_value=0.0,
            step=50.0
        )

    with c3:
        term = st.selectbox(
            "Term",
            ["Term 1", "Term 2", "Term 3"]
        )

    with c4:
        year = st.number_input(
            "Year",
            min_value=2020,
            max_value=2100,
            value=datetime.now().year
        )

    if st.button(
        "📦 Add Stock",
        type="primary"
    ):

        conn = get_connection()

        try:

            cur = conn.cursor()

            cur.execute("""
                INSERT INTO stock
                (
                    school_id,
                    product_id,
                    quantity_brought,
                    term,
                    year,
                    unit_cost
                )
                VALUES (%s,%s,%s,%s,%s,%s)
                RETURNING stock_id;
            """, (
                school_id,
                product_id,
                quantity,
                term,
                year,
                unit_cost
            ))

            stock_id = cur.fetchone()[0]

            total_cost = quantity * unit_cost

            cur.execute("""
                INSERT INTO financial_transactions
                (
                    transaction_type,
                    category,
                    description,
                    amount,
                    term,
                    year,
                    stock_id
                )
                VALUES
                (
                    'Stock Purchase',
                    'Inventory',
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                );
            """, (
                f"Stock purchase - {product_name}",
                total_cost,
                term,
                year,
                stock_id
            ))

            conn.commit()
            cur.close()
            conn.close()

            st.success("Stock added successfully.")

        except Exception as e:

            conn.rollback()
            conn.close()

            st.error(f"Could not add stock: {e}")

    st.markdown("---")

    st.markdown("### 📊 Current Stock")

    stock_df = fetch_dataframe("""
        SELECT
            st.stock_id,
            sc.school_name,
            p.product_name,
            st.quantity_brought,
            st.date_added,
            st.term,
            st.year,
            st.unit_cost
        FROM stock st
        JOIN schools sc
            ON st.school_id = sc.school_id
        JOIN products p
            ON st.product_id = p.product_id
        ORDER BY st.date_added DESC;
    """)

    if stock_df.empty:

        st.info("No stock records yet.")

    else:

        st.dataframe(
            stock_df,
            use_container_width=True,
            hide_index=True
        )

        st.markdown("### Remaining Stock")

        remaining = fetch_dataframe("""
            SELECT
                sc.school_name,
                p.product_name,
                COALESCE(SUM(st.quantity_brought),0)
                -
                COALESCE((
                    SELECT SUM(si.quantity)
                    FROM sale_items si
                    JOIN sales s
                        ON si.sale_id = s.sale_id
                    WHERE s.school_id = st.school_id
                      AND si.product_id = st.product_id
                      AND si.issued = TRUE
                ),0) AS remaining
            FROM stock st
            JOIN schools sc
                ON st.school_id = sc.school_id
            JOIN products p
                ON st.product_id = p.product_id
            GROUP BY
                sc.school_name,
                p.product_name,
                st.school_id,
                st.product_id
            ORDER BY remaining;
        """)

        st.dataframe(
            remaining,
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# TAILOR & PRODUCTION
# =========================================================

elif page == "Tailor & Production":

    st.markdown("## 🧵 Tailor & Production")

    schools = fetch_dataframe("""
        SELECT school_id, school_name
        FROM schools
        ORDER BY school_name
    """)

    products = fetch_dataframe("""
        SELECT product_id, product_name
        FROM products
        ORDER BY product_name
    """)

    c1, c2 = st.columns(2)

    with c1:

        school_name = st.selectbox(
            "School",
            schools["school_name"].tolist()
        )

        school_id = int(
            schools.loc[
                schools["school_name"] == school_name,
                "school_id"
            ].iloc[0]
        )

    with c2:

        product_name = st.selectbox(
            "Product",
            products["product_name"].tolist()
        )

        product_id = int(
            products.loc[
                products["product_name"] == product_name,
                "product_id"
            ].iloc[0]
        )

    tailor_name = st.text_input(
        "Tailor Name"
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        quantity = st.number_input(
            "Quantity Produced",
            min_value=1,
            step=1
        )

    with c2:
        cost_per_item = st.number_input(
            "Cost Per Item",
            min_value=0.0,
            step=50.0
        )

    with c3:
        term = st.selectbox(
            "Term",
            ["Term 1", "Term 2", "Term 3"]
        )

    year = st.number_input(
        "Year",
        min_value=2020,
        max_value=2100,
        value=datetime.now().year
    )

    notes = st.text_area(
        "Notes"
    )

    amount_paid = quantity * cost_per_item

    st.info(
        f"Total tailor payment: {money(amount_paid)}"
    )

    if st.button(
        "💳 Record Production",
        type="primary"
    ):

        conn = get_connection()

        try:

            cur = conn.cursor()

            cur.execute("""
                INSERT INTO tailor_production
                (
                    school_id,
                    product_id,
                    tailor_name,
                    quantity_produced,
                    cost_per_item,
                    amount_paid,
                    term,
                    year,
                    notes
                )
                VALUES
                (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING production_id;
            """, (
                school_id,
                product_id,
                tailor_name,
                quantity,
                cost_per_item,
                amount_paid,
                term,
                year,
                notes
            ))

            production_id = cur.fetchone()[0]

            cur.execute("""
                INSERT INTO financial_transactions
                (
                    transaction_type,
                    category,
                    description,
                    amount,
                    term,
                    year,
                    production_id
                )
                VALUES
                (
                    'Tailor Payment',
                    'Production',
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                );
            """, (
                f"Production - {product_name}",
                amount_paid,
                term,
                year,
                production_id
            ))

            conn.commit()

            cur.close()
            conn.close()

            st.success("Production recorded successfully.")

        except Exception as e:

            conn.rollback()
            conn.close()

            st.error(f"Could not record production: {e}")

    st.markdown("---")

    production = fetch_dataframe("""
        SELECT
            tp.production_id,
            tp.production_date,
            sc.school_name,
            p.product_name,
            tp.tailor_name,
            tp.quantity_produced,
            tp.cost_per_item,
            tp.amount_paid,
            tp.term,
            tp.year,
            tp.notes
        FROM tailor_production tp
        JOIN schools sc
            ON tp.school_id = sc.school_id
        JOIN products p
            ON tp.product_id = p.product_id
        ORDER BY tp.production_date DESC;
    """)

    if production.empty:
        st.info("No production records yet.")
    else:
        st.dataframe(
            production,
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# BUSINESS FINANCE
# =========================================================

elif page == "Business Finance":

    st.markdown("## 💼 Business Finance")

    # -----------------------------------------------------
    # INVESTORS
    # -----------------------------------------------------

    investors = fetch_dataframe("""
        SELECT
            i.investor_id,
            i.investor_name,
            COALESCE(SUM(ft.amount),0) AS capital
        FROM investors i
        LEFT JOIN financial_transactions ft
            ON i.investor_id = ft.investor_id
           AND ft.transaction_type = 'Capital Contribution'
        WHERE i.active = TRUE
        GROUP BY
            i.investor_id,
            i.investor_name
        ORDER BY i.investor_name;
    """)

    st.markdown("### 👥 Investors")

    if not investors.empty:

        total_capital = investors["capital"].sum()

        investors["Ownership %"] = investors["capital"].apply(
            lambda x:
                (x / total_capital * 100)
                if total_capital > 0
                else 0
        )

        display = investors.copy()

        display["capital"] = display["capital"].apply(money)
        display["Ownership %"] = display["Ownership %"].apply(
            lambda x: f"{x:.2f}%"
        )

        st.dataframe(
            display,
            use_container_width=True,
            hide_index=True
        )

    # -----------------------------------------------------
    # ADD INVESTMENT
    # -----------------------------------------------------

    st.markdown("### ➕ Additional Investment")

    investor_name = st.selectbox(
        "Investor",
        ["Gift", "Ken"]
    )

    amount = st.number_input(
        "Amount",
        min_value=0.0,
        step=1000.0
    )

    description = st.text_input(
        "Description",
        value="Additional capital contribution"
    )

    if st.button(
        "Record Investment",
        type="primary"
    ):

        investor = fetch_dataframe("""
            SELECT investor_id
            FROM investors
            WHERE investor_name = %s;
        """, (investor_name,))

        investor_id = int(
            investor.iloc[0]["investor_id"]
        )

        execute_query("""
            INSERT INTO financial_transactions
            (
                transaction_type,
                category,
                description,
                amount,
                investor_id
            )
            VALUES
            (
                'Capital Contribution',
                'Owner Capital',
                %s,
                %s,
                %s
            )
        """, (
            description,
            amount,
            investor_id
        ))

        st.success("Investment recorded.")
        st.rerun()

    # -----------------------------------------------------
    # GENERAL TRANSACTION
    # -----------------------------------------------------

    st.markdown("---")
    st.markdown("### 💸 Record Financial Transaction")

    transaction_type = st.selectbox(
        "Transaction Type",
        [
            "Expense",
            "Other Income",
            "Owner Withdrawal",
            "Profit Distribution"
        ]
    )

    category = st.text_input(
        "Category"
    )

    description = st.text_input(
        "Description"
    )

    amount = st.number_input(
        "Amount",
        min_value=0.0,
        step=100.0,
        key="finance_amount"
    )

    if st.button(
        "Record Transaction"
    ):

        execute_query("""
            INSERT INTO financial_transactions
            (
                transaction_type,
                category,
                description,
                amount
            )
            VALUES (%s,%s,%s,%s)
        """, (
            transaction_type,
            category,
            description,
            amount
        ))

        st.success("Transaction recorded.")
        st.rerun()

    # -----------------------------------------------------
    # FINANCIAL SUMMARY
    # -----------------------------------------------------

    st.markdown("---")
    st.markdown("### 📊 Financial Summary")

    revenue = fetch_dataframe("""
        SELECT COALESCE(SUM(amount),0) AS value
        FROM financial_transactions
        WHERE transaction_type = 'Sales Income'
    """).iloc[0]["value"]

    stock_purchases = fetch_dataframe("""
        SELECT COALESCE(SUM(amount),0) AS value
        FROM financial_transactions
        WHERE transaction_type = 'Stock Purchase'
    """).iloc[0]["value"]

    tailor_payments = fetch_dataframe("""
        SELECT COALESCE(SUM(amount),0) AS value
        FROM financial_transactions
        WHERE transaction_type = 'Tailor Payment'
    """).iloc[0]["value"]

    expenses = fetch_dataframe("""
        SELECT COALESCE(SUM(amount),0) AS value
        FROM financial_transactions
        WHERE transaction_type = 'Expense'
    """).iloc[0]["value"]

    other_income = fetch_dataframe("""
        SELECT COALESCE(SUM(amount),0) AS value
        FROM financial_transactions
        WHERE transaction_type = 'Other Income'
    """).iloc[0]["value"]

    withdrawals = fetch_dataframe("""
        SELECT COALESCE(SUM(amount),0) AS value
        FROM financial_transactions
        WHERE transaction_type = 'Owner Withdrawal'
    """).iloc[0]["value"]

    distributions = fetch_dataframe("""
        SELECT COALESCE(SUM(amount),0) AS value
        FROM financial_transactions
        WHERE transaction_type = 'Profit Distribution'
    """).iloc[0]["value"]

    capital = investors["capital"].sum() if not investors.empty else 0

    gross_profit = (
        float(revenue)
        - float(stock_purchases)
        - float(tailor_payments)
    )

    net_profit = (
        gross_profit
        + float(other_income)
        - float(expenses)
    )

    cash_position = (
        float(capital)
        + float(revenue)
        + float(other_income)
        - float(stock_purchases)
        - float(tailor_payments)
        - float(expenses)
        - float(withdrawals)
        - float(distributions)
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "Capital",
            money(capital)
        )

    with c2:
        st.metric(
            "Revenue",
            money(revenue)
        )

    with c3:
        st.metric(
            "Net Profit",
            money(net_profit)
        )

    with c4:
        st.metric(
            "Cash Position",
            money(cash_position)
        )

    st.markdown("### 📒 Financial Ledger")

    ledger = fetch_dataframe("""
        SELECT
            transaction_id,
            transaction_date,
            transaction_type,
            category,
            description,
            amount,
            term,
            year
        FROM financial_transactions
        ORDER BY transaction_date DESC;
    """)

    if not ledger.empty:

        st.dataframe(
            ledger,
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# ML & FORECASTING
# =========================================================

elif page == "ML & Forecasting":

    st.markdown("## 🤖 ML & Forecasting")

    st.info(
        "This section uses the business data already collected by the system. "
        "More advanced forecasting models can be added once enough real sales "
        "history exists."
    )

    # -----------------------------------------------------
    # DAILY REVENUE
    # -----------------------------------------------------

    daily = fetch_dataframe("""
        SELECT
            DATE(sale_date) AS sale_day,
            SUM(total_amount) AS revenue
        FROM sales
        GROUP BY DATE(sale_date)
        ORDER BY sale_day;
    """)

    if daily.empty:

        st.warning(
            "There is not enough sales data for forecasting yet."
        )

    else:

        st.markdown("### 📈 Historical Revenue")

        daily["sale_day"] = pd.to_datetime(
            daily["sale_day"]
        )

        st.line_chart(
            daily.set_index("sale_day")["revenue"]
        )

        if len(daily) >= 3:

            average_daily = daily["revenue"].tail(7).mean()

            st.metric(
                "Recent Average Daily Revenue",
                money(average_daily)
            )

    # -----------------------------------------------------
    # PRODUCT DEMAND
    # -----------------------------------------------------

    st.markdown("### 🧮 Product Demand")

    demand = fetch_dataframe("""
        SELECT
            p.product_name,
            SUM(si.quantity) AS units_sold,
            SUM(si.line_total) AS revenue
        FROM sale_items si
        JOIN products p
            ON si.product_id = p.product_id
        WHERE si.issued = TRUE
        GROUP BY p.product_name
        ORDER BY units_sold DESC;
    """)

    if demand.empty:

        st.info("No sales data available.")

    else:

        st.dataframe(
            demand,
            use_container_width=True,
            hide_index=True
        )

        st.bar_chart(
            demand.set_index("product_name")["units_sold"]
        )

    st.markdown("---")

    st.markdown("### 🔬 Future ML Features")

    st.write("""
    • Demand forecasting by product

    • School-level sales forecasting

    • Stock replenishment prediction

    • Customer purchasing patterns

    • Seasonal demand analysis

    • Sales anomaly detection

    • Profit forecasting
    """)


# =========================================================
# SYSTEM MANAGEMENT
# =========================================================

elif page == "System Management":

    st.markdown("## ⚙️ System Management")

    tabs = st.tabs([
        "Sales",
        "Stock",
        "Production",
        "Finance",
        "Products",
        "Schools"
    ])

    # =====================================================
    # SALES MANAGEMENT
    # =====================================================

    with tabs[0]:

        st.markdown("### 🧾 Manage Sales")

        sales = fetch_dataframe("""
            SELECT
                s.sale_id,
                s.sale_date,
                sc.school_name,
                c.customer_name,
                s.class_name,
                s.total_amount,
                s.payment_method,
                s.payment_status,
                s.term,
                s.year
            FROM sales s
            LEFT JOIN schools sc
                ON s.school_id = sc.school_id
            LEFT JOIN customers c
                ON s.customer_id = c.customer_id
            ORDER BY s.sale_date DESC;
        """)

        if sales.empty:

            st.info("No sales to manage.")

        else:

            st.dataframe(
                sales,
                use_container_width=True,
                hide_index=True
            )

            selected_sale = st.selectbox(
                "Select Sale",
                sales["sale_id"].tolist()
            )

            receipt = get_receipt(
                int(selected_sale)
            )

            if receipt:

                h = receipt["header"]

                st.markdown("#### Edit Sale")

                schools = fetch_dataframe("""
                    SELECT school_id, school_name
                    FROM schools
                    ORDER BY school_name
                """)

                school_options = schools["school_name"].tolist()

                current_school = h["school_name"]

                school_index = (
                    school_options.index(current_school)
                    if current_school in school_options
                    else 0
                )

                new_school_name = st.selectbox(
                    "School",
                    school_options,
                    index=school_index,
                    key="edit_sale_school"
                )

                new_customer = st.text_input(
                    "Customer",
                    value=h["customer_name"] or "",
                    key="edit_customer"
                )

                new_phone = st.text_input(
                    "Phone",
                    value=h["phone"] or "",
                    key="edit_phone"
                )

                new_class = st.text_input(
                    "Class",
                    value=h["class_name"] or "",
                    key="edit_class"
                )

                new_term = st.selectbox(
                    "Term",
                    ["Term 1", "Term 2", "Term 3"],
                    index=(
                        ["Term 1", "Term 2", "Term 3"].index(h["term"])
                        if h["term"] in ["Term 1", "Term 2", "Term 3"]
                        else 0
                    ),
                    key="edit_term"
                )

                new_payment = st.selectbox(
                    "Payment Method",
                    ["Cash", "M-Pesa", "Bank", "Other"],
                    index=(
                        ["Cash", "M-Pesa", "Bank", "Other"].index(
                            h["payment_method"]
                        )
                        if h["payment_method"] in
                        ["Cash", "M-Pesa", "Bank", "Other"]
                        else 0
                    ),
                    key="edit_payment"
                )

                new_status = st.selectbox(
                    "Payment Status",
                    ["Paid", "Pending", "Cancelled"],
                    index=(
                        ["Paid", "Pending", "Cancelled"].index(
                            h["payment_status"]
                        )
                        if h["payment_status"] in
                        ["Paid", "Pending", "Cancelled"]
                        else 0
                    ),
                    key="edit_status"
                )

                new_year = st.number_input(
                    "Year",
                    min_value=2020,
                    max_value=2100,
                    value=int(h["year"] or datetime.now().year),
                    key="edit_year"
                )

                if st.button(
                    "💾 Save Sale Changes",
                    type="primary"
                ):

                    school_id = int(
                        schools.loc[
                            schools["school_name"] == new_school_name,
                            "school_id"
                        ].iloc[0]
                    )

                    execute_query("""
                        UPDATE customers
                        SET
                            customer_name = %s,
                            phone = %s
                        WHERE customer_id = (
                            SELECT customer_id
                            FROM sales
                            WHERE sale_id = %s
                        );
                    """, (
                        new_customer,
                        new_phone,
                        selected_sale
                    ))

                    execute_query("""
                        UPDATE sales
                        SET
                            school_id = %s,
                            class_name = %s,
                            payment_method = %s,
                            payment_status = %s,
                            term = %s,
                            year = %s
                        WHERE sale_id = %s;
                    """, (
                        school_id,
                        new_class,
                        new_payment,
                        new_status,
                        new_term,
                        new_year,
                        selected_sale
                    ))

                    st.success("Sale updated.")
                    st.rerun()

                st.markdown("---")

                if st.button(
                    "🖨️ Print This Receipt",
                    key="print_old_receipt"
                ):
                    render_receipt(
                        get_receipt(selected_sale)
                    )

                st.markdown("### ⚠️ Delete Sale")

                confirm_delete = st.checkbox(
                    "I understand that deleting this sale cannot be undone.",
                    key="confirm_sale_delete"
                )

                if st.button(
                    "🗑️ Delete Sale",
                    disabled=not confirm_delete
                ):

                    execute_query("""
                        DELETE FROM sales
                        WHERE sale_id = %s;
                    """, (selected_sale,))

                    st.success(
                        f"Sale #{selected_sale} deleted."
                    )

                    st.rerun()

    # =====================================================
    # STOCK MANAGEMENT
    # =====================================================

    with tabs[1]:

        st.markdown("### 📦 Manage Stock")

        stock = fetch_dataframe("""
            SELECT
                st.stock_id,
                sc.school_name,
                p.product_name,
                st.quantity_brought,
                st.unit_cost,
                st.term,
                st.year,
                st.date_added
            FROM stock st
            JOIN schools sc
                ON st.school_id = sc.school_id
            JOIN products p
                ON st.product_id = p.product_id
            ORDER BY st.date_added DESC;
        """)

        if stock.empty:

            st.info("No stock records.")

        else:

            st.dataframe(
                stock,
                use_container_width=True,
                hide_index=True
            )

            stock_id = st.selectbox(
                "Select Stock Record",
                stock["stock_id"].tolist()
            )

            row = stock[
                stock["stock_id"] == stock_id
            ].iloc[0]

            new_quantity = st.number_input(
                "Quantity",
                min_value=0,
                value=int(row["quantity_brought"]),
                key=f"stock_qty_{stock_id}"
            )

            new_cost = st.number_input(
                "Unit Cost",
                min_value=0.0,
                value=float(row["unit_cost"] or 0),
                key=f"stock_cost_{stock_id}"
            )

            if st.button(
                "💾 Save Stock Changes"
            ):

                execute_query("""
                    UPDATE stock
                    SET
                        quantity_brought = %s,
                        unit_cost = %s
                    WHERE stock_id = %s;
                """, (
                    new_quantity,
                    new_cost,
                    stock_id
                ))

                execute_query("""
                    UPDATE financial_transactions
                    SET amount = %s
                    WHERE stock_id = %s;
                """, (
                    new_quantity * new_cost,
                    stock_id
                ))

                st.success("Stock updated.")
                st.rerun()

            confirm = st.checkbox(
                "Confirm stock deletion",
                key=f"delete_stock_confirm_{stock_id}"
            )

            if st.button(
                "🗑️ Delete Stock",
                disabled=not confirm
            ):

                execute_query("""
                    DELETE FROM stock
                    WHERE stock_id = %s;
                """, (stock_id,))

                st.success("Stock deleted.")
                st.rerun()

    # =====================================================
    # PRODUCTION MANAGEMENT
    # =====================================================

    with tabs[2]:

        st.markdown("### 🧵 Manage Production")

        production = fetch_dataframe("""
            SELECT
                tp.production_id,
                tp.production_date,
                sc.school_name,
                p.product_name,
                tp.tailor_name,
                tp.quantity_produced,
                tp.cost_per_item,
                tp.amount_paid,
                tp.term,
                tp.year
            FROM tailor_production tp
            JOIN schools sc
                ON tp.school_id = sc.school_id
            JOIN products p
                ON tp.product_id = p.product_id
            ORDER BY tp.production_date DESC;
        """)

        if production.empty:

            st.info("No production records.")

        else:

            st.dataframe(
                production,
                use_container_width=True,
                hide_index=True
            )

            production_id = st.selectbox(
                "Select Production Record",
                production["production_id"].tolist()
            )

            row = production[
                production["production_id"] == production_id
            ].iloc[0]

            quantity = st.number_input(
                "Quantity Produced",
                min_value=0,
                value=int(row["quantity_produced"]),
                key=f"prod_qty_{production_id}"
            )

            cost = st.number_input(
                "Cost Per Item",
                min_value=0.0,
                value=float(row["cost_per_item"]),
                key=f"prod_cost_{production_id}"
            )

            if st.button(
                "💾 Save Production Changes"
            ):

                amount = quantity * cost

                execute_query("""
                    UPDATE tailor_production
                    SET
                        quantity_produced = %s,
                        cost_per_item = %s,
                        amount_paid = %s
                    WHERE production_id = %s;
                """, (
                    quantity,
                    cost,
                    amount,
                    production_id
                ))

                execute_query("""
                    UPDATE financial_transactions
                    SET amount = %s
                    WHERE production_id = %s;
                """, (
                    amount,
                    production_id
                ))

                st.success("Production updated.")
                st.rerun()

            confirm = st.checkbox(
                "Confirm production deletion",
                key=f"delete_prod_{production_id}"
            )

            if st.button(
                "🗑️ Delete Production",
                disabled=not confirm
            ):

                execute_query("""
                    DELETE FROM tailor_production
                    WHERE production_id = %s;
                """, (production_id,))

                st.success("Production deleted.")
                st.rerun()

    # =====================================================
    # FINANCE MANAGEMENT
    # =====================================================

    with tabs[3]:

        st.markdown("### 💼 Manage Finance")

        finance = fetch_dataframe("""
            SELECT
                transaction_id,
                transaction_date,
                transaction_type,
                category,
                description,
                amount,
                sale_id,
                stock_id,
                production_id
            FROM financial_transactions
            ORDER BY transaction_date DESC;
        """)

        st.dataframe(
            finance,
            use_container_width=True,
            hide_index=True
        )

        if not finance.empty:

            transaction_id = st.selectbox(
                "Select Transaction",
                finance["transaction_id"].tolist()
            )

            row = finance[
                finance["transaction_id"] == transaction_id
            ].iloc[0]

            linked = (
                pd.notna(row["sale_id"])
                or pd.notna(row["stock_id"])
                or pd.notna(row["production_id"])
            )

            if linked:

                st.info(
                    "This transaction is linked to a sale, stock record "
                    "or production record. Edit the source record instead "
                    "of changing this transaction directly."
                )

            else:

                amount = st.number_input(
                    "Amount",
                    min_value=0.0,
                    value=float(row["amount"] or 0),
                    key=f"finance_edit_{transaction_id}"
                )

                description = st.text_input(
                    "Description",
                    value=row["description"] or "",
                    key=f"finance_desc_{transaction_id}"
                )

                if st.button(
                    "💾 Save Finance Changes"
                ):

                    execute_query("""
                        UPDATE financial_transactions
                        SET
                            amount = %s,
                            description = %s
                        WHERE transaction_id = %s;
                    """, (
                        amount,
                        description,
                        transaction_id
                    ))

                    st.success("Transaction updated.")
                    st.rerun()

                confirm = st.checkbox(
                    "Confirm transaction deletion",
                    key=f"delete_finance_{transaction_id}"
                )

                if st.button(
                    "🗑️ Delete Transaction",
                    disabled=not confirm
                ):

                    execute_query("""
                        DELETE FROM financial_transactions
                        WHERE transaction_id = %s;
                    """, (transaction_id,))

                    st.success("Transaction deleted.")
                    st.rerun()

    # =====================================================
    # PRODUCT MANAGEMENT
    # =====================================================

    with tabs[4]:

        st.markdown("### 👕 Manage Products")

        products = fetch_dataframe("""
            SELECT
                product_id,
                product_name,
                price,
                cost_price
            FROM products
            ORDER BY product_name;
        """)

        st.dataframe(
            products,
            use_container_width=True,
            hide_index=True
        )

        product_id = st.selectbox(
            "Select Product",
            products["product_id"].tolist()
        )

        row = products[
            products["product_id"] == product_id
        ].iloc[0]

        name = st.text_input(
            "Product Name",
            value=row["product_name"],
            key=f"product_name_{product_id}"
        )

        price = st.number_input(
            "Selling Price",
            min_value=0.0,
            value=float(row["price"]),
            key=f"product_price_{product_id}"
        )

        cost = st.number_input(
            "Cost Price",
            min_value=0.0,
            value=float(row["cost_price"]),
            key=f"product_cost_{product_id}"
        )

        if st.button(
            "💾 Save Product Changes"
        ):

            try:

                execute_query("""
                    UPDATE products
                    SET
                        product_name = %s,
                        price = %s,
                        cost_price = %s
                    WHERE product_id = %s;
                """, (
                    name.strip(),
                    price,
                    cost,
                    product_id
                ))

                st.success("Product updated.")
                st.rerun()

            except Exception as e:

                st.error(
                    f"Could not update product: {e}"
                )

        st.markdown("### 🗑️ Delete Product")

        confirm = st.checkbox(
            "I understand that a product cannot be deleted if it is already being used."
        )

        if st.button(
            "Delete Product",
            disabled=not confirm
        ):

            try:

                execute_query("""
                    DELETE FROM products
                    WHERE product_id = %s;
                """, (product_id,))

                st.success("Product deleted.")
                st.rerun()

            except Exception as e:

                st.error(
                    "Product cannot be deleted because it is "
                    "already referenced by business records."
                )

    # =====================================================
    # SCHOOL MANAGEMENT
    # =====================================================

    with tabs[5]:

        st.markdown("### 🏫 Manage Schools")

        schools = fetch_dataframe("""
            SELECT
                school_id,
                school_name
            FROM schools
            ORDER BY school_name;
        """)

        st.dataframe(
            schools,
            use_container_width=True,
            hide_index=True
        )

        school_id = st.selectbox(
            "Select School",
            schools["school_id"].tolist()
        )

        row = schools[
            schools["school_id"] == school_id
        ].iloc[0]

        new_name = st.text_input(
            "School Name",
            value=row["school_name"]
        )

        if st.button(
            "💾 Save School Changes"
        ):

            try:

                execute_query("""
                    UPDATE schools
                    SET school_name = %s
                    WHERE school_id = %s;
                """, (
                    new_name.strip(),
                    school_id
                ))

                st.success("School updated.")
                st.rerun()

            except Exception as e:

                st.error(
                    f"Could not update school: {e}"
                )

        st.markdown("### ➕ Add School")

        school_to_add = st.text_input(
            "New School Name"
        )

        if st.button(
            "Add School",
            type="primary"
        ):

            if not school_to_add.strip():

                st.error("Enter a school name.")

            else:

                try:

                    execute_query("""
                        INSERT INTO schools
                        (school_name)
                        VALUES (%s);
                    """, (
                        school_to_add.strip(),
                    ))

                    st.success("School added.")
                    st.rerun()

                except Exception as e:

                    st.error(
                        f"Could not add school: {e}"
                    )

        st.markdown("### 🗑️ Delete School")

        confirm = st.checkbox(
            "I understand that deleting a school cannot be undone."
        )

        if st.button(
            "Delete School",
            disabled=not confirm
        ):

            try:

                execute_query("""
                    DELETE FROM schools
                    WHERE school_id = %s;
                """, (school_id,))

                st.success("School deleted.")
                st.rerun()

            except Exception:

                st.error(
                    "This school cannot be deleted because it has "
                    "existing business records."
                )
