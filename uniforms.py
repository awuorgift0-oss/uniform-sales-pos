import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Uniform Business Management System",
    page_icon="🧾",
    layout="wide"
)


# ============================================================
# STYLING
# ============================================================

st.markdown("""
<style>
    .stApp {
        background-color: #eef6fb;
    }

    [data-testid="stSidebar"] {
        background-color: #0b1f3a;
    }

    [data-testid="stSidebar"] * {
        color: white;
    }

    h1, h2, h3 {
        color: #0b1f3a;
    }

    .stButton > button {
        background-color: #f28c28;
        color: white;
        border: none;
        border-radius: 7px;
        font-weight: bold;
    }

    .stButton > button:hover {
        background-color: #d97618;
        color: white;
    }

    div[data-testid="stMetric"] {
        background-color: white;
        border-radius: 10px;
        padding: 10px;
    }

    .receipt-box {
        background: white;
        padding: 25px;
        border-radius: 10px;
        border: 1px solid #ddd;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# APPLICATION HEADER
# ============================================================

st.markdown("""
<div style="text-align:center; padding:18px 10px 8px 10px;">
    <h1>🏫 UNIFORM BUSINESS MANAGEMENT SYSTEM</h1>
    <p style="font-size:1.05rem; color:#526579;">
        Sales • Inventory • Production • Finance • Reports
    </p>
</div>
""", unsafe_allow_html=True)


# ============================================================
# DATABASE CONNECTION
# ============================================================

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
        return None


# ============================================================
# DATABASE SETUP
# ============================================================

def setup_database():

    conn = get_connection()

    if conn is None:
        return

    cur = conn.cursor()

    try:

        # SCHOOLS
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schools (
                school_id SERIAL PRIMARY KEY,
                school_name VARCHAR(100) NOT NULL UNIQUE
            );
        """)

        # PRODUCTS
        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                product_id SERIAL PRIMARY KEY,
                product_name VARCHAR(100) NOT NULL UNIQUE,
                price NUMERIC(10,2) NOT NULL DEFAULT 0,
                cost_price NUMERIC(10,2) NOT NULL DEFAULT 0
            );
        """)

        cur.execute("""
            ALTER TABLE products
            ADD COLUMN IF NOT EXISTS cost_price
            NUMERIC(10,2) NOT NULL DEFAULT 0;
        """)

        # CUSTOMERS
        cur.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                customer_id SERIAL PRIMARY KEY,
                customer_name VARCHAR(100) NOT NULL,
                phone VARCHAR(20)
            );
        """)

        # SALES
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sales (
                sale_id SERIAL PRIMARY KEY,
                sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                school_id INT NOT NULL
                    REFERENCES schools(school_id),
                customer_id INT
                    REFERENCES customers(customer_id),
                total_amount NUMERIC(10,2) NOT NULL,
                payment_method VARCHAR(30),
                payment_status VARCHAR(20) DEFAULT 'Paid',
                term VARCHAR(20),
                year INT
            );
        """)

        cur.execute("""
            ALTER TABLE sales
            ADD COLUMN IF NOT EXISTS term VARCHAR(20);
        """)

        cur.execute("""
            ALTER TABLE sales
            ADD COLUMN IF NOT EXISTS year INT;
        """)

        # SALE ITEMS
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sale_items (
                sale_item_id SERIAL PRIMARY KEY,
                sale_id INT NOT NULL
                    REFERENCES sales(sale_id),
                product_id INT NOT NULL
                    REFERENCES products(product_id),
                quantity INT NOT NULL,
                unit_price NUMERIC(10,2) NOT NULL,
                line_total NUMERIC(10,2) NOT NULL
            );
        """)

        cur.execute("""
            ALTER TABLE sale_items
            ADD COLUMN IF NOT EXISTS issued BOOLEAN DEFAULT TRUE;
        """)

        # SCHOOL-SPECIFIC PRODUCT PRICES
        cur.execute("""
            CREATE TABLE IF NOT EXISTS school_product_prices (
                school_product_price_id SERIAL PRIMARY KEY,
                school_id INT NOT NULL
                    REFERENCES schools(school_id),
                category_name VARCHAR(100) NOT NULL,
                product_id INT NOT NULL
                    REFERENCES products(product_id),
                price NUMERIC(10,2) NOT NULL DEFAULT 0,
                UNIQUE (
                    school_id,
                    category_name,
                    product_id
                )
            );
        """)

        # STOCK
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stock (
                stock_id SERIAL PRIMARY KEY,
                school_id INT NOT NULL
                    REFERENCES schools(school_id),
                product_id INT NOT NULL
                    REFERENCES products(product_id),
                quantity_brought INT NOT NULL,
                date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cur.execute("""
            ALTER TABLE stock
            ADD COLUMN IF NOT EXISTS term VARCHAR(20);
        """)

        cur.execute("""
            ALTER TABLE stock
            ADD COLUMN IF NOT EXISTS year INT;
        """)

        cur.execute("""
            ALTER TABLE stock
            ADD COLUMN IF NOT EXISTS unit_cost
            NUMERIC(10,2) DEFAULT 0;
        """)

        # UNIFORM SETS
        cur.execute("""
            CREATE TABLE IF NOT EXISTS uniform_sets (
                set_id SERIAL PRIMARY KEY,
                school_id INT NOT NULL
                    REFERENCES schools(school_id),
                set_name VARCHAR(100) NOT NULL
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS set_items (
                set_item_id SERIAL PRIMARY KEY,
                set_id INT NOT NULL
                    REFERENCES uniform_sets(set_id),
                product_id INT NOT NULL
                    REFERENCES products(product_id),
                quantity INT NOT NULL
            );
        """)

        # INVESTORS
        cur.execute("""
            CREATE TABLE IF NOT EXISTS investors (
                investor_id SERIAL PRIMARY KEY,
                investor_name VARCHAR(100) NOT NULL UNIQUE,
                active BOOLEAN DEFAULT TRUE
            );
        """)

        # FINANCIAL TRANSACTIONS
        cur.execute("""
            CREATE TABLE IF NOT EXISTS financial_transactions (
                transaction_id SERIAL PRIMARY KEY,
                transaction_date TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,
                transaction_type VARCHAR(50) NOT NULL,
                category VARCHAR(100) NOT NULL,
                description VARCHAR(255),
                amount NUMERIC(12,2) NOT NULL,
                investor_id INT
                    REFERENCES investors(investor_id),
                term VARCHAR(20),
                year INT
            );
        """)

        # TAILOR PRODUCTION
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tailor_production (
                production_id SERIAL PRIMARY KEY,
                school_id INT NOT NULL
                    REFERENCES schools(school_id),
                product_id INT NOT NULL
                    REFERENCES products(product_id),
                tailor_name VARCHAR(100) NOT NULL,
                quantity_produced INT NOT NULL,
                cost_per_item NUMERIC(10,2) NOT NULL,
                amount_paid NUMERIC(12,2) NOT NULL,
                production_date TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,
                term VARCHAR(20),
                year INT,
                notes VARCHAR(255)
            );
        """)

        # SEED SCHOOLS
        schools = [
            "LOVING BLOOMS SCHOOL",
            "WARIDI UTAWALA SCHOOL"
        ]

        for school in schools:
            cur.execute("""
                INSERT INTO schools (school_name)
                VALUES (%s)
                ON CONFLICT (school_name) DO NOTHING;
            """, (school,))

        # SEED PRODUCTS
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

        for product_name, price in products:
            cur.execute("""
                INSERT INTO products (
                    product_name,
                    price,
                    cost_price
                )
                VALUES (%s, %s, 0)
                ON CONFLICT (product_name) DO NOTHING;
            """, (product_name, price))

        # ACTIVATE ONLY THE TWO CURRENT INVESTORS
        for investor_name in ("Gift", "Ken"):
            cur.execute("""
                INSERT INTO investors (
                    investor_name,
                    active
                )
                VALUES (%s, TRUE)
                ON CONFLICT (investor_name)
                DO UPDATE SET active = TRUE;
            """, (investor_name,))

        cur.execute("""
            UPDATE investors
            SET active = FALSE
            WHERE investor_name NOT IN ('Gift', 'Ken');
        """)

        # ENSURE INITIAL CAPITAL EXISTS FOR GIFT
        cur.execute("""
            SELECT investor_id
            FROM investors
            WHERE investor_name = 'Gift';
        """)
        gift_result = cur.fetchone()

        if gift_result:
            gift_id = gift_result[0]

            cur.execute("""
                SELECT COALESCE(SUM(amount), 0)
                FROM financial_transactions
                WHERE transaction_type = 'Capital Contribution'
                  AND investor_id = %s;
            """, (gift_id,))

            gift_capital = float(cur.fetchone()[0] or 0)

            if gift_capital == 0:
                cur.execute("""
                    INSERT INTO financial_transactions (
                        transaction_type,
                        category,
                        description,
                        amount,
                        investor_id,
                        year
                    )
                    VALUES (
                        'Capital Contribution',
                        'Investment',
                        'Initial investment by Gift',
                        150000,
                        %s,
                        %s
                    );
                """, (gift_id, datetime.now().year))

        # ENSURE INITIAL CAPITAL EXISTS FOR KEN
        cur.execute("""
            SELECT investor_id
            FROM investors
            WHERE investor_name = 'Ken';
        """)
        ken_result = cur.fetchone()

        if ken_result:
            ken_id = ken_result[0]

            cur.execute("""
                SELECT COALESCE(SUM(amount), 0)
                FROM financial_transactions
                WHERE transaction_type = 'Capital Contribution'
                  AND investor_id = %s;
            """, (ken_id,))

            ken_capital = float(cur.fetchone()[0] or 0)

            if ken_capital == 0:
                cur.execute("""
                    INSERT INTO financial_transactions (
                        transaction_type,
                        category,
                        description,
                        amount,
                        investor_id,
                        year
                    )
                    VALUES (
                        'Capital Contribution',
                        'Investment',
                        'Initial investment by Ken',
                        100000,
                        %s,
                        %s
                    );
                """, (ken_id, datetime.now().year))

        conn.commit()

    except Exception as e:
        conn.rollback()
        st.error(f"Database setup error: {e}")

    finally:
        cur.close()
        conn.close()


setup_database()


# ============================================================
# SESSION STATE
# ============================================================

if "cart" not in st.session_state:
    st.session_state.cart = []

if "last_receipt" not in st.session_state:
    st.session_state.last_receipt = None


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def fetch_dataframe(query, params=None):

    conn = get_connection()

    if conn is None:
        return pd.DataFrame()

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


def execute_query(query, params=None, fetch=False):

    conn = get_connection()

    if conn is None:
        return None

    cur = conn.cursor()

    try:
        cur.execute(query, params or ())

        result = cur.fetchall() if fetch else None

        conn.commit()
        return result

    except Exception as e:
        conn.rollback()
        st.error(f"Database error: {e}")
        return None

    finally:
        cur.close()
        conn.close()


def money(value):

    if value is None:
        value = 0

    return f"KSh {float(value):,.2f}"


# ============================================================
# SIDEBAR NAVIGATION
# ============================================================

st.sidebar.title("🧾 Uniform Sales POS")

page = st.sidebar.radio(
    "Menu",
    [
        "New Sale",
        "Price Management",
        "Stock Management",
        "Tailor & Production",
        "Business Finance",
        "Sales Overview",
        "Sales History",
        "ML & Forecasting"
    ]
)
