import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components
import base64


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
# CSS
# =========================================================

st.markdown("""
<style>

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
[data-testid="stToolbar"] {visibility: hidden;}

.stApp {
    background: linear-gradient(
        -45deg,
        #eef4f8,
        #fef3c7,
        #e0e7ff,
        #d1fae5,
        #fce7f3
    );
    background-size: 400% 400%;
    animation: gradientShift 25s ease infinite;
}

@keyframes gradientShift {
    0% {background-position: 0% 50%;}
    50% {background-position: 100% 50%;}
    100% {background-position: 0% 50%;}
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0b1f3a 0%, #1e3a8a 100%);
}

[data-testid="stSidebar"] * {
    color: white !important;
}

[data-testid="stSidebar"] .stRadio label {
    padding: 8px 12px;
    border-radius: 8px;
}

[data-testid="stSidebar"] .stRadio label:hover {
    background: rgba(255,255,255,0.1);
}

.app-header {
    background: linear-gradient(
        135deg,
        #0b1f3a 0%,
        #1e3a8a 50%,
        #7c3aed 100%
    );
    padding: 28px 32px;
    border-radius: 18px;
    color: white;
    margin-bottom: 25px;
    box-shadow: 0 10px 30px rgba(11,31,58,0.25);
}

.app-header h1 {
    color: white;
    margin: 0;
    font-size: 28px;
}

.app-header p {
    margin: 6px 0 0;
    color: #dbeafe;
}

.main-title {
    font-size: 26px;
    font-weight: 800;
    color: #0b1f3a;
}

.subtitle {
    color: #475569;
    font-size: 14px;
    margin-bottom: 22px;
}

div[data-testid="stMetric"] {
    background: white;
    border-radius: 16px;
    padding: 18px 22px;
    box-shadow: 0 6px 18px rgba(11,31,58,0.08);
    border-left: 5px solid #f28c28;
}

div[data-testid="stMetric"] label {
    color: #64748b !important;
    font-size: 12px !important;
    font-weight: 700 !important;
    letter-spacing: 1px !important;
    text-transform: uppercase !important;
}

div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
    color: #0b1f3a !important;
    font-size: 26px !important;
    font-weight: 800 !important;
}

div[data-testid="column"]:nth-child(1) div[data-testid="stMetric"] {
    border-left-color: #f28c28;
}

div[data-testid="column"]:nth-child(2) div[data-testid="stMetric"] {
    border-left-color: #10b981;
}

div[data-testid="column"]:nth-child(3) div[data-testid="stMetric"] {
    border-left-color: #3b82f6;
}

div[data-testid="column"]:nth-child(4) div[data-testid="stMetric"] {
    border-left-color: #8b5cf6;
}

.stButton > button {
    background: linear-gradient(135deg, #f28c28, #d97706);
    color: white;
    border: none;
    border-radius: 10px;
    font-weight: 700;
    padding: 10px 18px;
}

.stButton > button:hover {
    background: linear-gradient(135deg, #d97706, #b45309);
}

.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
    background: rgba(255,255,255,0.6);
    border-radius: 12px;
    padding: 6px;
}

.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(
        135deg,
        #0b1f3a,
        #1e3a8a
    ) !important;
    color: white !important;
}

[data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
}

.stTextInput input,
.stNumberInput input,
.stSelectbox div[data-baseweb="select"] {
    border-radius: 8px !important;
}

[data-testid="stAlert"] {
    border-radius: 12px;
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

        result = cur.fetchall() if fetch else None

        conn.commit()

        cur.close()

        return result

    except Exception:

        conn.rollback()
        raise

    finally:

        conn.close()


def safe_execute(
    query,
    params=None,
    fetch=False,
    error_message="Operation failed."
):

    try:

        result = execute_query(
            query,
            params,
            fetch
        )

        return True, result

    except Exception as e:

        st.error(
            f"{error_message}\n\n{e}"
        )

        return False, None


def fetch_dataframe(query, params=None):

    conn = get_connection()

    try:

        return pd.read_sql_query(
            query,
            conn,
            params=params
        )

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


def log_action(
    action,
    entity,
    entity_id,
    details=""
):

    try:

        execute_query(
            """
            INSERT INTO audit_log
            (action, entity, entity_id, details)
            VALUES (%s,%s,%s,%s)
            """,
            (
                action,
                entity,
                entity_id,
                details
            )
        )

    except Exception:

        pass


# =========================================================
# DATABASE SETUP + MIGRATION
# =========================================================

def setup_database():

    conn = get_connection()

    try:

        cur = conn.cursor()

        # =================================================
        # SCHOOLS
        # =================================================

        cur.execute("""
            CREATE TABLE IF NOT EXISTS schools (
                school_id SERIAL PRIMARY KEY,
                school_name VARCHAR(100) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cur.execute("""
            ALTER TABLE schools
            ADD COLUMN IF NOT EXISTS created_at
            TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
        """)

        # =================================================
        # PRODUCTS
        # =================================================

        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                product_id SERIAL PRIMARY KEY,
                product_name VARCHAR(100) UNIQUE NOT NULL,
                price NUMERIC(12,2) DEFAULT 0,
                cost_price NUMERIC(12,2) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cur.execute("""
            ALTER TABLE products
            ADD COLUMN IF NOT EXISTS price
            NUMERIC(12,2) DEFAULT 0;
        """)

        cur.execute("""
            ALTER TABLE products
            ADD COLUMN IF NOT EXISTS cost_price
            NUMERIC(12,2) DEFAULT 0;
        """)

        cur.execute("""
            ALTER TABLE products
            ADD COLUMN IF NOT EXISTS created_at
            TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
        """)

        # =================================================
        # CUSTOMERS
        # =================================================

        cur.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                customer_id SERIAL PRIMARY KEY,
                customer_name VARCHAR(150),
                phone VARCHAR(30),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cur.execute("""
            ALTER TABLE customers
            ADD COLUMN IF NOT EXISTS phone VARCHAR(30);
        """)

        cur.execute("""
            ALTER TABLE customers
            ADD COLUMN IF NOT EXISTS created_at
            TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
        """)

        # =================================================
        # SALES
        # =================================================

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

        cur.execute("""
            ALTER TABLE sales
            ADD COLUMN IF NOT EXISTS class_name VARCHAR(50);
        """)

        cur.execute("""
            ALTER TABLE sales
            ADD COLUMN IF NOT EXISTS total_amount
            NUMERIC(12,2) DEFAULT 0;
        """)

        cur.execute("""
            ALTER TABLE sales
            ADD COLUMN IF NOT EXISTS payment_method
            VARCHAR(50);
        """)

        cur.execute("""
            ALTER TABLE sales
            ADD COLUMN IF NOT EXISTS payment_status
            VARCHAR(30) DEFAULT 'Paid';
        """)

        cur.execute("""
            ALTER TABLE sales
            ADD COLUMN IF NOT EXISTS term VARCHAR(30);
        """)

        cur.execute("""
            ALTER TABLE sales
            ADD COLUMN IF NOT EXISTS year INT;
        """)

        # =================================================
        # SALE ITEMS
        # =================================================

        cur.execute("""
            CREATE TABLE IF NOT EXISTS sale_items (
                sale_item_id SERIAL PRIMARY KEY,
                sale_id INT REFERENCES sales(sale_id)
                    ON DELETE CASCADE,
                product_id INT REFERENCES products(product_id),
                quantity INT NOT NULL,
                unit_price NUMERIC(12,2),
                line_total NUMERIC(12,2),
                issued BOOLEAN DEFAULT TRUE
            );
        """)

        cur.execute("""
            ALTER TABLE sale_items
            ADD COLUMN IF NOT EXISTS issued
            BOOLEAN DEFAULT TRUE;
        """)

        # =================================================
        # SCHOOL PRODUCT PRICES
        # =================================================

        cur.execute("""
            CREATE TABLE IF NOT EXISTS school_product_prices (
                school_product_price_id SERIAL PRIMARY KEY,
                school_id INT REFERENCES schools(school_id)
                    ON DELETE CASCADE,
                category_name VARCHAR(100),
                product_id INT REFERENCES products(product_id)
                    ON DELETE CASCADE,
                price NUMERIC(12,2),
                UNIQUE(
                    school_id,
                    category_name,
                    product_id
                )
            );
        """)

        # =================================================
        # STOCK
        # =================================================

        cur.execute("""
            CREATE TABLE IF NOT EXISTS stock (
                stock_id SERIAL PRIMARY KEY,
                school_id INT REFERENCES schools(school_id),
                product_id INT REFERENCES products(product_id),
                quantity_brought INT DEFAULT 0,
                date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                term VARCHAR(30),
                year INT,
                unit_cost NUMERIC(12,2) DEFAULT 0
            );
        """)

        cur.execute("""
            ALTER TABLE stock
            ADD COLUMN IF NOT EXISTS quantity_brought INT DEFAULT 0;
        """)

        cur.execute("""
            ALTER TABLE stock
            ADD COLUMN IF NOT EXISTS unit_cost
            NUMERIC(12,2) DEFAULT 0;
        """)

        # =================================================
        # UNIFORM SETS
        # =================================================

        cur.execute("""
            CREATE TABLE IF NOT EXISTS uniform_sets (
                set_id SERIAL PRIMARY KEY,
                school_id INT REFERENCES schools(school_id)
                    ON DELETE CASCADE,
                set_name VARCHAR(100)
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS set_items (
                set_item_id SERIAL PRIMARY KEY,
                set_id INT REFERENCES uniform_sets(set_id)
                    ON DELETE CASCADE,
                product_id INT REFERENCES products(product_id),
                quantity INT
            );
        """)

        # =================================================
        # INVESTORS
        # =================================================

        cur.execute("""
            CREATE TABLE IF NOT EXISTS investors (
                investor_id SERIAL PRIMARY KEY,
                investor_name VARCHAR(100) UNIQUE NOT NULL,
                active BOOLEAN DEFAULT TRUE
            );
        """)

        cur.execute("""
            ALTER TABLE investors
            ADD COLUMN IF NOT EXISTS active BOOLEAN DEFAULT TRUE;
        """)

        # =================================================
        # PRODUCTION
        # =================================================

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

        # =================================================
        # FINANCIAL TRANSACTIONS
        # =================================================

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

        cur.execute("""
            ALTER TABLE financial_transactions
            ADD COLUMN IF NOT EXISTS sale_id INT;
        """)

        cur.execute("""
            ALTER TABLE financial_transactions
            ADD COLUMN IF NOT EXISTS stock_id INT;
        """)

        cur.execute("""
            ALTER TABLE financial_transactions
            ADD COLUMN IF NOT EXISTS production_id INT;
        """)

        # =================================================
        # AUDIT LOG
        # =================================================

        cur.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                log_id SERIAL PRIMARY KEY,
                log_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                action VARCHAR(50),
                entity VARCHAR(50),
                entity_id INT,
                details TEXT
            );
        """)

        # =================================================
        # FK MIGRATION — enforce ON DELETE CASCADE
        # =================================================

        cur.execute("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'sale_items_sale_id_fkey'
                      AND confdeltype <> 'c'
                ) THEN
                    ALTER TABLE sale_items
                    DROP CONSTRAINT sale_items_sale_id_fkey;

                    ALTER TABLE sale_items
                    ADD CONSTRAINT sale_items_sale_id_fkey
                    FOREIGN KEY (sale_id)
                    REFERENCES sales(sale_id)
                    ON DELETE CASCADE;
                END IF;

                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'sale_items_sale_id_fkey'
                ) THEN
                    ALTER TABLE sale_items
                    ADD CONSTRAINT sale_items_sale_id_fkey
                    FOREIGN KEY (sale_id)
                    REFERENCES sales(sale_id)
                    ON DELETE CASCADE;
                END IF;
            END $$;
        """)

        cur.execute("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'financial_transactions_sale_id_fkey'
                      AND confdeltype <> 'c'
                ) THEN
                    ALTER TABLE financial_transactions
                    DROP CONSTRAINT financial_transactions_sale_id_fkey;

                    ALTER TABLE financial_transactions
                    ADD CONSTRAINT financial_transactions_sale_id_fkey
                    FOREIGN KEY (sale_id)
                    REFERENCES sales(sale_id)
                    ON DELETE CASCADE;
                END IF;

                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'financial_transactions_sale_id_fkey'
                ) THEN
                    ALTER TABLE financial_transactions
                    ADD CONSTRAINT financial_transactions_sale_id_fkey
                    FOREIGN KEY (sale_id)
                    REFERENCES sales(sale_id)
                    ON DELETE CASCADE;
                END IF;
            END $$;
        """)

        cur.execute("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'financial_transactions_stock_id_fkey'
                      AND confdeltype <> 'c'
                ) THEN
                    ALTER TABLE financial_transactions
                    DROP CONSTRAINT financial_transactions_stock_id_fkey;

                    ALTER TABLE financial_transactions
                    ADD CONSTRAINT financial_transactions_stock_id_fkey
                    FOREIGN KEY (stock_id)
                    REFERENCES stock(stock_id)
                    ON DELETE CASCADE;
                END IF;

                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'financial_transactions_stock_id_fkey'
                ) THEN
                    ALTER TABLE financial_transactions
                    ADD CONSTRAINT financial_transactions_stock_id_fkey
                    FOREIGN KEY (stock_id)
                    REFERENCES stock(stock_id)
                    ON DELETE CASCADE;
                END IF;
            END $$;
        """)

        cur.execute("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'financial_transactions_production_id_fkey'
                      AND confdeltype <> 'c'
                ) THEN
                    ALTER TABLE financial_transactions
                    DROP CONSTRAINT financial_transactions_production_id_fkey;

                    ALTER TABLE financial_transactions
                    ADD CONSTRAINT financial_transactions_production_id_fkey
                    FOREIGN KEY (production_id)
                    REFERENCES tailor_production(production_id)
                    ON DELETE CASCADE;
                END IF;

                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'financial_transactions_production_id_fkey'
                ) THEN
                    ALTER TABLE financial_transactions
                    ADD CONSTRAINT financial_transactions_production_id_fkey
                    FOREIGN KEY (production_id)
                    REFERENCES tailor_production(production_id)
                    ON DELETE CASCADE;
                END IF;
            END $$;
        """)

        # =================================================
        # REAL SCHOOLS
        # =================================================

        cur.execute("""
            INSERT INTO schools (school_name)
            VALUES
                ('LOVING BLOOMS SCHOOL'),
                ('WARIDI UTAWALA SCHOOL')
            ON CONFLICT (school_name)
            DO NOTHING;
        """)

        # =================================================
        # REAL INVESTORS
        # =================================================

        cur.execute("""
            INSERT INTO investors
            (investor_name, active)
            VALUES
                ('Gift', TRUE),
                ('Ken', TRUE)
            ON CONFLICT (investor_name)
            DO UPDATE SET active = TRUE;
        """)

        # =================================================
        # REAL PRODUCT LIST
        # =================================================

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
                VALUES (%s,%s,0)
                ON CONFLICT (product_name)
                DO NOTHING;
            """, (name, price))

        conn.commit()

        cur.close()

    except Exception as e:

        conn.rollback()

        st.error(
            f"Database setup error: {e}"
        )

        st.stop()

    finally:

        conn.close()


