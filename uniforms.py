import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components

# ============================================================
# PAGE
# ============================================================

st.set_page_config(
    page_title="Uniform Sales POS",
    page_icon="🧾",
    layout="wide"
)

# ============================================================
# STYLE
# ============================================================

st.markdown("""
<style>
    .stApp {
        background-color: #eef6ff;
    }

    [data-testid="stSidebar"] {
        background-color: #102a43;
    }

    [data-testid="stSidebar"] * {
        color: white;
    }

    h1, h2, h3 {
        color: #102a43;
    }

    .metric-card {
        background: white;
        padding: 18px;
        border-radius: 12px;
        border: 1px solid #d9e6f2;
        margin-bottom: 10px;
    }

    .big-number {
        font-size: 28px;
        font-weight: bold;
        color: #102a43;
    }

    .small-label {
        color: #607d8b;
        font-size: 14px;
    }

    .profit {
        color: #16803c;
        font-weight: bold;
    }

    .loss {
        color: #c62828;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    cfg = st.secrets["postgres"]

    return psycopg2.connect(
        host=cfg["host"],
        port=cfg["port"],
        database=cfg["database"],
        user=cfg["user"],
        password=cfg["password"],
        sslmode=cfg.get("sslmode", "require")
    )


# ============================================================
# DATABASE SETUP
# ============================================================

def setup_database():

    conn = get_connection()
    cur = conn.cursor()

    # ---------------- SCHOOLS ----------------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS schools (
            school_id SERIAL PRIMARY KEY,
            school_name VARCHAR(100) NOT NULL UNIQUE
        );
    """)

    # ---------------- PRODUCTS ----------------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id SERIAL PRIMARY KEY,
            product_name VARCHAR(100) NOT NULL UNIQUE,
            price NUMERIC(10,2) NOT NULL DEFAULT 0,
            cost_price NUMERIC(10,2) NOT NULL DEFAULT 0
        );
    """)

    # Add cost price to an existing database
    cur.execute("""
        ALTER TABLE products
        ADD COLUMN IF NOT EXISTS cost_price NUMERIC(10,2) NOT NULL DEFAULT 0;
    """)

    # ---------------- CUSTOMERS ----------------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id SERIAL PRIMARY KEY,
            customer_name VARCHAR(100) NOT NULL,
            phone VARCHAR(20)
        );
    """)

    # ---------------- SALES ----------------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            sale_id SERIAL PRIMARY KEY,
            sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            school_id INT NOT NULL REFERENCES schools(school_id),
            customer_id INT,
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

    # ---------------- SALE ITEMS ----------------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sale_items (
            sale_item_id SERIAL PRIMARY KEY,
            sale_id INT NOT NULL REFERENCES sales(sale_id),
            product_id INT NOT NULL REFERENCES products(product_id),
            quantity INT NOT NULL,
            unit_price NUMERIC(10,2) NOT NULL,
            line_total NUMERIC(10,2) NOT NULL,
            issued BOOLEAN DEFAULT TRUE
        );
    """)

    cur.execute("""
        ALTER TABLE sale_items
        ADD COLUMN IF NOT EXISTS issued BOOLEAN DEFAULT TRUE;
    """)

    # ---------------- UNIFORM SETS ----------------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS uniform_sets (
            set_id SERIAL PRIMARY KEY,
            school_id INT NOT NULL REFERENCES schools(school_id),
            set_name VARCHAR(100) NOT NULL
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS set_items (
            set_item_id SERIAL PRIMARY KEY,
            set_id INT NOT NULL,
            product_id INT NOT NULL REFERENCES products(product_id),
            quantity INT NOT NULL
        );
    """)

    # ---------------- SCHOOL PRICES ----------------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS school_product_prices (
            school_product_price_id SERIAL PRIMARY KEY,
            school_id INT NOT NULL REFERENCES schools(school_id),
            category_name VARCHAR(100) NOT NULL,
            product_id INT NOT NULL REFERENCES products(product_id),
            price NUMERIC(10,2) NOT NULL DEFAULT 0,
            UNIQUE (school_id, category_name, product_id)
        );
    """)

    # ---------------- STOCK ----------------

    cur.execute("""
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
        ADD COLUMN IF NOT EXISTS unit_cost NUMERIC(10,2) DEFAULT 0;
    """)

    # ---------------- INVESTORS ----------------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS investors (
            investor_id SERIAL PRIMARY KEY,
            investor_name VARCHAR(100) NOT NULL UNIQUE,
            active BOOLEAN DEFAULT TRUE
        );
    """)

    # ---------------- FINANCIAL TRANSACTIONS ----------------

    cur.execute("""
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
    """)

    cur.execute("""
        ALTER TABLE financial_transactions
        ADD COLUMN IF NOT EXISTS term VARCHAR(20);
    """)

    cur.execute("""
        ALTER TABLE financial_transactions
        ADD COLUMN IF NOT EXISTS year INT;
    """)

    # ========================================================
    # INITIAL DATA
    # ========================================================

    cur.execute("""
        INSERT INTO schools (school_name)
        VALUES
        ('LOVING BLOOMS SCHOOL'),
        ('WARIDI UTAWALA SCHOOL')
        ON CONFLICT (school_name) DO NOTHING;
    """)

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

    for name, price, cost in products:
        cur.execute("""
            INSERT INTO products
            (product_name, price, cost_price)
            VALUES (%s, %s, %s)
            ON CONFLICT (product_name) DO NOTHING;
        """, (name, price, cost))

    # ========================================================
    # FRESH BUSINESS CYCLE
    # Only seed the two investors if the finance table is empty.
    # ========================================================

    cur.execute("SELECT COUNT(*) FROM investors;")
    investor_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM financial_transactions;")
    transaction_count = cur.fetchone()[0]

    if investor_count == 0 and transaction_count == 0:

        cur.execute("""
            INSERT INTO investors (investor_name)
            VALUES ('You'), ('Boyfriend')
            ON CONFLICT (investor_name) DO NOTHING;
        """)

        cur.execute("""
            SELECT investor_id
            FROM investors
            WHERE investor_name = 'You';
        """)
        you_id = cur.fetchone()[0]

        cur.execute("""
            SELECT investor_id
            FROM investors
            WHERE investor_name = 'Boyfriend';
        """)
        boyfriend_id = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO financial_transactions
            (
                transaction_type,
                category,
                description,
                amount,
                investor_id,
                term,
                year
            )
            VALUES
            (
                'Capital Contribution',
                'Investment',
                'Opening capital',
                150000,
                %s,
                'Current',
                EXTRACT(YEAR FROM CURRENT_DATE)
            ),
            (
                'Capital Contribution',
                'Investment',
                'Opening capital',
                100000,
                %s,
                'Current',
                EXTRACT(YEAR FROM CURRENT_DATE)
            );
        """, (you_id, boyfriend_id))

    conn.commit()
    cur.close()
    conn.close()


# Run database setup
setup_database()


# ============================================================
# HELPERS
# ============================================================

def fetch_all(query, params=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, params or ())
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    cur.close()
    conn.close()
    return pd.DataFrame(rows, columns=columns)


def execute_query(query, params=None, fetch=False):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(query, params or ())

    result = None

    if fetch:
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        result = pd.DataFrame(rows, columns=columns)

    conn.commit()
    cur.close()
    conn.close()

    return result


def get_schools():
    return fetch_all("""
        SELECT school_id, school_name
        FROM schools
        ORDER BY school_name;
    """)


def get_products():
    return fetch_all("""
        SELECT
            product_id,
            product_name,
            price,
            cost_price
        FROM products
        ORDER BY product_name;
    """)


def get_categories():
    df = fetch_all("""
        SELECT DISTINCT category_name
        FROM school_product_prices
        ORDER BY category_name;
    """)

    if df.empty:
        return ["Primary", "JSS"]

    return df["category_name"].tolist()


def get_products_for_school_category(school_id, category):
    return fetch_all("""
        SELECT
            p.product_id,
            p.product_name,
            spp.price,
            p.cost_price
        FROM school_product_prices spp
        JOIN products p
            ON p.product_id = spp.product_id
        WHERE spp.school_id = %s
          AND spp.category_name = %s
        ORDER BY p.product_name;
    """, (school_id, category))


def get_stock_summary(school_id):
    return fetch_all("""
        SELECT
            p.product_id,
            p.product_name,

            COALESCE(
                (
                    SELECT SUM(s.quantity_brought)
                    FROM stock s
                    WHERE s.school_id = %s
                      AND s.product_id = p.product_id
                ), 0
            ) AS brought_in,

            COALESCE(
                (
                    SELECT SUM(si.quantity)
                    FROM sale_items si
                    JOIN sales sa
                        ON sa.sale_id = si.sale_id
                    WHERE sa.school_id = %s
                      AND si.product_id = p.product_id
                ), 0
            ) AS sold,

            p.cost_price

        FROM products p
        WHERE p.product_id IN (
            SELECT product_id
            FROM school_product_prices
            WHERE school_id = %s
        )
        ORDER BY p.product_name;
    """, (school_id, school_id, school_id))


# ============================================================
# SESSION STATE
# ============================================================

if "cart" not in st.session_state:
    st.session_state.cart = []

if "last_receipt" not in st.session_state:
    st.session_state.last_receipt = None


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("🧾 Uniform Sales POS")

menu = st.sidebar.radio(
    "Menu",
    [
        "New Sale",
        "Price Management",
        "Stock Management",
        "Business Finance",
        "Sales Overview",
        "Sales History",
        "ML & Forecasting"
    ]
)

# ============================================================
# NEW SALE
# ============================================================

if menu == "New Sale":

    st.title("🧾 New Sale")

    schools = get_schools()

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

    col1, col2 = st.columns(2)

    with col1:
        term = st.selectbox(
            "Term",
            ["Term 1", "Term 2", "Term 3"]
        )

    with col2:
        year = st.number_input(
            "Year",
            min_value=2020,
            max_value=2100,
            value=datetime.now().year
        )

    category = st.selectbox(
        "Category",
        get_categories()
    )

    products_df = get_products_for_school_category(
        school_id,
        category
    )

    if products_df.empty:
        st.info(
            "No products have been assigned to this school/category yet."
        )
        st.stop()

    col1, col2 = st.columns(2)

    with col1:
        customer_name = st.text_input(
            "Student / Customer Name"
        )

    with col2:
        phone = st.text_input(
            "Phone Number"
        )

    class_grade = st.text_input(
        "Class / Grade"
    )

    product_name = st.selectbox(
        "Product",
        products_df["product_name"].tolist()
    )

    selected_product = products_df[
        products_df["product_name"] == product_name
    ].iloc[0]

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

    unit_price = float(selected_product["price"])

    if st.button("➕ Add to Cart", use_container_width=True):

        st.session_state.cart.append({
            "product_id": int(selected_product["product_id"]),
            "product": product_name,
            "quantity": int(quantity),
            "unit_price": unit_price,
            "total": unit_price * quantity,
            "issued": issued
        })

        st.success("Item added to cart.")

    # ---------------- CART ----------------

    if st.session_state.cart:

        st.subheader("🛒 Cart")

        cart_df = pd.DataFrame(st.session_state.cart)

        st.dataframe(
            cart_df[
                [
                    "product",
                    "quantity",
                    "unit_price",
                    "total",
                    "issued"
                ]
            ],
            use_container_width=True
        )

        total = sum(
            item["total"]
            for item in st.session_state.cart
        )

        st.markdown(
            f"### Total: KSh {total:,.2f}"
        )

        payment_method = st.selectbox(
            "Payment Method",
            ["Cash", "M-Pesa", "Bank", "Card"]
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button(
                "✅ Complete Sale",
                use_container_width=True
            ):

                if not customer_name.strip():
                    st.error("Enter the student/customer name.")
                    st.stop()

                conn = get_connection()
                cur = conn.cursor()

                try:

                    # Customer
                    cur.execute("""
                        INSERT INTO customers
                        (customer_name, phone)
                        VALUES (%s, %s)
                        RETURNING customer_id;
                    """, (customer_name, phone))

                    customer_id = cur.fetchone()[0]

                    # Sale
                    cur.execute("""
                        INSERT INTO sales
                        (
                            school_id,
                            customer_id,
                            total_amount,
                            payment_method,
                            payment_status,
                            term,
                            year
                        )
                        VALUES
                        (%s, %s, %s, %s, 'Paid', %s, %s)
                        RETURNING sale_id, sale_date;
                    """, (
                        school_id,
                        customer_id,
                        total,
                        payment_method,
                        term,
                        year
                    ))

                    sale_id, sale_date = cur.fetchone()

                    # Items
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
                            (%s, %s, %s, %s, %s, %s);
                        """, (
                            sale_id,
                            item["product_id"],
                            item["quantity"],
                            item["unit_price"],
                            item["total"],
                            item["issued"]
                        ))

                    # Sales income is automatically recorded in finance.
                    cur.execute("""
                        INSERT INTO financial_transactions
                        (
                            transaction_type,
                            category,
                            description,
                            amount,
                            term,
                            year
                        )
                        VALUES
                        (
                            'Sales Income',
                            'Sales',
                            %s,
                            %s,
                            %s,
                            %s
                        );
                    """, (
                        f"Sale #{sale_id}",
                        total,
                        term,
                        year
                    ))

                    conn.commit()

                    st.session_state.last_receipt = {
                        "sale_id": sale_id,
                        "sale_date": sale_date,
                        "school": school_name,
                        "customer": customer_name,
                        "phone": phone,
                        "class": class_grade,
                        "term": term,
                        "year": year,
                        "items": st.session_state.cart.copy(),
                        "total": total,
                        "payment": payment_method
                    }

                    st.session_state.cart = []

                    st.success(
                        f"Sale #{sale_id} completed successfully."
                    )

                except Exception as e:

                    conn.rollback()
                    st.error(f"Sale failed: {e}")

                finally:

                    cur.close()
                    conn.close()

        with col2:

            if st.button(
                "🗑️ Clear Cart",
                use_container_width=True
            ):
                st.session_state.cart = []
                st.rerun()

    # ---------------- RECEIPT ----------------

    if st.session_state.last_receipt:

        receipt = st.session_state.last_receipt

        st.divider()

        st.subheader("🧾 Receipt")

        receipt_html = f"""
        <div style="
            font-family:Arial;
            max-width:500px;
            padding:20px;
            border:1px solid #ddd;
            background:white;
        ">

        <h2>UNIFORM SALES RECEIPT</h2>

        <p><b>Sale:</b> #{receipt['sale_id']}</p>
        <p><b>Date:</b> {receipt['sale_date']}</p>
        <p><b>School:</b> {receipt['school']}</p>
        <p><b>Customer:</b> {receipt['customer']}</p>
        <p><b>Phone:</b> {receipt['phone']}</p>
        <p><b>Class:</b> {receipt['class']}</p>
        <p><b>Term:</b> {receipt['term']} {receipt['year']}</p>

        <hr>

        """

        for item in receipt["items"]:
            receipt_html += f"""
            <p>
                {item['product']} × {item['quantity']}
                —
                KSh {item['total']:,.2f}
            </p>
            """

        receipt_html += f"""
        <hr>

        <h3>Total: KSh {receipt['total']:,.2f}</h3>

        <p><b>Payment:</b> {receipt['payment']}</p>

        </div>
        """

        components.html(
            f"""
            {receipt_html}

            <br>

            <button
                onclick="window.print()"
                style="
                    padding:10px 20px;
                    background:#f57c00;
                    color:white;
                    border:none;
                    border-radius:5px;
                    cursor:pointer;
                "
            >
                Print Receipt
            </button>
            """,
            height=650
        )


