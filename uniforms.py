import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Uniform Sales POS",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# DESIGN
# ============================================================

st.markdown("""
<style>

.stApp {
    background-color: #EEF4F8;
}

section[data-testid="stSidebar"] {
    background-color: #173B5E;
}

section[data-testid="stSidebar"] * {
    color: white;
}

h1, h2, h3 {
    color: #173B5E;
}

.stButton > button {
    background-color: #F28C28;
    color: white;
    border: none;
    border-radius: 7px;
    font-weight: 600;
}

.stButton > button:hover {
    background-color: #D97706;
    color: white;
}

div[data-testid="stMetric"] {
    background-color: white;
    padding: 15px;
    border-radius: 10px;
    border: 1px solid #D9E2EA;
}

div[data-testid="stDataFrame"] {
    background-color: white;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# DATABASE CONNECTION
# ============================================================

DB_CONFIG = {
    "host": st.secrets["postgres"]["host"],
    "database": st.secrets["postgres"]["database"],
    "user": st.secrets["postgres"]["user"],
    "password": st.secrets["postgres"]["password"],
    "port": st.secrets["postgres"]["port"]
}


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


# ============================================================
# DATABASE SETUP
# ============================================================

def setup_database():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schools (
            school_id SERIAL PRIMARY KEY,
            school_name VARCHAR(100) NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id SERIAL PRIMARY KEY,
            product_name VARCHAR(100) NOT NULL,
            price NUMERIC(10,2) NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id SERIAL PRIMARY KEY,
            customer_name VARCHAR(100) NOT NULL,
            phone VARCHAR(20)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            sale_id SERIAL PRIMARY KEY,
            sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            school_id INT NOT NULL,
            customer_id INT,
            total_amount NUMERIC(10,2) NOT NULL,
            payment_method VARCHAR(30),
            payment_status VARCHAR(20) DEFAULT 'Paid',
            FOREIGN KEY (school_id)
                REFERENCES schools(school_id),
            FOREIGN KEY (customer_id)
                REFERENCES customers(customer_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sale_items (
            sale_item_id SERIAL PRIMARY KEY,
            sale_id INT NOT NULL,
            product_id INT NOT NULL,
            quantity INT NOT NULL,
            unit_price NUMERIC(10,2) NOT NULL,
            line_total NUMERIC(10,2) NOT NULL,
            FOREIGN KEY (sale_id)
                REFERENCES sales(sale_id),
            FOREIGN KEY (product_id)
                REFERENCES products(product_id)
        )
    """)

    cursor.execute("""
        ALTER TABLE sale_items
        ADD COLUMN IF NOT EXISTS issued BOOLEAN DEFAULT TRUE
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS uniform_sets (
            set_id SERIAL PRIMARY KEY,
            school_id INT NOT NULL
                REFERENCES schools(school_id),
            set_name VARCHAR(100) NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS set_items (
            set_item_id SERIAL PRIMARY KEY,
            set_id INT NOT NULL,
            product_id INT NOT NULL,
            quantity INT NOT NULL,
            FOREIGN KEY (product_id)
                REFERENCES products(product_id)
        )
    """)

    cursor.execute("""
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
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()


# ============================================================
# INITIALISE DATABASE
# ============================================================

try:
    setup_database()
except Exception as e:
    st.error("Unable to connect to the cloud database.")
    st.code(str(e))
    st.stop()


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def fetch_all(query, params=None):
    conn = get_connection()

    try:
        df = pd.read_sql_query(
            query,
            conn,
            params=params
        )
        return df

    finally:
        conn.close()


def execute_query(query, params=None, fetch=False):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(query, params)

        result = None

        if fetch:
            result = cursor.fetchone()

        conn.commit()

        return result

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()


def get_schools():
    return fetch_all("""
        SELECT school_id, school_name
        FROM schools
        ORDER BY school_name
    """)


def get_categories(school_id):
    df = fetch_all("""
        SELECT DISTINCT category_name
        FROM school_product_prices
        WHERE school_id = %s
        ORDER BY category_name
    """, (school_id,))

    return df["category_name"].tolist()


def get_products_for_category(school_id, category):
    return fetch_all("""
        SELECT
            p.product_id,
            p.product_name,
            spp.price
        FROM school_product_prices spp
        JOIN products p
            ON p.product_id = spp.product_id
        WHERE spp.school_id = %s
        AND spp.category_name = %s
        ORDER BY p.product_name
    """, (school_id, category))


def get_customer(customer_name, phone):
    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT customer_id
            FROM customers
            WHERE customer_name = %s
            AND COALESCE(phone, '') = COALESCE(%s, '')
            LIMIT 1
        """, (customer_name, phone))

        row = cursor.fetchone()

        if row:
            return row[0]

        cursor.execute("""
            INSERT INTO customers
            (customer_name, phone)
            VALUES (%s, %s)
            RETURNING customer_id
        """, (customer_name, phone))

        customer_id = cursor.fetchone()[0]

        conn.commit()

        return customer_id

    finally:
        cursor.close()
        conn.close()


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