# =========================================================
# RUN DATABASE SETUP
# =========================================================

@st.cache_resource
def setup_once():

    setup_database()

    return True


setup_once()


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
# RECEIPTS
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


def build_receipt_html(receipt):

    h = receipt["header"]
    items = receipt["items"]

    item_rows = ""

    for _, row in items.iterrows():

        item_rows += f"""
        <tr>
            <td>{row['product_name']}</td>
            <td style="text-align:center;">
                {int(row['quantity'])}
            </td>
            <td style="text-align:right;">
                KSh {float(row['unit_price']):,.2f}
            </td>
            <td style="text-align:right;">
                KSh {float(row['line_total']):,.2f}
            </td>
        </tr>
        """

    sale_date = h["sale_date"]

    if hasattr(sale_date, "strftime"):

        sale_date = sale_date.strftime(
            "%d %b %Y, %I:%M %p"
        )

    return f"""
    <!DOCTYPE html>
    <html>

    <head>

    <meta charset="utf-8">

    <style>

    body {{
        font-family: Arial, sans-serif;
        background:#f3f4f6;
        padding:20px;
    }}

    .receipt {{
        width:620px;
        max-width:100%;
        margin:auto;
        background:white;
        padding:34px;
        border-radius:10px;
        box-shadow:0 8px 24px rgba(0,0,0,.1);
    }}

    .header {{
        text-align:center;
        border-bottom:2px solid #0b1f3a;
        padding-bottom:16px;
        margin-bottom:18px;
    }}

    .header h2 {{
        margin:0;
        color:#0b1f3a;
    }}

    table {{
        width:100%;
        border-collapse:collapse;
    }}

    th,td {{
        padding:9px 6px;
        border-bottom:1px solid #e5e7eb;
    }}

    th {{
        background:#f3f4f6;
    }}

    .total {{
        text-align:right;
        font-size:22px;
        font-weight:bold;
        margin-top:22px;
        padding-top:14px;
        border-top:2px solid #0b1f3a;
        color:#0b1f3a;
    }}

    .footer {{
        text-align:center;
        margin-top:26px;
        color:#666;
    }}

    .print-button {{
        display:block;
        margin:22px auto 0;
        padding:12px 32px;
        background:#f28c28;
        color:white;
        border:none;
        border-radius:8px;
        cursor:pointer;
        font-weight:bold;
    }}

    @media print {{

        body {{
            background:white;
            padding:0;
        }}

        .receipt {{
            width:100%;
            box-shadow:none;
        }}

        .print-button {{
            display:none;
        }}

    }}

    </style>

    </head>

    <body>

    <div class="receipt">

        <div class="header">

            <h2>UNIFORM BUSINESS</h2>

            <p>
                {h.get('school_name') or ''}
            </p>

            <strong>
                SALES RECEIPT
            </strong>

        </div>

        <p>
            <strong>Receipt No:</strong>
            {h.get('sale_id')}
        </p>

        <p>
            <strong>Date:</strong>
            {sale_date}
        </p>

        <p>
            <strong>Customer:</strong>
            {h.get('customer_name') or ''}
        </p>

        <p>
            <strong>Phone:</strong>
            {h.get('phone') or ''}
        </p>

        <p>
            <strong>Class:</strong>
            {h.get('class_name') or ''}
        </p>

        <p>
            <strong>Term:</strong>
            {h.get('term') or ''}
        </p>

        <p>
            <strong>Payment:</strong>
            {h.get('payment_method') or ''}
        </p>

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

            TOTAL:
            KSh {float(h.get('total_amount') or 0):,.2f}

        </div>

        <div class="footer">

            Thank you for your business.

        </div>

        <button
            class="print-button"
            onclick="window.print()">

            🖨️ Print Receipt

        </button>

    </div>

    </body>

    </html>
    """


