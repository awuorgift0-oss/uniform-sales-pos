import streamlit as st
import psycopg2
import pandas as pd
from streamlit.components.v1 import html as components_html
from datetime import datetime, date
from decimal import Decimal


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Uniform Business Management System",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# CSS
# ============================================================

st.markdown("""
<style>

#MainMenu {
    visibility: hidden;
}

footer {
    visibility: hidden;
}

[data-testid="stToolbar"] {
    visibility: hidden;
}

.stApp {
    background-color: #f5f7fb;
}

section[data-testid="stSidebar"] {
    background-color: #0f172a;
}

section[data-testid="stSidebar"] * {
    color: white !important;
}

.app-header {
    background: linear-gradient(135deg, #0f172a, #1e3a8a);
    padding: 22px 28px;
    border-radius: 14px;
    color: white;
    margin-bottom: 22px;
}

.app-header h1 {
    margin: 0;
    font-size: 30px;
}

.app-header p {
    margin: 5px 0 0 0;
    opacity: 0.85;
}

.metric-card {
    background: white;
    padding: 20px;
    border-radius: 14px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    border: 1px solid #e5e7eb;
}

.metric-title {
    color: #64748b;
    font-size: 14px;
}

.metric-value {
    font-size: 28px;
    font-weight: 700;
    color: #0f172a;
    margin-top: 5px;
}

.receipt {
    width: 100%;
    max-width: 700px;
    margin: auto;
    background: white;
    padding: 30px;
    border: 1px solid #ddd;
    font-family: Arial, sans-serif;
}

.receipt-header {
    text-align: center;
    border-bottom: 2px solid #111827;
    padding-bottom: 15px;
    margin-bottom: 15px;
}

.receipt-header h2 {
    margin: 0;
}

.receipt-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 15px;
}

.receipt-table th,
.receipt-table td {
    border-bottom: 1px solid #ddd;
    padding: 8px;
    text-align: left;
}

.receipt-total {
    text-align: right;
    font-size: 20px;
    font-weight: bold;
    margin-top: 20px;
}

.print-button {
    display: block;
    margin: 25px auto 0 auto;
    padding: 10px 25px;
    background: #111827;
    color: white;
    border: none;
    border-radius: 7px;
    cursor: pointer;
}

@media print {

    body * {
        visibility: hidden;
    }

    .receipt,
    .receipt * {
        visibility: visible;
    }

    .receipt {
        position: absolute;
        left: 0;
        top: 0;
        width: 100%;
        border: none;
    }

    .print-button {
        display: none;
    }
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():

    db = st.secrets["postgres"]

    return psycopg2.connect(
        host=db["host"],
        port=db["port"],
        database=db["database"],
        user=db["user"],
        password=db["password"],
        sslmode=db.get("sslmode", "require")
    )


# ============================================================
# DATABASE HELPERS
# ============================================================

def execute_query(query, params=None, fetch=False):

    conn = get_connection()

    try:

        cur = conn.cursor()

        cur.execute(query, params)

        if fetch:
            result = cur.fetchall()
        else:
            result = None

        conn.commit()

        cur.close()
        conn.close()

        return result

    except Exception:

        conn.rollback()
        conn.close()

        raise


def fetch_dataframe(query, params=None):

    conn = get_connection()

    try:

        df = pd.read_sql_query(
            query,
            conn,
            params=params
        )

        conn.close()

        return df

    except Exception:

        conn.close()

        raise


def money(value):

    if value is None:
        return "KES 0.00"

    return f"KES {float(value):,.2f}"


# ============================================================
# DATABASE SETUP
# ============================================================

def setup_database():

    conn = get_connection()
    cur = conn.cursor()

    try:

        # ----------------------------------------------------
        # SCHOOLS
        # ----------------------------------------------------

        cur.execute("""
            CREATE TABLE IF NOT EXISTS schools (
                school_id SERIAL PRIMARY KEY,
                school_name VARCHAR(200) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # ----------------------------------------------------
        # PRODUCTS
        # ----------------------------------------------------

        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                product_id SERIAL PRIMARY KEY,
                product_name VARCHAR(200) UNIQUE NOT NULL,
                selling_price NUMERIC(12,2) DEFAULT 0,
                cost_price NUMERIC(12,2) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # ----------------------------------------------------
        # CUSTOMERS
        # ----------------------------------------------------

        cur.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                customer_id SERIAL PRIMARY KEY,
                customer_name VARCHAR(200) NOT NULL,
                phone VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # ----------------------------------------------------
        # SALES
        # ----------------------------------------------------

        cur.execute("""
            CREATE TABLE IF NOT EXISTS sales (
                sale_id SERIAL PRIMARY KEY,
                customer_id INT REFERENCES customers(customer_id),
                school_id INT REFERENCES schools(school_id),
                sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                term VARCHAR(50),
                year INT,
                class_name VARCHAR(100),
                total_amount NUMERIC(12,2) DEFAULT 0,
                payment_method VARCHAR(50),
                status VARCHAR(50) DEFAULT 'Completed'
            );
        """)

        cur.execute("""
            ALTER TABLE sales
            ADD COLUMN IF NOT EXISTS class_name VARCHAR(100);
        """)

        # ----------------------------------------------------
        # SALE ITEMS
        # ----------------------------------------------------

        cur.execute("""
            CREATE TABLE IF NOT EXISTS sale_items (
                sale_item_id SERIAL PRIMARY KEY,
                sale_id INT REFERENCES sales(sale_id),
                product_id INT REFERENCES products(product_id),
                quantity INT NOT NULL,
                unit_price NUMERIC(12,2) NOT NULL,
                total_price NUMERIC(12,2) NOT NULL
            );
        """)

        # ----------------------------------------------------
        # SCHOOL PRODUCT PRICES
        # ----------------------------------------------------

        cur.execute("""
            CREATE TABLE IF NOT EXISTS school_product_prices (
                school_product_price_id SERIAL PRIMARY KEY,
                school_id INT REFERENCES schools(school_id) ON DELETE CASCADE,
                product_id INT REFERENCES products(product_id) ON DELETE CASCADE,
                category VARCHAR(100),
                price NUMERIC(12,2) NOT NULL,
                UNIQUE(school_id, product_id, category)
            );
        """)

        # ----------------------------------------------------
        # STOCK
        # ----------------------------------------------------

        cur.execute("""
            CREATE TABLE IF NOT EXISTS stock (
                stock_id SERIAL PRIMARY KEY,
                product_id INT REFERENCES products(product_id),
                school_id INT REFERENCES schools(school_id),
                quantity INT NOT NULL,
                cost_per_unit NUMERIC(12,2) DEFAULT 0,
                stock_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # ----------------------------------------------------
        # UNIFORM SETS
        # ----------------------------------------------------

        cur.execute("""
            CREATE TABLE IF NOT EXISTS uniform_sets (
                set_id SERIAL PRIMARY KEY,
                set_name VARCHAR(200) NOT NULL,
                school_id INT REFERENCES schools(school_id),
                price NUMERIC(12,2) DEFAULT 0
            );
        """)

        # ----------------------------------------------------
        # SET ITEMS
        # ----------------------------------------------------

        cur.execute("""
            CREATE TABLE IF NOT EXISTS set_items (
                set_item_id SERIAL PRIMARY KEY,
                set_id INT REFERENCES uniform_sets(set_id)
                    ON DELETE CASCADE,
                product_id INT REFERENCES products(product_id),
                quantity INT NOT NULL
            );
        """)

        # ----------------------------------------------------
        # INVESTORS
        # ----------------------------------------------------

        cur.execute("""
            CREATE TABLE IF NOT EXISTS investors (
                investor_id SERIAL PRIMARY KEY,
                investor_name VARCHAR(200) UNIQUE NOT NULL,
                ownership_percentage NUMERIC(8,2) DEFAULT 0,
                active BOOLEAN DEFAULT TRUE
            );
        """)

        # ----------------------------------------------------
        # TAILOR PRODUCTION
        # IMPORTANT: CREATED BEFORE FINANCIAL TRANSACTIONS
        # ----------------------------------------------------

        cur.execute("""
            CREATE TABLE IF NOT EXISTS tailor_production (
                production_id SERIAL PRIMARY KEY,
                product_id INT REFERENCES products(product_id),
                school_id INT REFERENCES schools(school_id),
                quantity INT NOT NULL,
                cost_per_unit NUMERIC(12,2) DEFAULT 0,
                total_cost NUMERIC(12,2) DEFAULT 0,
                production_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tailor_name VARCHAR(200),
                status VARCHAR(50) DEFAULT 'Completed'
            );
        """)

        # ----------------------------------------------------
        # FINANCIAL TRANSACTIONS
        # ----------------------------------------------------

        cur.execute("""
            CREATE TABLE IF NOT EXISTS financial_transactions (
                transaction_id SERIAL PRIMARY KEY,
                transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                transaction_type VARCHAR(100) NOT NULL,
                description TEXT,
                amount NUMERIC(12,2) NOT NULL,
                investor_id INT REFERENCES investors(investor_id),
                sale_id INT REFERENCES sales(sale_id) ON DELETE CASCADE,
                stock_id INT REFERENCES stock(stock_id) ON DELETE CASCADE,
                production_id INT REFERENCES tailor_production(production_id)
                    ON DELETE CASCADE
            );
        """)

        # Existing databases may be missing these columns.

        cur.execute("""
            ALTER TABLE financial_transactions
            ADD COLUMN IF NOT EXISTS investor_id INT
            REFERENCES investors(investor_id);
        """)

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
            REFERENCES tailor_production(production_id)
            ON DELETE CASCADE;
        """)

        # ----------------------------------------------------
        # REAL SCHOOLS
        # ----------------------------------------------------

        cur.execute("""
            INSERT INTO schools (school_name)
            VALUES
                ('LOVING BLOOMS SCHOOL'),
                ('WARIDI UTAWALA SCHOOL')
            ON CONFLICT (school_name) DO NOTHING;
        """)

        # ----------------------------------------------------
        # REAL INVESTORS
        # ----------------------------------------------------

        cur.execute("""
            INSERT INTO investors
                (investor_name, ownership_percentage, active)
            VALUES
                ('Gift', 60, TRUE),
                ('Ken', 40, TRUE)
            ON CONFLICT (investor_name) DO NOTHING;
        """)

        # ----------------------------------------------------
        # REAL PRODUCTS
        # ----------------------------------------------------

        products = [
            ("Skirt", 650, 0),
            ("Blouse", 500, 0),
            ("Socks", 200, 0),
            ("Tracksuit Playgroup-PP2", 1600, 0),
            ("Tracksuit G1-G6", 1800, 0),
            ("Sweater", 1000, 0),
            ("Tie", 150, 0),
            ("Bow Tie", 150, 0),
            ("Short", 400, 0),
            ("Halfcoat", 600, 0),
            ("Fleece", 2500, 0),
            ("Trouser", 650, 0),
            ("T-Shirt", 500, 0),
            ("Wrap Skirt", 500, 0),
            ("Half Sweater", 800, 0)
        ]

        for product in products:

            cur.execute("""
                INSERT INTO products
                    (product_name, selling_price, cost_price)
                VALUES (%s, %s, %s)
                ON CONFLICT (product_name) DO NOTHING;
            """, product)

        conn.commit()

        cur.close()
        conn.close()

    except Exception:

        conn.rollback()
        cur.close()
        conn.close()

        raise


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

try:

    setup_database()

except Exception as e:

    st.error(f"Database initialization error: {e}")
    st.stop()


# ============================================================
# SESSION STATE
# ============================================================

if "cart" not in st.session_state:
    st.session_state.cart = []

if "last_receipt" not in st.session_state:
    st.session_state.last_receipt = None

if "page" not in st.session_state:
    st.session_state.page = "Dashboard"


# ============================================================
# HEADER
# ============================================================

st.markdown("""
<div class="app-header">
    <h1>🏫 Uniform Business Management System</h1>
    <p>Sales • Stock • Finance • Production • Business Intelligence</p>
</div>
""", unsafe_allow_html=True)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown("## 🏫 UNIFORM SYSTEM")

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

    for page in pages:

        if st.button(
            page,
            use_container_width=True,
            key=f"nav_{page}"
        ):

            st.session_state.page = page
            st.rerun()

    st.divider()

    st.caption("Uniform Business Management System")
    st.caption("Built with Python + Streamlit + PostgreSQL")


# ============================================================
# RECEIPT FUNCTIONS
# ============================================================

def get_receipt(sale_id):

    sale = fetch_dataframe("""
        SELECT
            s.sale_id,
            s.sale_date,
            s.term,
            s.year,
            s.class_name,
            s.total_amount,
            s.payment_method,
            s.status,
            s.customer_id,
            s.school_id,
            c.customer_name,
            c.phone,
            sc.school_name
        FROM sales s
        LEFT JOIN customers c
            ON s.customer_id = c.customer_id
        LEFT JOIN schools sc
            ON s.school_id = sc.school_id
        WHERE s.sale_id = %s;
    """, (sale_id,))

    if sale.empty:
        return None

    items = fetch_dataframe("""
        SELECT
            p.product_name,
            si.quantity,
            si.unit_price,
            si.total_price
        FROM sale_items si
        JOIN products p
            ON si.product_id = p.product_id
        WHERE si.sale_id = %s
        ORDER BY si.sale_item_id;
    """, (sale_id,))

    return {
        "sale": sale.iloc[0],
        "items": items
    }


def render_receipt(receipt):

    sale = receipt["sale"]
    items = receipt["items"]

    rows = ""

    for _, item in items.iterrows():

        rows += f"""
        <tr>
            <td>{item['product_name']}</td>
            <td>{int(item['quantity'])}</td>
            <td>{money(item['unit_price'])}</td>
            <td>{money(item['total_price'])}</td>
        </tr>
        """

    html = f"""
    <div class="receipt">

        <div class="receipt-header">

            <h2>{sale['school_name']}</h2>

            <p>
                <strong>UNIFORM SALES RECEIPT</strong>
            </p>

            <p>
                Receipt No: #{sale['sale_id']}
            </p>

        </div>

        <p>
            <strong>Date:</strong>
            {sale['sale_date']}
        </p>

        <p>
            <strong>Customer:</strong>
            {sale['customer_name'] or ''}
        </p>

        <p>
            <strong>Phone:</strong>
            {sale['phone'] or ''}
        </p>

        <p>
            <strong>Class:</strong>
            {sale['class_name'] or ''}
        </p>

        <p>
            <strong>Term:</strong>
            {sale['term'] or ''}
        </p>

        <p>
            <strong>Year:</strong>
            {sale['year'] or ''}
        </p>

        <table class="receipt-table">

            <thead>
                <tr>
                    <th>Item</th>
                    <th>Qty</th>
                    <th>Price</th>
                    <th>Total</th>
                </tr>
            </thead>

            <tbody>
                {rows}
            </tbody>

        </table>

        <div class="receipt-total">
            Total: {money(sale['total_amount'])}
        </div>

        <p>
            <strong>Payment:</strong>
            {sale['payment_method']}
        </p>

        <p>
            <strong>Status:</strong>
            {sale['status']}
        </p>

        <button
            class="print-button"
            onclick="window.print()"
        >
            🖨️ Print Receipt
        </button>

    </div>
    """

    components_html(
        html,
        height=700,
        scrolling=True
    )


# ============================================================
# DASHBOARD
# ============================================================

def dashboard():

    st.subheader("📊 Business Dashboard")

    today_sales = fetch_dataframe("""
        SELECT
            COALESCE(SUM(total_amount),0) AS total
        FROM sales
        WHERE DATE(sale_date) = CURRENT_DATE;
    """)

    month_sales = fetch_dataframe("""
        SELECT
            COALESCE(SUM(total_amount),0) AS total
        FROM sales
        WHERE DATE_TRUNC('month', sale_date)
              = DATE_TRUNC('month', CURRENT_DATE);
    """)

    today_transactions = fetch_dataframe("""
        SELECT COUNT(*) AS total
        FROM sales
        WHERE DATE(sale_date) = CURRENT_DATE;
    """)

    items_today = fetch_dataframe("""
        SELECT
            COALESCE(SUM(si.quantity),0) AS total
        FROM sale_items si
        JOIN sales s
            ON si.sale_id = s.sale_id
        WHERE DATE(s.sale_date) = CURRENT_DATE;
    """)

    col1, col2, col3, col4 = st.columns(4)

    metrics = [
        (
            col1,
            "Today's Sales",
            money(today_sales.iloc[0]["total"])
        ),
        (
            col2,
            "This Month",
            money(month_sales.iloc[0]["total"])
        ),
        (
            col3,
            "Today's Transactions",
            int(today_transactions.iloc[0]["total"])
        ),
        (
            col4,
            "Items Sold Today",
            int(items_today.iloc[0]["total"])
        )
    ]

    for col, title, value in metrics:

        with col:

            st.markdown(
                f"""
                <div class="metric-card">

                    <div class="metric-title">
                        {title}
                    </div>

                    <div class="metric-value">
                        {value}
                    </div>

                </div>
                """,
                unsafe_allow_html=True
            )

    st.write("")

    st.subheader("⚡ Quick Actions")

    q1, q2, q3, q4 = st.columns(4)

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
            "🧾 Sales History",
            use_container_width=True
        ):

            st.session_state.page = "Sales History"
            st.rerun()

    st.divider()

    # --------------------------------------------------------
    # SALES TREND
    # --------------------------------------------------------

    st.subheader("📈 Sales Trend")

    trend = fetch_dataframe("""
        SELECT
            DATE(sale_date) AS sale_day,
            SUM(total_amount) AS revenue
        FROM sales
        GROUP BY DATE(sale_date)
        ORDER BY sale_day;
    """)

    if not trend.empty:

        trend["sale_day"] = pd.to_datetime(
            trend["sale_day"]
        )

        trend = trend.set_index("sale_day")

        st.line_chart(
            trend["revenue"]
        )

    else:

        st.info("No sales data yet.")

    col1, col2 = st.columns(2)

    # --------------------------------------------------------
    # SALES BY SCHOOL
    # --------------------------------------------------------

    with col1:

        st.subheader("🏫 Sales by School")

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

            st.dataframe(
                school_sales,
                use_container_width=True,
                hide_index=True
            )

    # --------------------------------------------------------
    # TOP PRODUCTS
    # --------------------------------------------------------

    with col2:

        st.subheader("🔥 Top-Selling Products")

        top_products = fetch_dataframe("""
            SELECT
                p.product_name,
                SUM(si.quantity) AS quantity_sold,
                SUM(si.total_price) AS revenue
            FROM sale_items si
            JOIN products p
                ON si.product_id = p.product_id
            GROUP BY p.product_name
            ORDER BY quantity_sold DESC
            LIMIT 10;
        """)

        if not top_products.empty:

            st.dataframe(
                top_products,
                use_container_width=True,
                hide_index=True
            )

    # --------------------------------------------------------
    # RECENT SALES
    # --------------------------------------------------------

    st.subheader("🧾 Recent Sales")

    recent = fetch_dataframe("""
        SELECT
            s.sale_id,
            s.sale_date,
            sc.school_name,
            c.customer_name,
            s.total_amount,
            s.payment_method
        FROM sales s
        LEFT JOIN schools sc
            ON s.school_id = sc.school_id
        LEFT JOIN customers c
            ON s.customer_id = c.customer_id
        ORDER BY s.sale_id DESC
        LIMIT 10;
    """)

    if not recent.empty:

        st.dataframe(
            recent,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info("No sales recorded yet.")


# ============================================================
# NEW SALE
# ============================================================

def new_sale():

    st.subheader("🛒 New Sale")

    schools = fetch_dataframe("""
        SELECT school_id, school_name
        FROM schools
        ORDER BY school_name;
    """)

    if schools.empty:

        st.warning("Add a school first.")
        return

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

    col1, col2, col3 = st.columns(3)

    with col1:

        customer_name = st.text_input(
            "Customer / Student Name"
        )

    with col2:

        phone = st.text_input(
            "Phone Number"
        )

    with col3:

        class_name = st.text_input(
            "Class / Grade"
        )

    col1, col2, col3 = st.columns(3)

    with col1:

        term = st.selectbox(
            "Term",
            [
                "Term 1",
                "Term 2",
                "Term 3"
            ]
        )

    with col2:

        year = st.number_input(
            "Year",
            min_value=2020,
            max_value=2100,
            value=datetime.now().year
        )

    with col3:

        category = st.selectbox(
            "Category",
            [
                "Primary",
                "Junior Secondary",
                "All"
            ]
        )

    st.divider()

    # --------------------------------------------------------
    # AVAILABLE PRODUCTS
    # --------------------------------------------------------

    if category == "All":

        products = fetch_dataframe("""
            SELECT
                spp.school_product_price_id,
                p.product_id,
                p.product_name,
                spp.price,
                spp.category
            FROM school_product_prices spp
            JOIN products p
                ON spp.product_id = p.product_id
            WHERE spp.school_id = %s
            ORDER BY p.product_name;
        """, (school_id,))

    else:

        products = fetch_dataframe("""
            SELECT
                spp.school_product_price_id,
                p.product_id,
                p.product_name,
                spp.price,
                spp.category
            FROM school_product_prices spp
            JOIN products p
                ON spp.product_id = p.product_id
            WHERE spp.school_id = %s
              AND spp.category = %s
            ORDER BY p.product_name;
        """, (school_id, category))

    if products.empty:

        st.warning(
            "No products have been assigned to this school/category yet. "
            "Go to Price Management first."
        )

        return

    product_name = st.selectbox(
        "Product",
        products["product_name"].tolist()
    )

    selected_product = products[
        products["product_name"] == product_name
    ].iloc[0]

    unit_price = Decimal(
        str(selected_product["price"])
    )

    st.write(
        f"Unit price: **{money(unit_price)}**"
    )

    quantity = st.number_input(
        "Quantity",
        min_value=1,
        value=1,
        step=1
    )

    issued = st.checkbox(
        "Item issued immediately",
        value=True
    )

    if st.button(
        "➕ Add to Cart",
        use_container_width=True
    ):

        item = {
            "product_id": int(selected_product["product_id"]),
            "product_name": product_name,
            "quantity": int(quantity),
            "unit_price": float(unit_price),
            "total_price": float(unit_price * quantity),
            "issued": issued
        }

        st.session_state.cart.append(item)

        st.success(
            f"{quantity} × {product_name} added to cart."
        )

    # --------------------------------------------------------
    # CART
    # --------------------------------------------------------

    st.divider()

    st.subheader("🛍️ Current Cart")

    if st.session_state.cart:

        cart_df = pd.DataFrame(
            st.session_state.cart
        )

        display_df = cart_df[
            [
                "product_name",
                "quantity",
                "unit_price",
                "total_price"
            ]
        ].copy()

        display_df.columns = [
            "Product",
            "Quantity",
            "Unit Price",
            "Total"
        ]

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )

        cart_total = sum(
            item["total_price"]
            for item in st.session_state.cart
        )

        st.markdown(
            f"### Total: {money(cart_total)}"
        )

        payment_method = st.selectbox(
            "Payment Method",
            [
                "Cash",
                "M-Pesa",
                "Bank",
                "Card",
                "Other"
            ]
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

            if st.button(
                "✅ Complete Sale",
                use_container_width=True
            ):

                if not customer_name.strip():

                    st.error(
                        "Enter the customer/student name."
                    )

                else:

                    conn = get_connection()

                    try:

                        cur = conn.cursor()

                        # Customer

                        cur.execute("""
                            SELECT customer_id
                            FROM customers
                            WHERE customer_name = %s
                              AND COALESCE(phone,'') =
                                  COALESCE(%s,'')
                            LIMIT 1;
                        """, (
                            customer_name.strip(),
                            phone.strip()
                        ))

                        existing_customer = cur.fetchone()

                        if existing_customer:

                            customer_id = existing_customer[0]

                        else:

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

                        # Sale

                        cur.execute("""
                            INSERT INTO sales
                                (
                                    customer_id,
                                    school_id,
                                    term,
                                    year,
                                    class_name,
                                    total_amount,
                                    payment_method,
                                    status
                                )
                            VALUES
                                (
                                    %s,%s,%s,%s,%s,%s,%s,'Completed'
                                )
                            RETURNING sale_id;
                        """, (
                            customer_id,
                            school_id,
                            term,
                            year,
                            class_name,
                            cart_total,
                            payment_method
                        ))

                        sale_id = cur.fetchone()[0]

                        # Sale items

                        for item in st.session_state.cart:

                            cur.execute("""
                                INSERT INTO sale_items
                                    (
                                        sale_id,
                                        product_id,
                                        quantity,
                                        unit_price,
                                        total_price
                                    )
                                VALUES (%s,%s,%s,%s,%s);
                            """, (
                                sale_id,
                                item["product_id"],
                                item["quantity"],
                                item["unit_price"],
                                item["total_price"]
                            ))

                        # Finance

                        cur.execute("""
                            INSERT INTO financial_transactions
                                (
                                    transaction_type,
                                    description,
                                    amount,
                                    sale_id
                                )
                            VALUES
                                (
                                    'Sales Income',
                                    %s,
                                    %s,
                                    %s
                                );
                        """, (
                            f"Sale #{sale_id}",
                            cart_total,
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

                        st.rerun()

                    except Exception as e:

                        conn.rollback()
                        conn.close()

                        st.error(
                            f"Could not complete sale: {e}"
                        )

    else:

        st.info("Your cart is empty.")


# ============================================================
# SALES HISTORY
# ============================================================

def sales_history():

    st.subheader("🧾 Sales History")

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
            s.status
        FROM sales s
        LEFT JOIN schools sc
            ON s.school_id = sc.school_id
        LEFT JOIN customers c
            ON s.customer_id = c.customer_id
        ORDER BY s.sale_id DESC;
    """)

    if sales.empty:

        st.info("No sales recorded yet.")
        return

    st.dataframe(
        sales,
        use_container_width=True,
        hide_index=True
    )

    csv = sales.to_csv(index=False).encode("utf-8")

    st.download_button(
        "⬇️ Download Sales CSV",
        csv,
        "sales_history.csv",
        "text/csv"
    )

    st.divider()

    selected_sale = st.number_input(
        "Enter Sale ID to view receipt",
        min_value=1,
        step=1
    )

    if st.button("🧾 View Receipt"):

        receipt = get_receipt(
            int(selected_sale)
        )

        if receipt:

            render_receipt(receipt)

        else:

            st.error("Sale not found.")


# ============================================================
# STOCK MANAGEMENT
# ============================================================

def stock_management():

    st.subheader("📦 Stock Management")

    products = fetch_dataframe("""
        SELECT product_id, product_name
        FROM products
        ORDER BY product_name;
    """)

    schools = fetch_dataframe("""
        SELECT school_id, school_name
        FROM schools
        ORDER BY school_name;
    """)

    if products.empty or schools.empty:

        st.warning(
            "You need products and schools first."
        )

        return

    st.subheader("➕ Add Stock")

    col1, col2 = st.columns(2)

    with col1:

        product_name = st.selectbox(
            "Product",
            products["product_name"].tolist()
        )

    with col2:

        school_name = st.selectbox(
            "School",
            schools["school_name"].tolist()
        )

    quantity = st.number_input(
        "Quantity",
        min_value=1,
        value=1
    )

    cost_per_unit = st.number_input(
        "Cost per Unit",
        min_value=0.0,
        value=0.0,
        step=10.0
    )

    if st.button(
        "📦 Save Stock",
        use_container_width=True
    ):

        product_id = int(
            products.loc[
                products["product_name"] == product_name,
                "product_id"
            ].iloc[0]
        )

        school_id = int(
            schools.loc[
                schools["school_name"] == school_name,
                "school_id"
            ].iloc[0]
        )

        total_cost = quantity * cost_per_unit

        conn = get_connection()

        try:

            cur = conn.cursor()

            cur.execute("""
                INSERT INTO stock
                    (
                        product_id,
                        school_id,
                        quantity,
                        cost_per_unit
                    )
                VALUES (%s,%s,%s,%s)
                RETURNING stock_id;
            """, (
                product_id,
                school_id,
                quantity,
                cost_per_unit
            ))

            stock_id = cur.fetchone()[0]

            cur.execute("""
                INSERT INTO financial_transactions
                    (
                        transaction_type,
                        description,
                        amount,
                        stock_id
                    )
                VALUES
                    (
                        'Stock Purchase',
                        %s,
                        %s,
                        %s
                    );
            """, (
                f"Stock: {product_name}",
                total_cost,
                stock_id
            ))

            conn.commit()

            cur.close()
            conn.close()

            st.success(
                "Stock added successfully."
            )

            st.rerun()

        except Exception as e:

            conn.rollback()
            conn.close()

            st.error(
                f"Could not save stock: {e}"
            )

    st.divider()

    st.subheader("📊 Current Stock")

    stock = fetch_dataframe("""
        SELECT
            st.stock_id,
            p.product_name,
            sc.school_name,
            st.quantity,
            st.cost_per_unit,
            st.stock_date
        FROM stock st
        LEFT JOIN products p
            ON st.product_id = p.product_id
        LEFT JOIN schools sc
            ON st.school_id = sc.school_id
        ORDER BY st.stock_id DESC;
    """)

    if stock.empty:

        st.info("No stock records yet.")

    else:

        st.dataframe(
            stock,
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# PRICE MANAGEMENT
# ============================================================

def price_management():

    st.subheader("💰 Price Management")

    schools = fetch_dataframe("""
        SELECT school_id, school_name
        FROM schools
        ORDER BY school_name;
    """)

    products = fetch_dataframe("""
        SELECT product_id, product_name, selling_price
        FROM products
        ORDER BY product_name;
    """)

    if schools.empty:

        st.warning("Add a school first.")
        return

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
        [
            "Primary",
            "Junior Secondary"
        ]
    )

    st.subheader("Assigned Prices")

    assigned = fetch_dataframe("""
        SELECT
            spp.school_product_price_id,
            p.product_name,
            spp.price
        FROM school_product_prices spp
        JOIN products p
            ON spp.product_id = p.product_id
        WHERE spp.school_id = %s
          AND spp.category = %s
        ORDER BY p.product_name;
    """, (
        school_id,
        category
    ))

    if not assigned.empty:

        st.dataframe(
            assigned,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "No products assigned to this category yet."
        )

    st.divider()

    st.subheader("➕ Assign Product")

    product_name = st.selectbox(
        "Product",
        products["product_name"].tolist()
    )

    price = st.number_input(
        "Price",
        min_value=0.0,
        step=50.0
    )

    if st.button(
        "Assign / Update Price",
        use_container_width=True
    ):

        product_id = int(
            products.loc[
                products["product_name"] == product_name,
                "product_id"
            ].iloc[0]
        )

        execute_query("""
            INSERT INTO school_product_prices
                (
                    school_id,
                    product_id,
                    category,
                    price
                )
            VALUES (%s,%s,%s,%s)
            ON CONFLICT
                (school_id, product_id, category)
            DO UPDATE SET
                price = EXCLUDED.price;
        """, (
            school_id,
            product_id,
            category,
            price
        ))

        st.success(
            f"{product_name} price updated."
        )

        st.rerun()

    st.divider()

    st.subheader("➕ Create New Product")

    new_product = st.text_input(
        "Product Name"
    )

    default_price = st.number_input(
        "Default Selling Price",
        min_value=0.0,
        step=50.0
    )

    if st.button(
        "Create Product",
        use_container_width=True
    ):

        if not new_product.strip():

            st.error("Enter a product name.")

        else:

            try:

                execute_query("""
                    INSERT INTO products
                        (
                            product_name,
                            selling_price
                        )
                    VALUES (%s,%s);
                """, (
                    new_product.strip(),
                    default_price
                ))

                st.success(
                    "Product created successfully."
                )

                st.rerun()

            except Exception as e:

                st.error(
                    f"Could not create product: {e}"
                )


# ============================================================
# TAILOR & PRODUCTION
# ============================================================

def tailor_production():

    st.subheader("🧵 Tailor & Production")

    products = fetch_dataframe("""
        SELECT product_id, product_name
        FROM products
        ORDER BY product_name;
    """)

    schools = fetch_dataframe("""
        SELECT school_id, school_name
        FROM schools
        ORDER BY school_name;
    """)

    product_name = st.selectbox(
        "Product",
        products["product_name"].tolist()
    )

    school_name = st.selectbox(
        "School",
        schools["school_name"].tolist()
    )

    quantity = st.number_input(
        "Quantity Produced",
        min_value=1,
        value=1
    )

    cost_per_unit = st.number_input(
        "Cost per Unit",
        min_value=0.0,
        step=50.0
    )

    tailor_name = st.text_input(
        "Tailor Name"
    )

    if st.button(
        "🧵 Save Production",
        use_container_width=True
    ):

        product_id = int(
            products.loc[
                products["product_name"] == product_name,
                "product_id"
            ].iloc[0]
        )

        school_id = int(
            schools.loc[
                schools["school_name"] == school_name,
                "school_id"
            ].iloc[0]
        )

        total_cost = quantity * cost_per_unit

        conn = get_connection()

        try:

            cur = conn.cursor()

            cur.execute("""
                INSERT INTO tailor_production
                    (
                        product_id,
                        school_id,
                        quantity,
                        cost_per_unit,
                        total_cost,
                        tailor_name
                    )
                VALUES (%s,%s,%s,%s,%s,%s)
                RETURNING production_id;
            """, (
                product_id,
                school_id,
                quantity,
                cost_per_unit,
                total_cost,
                tailor_name
            ))

            production_id = cur.fetchone()[0]

            cur.execute("""
                INSERT INTO financial_transactions
                    (
                        transaction_type,
                        description,
                        amount,
                        production_id
                    )
                VALUES
                    (
                        'Production Cost',
                        %s,
                        %s,
                        %s
                    );
            """, (
                f"Production: {product_name}",
                total_cost,
                production_id
            ))

            conn.commit()

            cur.close()
            conn.close()

            st.success(
                "Production record saved."
            )

            st.rerun()

        except Exception as e:

            conn.rollback()
            conn.close()

            st.error(
                f"Could not save production: {e}"
            )

    st.divider()

    production = fetch_dataframe("""
        SELECT
            tp.production_id,
            tp.production_date,
            p.product_name,
            sc.school_name,
            tp.quantity,
            tp.cost_per_unit,
            tp.total_cost,
            tp.tailor_name,
            tp.status
        FROM tailor_production tp
        LEFT JOIN products p
            ON tp.product_id = p.product_id
        LEFT JOIN schools sc
            ON tp.school_id = sc.school_id
        ORDER BY tp.production_id DESC;
    """)

    st.dataframe(
        production,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# BUSINESS FINANCE
# ============================================================

def business_finance():

    st.subheader("💰 Business Finance")

    investors = fetch_dataframe("""
        SELECT
            investor_id,
            investor_name,
            ownership_percentage,
            active
        FROM investors
        ORDER BY investor_name;
    """)

    st.subheader("👥 Investors")

    st.dataframe(
        investors,
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    st.subheader("➕ Add Investment")

    investor_name = st.selectbox(
        "Investor",
        investors["investor_name"].tolist()
    )

    investment_amount = st.number_input(
        "Investment Amount",
        min_value=0.0,
        step=1000.0
    )

    if st.button(
        "Record Investment",
        use_container_width=True
    ):

        investor_id = int(
            investors.loc[
                investors["investor_name"] == investor_name,
                "investor_id"
            ].iloc[0]
        )

        execute_query("""
            INSERT INTO financial_transactions
                (
                    transaction_type,
                    description,
                    amount,
                    investor_id
                )
            VALUES
                (
                    'Investment',
                    %s,
                    %s,
                    %s
                );
        """, (
            f"Investment by {investor_name}",
            investment_amount,
            investor_id
        ))

        st.success(
            "Investment recorded."
        )

        st.rerun()

    st.divider()

    st.subheader("➕ Other Transaction")

    transaction_type = st.selectbox(
        "Transaction Type",
        [
            "Expense",
            "Other Income",
            "Owner Withdrawal",
            "Profit Distribution"
        ]
    )

    description = st.text_input(
        "Description"
    )

    amount = st.number_input(
        "Amount",
        min_value=0.0,
        step=100.0
    )

    if st.button(
        "Save Transaction",
        use_container_width=True
    ):

        execute_query("""
            INSERT INTO financial_transactions
                (
                    transaction_type,
                    description,
                    amount
                )
            VALUES (%s,%s,%s);
        """, (
            transaction_type,
            description,
            amount
        ))

        st.success(
            "Transaction saved."
        )

        st.rerun()

    st.divider()

    # --------------------------------------------------------
    # FINANCIAL SUMMARY
    # --------------------------------------------------------

    st.subheader("📊 Financial Summary")

    income = fetch_dataframe("""
        SELECT
            COALESCE(SUM(amount),0) AS total
        FROM financial_transactions
        WHERE transaction_type IN
            ('Sales Income','Other Income','Investment');
    """)

    expenses = fetch_dataframe("""
        SELECT
            COALESCE(SUM(amount),0) AS total
        FROM financial_transactions
        WHERE transaction_type IN
            (
                'Expense',
                'Stock Purchase',
                'Production Cost',
                'Owner Withdrawal',
                'Profit Distribution'
            );
    """)

    total_income = float(
        income.iloc[0]["total"]
    )

    total_expenses = float(
        expenses.iloc[0]["total"]
    )

    balance = total_income - total_expenses

    c1, c2, c3 = st.columns(3)

    with c1:

        st.metric(
            "Total Income",
            money(total_income)
        )

    with c2:

        st.metric(
            "Total Expenses",
            money(total_expenses)
        )

    with c3:

        st.metric(
            "Balance",
            money(balance)
        )

    st.divider()

    st.subheader("📒 Financial Ledger")

    ledger = fetch_dataframe("""
        SELECT
            ft.transaction_id,
            ft.transaction_date,
            ft.transaction_type,
            ft.description,
            ft.amount,
            i.investor_name
        FROM financial_transactions ft
        LEFT JOIN investors i
            ON ft.investor_id = i.investor_id
        ORDER BY ft.transaction_id DESC;
    """)

    st.dataframe(
        ledger,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# ML & FORECASTING
# ============================================================

def ml_forecasting():

    st.subheader("🤖 ML & Forecasting")

    sales = fetch_dataframe("""
        SELECT
            DATE(sale_date) AS sale_day,
            SUM(total_amount) AS revenue
        FROM sales
        GROUP BY DATE(sale_date)
        ORDER BY sale_day;
    """)

    if sales.empty:

        st.info(
            "ML forecasting will become available once "
            "the system has real sales history."
        )

        return

    sales["sale_day"] = pd.to_datetime(
        sales["sale_day"]
    )

    st.subheader("Historical Revenue")

    st.line_chart(
        sales.set_index("sale_day")["revenue"]
    )

    st.divider()

    recent = sales.tail(7)

    average_revenue = recent["revenue"].mean()

    st.metric(
        "Recent Average Daily Revenue",
        money(average_revenue)
    )

    st.divider()

    st.subheader("📦 Product Demand")

    demand = fetch_dataframe("""
        SELECT
            p.product_name,
            SUM(si.quantity) AS quantity_sold,
            SUM(si.total_price) AS revenue
        FROM sale_items si
        JOIN products p
            ON si.product_id = p.product_id
        GROUP BY p.product_name
        ORDER BY quantity_sold DESC;
    """)

    if not demand.empty:

        st.dataframe(
            demand,
            use_container_width=True,
            hide_index=True
        )

    st.divider()

    st.info(
        "Future ML modules can include demand forecasting, "
        "stock prediction, customer purchasing patterns, "
        "sales forecasting and anomaly detection."
    )


# ============================================================
# SYSTEM MANAGEMENT
# ============================================================

def system_management():

    st.subheader("⚙️ System Management")

    tabs = st.tabs([
        "Sales",
        "Stock",
        "Production",
        "Finance",
        "Products",
        "Schools"
    ])

    # ========================================================
    # SALES
    # ========================================================

    with tabs[0]:

        st.subheader("🧾 Manage Sales")

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
                s.status
            FROM sales s
            LEFT JOIN schools sc
                ON s.school_id = sc.school_id
            LEFT JOIN customers c
                ON s.customer_id = c.customer_id
            ORDER BY s.sale_id DESC;
        """)

        if sales.empty:

            st.info("No sales yet.")

        else:

            st.dataframe(
                sales,
                use_container_width=True,
                hide_index=True
            )

            selected_sale = st.number_input(
                "Sale ID",
                min_value=1,
                step=1,
                key="manage_sale_id"
            )

            sale_data = sales[
                sales["sale_id"] == selected_sale
            ]

            if not sale_data.empty:

                current = sale_data.iloc[0]

                st.write(
                    f"**Current customer:** "
                    f"{current['customer_name']}"
                )

                new_customer = st.text_input(
                    "Customer Name",
                    value=str(
                        current["customer_name"] or ""
                    ),
                    key="edit_customer"
                )

                new_phone = st.text_input(
                    "Phone",
                    value=str(
                        current["phone"] or ""
                    ),
                    key="edit_phone"
                )

                new_class = st.text_input(
                    "Class",
                    value=str(
                        current["class_name"] or ""
                    ),
                    key="edit_class"
                )

                c1, c2, c3 = st.columns(3)

                with c1:

                    if st.button(
                        "💾 Update Sale",
                        use_container_width=True
                    ):

                        conn = get_connection()

                        try:

                            cur = conn.cursor()

                            customer_id = None

                            cur.execute("""
                                SELECT customer_id
                                FROM sales
                                WHERE sale_id = %s;
                            """, (
                                selected_sale,
                            ))

                            sale_customer = cur.fetchone()

                            if sale_customer:

                                customer_id = sale_customer[0]

                            if customer_id:

                                cur.execute("""
                                    UPDATE customers
                                    SET
                                        customer_name = %s,
                                        phone = %s
                                    WHERE customer_id = %s;
                                """, (
                                    new_customer,
                                    new_phone,
                                    customer_id
                                ))

                            cur.execute("""
                                UPDATE sales
                                SET class_name = %s
                                WHERE sale_id = %s;
                            """, (
                                new_class,
                                selected_sale
                            ))

                            conn.commit()

                            cur.close()
                            conn.close()

                            st.success(
                                "Sale updated successfully."
                            )

                            st.rerun()

                        except Exception as e:

                            conn.rollback()
                            conn.close()

                            st.error(
                                f"Could not update sale: {e}"
                            )

                with c2:

                    if st.button(
                        "🧾 Print Receipt",
                        use_container_width=True
                    ):

                        receipt = get_receipt(
                            int(selected_sale)
                        )

                        if receipt:

                            render_receipt(receipt)

                        else:

                            st.error(
                                "Sale not found."
                            )

                with c3:

                    confirm_delete = st.checkbox(
                        "Confirm deletion",
                        key="confirm_sale_delete"
                    )

                    if st.button(
                        "🗑️ Delete Sale",
                        disabled=not confirm_delete,
                        use_container_width=True
                    ):

                        conn = get_connection()

                        try:

                            cur = conn.cursor()

                            # IMPORTANT:
                            # Delete child sale_items FIRST.
                            # This fixes:
                            #
                            # sale_items_sale_id_fkey
                            #
                            # foreign key deletion error.

                            cur.execute("""
                                DELETE FROM sale_items
                                WHERE sale_id = %s;
                            """, (
                                selected_sale,
                            ))

                            # financial_transactions.sale_id
                            # is configured with ON DELETE CASCADE.

                            cur.execute("""
                                DELETE FROM sales
                                WHERE sale_id = %s;
                            """, (
                                selected_sale,
                            ))

                            conn.commit()

                            cur.close()
                            conn.close()

                            st.success(
                                f"Sale #{selected_sale} deleted successfully."
                            )

                            st.rerun()

                        except Exception as e:

                            conn.rollback()
                            conn.close()

                            st.error(
                                f"Could not delete sale: {e}"
                            )

    # ========================================================
    # STOCK
    # ========================================================

    with tabs[1]:

        st.subheader("📦 Manage Stock")

        stock = fetch_dataframe("""
            SELECT
                st.stock_id,
                p.product_name,
                sc.school_name,
                st.quantity,
                st.cost_per_unit,
                st.stock_date
            FROM stock st
            LEFT JOIN products p
                ON st.product_id = p.product_id
            LEFT JOIN schools sc
                ON st.school_id = sc.school_id
            ORDER BY st.stock_id DESC;
        """)

        if not stock.empty:

            st.dataframe(
                stock,
                use_container_width=True,
                hide_index=True
            )

            stock_id = st.number_input(
                "Stock ID",
                min_value=1,
                step=1,
                key="manage_stock_id"
            )

            selected = stock[
                stock["stock_id"] == stock_id
            ]

            if not selected.empty:

                row = selected.iloc[0]

                quantity = st.number_input(
                    "Quantity",
                    min_value=0,
                    value=int(row["quantity"]),
                    key="edit_stock_quantity"
                )

                cost = st.number_input(
                    "Cost per Unit",
                    min_value=0.0,
                    value=float(
                        row["cost_per_unit"]
                    ),
                    key="edit_stock_cost"
                )

                c1, c2 = st.columns(2)

                with c1:

                    if st.button(
                        "💾 Update Stock",
                        use_container_width=True
                    ):

                        execute_query("""
                            UPDATE stock
                            SET
                                quantity = %s,
                                cost_per_unit = %s
                            WHERE stock_id = %s;
                        """, (
                            quantity,
                            cost,
                            stock_id
                        ))

                        execute_query("""
                            UPDATE financial_transactions
                            SET amount = %s
                            WHERE stock_id = %s;
                        """, (
                            quantity * cost,
                            stock_id
                        ))

                        st.success(
                            "Stock updated."
                        )

                        st.rerun()

                with c2:

                    confirm = st.checkbox(
                        "Confirm deletion",
                        key="delete_stock_confirm"
                    )

                    if st.button(
                        "🗑️ Delete Stock",
                        disabled=not confirm,
                        use_container_width=True
                    ):

                        try:

                            execute_query("""
                                DELETE FROM stock
                                WHERE stock_id = %s;
                            """, (
                                stock_id,
                            ))

                            st.success(
                                "Stock deleted."
                            )

                            st.rerun()

                        except Exception as e:

                            st.error(
                                f"Could not delete stock: {e}"
                            )

    # ========================================================
    # PRODUCTION
    # ========================================================

    with tabs[2]:

        st.subheader("🧵 Manage Production")

        production = fetch_dataframe("""
            SELECT
                tp.production_id,
                tp.production_date,
                p.product_name,
                sc.school_name,
                tp.quantity,
                tp.cost_per_unit,
                tp.total_cost,
                tp.tailor_name,
                tp.status
            FROM tailor_production tp
            LEFT JOIN products p
                ON tp.product_id = p.product_id
            LEFT JOIN schools sc
                ON tp.school_id = sc.school_id
            ORDER BY tp.production_id DESC;
        """)

        if not production.empty:

            st.dataframe(
                production,
                use_container_width=True,
                hide_index=True
            )

            production_id = st.number_input(
                "Production ID",
                min_value=1,
                step=1,
                key="manage_production_id"
            )

            selected = production[
                production["production_id"] ==
                production_id
            ]

            if not selected.empty:

                row = selected.iloc[0]

                quantity = st.number_input(
                    "Quantity",
                    min_value=0,
                    value=int(row["quantity"]),
                    key="edit_production_quantity"
                )

                cost = st.number_input(
                    "Cost Per Unit",
                    min_value=0.0,
                    value=float(
                        row["cost_per_unit"]
                    ),
                    key="edit_production_cost"
                )

                tailor = st.text_input(
                    "Tailor Name",
                    value=str(
                        row["tailor_name"] or ""
                    ),
                    key="edit_tailor"
                )

                c1, c2 = st.columns(2)

                with c1:

                    if st.button(
                        "💾 Update Production",
                        use_container_width=True
                    ):

                        total_cost = quantity * cost

                        execute_query("""
                            UPDATE tailor_production
                            SET
                                quantity = %s,
                                cost_per_unit = %s,
                                total_cost = %s,
                                tailor_name = %s
                            WHERE production_id = %s;
                        """, (
                            quantity,
                            cost,
                            total_cost,
                            tailor,
                            production_id
                        ))

                        execute_query("""
                            UPDATE financial_transactions
                            SET amount = %s
                            WHERE production_id = %s;
                        """, (
                            total_cost,
                            production_id
                        ))

                        st.success(
                            "Production updated."
                        )

                        st.rerun()

                with c2:

                    confirm = st.checkbox(
                        "Confirm deletion",
                        key="delete_production_confirm"
                    )

                    if st.button(
                        "🗑️ Delete Production",
                        disabled=not confirm,
                        use_container_width=True
                    ):

                        try:

                            execute_query("""
                                DELETE FROM tailor_production
                                WHERE production_id = %s;
                            """, (
                                production_id,
                            ))

                            st.success(
                                "Production deleted."
                            )

                            st.rerun()

                        except Exception as e:

                            st.error(
                                f"Could not delete production: {e}"
                            )

    # ========================================================
    # FINANCE
    # ========================================================

    with tabs[3]:

        st.subheader("📒 Financial Records")

        ledger = fetch_dataframe("""
            SELECT
                ft.transaction_id,
                ft.transaction_date,
                ft.transaction_type,
                ft.description,
                ft.amount,
                ft.sale_id,
                ft.stock_id,
                ft.production_id,
                i.investor_name
            FROM financial_transactions ft
            LEFT JOIN investors i
                ON ft.investor_id = i.investor_id
            ORDER BY ft.transaction_id DESC;
        """)

        st.dataframe(
            ledger,
            use_container_width=True,
            hide_index=True
        )

        st.info(
            "Transactions automatically linked to Sales, Stock "
            "or Production should be edited from their source record."
        )

    # ========================================================
    # PRODUCTS
    # ========================================================

    with tabs[4]:

        st.subheader("👕 Manage Products")

        products = fetch_dataframe("""
            SELECT
                product_id,
                product_name,
                selling_price,
                cost_price
            FROM products
            ORDER BY product_name;
        """)

        st.dataframe(
            products,
            use_container_width=True,
            hide_index=True
        )

        product_id = st.number_input(
            "Product ID",
            min_value=1,
            step=1,
            key="manage_product_id"
        )

        selected = products[
            products["product_id"] == product_id
        ]

        if not selected.empty:

            row = selected.iloc[0]

            product_name = st.text_input(
                "Product Name",
                value=str(
                    row["product_name"]
                ),
                key="edit_product_name"
            )

            selling_price = st.number_input(
                "Selling Price",
                min_value=0.0,
                value=float(
                    row["selling_price"]
                ),
                key="edit_product_selling"
            )

            cost_price = st.number_input(
                "Cost Price",
                min_value=0.0,
                value=float(
                    row["cost_price"]
                ),
                key="edit_product_cost"
            )

            c1, c2 = st.columns(2)

            with c1:

                if st.button(
                    "💾 Update Product",
                    use_container_width=True
                ):

                    try:

                        execute_query("""
                            UPDATE products
                            SET
                                product_name = %s,
                                selling_price = %s,
                                cost_price = %s
                            WHERE product_id = %s;
                        """, (
                            product_name,
                            selling_price,
                            cost_price,
                            product_id
                        ))

                        st.success(
                            "Product updated."
                        )

                        st.rerun()

                    except Exception as e:

                        st.error(
                            f"Could not update product: {e}"
                        )

            with c2:

                confirm = st.checkbox(
                    "Confirm deletion",
                    key="delete_product_confirm"
                )

                if st.button(
                    "🗑️ Delete Product",
                    disabled=not confirm,
                    use_container_width=True
                ):

                    try:

                        execute_query("""
                            DELETE FROM products
                            WHERE product_id = %s;
                        """, (
                            product_id,
                        ))

                        st.success(
                            "Product deleted."
                        )

                        st.rerun()

                    except Exception as e:

                        st.error(
                            "Product cannot be deleted because "
                            "it is already being used by another record. "
                            f"Details: {e}"
                        )

    # ========================================================
    # SCHOOLS
    # ========================================================

    with tabs[5]:

        st.subheader("🏫 Manage Schools")

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

        school_id = st.number_input(
            "School ID",
            min_value=1,
            step=1,
            key="manage_school_id"
        )

        selected = schools[
            schools["school_id"] == school_id
        ]

        if not selected.empty:

            row = selected.iloc[0]

            school_name = st.text_input(
                "School Name",
                value=str(
                    row["school_name"]
                ),
                key="edit_school_name"
            )

            c1, c2 = st.columns(2)

            with c1:

                if st.button(
                    "💾 Update School",
                    use_container_width=True
                ):

                    try:

                        execute_query("""
                            UPDATE schools
                            SET school_name = %s
                            WHERE school_id = %s;
                        """, (
                            school_name,
                            school_id
                        ))

                        st.success(
                            "School updated."
                        )

                        st.rerun()

                    except Exception as e:

                        st.error(
                            f"Could not update school: {e}"
                        )

            with c2:

                confirm = st.checkbox(
                    "Confirm deletion",
                    key="delete_school_confirm"
                )

                if st.button(
                    "🗑️ Delete School",
                    disabled=not confirm,
                    use_container_width=True
                ):

                    try:

                        execute_query("""
                            DELETE FROM schools
                            WHERE school_id = %s;
                        """, (
                            school_id,
                        ))

                        st.success(
                            "School deleted."
                        )

                        st.rerun()

                    except Exception as e:

                        st.error(
                            "This school cannot be deleted because "
                            "it is already linked to business records. "
                            f"Details: {e}"
                        )

        st.divider()

        st.subheader("➕ Add School")

        new_school = st.text_input(
            "New School Name",
            key="new_school_name"
        )

        if st.button(
            "Add School",
            use_container_width=True
        ):

            if not new_school.strip():

                st.error(
                    "Enter the school name."
                )

            else:

                try:

                    execute_query("""
                        INSERT INTO schools
                            (school_name)
                        VALUES (%s);
                    """, (
                        new_school.strip(),
                    ))

                    st.success(
                        "School added successfully."
                    )

                    st.rerun()

                except Exception as e:

                    st.error(
                        f"Could not add school: {e}"
                    )


# ============================================================
# PAGE ROUTING
# ============================================================

page = st.session_state.page

if page == "Dashboard":

    dashboard()

elif page == "New Sale":

    new_sale()

elif page == "Sales History":

    sales_history()

elif page == "Stock Management":

    stock_management()

elif page == "Price Management":

    price_management()

elif page == "Tailor & Production":

    tailor_production()

elif page == "Business Finance":

    business_finance()

elif page == "ML & Forecasting":

    ml_forecasting()

elif page == "System Management":

    system_management()