# ============================================================
# PRICE MANAGEMENT
# ============================================================

elif menu == "Price Management":

    st.title("💰 Price Management")

    schools = get_schools()

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
        ["Primary", "JSS"]
    )

    st.subheader("Assigned Products")

    assigned = get_products_for_school_category(
        school_id,
        category
    )

    if assigned.empty:

        st.info("No products assigned yet.")

    else:

        for _, row in assigned.iterrows():

            new_price = st.number_input(
                row["product_name"],
                min_value=0.0,
                value=float(row["price"]),
                step=50.0,
                key=f"price_{school_id}_{category}_{row['product_id']}"
            )

            if st.button(
                f"Save {row['product_name']}",
                key=f"saveprice_{school_id}_{category}_{row['product_id']}"
            ):

                execute_query("""
                    UPDATE school_product_prices
                    SET price = %s
                    WHERE school_id = %s
                      AND category_name = %s
                      AND product_id = %s;
                """, (
                    new_price,
                    school_id,
                    category,
                    int(row["product_id"])
                ))

                st.success("Price updated.")
                st.rerun()

    st.divider()

    st.subheader("➕ Add Product")

    product_name = st.text_input(
        "Product Name"
    )

    selling_price = st.number_input(
        "Selling Price",
        min_value=0.0,
        step=50.0
    )

    cost_price = st.number_input(
        "Purchase / Cost Price",
        min_value=0.0,
        step=50.0,
        help="What the business pays for one item."
    )

    if st.button(
        "Create Product",
        use_container_width=True
    ):

        if not product_name.strip():
            st.error("Enter a product name.")
            st.stop()

        try:

            conn = get_connection()
            cur = conn.cursor()

            cur.execute("""
                INSERT INTO products
                (
                    product_name,
                    price,
                    cost_price
                )
                VALUES (%s, %s, %s)
                RETURNING product_id;
            """, (
                product_name.strip(),
                selling_price,
                cost_price
            ))

            product_id = cur.fetchone()[0]

            cur.execute("""
                INSERT INTO school_product_prices
                (
                    school_id,
                    category_name,
                    product_id,
                    price
                )
                VALUES (%s, %s, %s, %s)
                ON CONFLICT
                (school_id, category_name, product_id)
                DO UPDATE SET price = EXCLUDED.price;
            """, (
                school_id,
                category,
                product_id,
                selling_price
            ))

            conn.commit()
            cur.close()
            conn.close()

            st.success("Product created and assigned.")

        except Exception as e:
            st.error(f"Could not create product: {e}")