def render_receipt(receipt):

    if not receipt:

        st.warning("Receipt not found.")

        return

    html = build_receipt_html(receipt)

    components.html(
        html,
        height=760,
        scrolling=True
    )


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.markdown("""
    <div style="
        text-align:center;
        padding:14px 0 20px;
        font-size:20px;
        font-weight:800;
    ">
        🏫 UNIFORM BUSINESS
    </div>
    """, unsafe_allow_html=True)

    pages = [
        "Dashboard",
        "New Sale",
        "Sales History",
        "Stock Management",
        "Price Management",
        "Tailor & Production",
        "Business Finance",
        "ML & Forecasting",
        "System Management"
    ]

    page = st.radio(
        "Navigation",
        pages,
        index=pages.index(
            st.session_state.page
        ),
        label_visibility="collapsed"
    )

    st.session_state.page = page

    st.markdown("---")

    st.caption(
        "Uniform Business Management System"
    )

    st.caption(
        "PostgreSQL • Python • Streamlit"
    )


# =========================================================
# HEADER
# =========================================================

st.markdown("""
<div class="app-header">

    <h1>
        🏫 UNIFORM BUSINESS MANAGEMENT SYSTEM
    </h1>

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
        '<div class="subtitle">'
        'Business overview and daily performance'
        '</div>',
        unsafe_allow_html=True
    )

    today_sales = fetch_dataframe("""
        SELECT COALESCE(
            SUM(total_amount),0
        ) AS value
        FROM sales
        WHERE DATE(sale_date)=CURRENT_DATE;
    """)

    month_sales = fetch_dataframe("""
        SELECT COALESCE(
            SUM(total_amount),0
        ) AS value
        FROM sales
        WHERE sale_date >=
        DATE_TRUNC('month',CURRENT_DATE);
    """)

    transactions = fetch_dataframe("""
        SELECT COUNT(*) AS value
        FROM sales
        WHERE DATE(sale_date)=CURRENT_DATE;
    """)

    items = fetch_dataframe("""
        SELECT COALESCE(
            SUM(si.quantity),0
        ) AS value
        FROM sale_items si
        JOIN sales s
            ON si.sale_id=s.sale_id
        WHERE DATE(s.sale_date)=CURRENT_DATE
        AND si.issued=TRUE;
    """)

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "Today's Sales",
            money(today_sales.iloc[0]["value"])
        )

    with c2:
        st.metric(
            "This Month",
            money(month_sales.iloc[0]["value"])
        )

    with c3:
        st.metric(
            "Today's Transactions",
            int(transactions.iloc[0]["value"])
        )

    with c4:
        st.metric(
            "Items Sold Today",
            int(items.iloc[0]["value"])
        )

    st.markdown("### ⚡ Quick Actions")

    q1,q2,q3,q4 = st.columns(4)

    with q1:

        if st.button(
            "➕ New Sale",
            use_container_width=True
        ):

            st.session_state.page = "New Sale"
            st.rerun()

    with q2:

        if st.button(
            "📦 Add Stock",
            use_container_width=True
        ):

            st.session_state.page = "Stock Management"
            st.rerun()

    with q3:

        if st.button(
            "💰 Manage Prices",
            use_container_width=True
        ):

            st.session_state.page = "Price Management"
            st.rerun()

    with q4:

        if st.button(
            "📜 Sales History",
            use_container_width=True
        ):

            st.session_state.page = "Sales History"
            st.rerun()

    st.markdown("---")

    left,right = st.columns(2)

    with left:

        st.markdown(
            "### 📈 Sales Trend"
        )

        trend = fetch_dataframe("""
            SELECT
                DATE(sale_date) AS sale_day,
                SUM(total_amount) AS revenue
            FROM sales
            WHERE sale_date >=
                CURRENT_DATE-INTERVAL '30 days'
            GROUP BY DATE(sale_date)
            ORDER BY sale_day;
        """)

        if trend.empty:

            st.info(
                "No sales recorded yet."
            )

        else:

            trend["sale_day"] = pd.to_datetime(
                trend["sale_day"]
            )

            st.line_chart(
                trend.set_index("sale_day")["revenue"]
            )

    with right:

        st.markdown(
            "### 🏫 Sales by School"
        )

        school_sales = fetch_dataframe("""
            SELECT
                sc.school_name,
                COALESCE(
                    SUM(s.total_amount),0
                ) AS revenue
            FROM schools sc
            LEFT JOIN sales s
                ON sc.school_id=s.school_id
            GROUP BY sc.school_name
            ORDER BY revenue DESC;
        """)

        if school_sales.empty:

            st.info(
                "No sales recorded yet."
            )

        else:

            st.bar_chart(
                school_sales.set_index(
                    "school_name"
                )["revenue"]
            )

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
            ON s.school_id=sc.school_id
        LEFT JOIN customers c
            ON s.customer_id=c.customer_id
        ORDER BY s.sale_date DESC
        LIMIT 10;
    """)

    if recent.empty:

        st.info(
            "No sales recorded yet."
        )

    else:

        st.dataframe(
            recent,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Amount":
                    st.column_config.NumberColumn(
                        "Amount",
                        format="KSh %.2f"
                    )
            }
        )


