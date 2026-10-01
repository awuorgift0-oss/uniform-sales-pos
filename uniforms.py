import streamlit as st
import psycopg2
import pandas as pd
import yaml
from yaml.loader import SafeLoader
from datetime import datetime
import streamlit.components.v1 as components

# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Uniform Sales POS",
    page_icon="🧥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================================================
# DATABASE
# =========================================================

DB_CONFIG = {
    "host": "127.0.0.1",
    "database": "uniforms_sales",
    "user": "postgres",
    "password": "Admin12",
    "port": 5432
}


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


# =========================================================
# DATABASE SETUP
# =========================================================

def setup_database():

    conn = get_connection()
    cursor = conn.cursor()

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

    cursor.execute("""
        ALTER TABLE sale_items
        ADD COLUMN IF NOT EXISTS issued BOOLEAN DEFAULT TRUE
    """)

    conn.commit()
    cursor.close()
    conn.close()


setup_database()


# =========================================================
# AUTHENTICATION
# =========================================================

try:

    with open(
        "config.yaml",
        "r",
        encoding="utf-8"
    ) as file:

        config = yaml.load(
            file,
            Loader=SafeLoader
        )

    import streamlit_authenticator as stauth

    authenticator = stauth.Authenticate(
        config["credentials"],
        config["cookie"]["name"],
        config["cookie"]["key"],
        config["cookie"]["expiry_days"]
    )

    authenticator.login(
        location="main",
        fields={
            "Form name": "Uniform Sales POS",
            "Username": "Username",
            "Password": "Password",
            "Login": "Sign in"
        }
    )

    authentication_status = st.session_state.get(
        "authentication_status"
    )

except Exception as e:

    st.error("Authentication could not be loaded.")
    st.code(str(e))
    st.stop()


if authentication_status is False:

    st.error(
        "Incorrect username or password."
    )
    st.stop()


if authentication_status is None:

    st.info(
        "Please sign in to continue."
    )
    st.stop()


# =========================================================
# USER
# =========================================================

username = st.session_state.get(
    "username",
    ""
)

user_name = st.session_state.get(
    "name",
    "User"
)

user_role = "cashier"

try:

    user_data = config[
        "credentials"
    ][
        "usernames"
    ].get(
        username,
        {}
    )

    roles = user_data.get(
        "roles",
        []
    )

    if "admin" in roles:
        user_role = "admin"

except Exception:
    pass


# =========================================================
# LOGOUT
# =========================================================

try:

    authenticator.logout(
        "Logout",
        location="sidebar"
    )

except Exception:
    pass


# =========================================================
# SESSION STATE
# =========================================================

if "cart" not in st.session_state:
    st.session_state.cart = []

if "last_sale_id" not in st.session_state:
    st.session_state.last_sale_id = None


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def money(value):

    return f"KSh {float(value):,.2f}"


def get_schools():

    conn = get_connection()

    df = pd.read_sql(
        """
        SELECT
            school_id,
            school_name
        FROM schools
        ORDER BY school_name
        """,
        conn
    )

    conn.close()

    return df


def get_products():

    conn = get_connection()

    df = pd.read_sql(
        """
        SELECT
            product_id,
            product_name,
            price
        FROM products
        ORDER BY product_name
        """,
        conn
    )

    conn.close()

    return df


def get_categories(school_id):

    conn = get_connection()

    df = pd.read_sql(
        """
        SELECT DISTINCT
            category_name
        FROM school_product_prices
        WHERE school_id = %s
        ORDER BY category_name
        """,
        conn,
        params=(school_id,)
    )

    conn.close()

    if df.empty:

        return ["Primary"]

    return df[
        "category_name"
    ].tolist()


def get_school_products(
    school_id,
    category
):

    conn = get_connection()

    df = pd.read_sql(
        """
        SELECT
            spp.product_id,
            p.product_name,
            spp.price
        FROM school_product_prices spp

        JOIN products p
            ON p.product_id = spp.product_id

        WHERE spp.school_id = %s
          AND spp.category_name = %s

        ORDER BY p.product_name
        """,
        conn,
        params=(
            school_id,
            category
        )
    )

    conn.close()

    return df