st.sidebar.title("UNIFORM POS")
st.sidebar.caption("School Uniform Sales System")

menu = st.sidebar.radio(
    "Navigation",
    [
        "New Sale",
        "Price Management",
        "Stock Management",
        "Sales Overview",
        "Sales History",
        "ML Utilities"
    ]
)


# ============================================================
# NEW SALE
# ============================================================

if menu == "New Sale":

    st.title("New Sale")
    st.caption("Point of Sale — create a uniform sale")

    schools = get_schools()

    if schools.empty:
        st.warning("No schools have been added.")
        st.stop()

    school_map = dict(
        zip(
            schools["school_name"],
            schools["school_id"]
        )
    )

    school_name = st.selectbox(
        "School",
        list(school_map.keys())
    )

    school_id = school_map[school_name]

    categories = get_categories(school_id)

    if not categories:
        st.warning(
            "No products have been assigned to this school yet."
        )
        st.stop()

    category = st.selectbox(
        "Category",
        categories
    )

    st.subheader("Customer")

    col1, col2, col3 = st.columns(3)

    with col1:
        customer_name = st.text_input(
            "Customer / Parent Name"
        )

    with col2:
        phone = st.text_input(
            "Phone Number"
        )

    with col3:
        student_class = st.text_input(
            "Class / Grade"
        )

    st.subheader("Add Items")

    products = get_products_for_category(
        school_id,
        category
    )

    if products.empty:
        st.warning(
            "No products have been assigned to this category."
        )
        st.stop()

    product_names = products["product_name"].tolist()

    col1, col2, col3 = st.columns([3, 1, 1])

    with col1:
        selected_product = st.selectbox(
            "Product",
            product_names
        )

    selected_row = products[
        products["product_name"] == selected_product
    ].iloc[0]

    product_id = int(
        selected_row["product_id"]
    )

    unit_price = float(
        selected_row["price"]
    )

    with col2:
        quantity = st.number_input(
            "Quantity",
            min_value=1,
            value=1,
            step=1
        )

    with col3:
        issued = st.checkbox(
            "Issued",
            value=True
        )

    if st.button("Add to Cart"):

        line_total = unit_price * quantity

        st.session_state.cart.append({
            "product_id": product_id,
            "product": selected_product,
            "quantity": quantity,
            "unit_price": unit_price,
            "line_total": line_total,
            "issued": issued
        })

        st.success(
            f"{selected_product} added to cart."
        )


    # --------------------------------------------------------
    # CART
    # --------------------------------------------------------

    st.subheader("Current Sale")

    if st.session_state.cart:

        cart_df = pd.DataFrame(
            st.session_state.cart
        )

        display_df = cart_df[
            [
                "product",
                "quantity",
                "unit_price",
                "line_total",
                "issued"
            ]
        ].copy()

        display_df.columns = [
            "Item",
            "Qty",
            "Unit Price",
            "Line Total",
            "Issued"
        ]

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )

        total = sum(
            item["line_total"]
            for item in st.session_state.cart
        )

        st.metric(
            "TOTAL",
            f"KES {total:,.2f}"
        )

        if st.button("Clear Cart"):
            st.session_state.cart = []
            st.rerun()

        st.subheader("Payment")

        payment_method = st.selectbox(
            "Payment Method",
            [
                "Cash",
                "M-Pesa",
                "Bank",
                "Card"
            ]
        )

        if st.button(
            "COMPLETE SALE",
            type="primary"
        ):

            if not customer_name.strip():
                st.error(
                    "Enter the customer / parent name."
                )
                st.stop()

            conn = get_connection()
            cursor = conn.cursor()

            try:

                customer_id = get_customer(
                    customer_name.strip(),
                    phone.strip()
                )

                cursor.execute("""
                    INSERT INTO sales
                    (
                        school_id,
                        customer_id,
                        total_amount,
                        payment_method,
                        payment_status
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING sale_id, sale_date
                """, (
                    school_id,
                    customer_id,
                    total,
                    payment_method,
                    "Paid"
                ))

                sale_id, sale_date = cursor.fetchone()

                for item in st.session_state.cart:

                    cursor.execute("""
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
                        (%s, %s, %s, %s, %s, %s)
                    """, (
                        sale_id,
                        item["product_id"],
                        item["quantity"],
                        item["unit_price"],
                        item["line_total"],
                        item["issued"]
                    ))

                conn.commit()

                receipt_items = [
                    item.copy()
                    for item in st.session_state.cart
                ]

                st.session_state.last_receipt = {
                    "sale_id": sale_id,
                    "sale_date": sale_date,
                    "school": school_name,
                    "customer": customer_name,
                    "phone": phone,
                    "class": student_class,
                    "category": category,
                    "payment": payment_method,
                    "items": receipt_items,
                    "total": total
                }

                st.session_state.cart = []

                st.success(
                    f"Sale #{sale_id} completed successfully."
                )

            except Exception as e:

                conn.rollback()

                st.error(
                    "The sale could not be completed."
                )

                st.code(str(e))

            finally:

                cursor.close()
                conn.close()


    # --------------------------------------------------------
    # PRINT RECEIPT
    # --------------------------------------------------------

    if st.session_state.last_receipt:

        st.divider()

        st.subheader("Receipt")

        receipt = st.session_state.last_receipt

        rows_html = ""

        for item in receipt["items"]:

            status = (
                "Issued"
                if item["issued"]
                else "Not Issued"
            )

            rows_html += f"""
            <tr>
                <td>{item['product']}</td>
                <td>{item['quantity']}</td>
                <td>{item['unit_price']:,.2f}</td>
                <td>{item['line_total']:,.2f}</td>
                <td>{status}</td>
            </tr>
            """

        receipt_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>

                body {{
                    font-family: Arial, sans-serif;
                    padding: 30px;
                    color: #222;
                }}

                .receipt {{
                    max-width: 700px;
                    margin: auto;
                }}

                h1 {{
                    text-align: center;
                    color: #173B5E;
                }}

                .details {{
                    margin-bottom: 20px;
                }}

                table {{
                    width: 100%;
                    border-collapse: collapse;
                }}

                th, td {{
                    border: 1px solid #ccc;
                    padding: 8px;
                    text-align: left;
                }}

                th {{
                    background: #173B5E;
                    color: white;
                }}

                .total {{
                    text-align: right;
                    font-size: 20px;
                    font-weight: bold;
                    margin-top: 20px;
                }}

                .print {{
                    background: #F28C28;
                    color: white;
                    border: none;
                    padding: 12px 20px;
                    cursor: pointer;
                    border-radius: 5px;
                    font-weight: bold;
                }}

                @media print {{
                    .print {{
                        display: none;
                    }}
                }}

            </style>
        </head>

        <body>

        <div class="receipt">

            <button
                class="print"
                onclick="window.print()">
                PRINT RECEIPT
            </button>

            <h1>UNIFORM SALES RECEIPT</h1>

            <div class="details">

                <strong>School:</strong>
                {receipt['school']}<br>

                <strong>Receipt No:</strong>
                {receipt['sale_id']}<br>

                <strong>Date:</strong>
                {receipt['sale_date']}<br>

                <strong>Customer:</strong>
                {receipt['customer']}<br>

                <strong>Phone:</strong>
                {receipt['phone']}<br>

                <strong>Class:</strong>
                {receipt['class']}<br>

                <strong>Category:</strong>
                {receipt['category']}<br>

                <strong>Payment:</strong>
                {receipt['payment']}

            </div>

            <table>

                <tr>
                    <th>Item</th>
                    <th>Qty</th>
                    <th>Unit Price</th>
                    <th>Amount</th>
                    <th>Status</th>
                </tr>

                {rows_html}

            </table>

            <div class="total">
                TOTAL PAID:
                KES {receipt['total']:,.2f}
            </div>

            <p>
                <strong>Legend:</strong>
                Issued = item given to customer.
                Not Issued = item pending availability.
            </p>

            <p style="text-align:center;">
                Thank you for your business.
            </p>

        </div>

        </body>
        </html>
        """

        components.html(
            receipt_html,
            height=700,
            scrolling=True
        )


# ============================================================
# PRICE MANAGEMENT
# ============================================================

elif menu == "Price Management":

    st.title("Price Management")
    st.caption(
        "Manage prices by school and category."
    )

    schools = get_schools()

    school_map = dict(
        zip(
            schools["school_name"],
            schools["school_id"]
        )
    )

    school_name = st.selectbox(
        "School",
        list(school_map.keys())
    )

    school_id = school_map[school_name]

    categories = get_categories(school_id)

    category_options = categories + ["Create New Category"]

    category = st.selectbox(
        "Category",
        category_options
    )

    if category == "Create New Category":

        new_category = st.text_input(
            "New Category Name"
        )

        if new_category:

            category = new_category

    else:

        if not category:
            st.info(
                "No categories available."
            )
            st.stop()


    # --------------------------------------------------------
    # CURRENT PRICES
    # --------------------------------------------------------

    prices = get_products_for_category(
        school_id,
        category
    )

    if not prices.empty:

        st.subheader("Current Prices")

        for _, row in prices.iterrows():

            col1, col2, col3 = st.columns(
                [3, 2, 1]
            )

            with col1:
                st.write(row["product_name"])

            with col2:

                new_price = st.number_input(
                    f"Price_{row['product_id']}",
                    min_value=0.0,
                    value=float(row["price"]),
                    step=50.0,
                    key=f"price_{school_id}_{category}_{row['product_id']}"
                )

            with col3:

                if st.button(
                    "Save",
                    key=f"save_{school_id}_{category}_{row['product_id']}"
                ):

                    execute_query("""
                        UPDATE school_product_prices
                        SET price = %s
                        WHERE school_id = %s
                        AND category_name = %s
                        AND product_id = %s
                    """, (
                        new_price,
                        school_id,
                        category,
                        int(row["product_id"])
                    ))

                    st.success(
                        "Price updated."
                    )

    else:

        st.info(
            "No products assigned to this category yet."
        )


    # --------------------------------------------------------
    # ADD PRODUCT
    # --------------------------------------------------------

    st.divider()

    st.subheader("Create Product")

    new_product_name = st.text_input(
        "Product Name"
    )

    new_product_price = st.number_input(
        "Starting Price",
        min_value=0.0,
        value=0.0,
        step=50.0
    )

    if st.button("Create Product"):

        if not new_product_name.strip():

            st.error(
                "Enter a product name."
            )

        else:

            existing = fetch_all("""
                SELECT product_id
                FROM products
                WHERE product_name = %s
                LIMIT 1
            """, (new_product_name.strip(),))

            if existing.empty:

                result = execute_query("""
                    INSERT INTO products
                    (product_name, price)
                    VALUES (%s, %s)
                    RETURNING product_id
                """, (
                    new_product_name.strip(),
                    new_product_price
                ), fetch=True)

                product_id = result[0]

            else:

                product_id = int(
                    existing.iloc[0]["product_id"]
                )

            execute_query("""
                INSERT INTO school_product_prices
                (
                    school_id,
                    category_name,
                    product_id,
                    price
                )
                VALUES (%s, %s, %s, %s)
                ON CONFLICT
                (
                    school_id,
                    category_name,
                    product_id
                )
                DO UPDATE SET price = EXCLUDED.price
            """, (
                school_id,
                category,
                product_id,
                new_product_price
            ))

            st.success(
                "Product added to the category."
            )

            st.rerun()


# ============================================================
# STOCK MANAGEMENT
# ============================================================

elif menu == "Stock Management":
st.header("📦 Stock Management")

# Select school
school_options = get_schools()
stock_school = st.selectbox(
    "Select School",
    school_options,
    key="stock_school"
)

stock_school_id = stock_school[0]

# Get products assigned to this school
stock_products = fetch_all(
    """
    SELECT
        spp.product_id,
        p.product_name,
        spp.price
    FROM school_product_prices spp
    JOIN products p ON spp.product_id = p.product_id
    WHERE spp.school_id = %s
    ORDER BY p.product_name
    """,
    (stock_school_id,)
)

if not stock_products:
    st.warning("No products have been assigned to this school yet.")
else:

    st.subheader("Add Uniforms Brought In")

    product_options = {
        row[1]: row[0]
        for row in stock_products
    }

    selected_product = st.selectbox(
        "Uniform",
        list(product_options.keys())
    )

    quantity_brought = st.number_input(
        "Quantity Brought In",
        min_value=1,
        step=1
    )

    if st.button("Add Stock"):
        execute_query(
            """
            INSERT INTO stock
            (school_id, product_id, quantity_brought)
            VALUES (%s, %s, %s)
            """,
            (
                stock_school_id,
                product_options[selected_product],
                quantity_brought
            )
        )

        st.success("Stock added successfully!")
        st.rerun()

    st.subheader("Current Stock")

    stock_data = fetch_all(
        """
        SELECT
            p.product_name,
            COALESCE(SUM(st.quantity_brought), 0) AS brought_in,
            COALESCE(
                (
                    SELECT SUM(si.quantity)
                    FROM sale_items si
                    JOIN sales s ON si.sale_id = s.sale_id
                    WHERE s.school_id = %s
                    AND si.product_id = p.product_id
                    AND si.issued = TRUE
                ), 0
            ) AS sold
        FROM products p
        LEFT JOIN stock st
            ON st.product_id = p.product_id
            AND st.school_id = %s
        WHERE p.product_id IN (
            SELECT product_id
            FROM school_product_prices
            WHERE school_id = %s
        )
        GROUP BY p.product_id, p.product_name
        ORDER BY p.product_name
        """,
        (
            stock_school_id,
            stock_school_id,
            stock_school_id
        )
    )

    stock_table = []

    for row in stock_data:
        product_name = row[0]
        brought_in = int(row[1])
        sold = int(row[2])
        remaining = brought_in - sold

        stock_table.append({
            "Uniform": product_name,
            "Brought In": brought_in,
            "Sold": sold,
            "Remaining": remaining
        })

    st.dataframe(
        pd.DataFrame(stock_table),
        use_container_width=True,
        hide_index=True
    )
     


# ============================================================
# SALES OVERVIEW
# ============================================================

elif menu == "Sales Overview":

    st.title("Sales Overview")

    summary = fetch_all("""
        SELECT
            COUNT(*) AS total_sales,
            COALESCE(
                SUM(total_amount), 0
            ) AS revenue
        FROM sales
    """)

    total_sales = int(
        summary.iloc[0]["total_sales"]
    )

    revenue = float(
        summary.iloc[0]["revenue"]
    )

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Total Sales",
            total_sales
        )

    with col2:
        st.metric(
            "Total Revenue",
            f"KES {revenue:,.2f}"
        )


    st.subheader("Daily Revenue")

    daily = fetch_all("""
        SELECT
            DATE(sale_date) AS sale_day,
            SUM(total_amount) AS revenue
        FROM sales
        GROUP BY DATE(sale_date)
        ORDER BY sale_day
    """)

    if not daily.empty:

        daily["sale_day"] = pd.to_datetime(
            daily["sale_day"]
        )

        daily = daily.set_index(
            "sale_day"
        )

        st.line_chart(
            daily["revenue"]
        )


# ============================================================
# SALES HISTORY
# ============================================================

elif menu == "Sales History":

    st.title("Sales History")

    history = fetch_all("""
        SELECT
            s.sale_id,
            s.sale_date,
            sc.school_name,
            c.customer_name,
            c.phone,
            s.total_amount,
            s.payment_method,
            s.payment_status
        FROM sales s
        JOIN schools sc
            ON sc.school_id = s.school_id
        LEFT JOIN customers c
            ON c.customer_id = s.customer_id
        ORDER BY s.sale_date DESC
    """)

    if history.empty:

        st.info(
            "No sales recorded yet."
        )

    else:

        st.dataframe(
            history,
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# ML UTILITIES
# ============================================================

elif menu == "ML Utilities":

    st.title("ML Utilities")

    st.write(
        "This section is reserved for the future "
        "machine-learning layer of the system."
    )

    st.subheader(
        "Possible future features"
    )

    st.markdown("""
    - Sales forecasting
    - Demand prediction
    - Stock requirement prediction
    - Fast-moving product analysis
    - Slow-moving product analysis
    - School-level demand patterns
    - Seasonal uniform demand
    """)

    sales = fetch_all("""
        SELECT
            DATE(sale_date) AS sale_day,
            SUM(total_amount) AS revenue
        FROM sales
        GROUP BY DATE(sale_date)
        ORDER BY sale_day
    """)

    if not sales.empty:

        st.subheader(
            "Current Sales Data"
        )

        st.dataframe(
            sales,
            use_container_width=True,
            hide_index=True
        )