# =========================================================
# NEW SALE
# =========================================================

elif page == "New Sale":

    st.markdown("## 🧾 New Sale")

    schools = fetch_dataframe("""
        SELECT school_id, school_name
        FROM schools
        ORDER BY school_name;
    """)

    if schools.empty:

        st.warning(
            "No schools found."
        )

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

    c1,c2,c3 = st.columns(3)

    with c1:

        term = st.selectbox(
            "Term",
            ["Term 1","Term 2","Term 3"]
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
            ["Primary","Junior Secondary"]
        )

    c1,c2 = st.columns(2)

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
            ON spp.product_id=p.product_id
        WHERE spp.school_id=%s
        AND spp.category_name=%s
        ORDER BY p.product_name;
    """, (school_id,category))

    if available.empty:

        st.warning(
            "No prices assigned to this "
            "school/category. Go to "
            "Price Management first."
        )

    else:

        product_name = st.selectbox(
            "Product",
            available["product_name"].tolist()
        )

        selected = available[
            available["product_name"] ==
            product_name
        ].iloc[0]

        unit_price = float(
            selected["price"]
        )

        st.info(
            f"Unit price: {money(unit_price)}"
        )

        quantity = st.number_input(
            "Quantity",
            min_value=1,
            value=1,
            step=1
        )

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

                "product_id":
                    int(selected["product_id"]),

                "product":
                    product_name,

                "quantity":
                    int(quantity),

                "unit_price":
                    unit_price,

                "line_total":
                    unit_price * quantity,

                "issued":
                    issued
            })

            st.success(
                "Item added to cart."
            )

    st.markdown("### 🛒 Cart")

    if st.session_state.cart:

        cart_df = pd.DataFrame(
            st.session_state.cart
        )

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
            hide_index=True,
            column_config={

                "unit_price":
                    st.column_config.NumberColumn(
                        "Unit Price",
                        format="KSh %.2f"
                    ),

                "line_total":
                    st.column_config.NumberColumn(
                        "Line Total",
                        format="KSh %.2f"
                    )
            }
        )

        total = sum(
            item["line_total"]
            for item in st.session_state.cart
        )

        st.markdown(
            f"## Total: {money(total)}"
        )

        payment_method = st.selectbox(
            "Payment Method",
            ["Cash","M-Pesa","Bank","Other"]
        )

        c1,c2 = st.columns(2)

        with c1:

            if st.button(
                "🗑️ Clear Cart",
                use_container_width=True
            ):

                st.session_state.cart = []
                st.rerun()

        with c2:

            if st.button(
                "✅ Complete Sale",
                type="primary",
                use_container_width=True
            ):

                if not customer_name.strip():

                    st.error(
                        "Enter the student/customer name."
                    )

                else:

                    conn = get_connection()

                    try:

                        cur = conn.cursor()

                        for item in st.session_state.cart:

                            cur.execute("""
                                SELECT
                                    COALESCE(
                                        SUM(quantity_brought),
                                        0
                                    )
                                FROM stock
                                WHERE school_id=%s
                                AND product_id=%s;
                            """, (
                                school_id,
                                item["product_id"]
                            ))

                            total_stock = cur.fetchone()[0]

                            cur.execute("""
                                SELECT
                                    COALESCE(
                                        SUM(si.quantity),
                                        0
                                    )
                                FROM sale_items si
                                JOIN sales s
                                    ON si.sale_id=s.sale_id
                                WHERE s.school_id=%s
                                AND si.product_id=%s
                                AND si.issued=TRUE;
                            """, (
                                school_id,
                                item["product_id"]
                            ))

                            total_sold = cur.fetchone()[0]

                            available_stock = (
                                int(total_stock or 0)
                                -
                                int(total_sold or 0)
                            )

                            if (
                                item["issued"]
                                and
                                item["quantity"] >
                                available_stock
                            ):

                                raise ValueError(
                                    f"Not enough stock for "
                                    f"{item['product']}."
                                    f" Available: "
                                    f"{available_stock}"
                                )

                        cur.execute("""
                            INSERT INTO customers
                            (customer_name, phone)
                            VALUES (%s,%s)
                            RETURNING customer_id;
                        """, (
                            customer_name.strip(),
                            phone.strip()
                        ))

                        customer_id = cur.fetchone()[0]

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
                            (%s,%s,%s,%s,%s,
                             'Paid',%s,%s)
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

                        log_action(
                            "CREATE",
                            "sale",
                            sale_id,
                            f"Total {money(total)}"
                        )

                        st.session_state.last_receipt = sale_id
                        st.session_state.cart = []

                        st.success(
                            f"Sale #{sale_id} completed successfully."
                        )

                        st.rerun()

                    except Exception as e:

                        conn.rollback()
                        conn.close()

                        st.error(
                            f"Sale could not be completed: {e}"
                        )

    else:

        st.info(
            "Your cart is empty."
        )


# =========================================================
# RECEIPT
# =========================================================

if (
    page == "New Sale"
    and
    st.session_state.last_receipt
):

    st.markdown("---")

    st.markdown(
        "## 🧾 Receipt"
    )

    render_receipt(
        get_receipt(
            st.session_state.last_receipt
        )
    )

    if st.button(
        "Close Receipt"
    ):

        st.session_state.last_receipt = None
        st.rerun()


# =========================================================
# SALES HISTORY
# =========================================================

elif page == "Sales History":

    st.markdown(
        "## 📜 Sales History"
    )

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
            ON s.school_id=sc.school_id
        LEFT JOIN customers c
            ON s.customer_id=c.customer_id
        ORDER BY s.sale_date DESC;
    """)

    if sales.empty:

        st.info(
            "No sales have been recorded yet."
        )

    else:

        st.dataframe(
            sales,
            use_container_width=True,
            hide_index=True,
            column_config={
                "total_amount":
                    st.column_config.NumberColumn(
                        "Amount",
                        format="KSh %.2f"
                    )
            }
        )

        st.download_button(
            "⬇️ Download Sales CSV",
            sales.to_csv(index=False),
            file_name="sales_history.csv",
            mime="text/csv"
        )

        st.markdown("---")

        sale_id = st.number_input(
            "Receipt number",
            min_value=1,
            step=1
        )

        if st.button(
            "🧾 View / Print Receipt",
            type="primary"
        ):

            receipt = get_receipt(
                int(sale_id)
            )

            if receipt:

                render_receipt(
                    receipt
                )

            else:

                st.error(
                    "Receipt not found."
                )