def calculate_total():

    total = 0

    for item in st.session_state.cart:

        total += (
            item["quantity"]
            * item["unit_price"]
        )

    return total


def clear_cart():

    st.session_state.cart = []


# =========================================================
# CUSTOM THEME
# =========================================================

st.markdown(
    """
    <style>

    /* Main background */
    .stApp {
        background-color: #EEF4F8;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #173B5E;
    }

    section[data-testid="stSidebar"] * {
        color: white;
    }

    /* Main headings */
    h1, h2, h3 {
        color: #173B5E;
    }

    /* Buttons */
    .stButton > button {
        background-color: #F28C28;
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
    }

    .stButton > button:hover {
        background-color: #D97415;
        color: white;
    }

    /* Metrics */
    div[data-testid="stMetric"] {
        background-color: white;
        border-radius: 12px;
        padding: 15px;
        border-left: 5px solid #F28C28;
    }

    /* Inputs */
    div[data-baseweb="input"],
    div[data-baseweb="select"] {
        border-radius: 8px;
    }

    /* Dataframes */
    div[data-testid="stDataFrame"] {
        border-radius: 10px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.title("UNIFORM SALES")

    st.caption(
        "Point of Sale System"
    )

    st.divider()

    st.write(
        f"👤 **{user_name}**"
    )

    st.write(
        f"Role: **{user_role.title()}**"
    )

    st.divider()

    if user_role == "admin":

        selected_page = st.radio(
            "MENU",
            [
                "New Sale",
                "Price Management",
                "Stock Management",
                "Sales Overview",
                "Sales History",
                "ML Utilities"
            ]
        )

    else:

        selected_page = st.radio(
            "MENU",
            [
                "New Sale",
                "Sales History"
            ]
        )

    st.divider()

    st.caption(
        "Uniform Sales POS"
    )


# =========================================================
# NEW SALE
# =========================================================

if selected_page == "New Sale":

    st.title("New Sale")

    st.caption(
        "Create a uniform sale and print the customer's receipt."
    )

    # -----------------------------------------------------
    # SCHOOL
    # -----------------------------------------------------

    schools = get_schools()

    if schools.empty:

        st.error(
            "No schools have been configured."
        )

        st.stop()

    school_names = schools[
        "school_name"
    ].tolist()

    selected_school = st.selectbox(
        "School",
        school_names
    )

    school_id = int(
        schools.loc[
            schools["school_name"]
            == selected_school,
            "school_id"
        ].iloc[0]
    )

    # -----------------------------------------------------
    # CATEGORY
    # -----------------------------------------------------

    categories = get_categories(
        school_id
    )

    selected_category = st.selectbox(
        "Category",
        categories
    )

    # -----------------------------------------------------
    # CUSTOMER
    # -----------------------------------------------------

    st.subheader(
        "Customer Information"
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

    # -----------------------------------------------------
    # PRODUCT
    # -----------------------------------------------------

    st.subheader(
        "Add Uniform Item"
    )

    products = get_school_products(
        school_id,
        selected_category
    )

    if products.empty:

        st.warning(
            "No products have been configured "
            "for this school and category."
        )

    else:

        product_names = products[
            "product_name"
        ].tolist()

        col1, col2, col3 = st.columns(
            [3, 1, 1]
        )

        with col1:

            selected_product_name = st.selectbox(
                "Product",
                product_names
            )

        selected_product = products[
            products["product_name"]
            == selected_product_name
        ].iloc[0]

        product_id = int(
            selected_product["product_id"]
        )

        unit_price = float(
            selected_product["price"]
        )

        with col2:

            quantity = st.number_input(
                "Quantity",
                min_value=1,
                max_value=100,
                value=1,
                step=1
            )

        with col3:

            st.write("Unit Price")

            st.write(
                money(unit_price)
            )

        issued = st.checkbox(
            "Item available / issued",
            value=True
        )

        if st.button(
            "Add Item",
            type="primary",
            use_container_width=True
        ):

            found = False

            for item in st.session_state.cart:

                if (
                    item["product_id"]
                    == product_id
                    and item["issued"]
                    == issued
                ):

                    item["quantity"] += quantity

                    found = True

                    break

            if not found:

                st.session_state.cart.append(
                    {
                        "product_id":
                            product_id,

                        "product_name":
                            selected_product_name,

                        "quantity":
                            quantity,

                        "unit_price":
                            unit_price,

                        "issued":
                            issued
                    }
                )

            st.success(
                "Item added to sale."
            )

    # -----------------------------------------------------
    # CART
    # -----------------------------------------------------

    st.subheader(
        "Current Sale"
    )

    if st.session_state.cart:

        rows = []

        for index, item in enumerate(
            st.session_state.cart
        ):

            line_total = (
                item["quantity"]
                * item["unit_price"]
            )

            status = (
                "ISSUED"
                if item["issued"]
                else "NOT ISSUED"
            )

            rows.append(
                {
                    "Item":
                        item["product_name"],

                    "Qty":
                        item["quantity"],

                    "Unit Price":
                        money(
                            item["unit_price"]
                        ),

                    "Total":
                        money(
                            line_total
                        ),

                    "Status":
                        status
                }
            )

        cart_df = pd.DataFrame(
            rows
        )

        st.dataframe(
            cart_df,
            use_container_width=True,
            hide_index=True
        )

        total = calculate_total()

        st.divider()

        col1, col2, col3 = st.columns(3)

        with col1:

            st.metric(
                "Items",
                len(
                    st.session_state.cart
                )
            )

        with col2:

            total_quantity = sum(
                item["quantity"]
                for item
                in st.session_state.cart
            )

            st.metric(
                "Quantity",
                total_quantity
            )

        with col3:

            st.metric(
                "TOTAL SALE",
                money(total)
            )

        # -------------------------------------------------
        # PAYMENT
        # -------------------------------------------------

        st.subheader(
            "Payment"
        )

        payment_method = st.selectbox(
            "Payment Method",
            [
                "Cash",
                "M-Pesa",
                "Bank",
                "Card"
            ]
        )

        col1, col2 = st.columns(2)

        with col1:

            complete_sale = st.button(
                "Complete Sale",
                type="primary",
                use_container_width=True
            )

        with col2:

            clear_sale = st.button(
                "Clear Sale",
                use_container_width=True
            )

        if clear_sale:

            clear_cart()

            st.rerun()

        # -------------------------------------------------
        # COMPLETE SALE
        # -------------------------------------------------

        if complete_sale:

            if not customer_name.strip():

                st.error(
                    "Please enter the customer/student name."
                )

            else:

                conn = get_connection()

                cursor = conn.cursor()

                try:

                    # CUSTOMER
                    cursor.execute(
                        """
                        INSERT INTO customers
                        (
                            customer_name,
                            phone
                        )
                        VALUES
                        (%s, %s)

                        RETURNING customer_id
                        """,
                        (
                            customer_name.strip(),
                            phone.strip()
                        )
                    )

                    customer_id = (
                        cursor.fetchone()[0]
                    )

                    # SALE
                    cursor.execute(
                        """
                        INSERT INTO sales
                        (
                            school_id,
                            customer_id,
                            total_amount,
                            payment_method,
                            payment_status
                        )
                        VALUES
                        (%s, %s, %s, %s, %s)

                        RETURNING sale_id
                        """,
                        (
                            school_id,
                            customer_id,
                            total,
                            payment_method,
                            "Paid"
                        )
                    )

                    sale_id = (
                        cursor.fetchone()[0]
                    )

                    # SALE ITEMS
                    for item in st.session_state.cart:

                        line_total = (
                            item["quantity"]
                            * item["unit_price"]
                        )

                        cursor.execute(
                            """
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
                            (
                                %s,
                                %s,
                                %s,
                                %s,
                                %s,
                                %s
                            )
                            """,
                            (
                                sale_id,
                                item["product_id"],
                                item["quantity"],
                                item["unit_price"],
                                line_total,
                                item["issued"]
                            )
                        )

                    conn.commit()

                    # SAVE RECEIPT DATA
                    st.session_state.last_sale_id = sale_id

                    st.session_state.last_sale = {
                        "sale_id":
                            sale_id,

                        "school":
                            selected_school,

                        "category":
                            selected_category,

                        "customer":
                            customer_name,

                        "phone":
                            phone,

                        "class":
                            class_name,

                        "payment":
                            payment_method,

                        "total":
                            total,

                        "date":
                            datetime.now(),

                        "items":
                            st.session_state.cart.copy()
                    }

                    clear_cart()

                    st.success(
                        f"Sale #{sale_id} completed successfully."
                    )

                except Exception as e:

                    conn.rollback()

                    st.error(
                        f"Sale could not be completed: {e}"
                    )

                finally:

                    cursor.close()
                    conn.close()

    else:

        st.info(
            "Add items to the sale to continue."
        )

    # =====================================================
    # PRINT RECEIPT
    # =====================================================

    if (
        "last_sale"
        in st.session_state
    ):

        sale = st.session_state.last_sale

        st.divider()

        st.subheader(
            f"Receipt #{sale['sale_id']}"
        )

        st.success(
            "Sale completed. Your receipt is ready to print."
        )

        # ---------------------------------------------
        # RECEIPT HTML
        # ---------------------------------------------

        receipt_rows = ""

        for item in sale["items"]:

            line_total = (
                item["quantity"]
                * item["unit_price"]
            )

            status = (
                "ISSUED"
                if item["issued"]
                else "NOT ISSUED"
            )

            receipt_rows += f"""
            <tr>
                <td>{item["product_name"]}</td>
                <td>{item["quantity"]}</td>
                <td>KSh {item["unit_price"]:,.2f}</td>
                <td>KSh {line_total:,.2f}</td>
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
            margin: 0;
            padding: 25px;
            color: #173B5E;
            background: white;
        }}

        .receipt {{
            max-width: 750px;
            margin: auto;
            border: 1px solid #D9E2EA;
            padding: 30px;
        }}

        .header {{
            text-align: center;
            border-bottom: 4px solid #F28C28;
            padding-bottom: 15px;
            margin-bottom: 20px;
        }}

        .header h1 {{
            margin: 0;
            color: #173B5E;
        }}

        .header p {{
            margin: 5px;
            color: #666;
        }}

        .details {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            margin-bottom: 20px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}

        th {{
            background: #173B5E;
            color: white;
            padding: 10px;
            text-align: left;
        }}

        td {{
            padding: 9px;
            border-bottom: 1px solid #ddd;
        }}

        .total {{
            margin-top: 20px;
            text-align: right;
            font-size: 22px;
            font-weight: bold;
            color: #F28C28;
        }}

        .payment {{
            margin-top: 10px;
            text-align: right;
            font-weight: bold;
        }}

        .legend {{
            margin-top: 25px;
            padding: 12px;
            background: #EEF4F8;
            font-size: 13px;
        }}

        .footer {{
            text-align: center;
            margin-top: 25px;
            color: #777;
        }}

        .print-button {{
            background: #F28C28;
            color: white;
            border: none;
            padding: 12px 25px;
            border-radius: 6px;
            font-size: 16px;
            cursor: pointer;
            margin-bottom: 20px;
        }}

        @media print {{

            .print-button {{
                display: none;
            }}

            body {{
                padding: 0;
            }}

            .receipt {{
                border: none;
            }}

        }}

        </style>

        </head>

        <body>

        <div class="receipt">

            <button
                class="print-button"
                onclick="window.print()"
            >
                PRINT RECEIPT
            </button>

            <div class="header">

                <h1>
                    {sale["school"]}
                </h1>

                <p>
                    UNIFORM SALES RECEIPT
                </p>

            </div>

            <div class="details">

                <div>
                    <strong>Receipt No:</strong>
                    {sale["sale_id"]}
                </div>

                <div>
                    <strong>Date:</strong>
                    {sale["date"].strftime("%d/%m/%Y %H:%M")}
                </div>

                <div>
                    <strong>Customer:</strong>
                    {sale["customer"]}
                </div>

                <div>
                    <strong>Phone:</strong>
                    {sale["phone"]}
                </div>

                <div>
                    <strong>Class:</strong>
                    {sale["class"]}
                </div>

                <div>
                    <strong>Category:</strong>
                    {sale["category"]}
                </div>

            </div>

            <table>

                <thead>

                    <tr>
                        <th>Item</th>
                        <th>Qty</th>
                        <th>Unit Price</th>
                        <th>Total</th>
                        <th>Status</th>
                    </tr>

                </thead>

                <tbody>

                    {receipt_rows}

                </tbody>

            </table>

            <div class="total">

                TOTAL PAID:
                KSh {sale["total"]:,.2f}

            </div>

            <div class="payment">

                Payment:
                {sale["payment"]}

            </div>

            <div class="legend">

                <strong>ISSUED</strong>
                = Item given to customer

                <br>

                <strong>NOT ISSUED</strong>
                = Item pending / unavailable

            </div>

            <div class="footer">

                Thank you for your business.

            </div>

        </div>

        </body>

        </html>
        """

        components.html(
            receipt_html,
            height=750,
            scrolling=True
        )


# =========================================================
# PRICE MANAGEMENT
# =========================================================

elif selected_page == "Price Management":

    st.title("Price Management")

    st.caption(
        "Manage prices for every school and category."
    )

    schools = get_schools()

    school_name = st.selectbox(
        "School",
        schools["school_name"].tolist()
    )

    school_id = int(
        schools.loc[
            schools["school_name"]
            == school_name,
            "school_id"
        ].iloc[0]
    )

    categories = get_categories(
        school_id
    )

    category = st.selectbox(
        "Category",
        categories
    )

    prices = get_school_products(
        school_id,
        category
    )

    if prices.empty:

        st.warning(
            "No products configured."
        )

    else:

        st.subheader(
            f"{school_name} — {category}"
        )

        for _, row in prices.iterrows():

            product_id = int(
                row["product_id"]
            )

            current_price = float(
                row["price"]
            )

            col1, col2 = st.columns(
                [3, 1]
            )

            with col1:

                st.write(
                    f"**{row['product_name']}**"
                )

            with col2:

                new_price = st.number_input(
                    "Price",
                    min_value=0.0,
                    value=current_price,
                    step=50.0,
                    key=(
                        f"price_"
                        f"{school_id}_"
                        f"{category}_"
                        f"{product_id}"
                    )
                )

                if st.button(
                    "Save",
                    key=(
                        f"save_"
                        f"{school_id}_"
                        f"{category}_"
                        f"{product_id}"
                    )
                ):

                    conn = get_connection()

                    cursor = conn.cursor()

                    cursor.execute(
                        """
                        UPDATE
                            school_product_prices
                        SET price = %s
                        WHERE school_id = %s
                          AND category_name = %s
                          AND product_id = %s
                        """,
                        (
                            new_price,
                            school_id,
                            category,
                            product_id
                        )
                    )

                    conn.commit()

                    cursor.close()
                    conn.close()

                    st.success(
                        "Price updated."
                    )

    # -----------------------------------------------------
    # CREATE PRODUCT
    # -----------------------------------------------------

    st.divider()

    st.subheader(
        "Create New Product"
    )

    new_product = st.text_input(
        "Product Name"
    )

    new_price = st.number_input(
        "Starting Price",
        min_value=0.0,
        step=50.0
    )

    if st.button(
        "Create Product",
        type="primary"
    ):

        if not new_product.strip():

            st.error(
                "Enter a product name."
            )

        else:

            conn = get_connection()

            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT product_id
                FROM products
                WHERE LOWER(product_name)
                    = LOWER(%s)
                LIMIT 1
                """,
                (
                    new_product.strip(),
                )
            )

            existing = cursor.fetchone()

            if existing:

                st.error(
                    "That product already exists."
                )

            else:

                cursor.execute(
                    """
                    INSERT INTO products
                    (
                        product_name,
                        price
                    )
                    VALUES
                    (%s, %s)

                    RETURNING product_id
                    """,
                    (
                        new_product.strip(),
                        new_price
                    )
                )

                product_id = (
                    cursor.fetchone()[0]
                )

                cursor.execute(
                    """
                    INSERT INTO
                        school_product_prices
                    (
                        school_id,
                        category_name,
                        product_id,
                        price
                    )
                    VALUES
                    (%s, %s, %s, %s)
                    """,
                    (
                        school_id,
                        category,
                        product_id,
                        new_price
                    )
                )

                conn.commit()

                st.success(
                    "Product created."
                )

            cursor.close()
            conn.close()