# ============================================================
# STOCK MANAGEMENT
# ============================================================

elif menu == "Stock Management":

    st.title("📦 Stock Management")

    schools = get_schools()

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

    stock_products = get_stock_summary(school_id)

    if stock_products.empty:

        st.info("No products assigned to this school.")

    else:

        st.subheader("➕ Add Stock")

        product_name = st.selectbox(
            "Product",
            stock_products["product_name"].tolist()
        )

        product_row = stock_products[
            stock_products["product_name"] == product_name
        ].iloc[0]

        quantity = st.number_input(
            "Quantity Brought In",
            min_value=1,
            value=1,
            step=1
        )

        unit_cost = st.number_input(
            "Cost Per Item",
            min_value=0.0,
            value=float(product_row["cost_price"]),
            step=50.0
        )

        col1, col2 = st.columns(2)

        with col1:
            term = st.selectbox(
                "Term",
                ["Term 1", "Term 2", "Term 3"],
                key="stock_term"
            )

        with col2:
            year = st.number_input(
                "Year",
                min_value=2020,
                max_value=2100,
                value=datetime.now().year,
                key="stock_year"
            )

        if st.button(
            "📦 Add Stock",
            use_container_width=True
        ):

            conn = get_connection()
            cur = conn.cursor()

            try:

                product_id = int(product_row["product_id"])
                total_cost = quantity * unit_cost

                # Add physical stock
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
                    (%s, %s, %s, %s, %s, %s);
                """, (
                    school_id,
                    product_id,
                    quantity,
                    term,
                    year,
                    unit_cost
                ))

                # Record cash leaving the business
                cur.execute("""
                    INSERT INTO financial_transactions
                    (
                        transaction_type,
                        category,
                        description,
                        amount,
                        term,
                        year
                    )
                    VALUES
                    (
                        'Stock Purchase',
                        'Inventory',
                        %s,
                        %s,
                        %s,
                        %s
                    );
                """, (
                    f"{quantity} × {product_name}",
                    total_cost,
                    term,
                    year
                ))

                conn.commit()

                st.success(
                    f"Added {quantity} {product_name}(s). "
                    f"Stock cost: KSh {total_cost:,.2f}"
                )

            except Exception as e:

                conn.rollback()
                st.error(f"Could not add stock: {e}")

            finally:

                cur.close()
                conn.close()

        st.divider()

        st.subheader("📊 Current Stock")

        stock_products["remaining"] = (
            stock_products["brought_in"]
            - stock_products["sold"]
        )

        stock_products["stock_value"] = (
            stock_products["remaining"]
            * stock_products["cost_price"]
        )

        display_stock = stock_products[
            [
                "product_name",
                "brought_in",
                "sold",
                "remaining",
                "cost_price",
                "stock_value"
            ]
        ].copy()

        display_stock.columns = [
            "Uniform",
            "Brought In",
            "Sold",
            "Remaining",
            "Cost / Item",
            "Remaining Stock Value"
        ]

        st.dataframe(
            display_stock,
            use_container_width=True
        )

        low_stock = stock_products[
            stock_products["remaining"] <= 5
        ]

        if not low_stock.empty:

            st.warning(
                "⚠️ Low stock: "
                + ", ".join(
                    low_stock["product_name"].tolist()
                )
            )


# ============================================================
# BUSINESS FINANCE
# ============================================================

elif menu == "Business Finance":

    st.title("💵 Business Finance & Investment")

    st.caption(
        "Fresh business cycle — previous stolen/lost capital is not included."
    )

    # ========================================================
    # INVESTORS
    # ========================================================

    st.subheader("👥 Investors")

    investors = fetch_all("""
        SELECT
            investor_id,
            investor_name,
            active
        FROM investors
        ORDER BY investor_id;
    """)

    investment_summary = fetch_all("""
        SELECT
            i.investor_name,
            COALESCE(
                SUM(
                    CASE
                        WHEN ft.transaction_type = 'Capital Contribution'
                        THEN ft.amount
                        ELSE 0
                    END
                ), 0
            ) AS invested
        FROM investors i
        LEFT JOIN financial_transactions ft
            ON i.investor_id = ft.investor_id
        GROUP BY i.investor_id, i.investor_name
        ORDER BY i.investor_id;
    """)

    total_capital = (
        float(investment_summary["invested"].sum())
        if not investment_summary.empty
        else 0
    )

    if not investment_summary.empty:

        investment_summary["percentage"] = (
            investment_summary["invested"]
            / total_capital * 100
            if total_capital > 0
            else 0
        )

        investment_summary["invested"] = (
            investment_summary["invested"].map(
                lambda x: f"KSh {x:,.2f}"
            )
        )

        investment_summary["percentage"] = (
            investment_summary["percentage"].map(
                lambda x: f"{x:.1f}%"
            )
        )

        investment_summary.columns = [
            "Investor",
            "Capital Invested",
            "Contribution"
        ]

        st.dataframe(
            investment_summary,
            use_container_width=True
        )

    # ========================================================
    # ADD INVESTOR
    # ========================================================

    with st.expander("➕ Add / Edit Investor"):

        new_investor = st.text_input(
            "Investor Name"
        )

        if st.button("Add Investor"):

            if new_investor.strip():

                try:

                    execute_query("""
                        INSERT INTO investors
                        (investor_name)
                        VALUES (%s)
                        ON CONFLICT (investor_name)
                        DO NOTHING;
                    """, (new_investor.strip(),))

                    st.success("Investor added.")
                    st.rerun()

                except Exception as e:
                    st.error(str(e))

    st.divider()

    # ========================================================
    # ADD FINANCIAL TRANSACTION
    # ========================================================

    st.subheader("➕ Add Financial Transaction")

    col1, col2 = st.columns(2)

    with col1:

        transaction_type = st.selectbox(
            "Transaction Type",
            [
                "Capital Contribution",
                "Stock Purchase",
                "Expense",
                "Other Income",
                "Owner Withdrawal",
                "Profit Distribution"
            ]
        )

    with col2:

        amount = st.number_input(
            "Amount",
            min_value=0.0,
            step=100.0
        )

    category = st.text_input(
        "Category",
        value=(
            "Investment"
            if transaction_type == "Capital Contribution"
            else ""
        )
    )

    description = st.text_input(
        "Description"
    )

    col1, col2 = st.columns(2)

    with col1:

        transaction_term = st.selectbox(
            "Term",
            ["Term 1", "Term 2", "Term 3", "Current"],
            key="finance_term"
        )

    with col2:

        transaction_year = st.number_input(
            "Year",
            min_value=2020,
            max_value=2100,
            value=datetime.now().year,
            key="finance_year"
        )

    investor_id = None

    if transaction_type in [
        "Capital Contribution",
        "Owner Withdrawal",
        "Profit Distribution"
    ]:

        investor_options = {
            row["investor_name"]: int(row["investor_id"])
            for _, row in investors.iterrows()
        }

        if investor_options:

            investor_name = st.selectbox(
                "Investor",
                list(investor_options.keys())
            )

            investor_id = investor_options[investor_name]

    if st.button(
        "💾 Save Transaction",
        use_container_width=True
    ):

        if amount <= 0:
            st.error("Amount must be greater than zero.")
            st.stop()

        execute_query("""
            INSERT INTO financial_transactions
            (
                transaction_type,
                category,
                description,
                amount,
                investor_id,
                term,
                year
            )
            VALUES
            (%s, %s, %s, %s, %s, %s, %s);
        """, (
            transaction_type,
            category or "General",
            description,
            amount,
            investor_id,
            transaction_term,
            transaction_year
        ))

        st.success("Transaction recorded.")
        st.rerun()

    # ========================================================
    # FINANCIAL CALCULATIONS
    # ========================================================

    transactions = fetch_all("""
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

    capital = total_capital

    sales_revenue = (
        float(
            transactions.loc[
                transactions["transaction_type"] == "Sales Income",
                "amount"
            ].sum()
        )
        if not transactions.empty
        else 0
    )

    stock_purchases = (
        float(
            transactions.loc[
                transactions["transaction_type"] == "Stock Purchase",
                "amount"
            ].sum()
        )
        if not transactions.empty
        else 0
    )

    expenses = (
        float(
            transactions.loc[
                transactions["transaction_type"] == "Expense",
                "amount"
            ].sum()
        )
        if not transactions.empty
        else 0
    )

    other_income = (
        float(
            transactions.loc[
                transactions["transaction_type"] == "Other Income",
                "amount"
            ].sum()
        )
        if not transactions.empty
        else 0
    )

    withdrawals = (
        float(
            transactions.loc[
                transactions["transaction_type"].isin(
                    [
                        "Owner Withdrawal",
                        "Profit Distribution"
                    ]
                ),
                "amount"
            ].sum()
        )
        if not transactions.empty
        else 0
    )

    # ========================================================
    # COGS / PROFIT
    # ========================================================

    cogs_df = fetch_all("""
        SELECT
            COALESCE(
                SUM(si.quantity * p.cost_price),
                0
            ) AS cogs
        FROM sale_items si
        JOIN products p
            ON p.product_id = si.product_id;
    """)

    cogs = float(cogs_df.iloc[0]["cogs"])

    gross_profit = sales_revenue - cogs

    net_profit = gross_profit + other_income - expenses

    cash_position = (
        capital
        + sales_revenue
        + other_income
        - stock_purchases
        - expenses
        - withdrawals
    )

    # ========================================================
    # INVENTORY VALUE
    # ========================================================

    inventory_df = fetch_all("""
        SELECT
            COALESCE(
                SUM(
                    stock_total.quantity_brought
                    - COALESCE(sold_total.sold_quantity, 0)
                ) * p.cost_price,
                0
            ) AS inventory_value
        FROM products p

        LEFT JOIN (
            SELECT
                product_id,
                SUM(quantity_brought) AS quantity_brought
            FROM stock
            GROUP BY product_id
        ) stock_total
            ON stock_total.product_id = p.product_id

        LEFT JOIN (
            SELECT
                si.product_id,
                SUM(si.quantity) AS sold_quantity
            FROM sale_items si
            GROUP BY si.product_id
        ) sold_total
            ON sold_total.product_id = p.product_id;
    """)

    inventory_value = (
        float(inventory_df.iloc[0]["inventory_value"])
        if not inventory_df.empty
        else 0
    )

    # ========================================================
    # ROI
    # ========================================================

    roi = (
        (net_profit / capital) * 100
        if capital > 0
        else 0
    )

    # ========================================================
    # METRICS
    # ========================================================

    st.subheader("📊 Business Position")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "Capital Invested",
            f"KSh {capital:,.0f}"
        )

    with c2:
        st.metric(
            "Sales Revenue",
            f"KSh {sales_revenue:,.0f}"
        )

    with c3:
        st.metric(
            "Inventory Value",
            f"KSh {inventory_value:,.0f}"
        )

    with c4:
        st.metric(
            "Cash Position",
            f"KSh {cash_position:,.0f}"
        )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "Cost of Goods Sold",
            f"KSh {cogs:,.0f}"
        )

    with c2:
        st.metric(
            "Gross Profit",
            f"KSh {gross_profit:,.0f}"
        )

    with c3:
        st.metric(
            "Net Profit",
            f"KSh {net_profit:,.0f}"
        )

    with c4:
        st.metric(
            "ROI",
            f"{roi:.2f}%"
        )

    # ========================================================
    # BREAKDOWN
    # ========================================================

    st.subheader("💰 Financial Breakdown")

    breakdown = pd.DataFrame({
        "Category": [
            "Capital Invested",
            "Sales Revenue",
            "Stock Purchases",
            "Operating Expenses",
            "Owner Withdrawals",
            "Inventory Value",
            "Net Profit"
        ],
        "Amount": [
            capital,
            sales_revenue,
            stock_purchases,
            expenses,
            withdrawals,
            inventory_value,
            net_profit
        ]
    })

    breakdown["Amount"] = breakdown["Amount"].map(
        lambda x: f"KSh {x:,.2f}"
    )

    st.dataframe(
        breakdown,
        use_container_width=True
    )

    # ========================================================
    # INVESTMENT RETURN
    # ========================================================

    st.subheader("📈 Investment Return")

    st.info(
        "ROI is calculated from recorded profit relative to the fresh capital "
        "invested in this business cycle."
    )

    if capital > 0:

        st.write(
            f"**Current capital:** KSh {capital:,.2f}"
        )

        st.write(
            f"**Current net profit:** KSh {net_profit:,.2f}"
        )

        st.write(
            f"**Current ROI:** {roi:.2f}%"
        )

        investor_returns = fetch_all("""
            SELECT
                i.investor_name,
                COALESCE(
                    SUM(
                        CASE
                            WHEN ft.transaction_type =
                                'Capital Contribution'
                            THEN ft.amount
                            ELSE 0
                        END
                    ), 0
                ) AS invested
            FROM investors i
            LEFT JOIN financial_transactions ft
                ON i.investor_id = ft.investor_id
            GROUP BY i.investor_id, i.investor_name
            ORDER BY i.investor_id;
        """)

        if not investor_returns.empty:

            investor_returns["ownership"] = (
                investor_returns["invested"]
                / capital * 100
            )

            investor_returns["estimated_profit_share"] = (
                investor_returns["ownership"]
                / 100
                * net_profit
            )

            investor_returns_display = investor_returns.copy()

            investor_returns_display[
                "invested"
            ] = investor_returns_display["invested"].map(
                lambda x: f"KSh {x:,.2f}"
            )

            investor_returns_display[
                "ownership"
            ] = investor_returns_display["ownership"].map(
                lambda x: f"{x:.1f}%"
            )

            investor_returns_display[
                "estimated_profit_share"
            ] = investor_returns_display[
                "estimated_profit_share"
            ].map(
                lambda x: f"KSh {x:,.2f}"
            )

            investor_returns_display.columns = [
                "Investor",
                "Capital",
                "Contribution %",
                "Estimated Profit Share"
            ]

            st.dataframe(
                investor_returns_display,
                use_container_width=True
            )

    # ========================================================
    # TRANSACTION HISTORY
    # ========================================================

    st.subheader("📋 Financial Ledger")

    if transactions.empty:

        st.info("No financial transactions yet.")

    else:

        ledger = transactions.copy()

        ledger["amount"] = ledger["amount"].map(
            lambda x: f"KSh {float(x):,.2f}"
        )

        st.dataframe(
            ledger,
            use_container_width=True
        )