# =========================================================
# PRICE MANAGEMENT
# =========================================================

elif page == "Price Management":

    st.markdown(
        "## 💰 Price Management"
    )

    schools = fetch_dataframe("""
        SELECT school_id, school_name
        FROM schools
        ORDER BY school_name;
    """)

    school_name = st.selectbox(
        "School",
        schools["school_name"].tolist()
    )

    school_id = int(
        schools.loc[
            schools["school_name"] ==
            school_name,
            "school_id"
        ].iloc[0]
    )

    category = st.selectbox(
        "Category",
        ["Primary","Junior Secondary"]
    )

    prices = fetch_dataframe("""
        SELECT
            spp.school_product_price_id,
            p.product_name,
            spp.price
        FROM school_product_prices spp
        JOIN products p
            ON spp.product_id=p.product_id
        WHERE spp.school_id=%s
        AND spp.category_name=%s
        ORDER BY p.product_name;
    """, (
        school_id,
        category
    ))

    st.markdown(
        "### Existing Prices"
    )

    if prices.empty:

        st.info(
            "No prices assigned yet."
        )

    else:

        for _, row in prices.iterrows():

            c1,c2,c3 = st.columns(
                [4,2,1]
            )

            with c1:

                st.write(
                    row["product_name"]
                )

            with c2:

                new_price = st.number_input(
                    "Price",
                    min_value=0.0,
                    value=float(
                        row["price"]
                    ),
                    step=50.0,
                    key=f"price_{row['school_product_price_id']}"
                )

            with c3:

                if st.button(
                    "Save",
                    key=f"save_price_{row['school_product_price_id']}"
                ):

                    ok,_ = safe_execute("""
                        UPDATE
                            school_product_prices
                        SET price=%s
                        WHERE
                            school_product_price_id=%s;
                    """, (
                        new_price,
                        row["school_product_price_id"]
                    ))

                    if ok:

                        st.success(
                            "Price updated."
                        )

                        st.rerun()

    st.markdown("---")

    st.markdown(
        "### ➕ Assign Product"
    )

    products = fetch_dataframe("""
        SELECT
            product_id,
            product_name,
            price
        FROM products
        ORDER BY product_name;
    """)

    assigned = fetch_dataframe("""
        SELECT product_id
        FROM school_product_prices
        WHERE school_id=%s
        AND category_name=%s;
    """, (
        school_id,
        category
    ))

    assigned_ids = set(
        assigned["product_id"].tolist()
    ) if not assigned.empty else set()

    unassigned = products[
        ~products["product_id"].isin(
            assigned_ids
        )
    ]

    if unassigned.empty:

        st.success(
            "All products have been assigned."
        )

    else:

        product_name = st.selectbox(
            "Product",
            unassigned["product_name"].tolist()
        )

        product = unassigned[
            unassigned["product_name"] ==
            product_name
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

            ok,_ = safe_execute("""
                INSERT INTO
                    school_product_prices
                (
                    school_id,
                    category_name,
                    product_id,
                    price
                )
                VALUES (%s,%s,%s,%s);
            """, (
                school_id,
                category,
                int(product["product_id"]),
                price
            ))

            if ok:

                st.success(
                    "Product assigned."
                )

                st.rerun()

    st.markdown("---")

    st.markdown(
        "### ➕ Create New Product"
    )

    new_product = st.text_input(
        "Product Name"
    )

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

            st.error(
                "Enter product name."
            )

        else:

            ok,_ = safe_execute("""
                INSERT INTO products
                (
                    product_name,
                    price,
                    cost_price
                )
                VALUES (%s,%s,%s);
            """, (
                new_product.strip(),
                selling_price,
                cost_price
            ))

            if ok:

                st.success(
                    "Product created."
                )

                st.rerun()


# =========================================================
# STOCK MANAGEMENT
# =========================================================

elif page == "Stock Management":

    st.markdown(
        "## 📦 Stock Management"
    )

    schools = fetch_dataframe("""
        SELECT school_id, school_name
        FROM schools
        ORDER BY school_name;
    """)

    products = fetch_dataframe("""
        SELECT product_id, product_name
        FROM products
        ORDER BY product_name;
    """)

    school_name = st.selectbox(
        "School",
        schools["school_name"].tolist()
    )

    school_id = int(
        schools.loc[
            schools["school_name"] ==
            school_name,
            "school_id"
        ].iloc[0]
    )

    product_name = st.selectbox(
        "Product",
        products["product_name"].tolist()
    )

    product_id = int(
        products.loc[
            products["product_name"] ==
            product_name,
            "product_id"
        ].iloc[0]
    )

    c1,c2,c3,c4 = st.columns(4)

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
            ["Term 1","Term 2","Term 3"]
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
                VALUES
                (%s,%s,%s,%s,%s,%s)
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

            total_cost = (
                quantity * unit_cost
            )

            cur.execute("""
                INSERT INTO
                    financial_transactions
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

            log_action(
                "CREATE",
                "stock",
                stock_id,
                f"{quantity} x {product_name}"
            )

            st.success(
                "Stock added successfully."
            )

            st.rerun()

        except Exception as e:

            conn.rollback()
            conn.close()

            st.error(
                f"Could not add stock: {e}"
            )

    st.markdown("---")

    st.markdown(
        "### 📊 Current Stock"
    )

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
            ON st.school_id=sc.school_id
        JOIN products p
            ON st.product_id=p.product_id
        ORDER BY st.date_added DESC;
    """)

    if stock_df.empty:

        st.info(
            "No stock records yet."
        )

    else:

        st.dataframe(
            stock_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "unit_cost":
                    st.column_config.NumberColumn(
                        "Unit Cost",
                        format="KSh %.2f"
                    )
            }
        )

        remaining = fetch_dataframe("""
            WITH brought AS (

                SELECT
                    school_id,
                    product_id,
                    SUM(quantity_brought) AS qty

                FROM stock

                GROUP BY
                    school_id,
                    product_id
            ),

            sold AS (

                SELECT
                    s.school_id,
                    si.product_id,
                    SUM(si.quantity) AS qty

                FROM sale_items si

                JOIN sales s
                    ON si.sale_id=s.sale_id

                WHERE si.issued=TRUE

                GROUP BY
                    s.school_id,
                    si.product_id
            )

            SELECT

                sc.school_name,
                p.product_name,

                COALESCE(b.qty,0)
                -
                COALESCE(sl.qty,0)
                AS remaining

            FROM brought b

            JOIN schools sc
                ON b.school_id=sc.school_id

            JOIN products p
                ON b.product_id=p.product_id

            LEFT JOIN sold sl

                ON sl.school_id=b.school_id

                AND sl.product_id=b.product_id

            ORDER BY remaining ASC;
        """)

        st.markdown(
            "### Remaining Stock"
        )

        st.dataframe(
            remaining,
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# TAILOR & PRODUCTION
# =========================================================

elif page == "Tailor & Production":

    st.markdown(
        "## 🧵 Tailor & Production"
    )

    schools = fetch_dataframe("""
        SELECT school_id, school_name
        FROM schools
        ORDER BY school_name;
    """)

    products = fetch_dataframe("""
        SELECT product_id, product_name
        FROM products
        ORDER BY product_name;
    """)

    school_name = st.selectbox(
        "School",
        schools["school_name"].tolist()
    )

    school_id = int(
        schools.loc[
            schools["school_name"] ==
            school_name,
            "school_id"
        ].iloc[0]
    )

    product_name = st.selectbox(
        "Product",
        products["product_name"].tolist()
    )

    product_id = int(
        products.loc[
            products["product_name"] ==
            product_name,
            "product_id"
        ].iloc[0]
    )

    tailor_name = st.text_input(
        "Tailor Name"
    )

    quantity = st.number_input(
        "Quantity Produced",
        min_value=1,
        step=1
    )

    cost_per_item = st.number_input(
        "Cost Per Item",
        min_value=0.0,
        step=50.0
    )

    term = st.selectbox(
        "Term",
        ["Term 1","Term 2","Term 3"]
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

    amount_paid = (
        quantity * cost_per_item
    )

    st.info(
        f"Total tailor payment: "
        f"{money(amount_paid)}"
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
                INSERT INTO
                    financial_transactions
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

            log_action(
                "CREATE",
                "production",
                production_id,
                f"{quantity} x {product_name}"
            )

            st.success(
                "Production recorded successfully."
            )

            st.rerun()

        except Exception as e:

            conn.rollback()
            conn.close()

            st.error(
                f"Could not record production: {e}"
            )

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
            ON tp.school_id=sc.school_id
        JOIN products p
            ON tp.product_id=p.product_id
        ORDER BY tp.production_date DESC;
    """)

    if production.empty:

        st.info(
            "No production records yet."
        )

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

    st.markdown(
        "## 💼 Business Finance"
    )

    investors = fetch_dataframe("""
        SELECT
            i.investor_id,
            i.investor_name,
            COALESCE(
                SUM(ft.amount),
                0
            ) AS capital

        FROM investors i

        LEFT JOIN financial_transactions ft

            ON i.investor_id =
               ft.investor_id

            AND ft.transaction_type =
               'Capital Contribution'

        WHERE i.active=TRUE

        GROUP BY
            i.investor_id,
            i.investor_name

        ORDER BY
            i.investor_name;
    """)

    st.markdown(
        "### 👥 Investors"
    )

    if investors.empty:

        st.info(
            "No investors found."
        )

        capital = 0

    else:

        capital = float(
            investors["capital"].sum()
        )

        display = investors.copy()

        display["Capital"] = display[
            "capital"
        ].apply(money)

        display = display[
            ["investor_name","Capital"]
        ]

        display.columns = [
            "Investor",
            "Capital"
        ]

        st.dataframe(
            display,
            use_container_width=True,
            hide_index=True
        )

    st.markdown(
        "### ➕ Additional Investment"
    )

    investor_name = st.selectbox(
        "Investor",
        ["Gift","Ken"]
    )

    investment_amount = st.number_input(
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
            WHERE investor_name=%s;
        """, (investor_name,))

        if investor.empty:

            st.error(
                "Investor not found."
            )

        else:

            investor_id = int(
                investor.iloc[0]["investor_id"]
            )

            ok,_ = safe_execute("""
                INSERT INTO
                    financial_transactions
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
                );
            """, (
                description,
                investment_amount,
                investor_id
            ))

            if ok:

                log_action(
                    "CREATE",
                    "capital",
                    investor_id,
                    f"{money(investment_amount)}"
                )

                st.success(
                    "Investment recorded."
                )

                st.rerun()

    st.markdown("---")

    st.markdown(
        "### 💸 Financial Transaction"
    )

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
        "Description",
        key="finance_description"
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

        ok,_ = safe_execute("""
            INSERT INTO
                financial_transactions
            (
                transaction_type,
                category,
                description,
                amount
            )
            VALUES
            (%s,%s,%s,%s);
        """, (
            transaction_type,
            category,
            description,
            amount
        ))

        if ok:

            st.success(
                "Transaction recorded."
            )

            st.rerun()

    st.markdown("---")

    st.markdown(
        "### 📊 Financial Summary"
    )

    def get_sum(transaction_type):

        df = fetch_dataframe("""
            SELECT
                COALESCE(
                    SUM(amount),0
                ) AS value
            FROM financial_transactions
            WHERE transaction_type=%s;
        """, (transaction_type,))

        return float(
            df.iloc[0]["value"]
        )

    revenue = get_sum(
        "Sales Income"
    )

    stock_purchases = get_sum(
        "Stock Purchase"
    )

    tailor_payments = get_sum(
        "Tailor Payment"
    )

    expenses = get_sum(
        "Expense"
    )

    other_income = get_sum(
        "Other Income"
    )

    withdrawals = get_sum(
        "Owner Withdrawal"
    )

    distributions = get_sum(
        "Profit Distribution"
    )

    gross_profit = (
        revenue
        -
        stock_purchases
        -
        tailor_payments
    )

    net_profit = (
        gross_profit
        +
        other_income
        -
        expenses
    )

    cash_position = (
        capital
        +
        revenue
        +
        other_income
        -
        stock_purchases
        -
        tailor_payments
        -
        expenses
        -
        withdrawals
        -
        distributions
    )

    c1,c2,c3,c4 = st.columns(4)

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

    st.markdown(
        "### 📒 Financial Ledger"
    )

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
            hide_index=True,
            column_config={
                "amount":
                    st.column_config.NumberColumn(
                        "Amount",
                        format="KSh %.2f"
                    )
            }
        )


# =========================================================
# ML
# =========================================================

elif page == "ML & Forecasting":

    st.markdown(
        "## 🤖 ML & Forecasting"
    )

    st.info(
        "ML features will become more useful "
        "after enough real sales data has been "
        "collected."
    )

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
            "There is not enough sales data yet."
        )

    else:

        daily["sale_day"] = pd.to_datetime(
            daily["sale_day"]
        )

        st.line_chart(
            daily.set_index(
                "sale_day"
            )["revenue"]
        )

        if len(daily) >= 3:

            avg = daily[
                "revenue"
            ].tail(7).mean()

            st.metric(
                "Recent Average Daily Revenue",
                money(avg)
            )

    st.markdown(
        "### 🧮 Product Demand"
    )

    demand = fetch_dataframe("""
        SELECT
            p.product_name,
            SUM(si.quantity) AS units_sold,
            SUM(si.line_total) AS revenue
        FROM sale_items si
        JOIN products p
            ON si.product_id=p.product_id
        WHERE si.issued=TRUE
        GROUP BY p.product_name
        ORDER BY units_sold DESC;
    """)

    if demand.empty:

        st.info(
            "No sales data available."
        )

    else:

        st.dataframe(
            demand,
            use_container_width=True,
            hide_index=True
        )

        st.bar_chart(
            demand.set_index(
                "product_name"
            )["units_sold"]
        )

    st.markdown("---")

    st.markdown(
        "### 🔬 Future ML Features"
    )

    st.write("""
    • Product demand forecasting

    • School-level forecasting

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

    st.markdown(
        "## ⚙️ System Management"
    )

    tabs = st.tabs([
        "Sales",
        "Stock",
        "Production",
        "Finance",
        "Products",
        "Schools",
        "Audit Log",
        "Danger Zone"
    ])


    # =====================================================
    # SALES
    # =====================================================

    with tabs[0]:

        st.markdown(
            "### 🧾 Manage Sales"
        )

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
                ON s.school_id=sc.school_id
            LEFT JOIN customers c
                ON s.customer_id=c.customer_id
            ORDER BY s.sale_date DESC;
        """)

        if sales.empty:

            st.info(
                "No sales to manage."
            )

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

                st.markdown(
                    "#### Edit Sale"
                )

                schools = fetch_dataframe("""
                    SELECT
                        school_id,
                        school_name
                    FROM schools
                    ORDER BY school_name;
                """)

                school_options = (
                    schools["school_name"].tolist()
                )

                current_school = h[
                    "school_name"
                ]

                school_index = (
                    school_options.index(
                        current_school
                    )
                    if current_school
                    in school_options
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

                terms = [
                    "Term 1",
                    "Term 2",
                    "Term 3"
                ]

                new_term = st.selectbox(
                    "Term",
                    terms,
                    index=(
                        terms.index(h["term"])
                        if h["term"] in terms
                        else 0
                    ),
                    key="edit_term"
                )

                payments = [
                    "Cash",
                    "M-Pesa",
                    "Bank",
                    "Other"
                ]

                new_payment = st.selectbox(
                    "Payment Method",
                    payments,
                    index=(
                        payments.index(
                            h["payment_method"]
                        )
                        if h["payment_method"]
                        in payments
                        else 0
                    ),
                    key="edit_payment"
                )

                statuses = [
                    "Paid",
                    "Pending",
                    "Cancelled"
                ]

                new_status = st.selectbox(
                    "Payment Status",
                    statuses,
                    index=(
                        statuses.index(
                            h["payment_status"]
                        )
                        if h["payment_status"]
                        in statuses
                        else 0
                    ),
                    key="edit_status"
                )

                new_year = st.number_input(
                    "Year",
                    min_value=2020,
                    max_value=2100,
                    value=int(
                        h["year"]
                        or datetime.now().year
                    ),
                    key="edit_year"
                )

                if st.button(
                    "💾 Save Sale Changes",
                    type="primary"
                ):

                    school_id = int(
                        schools.loc[
                            schools["school_name"]
                            == new_school_name,
                            "school_id"
                        ].iloc[0]
                    )

                    ok1,_ = safe_execute("""
                        UPDATE customers
                        SET
                            customer_name=%s,
                            phone=%s
                        WHERE customer_id=(
                            SELECT customer_id
                            FROM sales
                            WHERE sale_id=%s
                        );
                    """, (
                        new_customer,
                        new_phone,
                        selected_sale
                    ))

                    ok2,_ = safe_execute("""
                        UPDATE sales
                        SET
                            school_id=%s,
                            class_name=%s,
                            payment_method=%s,
                            payment_status=%s,
                            term=%s,
                            year=%s
                        WHERE sale_id=%s;
                    """, (
                        school_id,
                        new_class,
                        new_payment,
                        new_status,
                        new_term,
                        new_year,
                        selected_sale
                    ))

                    if ok1 and ok2:

                        log_action(
                            "UPDATE",
                            "sale",
                            selected_sale,
                            f"Updated sale #{selected_sale}"
                        )

                        st.success(
                            "Sale updated."
                        )

                        st.rerun()

                st.markdown("---")

                if st.button(
                    "🖨️ Print This Receipt",
                    key="print_old_receipt"
                ):

                    render_receipt(
                        get_receipt(
                            selected_sale
                        )
                    )

                st.markdown(
                    "### ⚠️ Delete Sale"
                )

                confirm_delete = st.checkbox(
                    "I understand that deleting this sale cannot be undone.",
                    key="confirm_sale_delete"
                )

                if st.button(
                    "🗑️ Delete Sale",
                    disabled=not confirm_delete
                ):

                    ok,_ = safe_execute("""
                        DELETE FROM sales
                        WHERE sale_id=%s;
                    """, (
                        selected_sale,
                    ),
                        error_message=
                        "Could not delete sale."
                    )

                    if ok:

                        log_action(
                            "DELETE",
                            "sale",
                            selected_sale,
                            f"Deleted sale #{selected_sale}"
                        )

                        st.success(
                            f"Sale #{selected_sale} deleted."
                        )

                        st.rerun()


    # =====================================================
    # STOCK MANAGEMENT
    # =====================================================

    with tabs[1]:

        st.markdown(
            "### 📦 Manage Stock"
        )

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
                ON st.school_id=sc.school_id
            JOIN products p
                ON st.product_id=p.product_id
            ORDER BY st.date_added DESC;
        """)

        if stock.empty:

            st.info(
                "No stock records."
            )

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
                stock["stock_id"] ==
                stock_id
            ].iloc[0]

            new_quantity = st.number_input(
                "Quantity",
                min_value=0,
                value=int(
                    row["quantity_brought"]
                ),
                key=f"stock_qty_{stock_id}"
            )

            new_cost = st.number_input(
                "Unit Cost",
                min_value=0.0,
                value=float(
                    row["unit_cost"] or 0
                ),
                key=f"stock_cost_{stock_id}"
            )

            if st.button(
                "💾 Save Stock Changes"
            ):

                ok,_ = safe_execute("""
                    UPDATE stock
                    SET
                        quantity_brought=%s,
                        unit_cost=%s
                    WHERE stock_id=%s;
                """, (
                    new_quantity,
                    new_cost,
                    stock_id
                ))

                if ok:

                    safe_execute("""
                        UPDATE
                            financial_transactions
                        SET amount=%s
                        WHERE stock_id=%s;
                    """, (
                        new_quantity * new_cost,
                        stock_id
                    ))

                    log_action(
                        "UPDATE",
                        "stock",
                        stock_id,
                        f"Qty={new_quantity}"
                    )

                    st.success(
                        "Stock updated."
                    )

                    st.rerun()

            confirm = st.checkbox(
                "Confirm stock deletion",
                key=f"delete_stock_confirm_{stock_id}"
            )

            if st.button(
                "🗑️ Delete Stock",
                disabled=not confirm
            ):

                ok,_ = safe_execute("""
                    DELETE FROM stock
                    WHERE stock_id=%s;
                """, (
                    stock_id,
                ))

                if ok:

                    log_action(
                        "DELETE",
                        "stock",
                        stock_id,
                        f"Deleted stock #{stock_id}"
                    )

                    st.success(
                        "Stock deleted."
                    )

                    st.rerun()


    # =====================================================
    # PRODUCTION
    # =====================================================

    with tabs[2]:

        st.markdown(
            "### 🧵 Manage Production"
        )

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
                ON tp.school_id=sc.school_id
            JOIN products p
                ON tp.product_id=p.product_id
            ORDER BY tp.production_date DESC;
        """)

        if production.empty:

            st.info(
                "No production records."
            )

        else:

            st.dataframe(
                production,
                use_container_width=True,
                hide_index=True
            )

            production_id = st.selectbox(
                "Select Production Record",
                production[
                    "production_id"
                ].tolist()
            )

            row = production[
                production["production_id"]
                == production_id
            ].iloc[0]

            quantity = st.number_input(
                "Quantity Produced",
                min_value=0,
                value=int(
                    row["quantity_produced"]
                ),
                key=f"prod_qty_{production_id}"
            )

            cost = st.number_input(
                "Cost Per Item",
                min_value=0.0,
                value=float(
                    row["cost_per_item"]
                ),
                key=f"prod_cost_{production_id}"
            )

            if st.button(
                "💾 Save Production Changes"
            ):

                amount = quantity * cost

                ok,_ = safe_execute("""
                    UPDATE tailor_production
                    SET
                        quantity_produced=%s,
                        cost_per_item=%s,
                        amount_paid=%s
                    WHERE production_id=%s;
                """, (
                    quantity,
                    cost,
                    amount,
                    production_id
                ))

                if ok:

                    safe_execute("""
                        UPDATE
                            financial_transactions
                        SET amount=%s
                        WHERE production_id=%s;
                    """, (
                        amount,
                        production_id
                    ))

                    st.success(
                        "Production updated."
                    )

                    st.rerun()

            confirm = st.checkbox(
                "Confirm production deletion",
                key=f"delete_prod_{production_id}"
            )

            if st.button(
                "🗑️ Delete Production",
                disabled=not confirm
            ):

                ok,_ = safe_execute("""
                    DELETE FROM tailor_production
                    WHERE production_id=%s;
                """, (
                    production_id,
                ))

                if ok:

                    st.success(
                        "Production deleted."
                    )

                    st.rerun()


    # =====================================================
    # FINANCE
    # =====================================================

    with tabs[3]:

        st.markdown(
            "### 💼 Manage Finance"
        )

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
                finance[
                    "transaction_id"
                ].tolist()
            )

            row = finance[
                finance["transaction_id"]
                == transaction_id
            ].iloc[0]

            linked = (
                pd.notna(row["sale_id"])
                or
                pd.notna(row["stock_id"])
                or
                pd.notna(row["production_id"])
            )

            if linked:

                st.info(
                    "This transaction is linked to "
                    "a business record. Edit the "
                    "source record instead."
                )

            else:

                amount = st.number_input(
                    "Amount",
                    min_value=0.0,
                    value=float(
                        row["amount"] or 0
                    ),
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

                    ok,_ = safe_execute("""
                        UPDATE financial_transactions
                        SET
                            amount=%s,
                            description=%s
                        WHERE transaction_id=%s;
                    """, (
                        amount,
                        description,
                        transaction_id
                    ))

                    if ok:

                        st.success(
                            "Transaction updated."
                        )

                        st.rerun()

                confirm = st.checkbox(
                    "Confirm transaction deletion",
                    key=f"delete_finance_{transaction_id}"
                )

                if st.button(
                    "🗑️ Delete Transaction",
                    disabled=not confirm
                ):

                    ok,_ = safe_execute("""
                        DELETE FROM
                            financial_transactions
                        WHERE transaction_id=%s;
                    """, (
                        transaction_id,
                    ))

                    if ok:

                        st.success(
                            "Transaction deleted."
                        )

                        st.rerun()


    # =====================================================
    # PRODUCTS
    # =====================================================

    with tabs[4]:

        st.markdown(
            "### 👕 Manage Products"
        )

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

        if not products.empty:

            product_id = st.selectbox(
                "Select Product",
                products[
                    "product_id"
                ].tolist()
            )

            row = products[
                products["product_id"]
                == product_id
            ].iloc[0]

            name = st.text_input(
                "Product Name",
                value=row["product_name"],
                key=f"product_name_{product_id}"
            )

            price = st.number_input(
                "Selling Price",
                min_value=0.0,
                value=float(
                    row["price"]
                ),
                key=f"product_price_{product_id}"
            )

            cost = st.number_input(
                "Cost Price",
                min_value=0.0,
                value=float(
                    row["cost_price"]
                ),
                key=f"product_cost_{product_id}"
            )

            if st.button(
                "💾 Save Product Changes"
            ):

                ok,_ = safe_execute("""
                    UPDATE products
                    SET
                        product_name=%s,
                        price=%s,
                        cost_price=%s
                    WHERE product_id=%s;
                """, (
                    name.strip(),
                    price,
                    cost,
                    product_id
                ))

                if ok:

                    st.success(
                        "Product updated."
                    )

                    st.rerun()

            confirm = st.checkbox(
                "I understand this product "
                "cannot be deleted if it is "
                "already used."
            )

            if st.button(
                "🗑️ Delete Product",
                disabled=not confirm
            ):

                ok,_ = safe_execute("""
                    DELETE FROM products
                    WHERE product_id=%s;
                """, (
                    product_id,
                ),
                    error_message=
                    "Product cannot be deleted because "
                    "it is referenced by business records."
                )

                if ok:

                    st.success(
                        "Product deleted."
                    )

                    st.rerun()


    # =====================================================
    # SCHOOLS
    # =====================================================

    with tabs[5]:

        st.markdown(
            "### 🏫 Manage Schools"
        )

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

        if not schools.empty:

            school_id = st.selectbox(
                "Select School",
                schools[
                    "school_id"
                ].tolist()
            )

            row = schools[
                schools["school_id"] ==
                school_id
            ].iloc[0]

            new_name = st.text_input(
                "School Name",
                value=row["school_name"]
            )

            if st.button(
                "💾 Save School Changes"
            ):

                ok,_ = safe_execute("""
                    UPDATE schools
                    SET school_name=%s
                    WHERE school_id=%s;
                """, (
                    new_name.strip(),
                    school_id
                ))

                if ok:

                    st.success(
                        "School updated."
                    )

                    st.rerun()

            st.markdown(
                "### ➕ Add School"
            )

            school_to_add = st.text_input(
                "New School Name"
            )

            if st.button(
                "Add School",
                type="primary"
            ):

                if not school_to_add.strip():

                    st.error(
                        "Enter a school name."
                    )

                else:

                    ok,_ = safe_execute("""
                        INSERT INTO schools
                        (school_name)
                        VALUES (%s);
                    """, (
                        school_to_add.strip(),
                    ))

                    if ok:

                        st.success(
                            "School added."
                        )

                        st.rerun()

            st.markdown(
                "### 🗑️ Delete School"
            )

            confirm = st.checkbox(
                "I understand that deleting a "
                "school cannot be undone."
            )

            if st.button(
                "Delete School",
                disabled=not confirm
            ):

                ok,_ = safe_execute("""
                    DELETE FROM schools
                    WHERE school_id=%s;
                """, (
                    school_id,
                ),
                    error_message=
                    "This school cannot be deleted "
                    "because it has existing records."
                )

                if ok:

                    st.success(
                        "School deleted."
                    )

                    st.rerun()


    # =====================================================
    # AUDIT LOG
    # =====================================================

    with tabs[6]:

        st.markdown(
            "### 📋 Audit Log"
        )

        logs = fetch_dataframe("""
            SELECT
                log_id,
                log_time,
                action,
                entity,
                entity_id,
                details
            FROM audit_log
            ORDER BY log_time DESC
            LIMIT 500;
        """)

        if logs.empty:

            st.info(
                "No audit entries yet."
            )

        else:

            st.dataframe(
                logs,
                use_container_width=True,
                hide_index=True
            )


    # =====================================================
    # DANGER ZONE
    # =====================================================

    with tabs[7]:

        st.markdown(
            "### ⚠️ Danger Zone"
        )

        st.warning(
            "These actions permanently delete "
            "transactional data."
        )

        st.markdown(
            "#### 🧹 Clear Transactional Data"
        )

        st.write(
            "Deletes sales, sale items, stock, "
            "production, finance and customers. "
            "Keeps schools, products, prices "
            "and investors."
        )

        confirm_clear = st.checkbox(
            "I understand this deletes transactional data",
            key="danger_confirm_clear"
        )

        if st.button(
            "Clear Transactional Data",
            disabled=not confirm_clear
        ):

            ok,_ = safe_execute("""
                TRUNCATE TABLE
                    sale_items,
                    sales,
                    stock,
                    tailor_production,
                    financial_transactions,
                    customers
                RESTART IDENTITY CASCADE;
            """)

            if ok:

                st.success(
                    "Transactional data cleared."
                )

                st.rerun()

        st.markdown("---")

        st.markdown(
            "#### 💣 Full Reset"
        )

        st.write(
            "Clears business transaction records "
            "and price assignments."
        )

        confirm_full = st.checkbox(
            "I understand this is a full reset",
            key="danger_confirm_full"
        )

        if st.button(
            "Full Reset",
            disabled=not confirm_full
        ):

            ok,_ = safe_execute("""
                TRUNCATE TABLE
                    sale_items,
                    sales,
                    stock,
                    tailor_production,
                    financial_transactions,
                    customers,
                    school_product_prices,
                    set_items,
                    uniform_sets
                RESTART IDENTITY CASCADE;
            """)

            if ok:

                st.success(
                    "Full reset complete."
                )

                st.rerun()