# =========================================================
# STOCK MANAGEMENT
# =========================================================

elif selected_page == "Stock Management":

    st.title("Stock Management")

    st.caption(
        "Monitor sold and pending uniform items."
    )

    conn = get_connection()

    stock_df = pd.read_sql(
        """
        SELECT
            p.product_name AS "Product",

            COALESCE(
                SUM(si.quantity),
                0
            ) AS "Units Sold",

            COALESCE(
                SUM(
                    CASE
                        WHEN si.issued = FALSE
                        THEN si.quantity
                        ELSE 0
                    END
                ),
                0
            ) AS "Pending"

        FROM products p

        LEFT JOIN sale_items si
            ON p.product_id = si.product_id

        GROUP BY
            p.product_id,
            p.product_name

        ORDER BY
            p.product_name
        """,
        conn
    )

    conn.close()

    st.dataframe(
        stock_df,
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    st.subheader(
        "Pending Items"
    )

    conn = get_connection()

    pending_df = pd.read_sql(
        """
        SELECT
            s.sale_id AS "Sale",
            s.sale_date AS "Date",
            c.customer_name AS "Customer",
            p.product_name AS "Item",
            si.quantity AS "Quantity"

        FROM sale_items si

        JOIN sales s
            ON s.sale_id = si.sale_id

        JOIN products p
            ON p.product_id = si.product_id

        LEFT JOIN customers c
            ON c.customer_id = s.customer_id

        WHERE si.issued = FALSE

        ORDER BY
            s.sale_date DESC
        """,
        conn
    )

    conn.close()

    if pending_df.empty:

        st.success(
            "There are no pending items."
        )

    else:

        st.dataframe(
            pending_df,
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# SALES OVERVIEW
# =========================================================

elif selected_page == "Sales Overview":

    st.title("Sales Overview")

    st.caption(
        "Monitor sales performance."
    )

    conn = get_connection()

    summary = pd.read_sql(
        """
        SELECT
            COUNT(*) AS total_sales,
            COALESCE(
                SUM(total_amount),
                0
            ) AS total_revenue,
            COALESCE(
                AVG(total_amount),
                0
            ) AS average_sale
        FROM sales
        """,
        conn
    )

    conn.close()

    total_sales = int(
        summary.iloc[0]["total_sales"]
    )

    total_revenue = float(
        summary.iloc[0]["total_revenue"]
    )

    average_sale = float(
        summary.iloc[0]["average_sale"]
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "Total Sales",
            total_sales
        )

    with col2:

        st.metric(
            "Total Revenue",
            money(total_revenue)
        )

    with col3:

        st.metric(
            "Average Sale",
            money(average_sale)
        )

    st.divider()

    conn = get_connection()

    daily_sales = pd.read_sql(
        """
        SELECT
            DATE(sale_date) AS sale_date,
            COUNT(*) AS sales,
            SUM(total_amount) AS revenue

        FROM sales

        GROUP BY
            DATE(sale_date)

        ORDER BY
            sale_date
        """,
        conn
    )

    conn.close()

    if not daily_sales.empty:

        st.subheader(
            "Revenue Trend"
        )

        st.line_chart(
            daily_sales.set_index(
                "sale_date"
            )["revenue"]
        )

        st.subheader(
            "Daily Sales"
        )

        st.dataframe(
            daily_sales,
            use_container_width=True,
            hide_index=True
        )

    # -----------------------------------------------------
    # SCHOOL PERFORMANCE
    # -----------------------------------------------------

    conn = get_connection()

    school_sales = pd.read_sql(
        """
        SELECT
            sc.school_name AS "School",
            COUNT(s.sale_id) AS "Sales",
            SUM(s.total_amount) AS "Revenue"

        FROM sales s

        JOIN schools sc
            ON sc.school_id = s.school_id

        GROUP BY
            sc.school_name

        ORDER BY
            "Revenue" DESC
        """,
        conn
    )

    conn.close()

    st.subheader(
        "Sales by School"
    )

    st.dataframe(
        school_sales,
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# SALES HISTORY
# =========================================================

elif selected_page == "Sales History":

    st.title("Sales History")

    st.caption(
        "Search and review completed sales."
    )

    conn = get_connection()

    history_df = pd.read_sql(
        """
        SELECT
            s.sale_id AS "Sale ID",
            s.sale_date AS "Date",
            sc.school_name AS "School",
            c.customer_name AS "Customer",
            c.phone AS "Phone",
            s.total_amount AS "Amount",
            s.payment_method AS "Payment",
            s.payment_status AS "Status"

        FROM sales s

        JOIN schools sc
            ON sc.school_id = s.school_id

        LEFT JOIN customers c
            ON c.customer_id = s.customer_id

        ORDER BY
            s.sale_date DESC
        """,
        conn
    )

    conn.close()

    if history_df.empty:

        st.info(
            "No sales recorded yet."
        )

    else:

        search = st.text_input(
            "Search customer, school or phone"
        )

        if search.strip():

            mask = (
                history_df
                .astype(str)
                .apply(
                    lambda row:
                    row.str.contains(
                        search,
                        case=False,
                        na=False
                    ).any(),
                    axis=1
                )
            )

            filtered_df = history_df[
                mask
            ]

        else:

            filtered_df = history_df

        st.dataframe(
            filtered_df,
            use_container_width=True,
            hide_index=True
        )

        if not filtered_df.empty:

            selected_sale = st.selectbox(
                "View Sale Details",
                filtered_df["Sale ID"].tolist()
            )

            conn = get_connection()

            details_df = pd.read_sql(
                """
                SELECT
                    p.product_name AS "Item",
                    si.quantity AS "Quantity",
                    si.unit_price AS "Unit Price",
                    si.line_total AS "Total",

                    CASE
                        WHEN si.issued = TRUE
                        THEN 'ISSUED'
                        ELSE 'NOT ISSUED'
                    END AS "Status"

                FROM sale_items si

                JOIN products p
                    ON p.product_id =
                       si.product_id

                WHERE si.sale_id = %s

                ORDER BY
                    p.product_name
                """,
                conn,
                params=(int(selected_sale),)
            )

            conn.close()

            st.subheader(
                f"Sale #{selected_sale}"
            )

            st.dataframe(
                details_df,
                use_container_width=True,
                hide_index=True
            )


# =========================================================
# ML UTILITIES
# =========================================================

elif selected_page == "ML Utilities":

    st.title("ML Utilities")

    st.caption(
        "Prepare sales data for future forecasting "
        "and machine learning."
    )

    conn = get_connection()

    ml_df = pd.read_sql(
        """
        SELECT
            DATE(s.sale_date) AS sale_date,
            sc.school_name AS school,
            p.product_name AS product,
            SUM(si.quantity) AS quantity_sold,
            SUM(si.line_total) AS revenue

        FROM sale_items si

        JOIN sales s
            ON s.sale_id = si.sale_id

        JOIN schools sc
            ON sc.school_id = s.school_id

        JOIN products p
            ON p.product_id = si.product_id

        GROUP BY
            DATE(s.sale_date),
            sc.school_name,
            p.product_name

        ORDER BY
            sale_date
        """,
        conn
    )

    conn.close()

    if ml_df.empty:

        st.info(
            "Not enough sales data yet."
        )

    else:

        st.metric(
            "Training Records",
            len(ml_df)
        )

        st.dataframe(
            ml_df,
            use_container_width=True,
            hide_index=True
        )

        st.subheader(
            "Revenue Trend"
        )

        daily_ml = (
            ml_df
            .groupby("sale_date")
            ["revenue"]
            .sum()
        )

        st.line_chart(
            daily_ml
        )

        st.download_button(
            "Download ML Dataset",
            data=ml_df.to_csv(
                index=False
            ),
            file_name=(
                "uniform_sales_ml_dataset.csv"
            ),
            mime="text/csv",
            use_container_width=True
        )