# ============================================================
# SALES OVERVIEW
# ============================================================

elif menu == "Sales Overview":

    st.title("📊 Sales Overview")

    sales = fetch_all("""
        SELECT
            s.sale_id,
            s.sale_date,
            s.total_amount,
            s.term,
            s.year,
            sc.school_name
        FROM sales s
        JOIN schools sc
            ON sc.school_id = s.school_id
        ORDER BY s.sale_date;
    """)

    if sales.empty:

        st.info("No sales recorded yet.")

    else:

        sales["sale_date"] = pd.to_datetime(
            sales["sale_date"]
        )

        total_revenue = float(
            sales["total_amount"].sum()
        )

        total_sales = len(sales)

        average_sale = (
            total_revenue / total_sales
            if total_sales > 0
            else 0
        )

        c1, c2, c3 = st.columns(3)

        with c1:
            st.metric(
                "Total Sales",
                total_sales
            )

        with c2:
            st.metric(
                "Revenue",
                f"KSh {total_revenue:,.2f}"
            )

        with c3:
            st.metric(
                "Average Sale",
                f"KSh {average_sale:,.2f}"
            )

        st.subheader("Revenue by Term")

        term_summary = (
            sales
            .groupby(["year", "term"], dropna=False)
            ["total_amount"]
            .sum()
            .reset_index()
        )

        st.dataframe(
            term_summary,
            use_container_width=True
        )

        st.bar_chart(
            term_summary.set_index(
                ["year", "term"]
            )["total_amount"]
        )

        st.subheader("Revenue by School")

        school_summary = (
            sales
            .groupby("school_name")["total_amount"]
            .sum()
            .sort_values(ascending=False)
        )

        st.bar_chart(
            school_summary
        )


# ============================================================
# SALES HISTORY
# ============================================================

elif menu == "Sales History":

    st.title("📋 Sales History")

    history = fetch_all("""
        SELECT
            s.sale_id,
            s.sale_date,
            sc.school_name,
            c.customer_name,
            c.phone,
            s.term,
            s.year,
            s.total_amount,
            s.payment_method,
            s.payment_status
        FROM sales s

        JOIN schools sc
            ON sc.school_id = s.school_id

        LEFT JOIN customers c
            ON c.customer_id = s.customer_id

        ORDER BY s.sale_date DESC;
    """)

    if history.empty:

        st.info("No sales yet.")

    else:

        st.dataframe(
            history,
            use_container_width=True
        )


# ============================================================
# ML & FORECASTING
# ============================================================

elif menu == "ML & Forecasting":

    st.title("🤖 ML & Business Forecasting")

    st.write(
        "This section will use the business data collected by the system "
        "to support forecasting and decision-making."
    )

    # ========================================================
    # BUSINESS INVESTMENT ANALYSIS
    # ========================================================

    st.subheader("💰 Investment Analysis")

    finance = fetch_all("""
        SELECT
            transaction_date,
            transaction_type,
            amount,
            term,
            year
        FROM financial_transactions
        ORDER BY transaction_date;
    """)

    if finance.empty:

        st.info(
            "Investment analysis will become available once financial "
            "transactions are recorded."
        )

    else:

        capital = float(
            finance.loc[
                finance["transaction_type"]
                == "Capital Contribution",
                "amount"
            ].sum()
        )

        revenue = float(
            finance.loc[
                finance["transaction_type"]
                == "Sales Income",
                "amount"
            ].sum()
        )

        expenses = float(
            finance.loc[
                finance["transaction_type"]
                == "Expense",
                "amount"
            ].sum()
        )

        st.write(
            f"**Capital invested:** KSh {capital:,.2f}"
        )

        st.write(
            f"**Revenue generated:** KSh {revenue:,.2f}"
        )

        st.write(
            f"**Operating expenses:** KSh {expenses:,.2f}"
        )

        if capital > 0:

            simple_return = (
                (revenue - expenses - capital)
                / capital
            ) * 100

            st.metric(
                "Revenue-based return indicator",
                f"{simple_return:.2f}%"
            )

    # ========================================================
    # SALES DATA
    # ========================================================

    sales_ml = fetch_all("""
        SELECT
            sale_date,
            total_amount,
            term,
            year,
            school_id
        FROM sales
        ORDER BY sale_date;
    """)

    if sales_ml.empty:

        st.info(
            "More sales data is needed before meaningful forecasting "
            "can be performed."
        )

    else:

        sales_ml["sale_date"] = pd.to_datetime(
            sales_ml["sale_date"]
        )

        daily = (
            sales_ml
            .groupby(
                sales_ml["sale_date"].dt.date
            )["total_amount"]
            .sum()
            .reset_index()
        )

        daily.columns = [
            "date",
            "revenue"
        ]

        st.subheader("📈 Historical Revenue")

        st.line_chart(
            daily.set_index("date")["revenue"]
        )

        # ====================================================
        # SIMPLE FORECAST
        # ====================================================

        if len(daily) >= 3:

            recent = daily["revenue"].tail(
                min(7, len(daily))
            )

            average_recent = recent.mean()

            st.subheader(
                "🔮 Simple Revenue Forecast"
            )

            st.write(
                f"Recent average daily revenue: "
                f"**KSh {average_recent:,.2f}**"
            )

            st.info(
                "This is a simple baseline forecast. "
                "Once enough historical sales accumulate, "
                "we can replace it with proper ML forecasting."
            )

        # ====================================================
        # PRODUCT DEMAND
        # ====================================================

        product_sales = fetch_all("""
            SELECT
                p.product_name,
                SUM(si.quantity) AS quantity_sold,
                SUM(si.line_total) AS revenue
            FROM sale_items si
            JOIN products p
                ON p.product_id = si.product_id
            GROUP BY p.product_name
            ORDER BY quantity_sold DESC;
        """)

        if not product_sales.empty:

            st.subheader(
                "📦 Product Demand"
            )

            st.dataframe(
                product_sales,
                use_container_width=True
            )

            st.bar_chart(
                product_sales.set_index(
                    "product_name"
                )["quantity_sold"]
            )

    # ========================================================
    # FUTURE ML MODULES
    # ========================================================

    st.subheader("🚀 Planned ML Intelligence")

    st.markdown("""
    **Sales Forecasting**
    - Predict next-term revenue
    - Predict monthly sales

    **Demand Forecasting**
    - Predict which uniforms will sell fastest
    - Estimate quantities to bring in

    **Inventory Intelligence**
    - Detect slow-moving stock
    - Detect likely stock-outs

    **Financial Forecasting**
    - Forecast revenue
    - Forecast profit
    - Track return on capital

    **Investment Analysis**
    - Track capital growth
    - Compare actual return against invested capital
    - Estimate future returns based on historical performance

    **School Analysis**
    - Compare Loving Blooms and Waridi
    - Identify stronger-selling products by school

    The forecasts will become more reliable as the system collects more
    real sales and financial data.
    """)


# ============================================================
# FOOTER
# ============================================================

st.sidebar.divider()
st.sidebar.caption("Uniform Sales POS")
st.sidebar.caption("Fresh business cycle • 2 investors • Term-based tracking")
