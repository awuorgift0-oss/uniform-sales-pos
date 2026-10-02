import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Uniform Sales POS",
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

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden;}
    [data-testid="stDecoration"] {visibility: hidden;}
</style>
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

        st.error(
            f"Database connection failed: {e}"
        )

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

        # ====================================================
        # SCHOOLS
        # ====================================================

        cur.execute("""
            CREATE TABLE IF NOT EXISTS schools (
                school_id SERIAL PRIMARY KEY,
                school_name VARCHAR(100) NOT NULL UNIQUE
            );
        """)

        # ====================================================
        # PRODUCTS
        # ====================================================

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

        # ====================================================
        # CUSTOMERS
        # ====================================================

        cur.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                customer_id SERIAL PRIMARY KEY,
                customer_name VARCHAR(100) NOT NULL,
                phone VARCHAR(20)
            );
        """)

        # ====================================================
        # SALES
        # ====================================================

        cur.execute("""
            CREATE TABLE IF NOT EXISTS sales (
                sale_id SERIAL PRIMARY KEY,
                sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                school_id INT NOT NULL REFERENCES schools(school_id),
                customer_id INT REFERENCES customers(customer_id),
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

        # ====================================================
        # SALE ITEMS
        # ====================================================

        cur.execute("""
            CREATE TABLE IF NOT EXISTS sale_items (
                sale_item_id SERIAL PRIMARY KEY,
                sale_id INT NOT NULL REFERENCES sales(sale_id),
                product_id INT NOT NULL REFERENCES products(product_id),
                quantity INT NOT NULL,
                unit_price NUMERIC(10,2) NOT NULL,
                line_total NUMERIC(10,2) NOT NULL
            );
        """)

        cur.execute("""
            ALTER TABLE sale_items
            ADD COLUMN IF NOT EXISTS issued BOOLEAN DEFAULT TRUE;
        """)

        # ====================================================
        # SCHOOL PRODUCT PRICES
        # ====================================================

        cur.execute("""
            CREATE TABLE IF NOT EXISTS school_product_prices (
                school_product_price_id SERIAL PRIMARY KEY,
                school_id INT NOT NULL REFERENCES schools(school_id),
                category_name VARCHAR(100) NOT NULL,
                product_id INT NOT NULL REFERENCES products(product_id),
                price NUMERIC(10,2) NOT NULL DEFAULT 0,
                UNIQUE (
                    school_id,
                    category_name,
                    product_id
                )
            );
        """)

        # ====================================================
        # STOCK
        # ====================================================

        cur.execute("""
            CREATE TABLE IF NOT EXISTS stock (
                stock_id SERIAL PRIMARY KEY,
                school_id INT NOT NULL REFERENCES schools(school_id),
                product_id INT NOT NULL REFERENCES products(product_id),
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

        # ====================================================
        # UNIFORM SETS
        # ====================================================

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
                set_id INT NOT NULL REFERENCES uniform_sets(set_id),
                product_id INT NOT NULL REFERENCES products(product_id),
                quantity INT NOT NULL
            );
        """)

        # ====================================================
        # INVESTORS
        # ====================================================

        cur.execute("""
            CREATE TABLE IF NOT EXISTS investors (
                investor_id SERIAL PRIMARY KEY,
                investor_name VARCHAR(100) NOT NULL UNIQUE,
                active BOOLEAN DEFAULT TRUE
            );
        """)

        # ====================================================
        # FINANCIAL TRANSACTIONS
        # ====================================================

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

        # ====================================================
        # TAILOR PRODUCTION
        # ====================================================

        cur.execute("""
            CREATE TABLE IF NOT EXISTS tailor_production (
                production_id SERIAL PRIMARY KEY,
                school_id INT NOT NULL REFERENCES schools(school_id),
                product_id INT NOT NULL REFERENCES products(product_id),
                tailor_name VARCHAR(100) NOT NULL,
                quantity_produced INT NOT NULL,
                cost_per_item NUMERIC(10,2) NOT NULL,
                amount_paid NUMERIC(12,2) NOT NULL,
                production_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                term VARCHAR(20),
                year INT,
                notes VARCHAR(255)
            );
        """)

        # ====================================================
        # SEED SCHOOLS
        # ====================================================

        schools = [
            "LOVING BLOOMS SCHOOL",
            "WARIDI UTAWALA SCHOOL"
        ]

        for school in schools:

            cur.execute("""
                INSERT INTO schools (
                    school_name
                )
                VALUES (%s)
                ON CONFLICT (school_name)
                DO NOTHING;
            """, (school,))

        # ====================================================
        # SEED PRODUCTS
        # ====================================================

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
                VALUES (
                    %s,
                    %s,
                    0
                )
                ON CONFLICT (product_name)
                DO NOTHING;
            """, (
                product_name,
                price
            ))

        # ====================================================
        # INVESTORS
        # ONLY GIFT AND KEN
        # ====================================================

        cur.execute("""
            INSERT INTO investors (
                investor_name,
                active
            )
            VALUES (
                'Gift',
                TRUE
            )
            ON CONFLICT (investor_name)
            DO UPDATE SET
                active = TRUE;
        """)

        cur.execute("""
            INSERT INTO investors (
                investor_name,
                active
            )
            VALUES (
                'Ken',
                TRUE
            )
            ON CONFLICT (investor_name)
            DO UPDATE SET
                active = TRUE;
        """)

        cur.execute("""
            UPDATE investors
            SET active = FALSE
            WHERE investor_name NOT IN (
                'Gift',
                'Ken'
            );
        """)

        # ====================================================
        # NOTE:
        # Initial capital seeding (Gift 150,000 and Ken 100,000)
        # has been REMOVED so real contributions can be entered
        # via "Edit Data" -> "Capital / Transactions" or via
        # "Business Finance" -> "Record Additional Investment".
        # ====================================================

        conn.commit()

    except Exception as e:

        conn.rollback()

        st.error(
            f"Database setup error: {e}"
        )

    finally:

        cur.close()
        conn.close()


@st.cache_resource
def _setup_once():
    setup_database()
    return True


_setup_once()


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

def fetch_dataframe(
    query,
    params=None
):

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

        st.error(
            f"Database error: {e}"
        )

        return pd.DataFrame()

    finally:

        conn.close()


def execute_query(
    query,
    params=None,
    fetch=False
):

    conn = get_connection()

    if conn is None:
        return None

    cur = conn.cursor()

    try:

        cur.execute(
            query,
            params or ()
        )

        result = (
            cur.fetchall()
            if fetch
            else None
        )

        conn.commit()

        return result

    except Exception as e:

        conn.rollback()

        st.error(
            f"Database error: {e}"
        )

        return None

    finally:

        cur.close()
        conn.close()


def money(value):

    if value is None:
        value = 0

    return f"KSh {float(value):,.2f}"


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title(
    "🧾 Uniform Sales POS"
)

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
        "Edit Data",
        "ML & Forecasting"
    ]
)


# ============================================================
# NEW SALE
# ============================================================

if page == "New Sale":

    st.title("🧾 New Sale")

    schools_df = fetch_dataframe("""
        SELECT
            school_id,
            school_name
        FROM schools
        ORDER BY school_name;
    """)

    if schools_df.empty:

        st.warning(
            "No schools found."
        )

        st.stop()

    school_name = st.selectbox(
        "School",
        schools_df[
            "school_name"
        ].tolist()
    )

    school_id = int(
        schools_df.loc[
            schools_df["school_name"]
            == school_name,
            "school_id"
        ].iloc[0]
    )

    col1, col2 = st.columns(2)

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

    category = st.selectbox(
        "Category",
        [
            "Primary",
            "Junior Secondary"
        ]
    )

    customer_name = st.text_input(
        "Student / Customer Name"
    )

    phone = st.text_input(
        "Phone Number"
    )

    class_name = st.text_input(
        "Class / Grade"
    )

    products_df = fetch_dataframe("""
        SELECT
            spp.product_id,
            p.product_name,
            spp.price
        FROM school_product_prices spp
        JOIN products p
            ON spp.product_id =
               p.product_id
        WHERE
            spp.school_id = %s
        AND
            spp.category_name = %s
        ORDER BY
            p.product_name;
    """, (
        school_id,
        category
    ))

    if products_df.empty:

        st.warning(
            "No products have been assigned "
            "to this school yet."
        )

    else:

        product_name = st.selectbox(
            "Product",
            products_df[
                "product_name"
            ].tolist()
        )

        selected_product = products_df[
            products_df[
                "product_name"
            ] == product_name
        ].iloc[0]

        product_id = int(
            selected_product[
                "product_id"
            ]
        )

        unit_price = float(
            selected_product["price"]
        )

        st.info(
            f"Current selling price: "
            f"{money(unit_price)}"
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
            "➕ Add to Cart"
        ):

            st.session_state.cart.append({
                "product_id": product_id,
                "product_name": product_name,
                "quantity": quantity,
                "unit_price": unit_price,
                "line_total":
                    quantity * unit_price,
                "issued": issued
            })

            st.success(
                f"{quantity} × "
                f"{product_name} "
                "added to cart."
            )

    if st.session_state.cart:

        st.subheader(
            "🛒 Current Cart"
        )

        cart_df = pd.DataFrame(
            st.session_state.cart
        )

        st.dataframe(
            cart_df[
                [
                    "product_name",
                    "quantity",
                    "unit_price",
                    "line_total"
                ]
            ],
            use_container_width=True
        )

        total = sum(
            item["line_total"]
            for item in st.session_state.cart
        )

        st.metric(
            "Total Sale",
            money(total)
        )

        if st.button(
            "🗑️ Clear Cart"
        ):

            st.session_state.cart = []

            st.rerun()

        payment_method = st.selectbox(
            "Payment Method",
            [
                "Cash",
                "M-Pesa",
                "Bank",
                "Other"
            ]
        )

        if st.button(
            "✅ Complete Sale"
        ):

            if not customer_name.strip():

                st.error(
                    "Please enter the "
                    "student/customer name."
                )

            else:

                conn = get_connection()

                if conn is None:
                    st.stop()

                cur = conn.cursor()

                try:

                    cur.execute("""
                        INSERT INTO customers
                        (
                            customer_name,
                            phone
                        )
                        VALUES
                        (%s, %s)
                        RETURNING customer_id;
                    """, (
                        customer_name,
                        phone
                    ))

                    customer_id = (
                        cur.fetchone()[0]
                    )

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
                        (
                            %s,
                            %s,
                            %s,
                            %s,
                            'Paid',
                            %s,
                            %s
                        )
                        RETURNING
                            sale_id,
                            sale_date;
                    """, (
                        school_id,
                        customer_id,
                        total,
                        payment_method,
                        term,
                        year
                    ))

                    sale_id, sale_date = (
                        cur.fetchone()
                    )

                    for item in (
                        st.session_state.cart
                    ):

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
                            (
                                %s,
                                %s,
                                %s,
                                %s,
                                %s,
                                %s
                            );
                        """, (
                            sale_id,
                            item["product_id"],
                            item["quantity"],
                            item["unit_price"],
                            item["line_total"],
                            item["issued"]
                        ))

                    cur.execute("""
                        INSERT INTO
                            financial_transactions
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
                        f"Sale #{sale_id} - "
                        f"{school_name}",
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
                        "class": class_name,
                        "term": term,
                        "year": year,
                        "payment_method":
                            payment_method,
                        "items": list(
                            st.session_state.cart
                        ),
                        "total": total
                    }

                    st.session_state.cart = []

                    st.success(
                        f"Sale #{sale_id} "
                        "completed successfully."
                    )

                except Exception as e:

                    conn.rollback()

                    st.error(
                        f"Could not complete sale: {e}"
                    )

                finally:

                    cur.close()
                    conn.close()

    if st.session_state.last_receipt:

        receipt = (
            st.session_state.last_receipt
        )

        st.divider()

        st.subheader(
            "🧾 Printable Receipt"
        )

        receipt_items = ""

        for item in receipt["items"]:

            receipt_items += f"""
                <tr>
                    <td>
                        {item['product_name']}
                    </td>
                    <td>
                        {item['quantity']}
                    </td>
                    <td>
                        KSh {item['unit_price']:,.2f}
                    </td>
                    <td>
                        KSh {item['line_total']:,.2f}
                    </td>
                </tr>
            """

        receipt_html = f"""
        <html>
        <head>

        <style>

        body {{
            font-family: Arial, sans-serif;
            padding: 25px;
        }}

        .receipt {{
            max-width: 700px;
            margin: auto;
            border: 1px solid #ddd;
            padding: 25px;
        }}

        h1, h2 {{
            text-align: center;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}

        th, td {{
            border-bottom: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}

        .total {{
            font-size: 20px;
            font-weight: bold;
            text-align: right;
            margin-top: 20px;
        }}

        .center {{
            text-align: center;
        }}

        </style>

        </head>

        <body>

        <div class="receipt">

            <h1>
                {receipt['school']}
            </h1>

            <h2>
                UNIFORM SALES RECEIPT
            </h2>

            <p>

                <strong>
                    Receipt No:
                </strong>
                {receipt['sale_id']}
                <br>

                <strong>
                    Date:
                </strong>
                {receipt['sale_date']}
                <br>

                <strong>
                    Student:
                </strong>
                {receipt['customer']}
                <br>

                <strong>
                    Phone:
                </strong>
                {receipt['phone']}
                <br>

                <strong>
                    Class:
                </strong>
                {receipt['class']}
                <br>

                <strong>
                    Term:
                </strong>
                {receipt['term']}
                <br>

                <strong>
                    Year:
                </strong>
                {receipt['year']}
                <br>

                <strong>
                    Payment:
                </strong>
                {receipt['payment_method']}

            </p>

            <table>

                <tr>
                    <th>Item</th>
                    <th>Qty</th>
                    <th>Unit Price</th>
                    <th>Total</th>
                </tr>

                {receipt_items}

            </table>

            <div class="total">

                TOTAL:
                KSh {receipt['total']:,.2f}

            </div>

            <p class="center">
                Thank you for your purchase.
            </p>

        </div>

        </body>
        </html>
        """

        components.html(
            receipt_html,
            height=650,
            scrolling=True
        )

        if st.button(
            "🖨️ Print Receipt"
        ):

            escaped_receipt = (
                receipt_html
                .replace("\\", "\\\\")
                .replace("`", "\\`")
                .replace("${", "\\${")
            )

            components.html(
                f"""
                <script>

                const receiptWindow =
                    window.open(
                        '',
                        '_blank'
                    );

                receiptWindow.document.write(`
                    {escaped_receipt}
                `);

                receiptWindow.document.close();

                receiptWindow.focus();

                receiptWindow.print();

                </script>
                """,
                height=100
            )


# ============================================================
# PRICE MANAGEMENT
# ============================================================

elif page == "Price Management":

    st.title(
        "💰 Price Management"
    )

    schools_df = fetch_dataframe("""
        SELECT
            school_id,
            school_name
        FROM schools
        ORDER BY school_name;
    """)

    if schools_df.empty:

        st.warning(
            "No schools found."
        )

        st.stop()

    school_name = st.selectbox(
        "School",
        schools_df[
            "school_name"
        ].tolist()
    )

    school_id = int(
        schools_df.loc[
            schools_df["school_name"]
            == school_name,
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

    st.subheader(
        "Existing Prices"
    )

    prices_df = fetch_dataframe("""
        SELECT
            spp.school_product_price_id,
            p.product_name,
            spp.price
        FROM school_product_prices spp
        JOIN products p
            ON spp.product_id =
               p.product_id
        WHERE
            spp.school_id = %s
        AND
            spp.category_name = %s
        ORDER BY
            p.product_name;
    """, (
        school_id,
        category
    ))

    if not prices_df.empty:

        for _, row in prices_df.iterrows():

            col1, col2, col3 = st.columns(
                [2, 1, 1]
            )

            with col1:

                st.write(
                    row["product_name"]
                )

            with col2:

                new_price = st.number_input(
                    f"Price {row['product_name']}",
                    min_value=0.0,
                    value=float(row["price"]),
                    step=50.0,
                    key=(
                        f"price_"
                        f"{row['school_product_price_id']}"
                    )
                )

            with col3:

                if st.button(
                    "Save",
                    key=(
                        f"save_"
                        f"{row['school_product_price_id']}"
                    )
                ):

                    execute_query("""
                        UPDATE
                            school_product_prices
                        SET price = %s
                        WHERE
                            school_product_price_id = %s;
                    """, (
                        new_price,
                        int(
                            row[
                                "school_product_price_id"
                            ]
                        )
                    ))

                    st.success(
                        "Price updated."
                    )

                    st.rerun()

    else:

        st.info(
            "No products have been assigned "
            "to this school/category."
        )

    st.divider()

    st.subheader(
        "➕ Assign Product"
    )

    all_products = fetch_dataframe("""
        SELECT
            product_id,
            product_name,
            price
        FROM products
        ORDER BY product_name;
    """)

    assigned_ids = []

    if not prices_df.empty:

        assigned_ids = (
            prices_df[
                "product_name"
            ].tolist()
        )

    available_products = all_products[
        ~all_products[
            "product_name"
        ].isin(assigned_ids)
    ]

    if not available_products.empty:

        selected_product = st.selectbox(
            "Product to Assign",
            available_products[
                "product_name"
            ].tolist()
        )

        product_row = available_products[
            available_products[
                "product_name"
            ] == selected_product
        ].iloc[0]

        assign_price = st.number_input(
            "Selling Price",
            min_value=0.0,
            value=float(
                product_row["price"]
            ),
            step=50.0
        )

        if st.button(
            "Assign Product"
        ):

            execute_query("""
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

                ON CONFLICT
                (
                    school_id,
                    category_name,
                    product_id
                )

                DO UPDATE SET
                    price =
                        EXCLUDED.price;
            """, (
                school_id,
                category,
                int(
                    product_row[
                        "product_id"
                    ]
                ),
                assign_price
            ))

            st.success(
                "Product assigned."
            )

            st.rerun()

    st.divider()

    st.subheader(
        "➕ Create New Product"
    )

    new_product_name = st.text_input(
        "Product Name"
    )

    new_selling_price = st.number_input(
        "Selling Price",
        min_value=0.0,
        step=50.0
    )

    new_cost_price = st.number_input(
        "Cost Price",
        min_value=0.0,
        step=50.0
    )

    if st.button(
        "Create Product"
    ):

        if not new_product_name.strip():

            st.error(
                "Enter a product name."
            )

        else:

            result = execute_query("""
                INSERT INTO products
                (
                    product_name,
                    price,
                    cost_price
                )
                VALUES
                (%s, %s, %s)

                ON CONFLICT (product_name)
                DO UPDATE SET
                    price =
                        EXCLUDED.price,
                    cost_price =
                        EXCLUDED.cost_price

                RETURNING product_id;
            """, (
                new_product_name.strip(),
                new_selling_price,
                new_cost_price
            ), fetch=True)

            if result is not None:

                st.success(
                    f"{new_product_name} is ready."
                )

                st.rerun()


# ============================================================
# STOCK MANAGEMENT
# ============================================================

elif page == "Stock Management":

    st.title(
        "📦 Stock Management"
    )

    schools_df = fetch_dataframe("""
        SELECT
            school_id,
            school_name
        FROM schools
        ORDER BY school_name;
    """)

    if schools_df.empty:
        st.warning("No schools found.")
        st.stop()

    school_name = st.selectbox(
        "School",
        schools_df[
            "school_name"
        ].tolist()
    )

    school_id = int(
        schools_df.loc[
            schools_df["school_name"]
            == school_name,
            "school_id"
        ].iloc[0]
    )

    products_df = fetch_dataframe("""
        SELECT
            product_id,
            product_name
        FROM products
        ORDER BY product_name;
    """)

    if products_df.empty:
        st.warning("No products found.")
        st.stop()

    product_name = st.selectbox(
        "Product",
        products_df[
            "product_name"
        ].tolist()
    )

    product_id = int(
        products_df.loc[
            products_df[
                "product_name"
            ] == product_name,
            "product_id"
        ].iloc[0]
    )

    col1, col2 = st.columns(2)

    with col1:

        quantity = st.number_input(
            "Quantity Brought In",
            min_value=1,
            value=1,
            step=1
        )

    with col2:

        unit_cost = st.number_input(
            "Cost Per Item",
            min_value=0.0,
            step=50.0
        )

    col3, col4 = st.columns(2)

    with col3:

        term = st.selectbox(
            "Term",
            [
                "Term 1",
                "Term 2",
                "Term 3"
            ],
            key="stock_term"
        )

    with col4:

        year = st.number_input(
            "Year",
            min_value=2020,
            max_value=2100,
            value=datetime.now().year,
            key="stock_year"
        )

    if st.button(
        "📦 Add Stock"
    ):

        conn = get_connection()

        if conn is None:
            st.stop()

        cur = conn.cursor()

        try:

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
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                );
            """, (
                school_id,
                product_id,
                quantity,
                term,
                year,
                unit_cost
            ))

            cur.execute("""
                INSERT INTO
                    financial_transactions
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
                f"Stock purchase: "
                f"{quantity} × {product_name}",
                quantity * unit_cost,
                term,
                year
            ))

            conn.commit()

            st.success(
                f"{quantity} units of "
                f"{product_name} added to stock."
            )

        except Exception as e:

            conn.rollback()

            st.error(str(e))

        finally:

            cur.close()
            conn.close()

    st.divider()

    st.subheader(
        "Current Stock"
    )

    stock_df = fetch_dataframe("""
        SELECT
            p.product_name,

            SUM(
                s.quantity_brought
            ) AS brought_in,

            COALESCE(
                (
                    SELECT
                        SUM(si.quantity)
                    FROM sale_items si
                    JOIN sales sa
                        ON si.sale_id =
                           sa.sale_id
                    WHERE
                        si.product_id =
                        p.product_id
                    AND
                        sa.school_id =
                        %s
                    AND
                        si.issued = TRUE
                ),
                0
            ) AS sold,

            SUM(
                s.quantity_brought
            )
            -
            COALESCE(
                (
                    SELECT
                        SUM(si.quantity)
                    FROM sale_items si
                    JOIN sales sa
                        ON si.sale_id =
                           sa.sale_id
                    WHERE
                        si.product_id =
                        p.product_id
                    AND
                        sa.school_id =
                        %s
                    AND
                        si.issued = TRUE
                ),
                0
            ) AS remaining,

            AVG(
                s.unit_cost
            ) AS average_cost

        FROM stock s

        JOIN products p
            ON s.product_id =
               p.product_id

        WHERE
            s.school_id =
            %s

        GROUP BY
            p.product_id,
            p.product_name

        ORDER BY
            p.product_name;
    """, (
        school_id,
        school_id,
        school_id
    ))

    if not stock_df.empty:

        stock_df[
            "remaining_value"
        ] = (
            stock_df["remaining"]
            *
            stock_df["average_cost"]
        )

        st.dataframe(
            stock_df,
            use_container_width=True
        )

        low_stock = stock_df[
            stock_df["remaining"] <= 5
        ]

        if not low_stock.empty:

            st.warning(
                "⚠️ Some products are running low."
            )


# ============================================================
# TAILOR & PRODUCTION
# ============================================================

elif page == "Tailor & Production":

    st.title(
        "🧵 Tailor & Production"
    )

    st.write(
        "Track money given to tailors and "
        "how much of the tailoring cost "
        "has been used through sales."
    )

    schools_df = fetch_dataframe("""
        SELECT
            school_id,
            school_name
        FROM schools
        ORDER BY school_name;
    """)

    if schools_df.empty:
        st.warning("No schools found.")
        st.stop()

    school_name = st.selectbox(
        "School",
        schools_df[
            "school_name"
        ].tolist(),
        key="tailor_school"
    )

    school_id = int(
        schools_df.loc[
            schools_df[
                "school_name"
            ] == school_name,
            "school_id"
        ].iloc[0]
    )

    products_df = fetch_dataframe("""
        SELECT
            product_id,
            product_name
        FROM products
        ORDER BY product_name;
    """)

    if products_df.empty:
        st.warning("No products found.")
        st.stop()

    product_name = st.selectbox(
        "Item Produced",
        products_df[
            "product_name"
        ].tolist()
    )

    product_id = int(
        products_df.loc[
            products_df[
                "product_name"
            ] == product_name,
            "product_id"
        ].iloc[0]
    )

    tailor_name = st.text_input(
        "Tailor Name"
    )

    col1, col2 = st.columns(2)

    with col1:

        quantity_produced = st.number_input(
            "Quantity Produced",
            min_value=1,
            value=1,
            step=1
        )

    with col2:

        cost_per_item = st.number_input(
            "Tailoring Cost Per Item",
            min_value=0.0,
            step=50.0
        )

    total_tailor_payment = (
        quantity_produced
        *
        cost_per_item
    )

    st.metric(
        "Total Given To Tailor",
        money(total_tailor_payment)
    )

    col3, col4 = st.columns(2)

    with col3:

        term = st.selectbox(
            "Term",
            [
                "Term 1",
                "Term 2",
                "Term 3"
            ],
            key="tailor_term"
        )

    with col4:

        year = st.number_input(
            "Year",
            min_value=2020,
            max_value=2100,
            value=datetime.now().year,
            key="tailor_year"
        )

    notes = st.text_area(
        "Notes",
        placeholder=(
            "Optional notes about production"
        )
    )

    if st.button(
        "💰 Record Tailor Payment"
    ):

        if not tailor_name.strip():

            st.error(
                "Enter the tailor's name."
            )

        else:

            conn = get_connection()

            if conn is None:
                st.stop()

            cur = conn.cursor()

            try:

                cur.execute("""
                    INSERT INTO
                        tailor_production
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
                    (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    );
                """, (
                    school_id,
                    product_id,
                    tailor_name,
                    quantity_produced,
                    cost_per_item,
                    total_tailor_payment,
                    term,
                    year,
                    notes
                ))

                cur.execute("""
                    INSERT INTO
                        financial_transactions
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
                        'Tailor Payment',
                        'Production',
                        %s,
                        %s,
                        %s,
                        %s
                    );
                """, (
                    f"Tailor payment - "
                    f"{tailor_name} - "
                    f"{quantity_produced} × "
                    f"{product_name}",
                    total_tailor_payment,
                    term,
                    year
                ))

                conn.commit()

                st.success(
                    f"{money(total_tailor_payment)} "
                    f"recorded as paid to "
                    f"{tailor_name}."
                )

            except Exception as e:

                conn.rollback()

                st.error(str(e))

            finally:

                cur.close()
                conn.close()

    st.divider()

    st.subheader(
        "📊 Tailoring Cost Usage"
    )

    production_df = fetch_dataframe("""
        SELECT
            tp.production_id,
            tp.product_id,
            tp.production_date,
            s.school_name,
            p.product_name,
            tp.tailor_name,
            tp.quantity_produced,
            tp.cost_per_item,
            tp.amount_paid,
            tp.term,
            tp.year

        FROM tailor_production tp

        JOIN schools s
            ON tp.school_id =
               s.school_id

        JOIN products p
            ON tp.product_id =
               p.product_id

        WHERE
            tp.school_id =
            %s

        ORDER BY
            tp.production_date DESC;
    """, (
        school_id,
    ))

    if production_df.empty:

        st.info(
            "No tailor production has "
            "been recorded yet."
        )

    else:

        for _, row in production_df.iterrows():

            prod_product_id = int(row["product_id"])

            sold_df = fetch_dataframe("""
                SELECT
                    COALESCE(
                        SUM(si.quantity),
                        0
                    ) AS sold

                FROM sale_items si

                JOIN sales sa
                    ON si.sale_id =
                       sa.sale_id

                WHERE
                    si.product_id =
                    %s

                AND
                    sa.school_id =
                    %s

                AND
                    si.issued = TRUE

                AND
                    sa.sale_date >= %s;
            """, (
                prod_product_id,
                school_id,
                row["production_date"]
            ))

            sold_quantity = int(
                sold_df.iloc[0]["sold"]
            )

            produced = int(
                row["quantity_produced"]
            )

            used_quantity = min(
                sold_quantity,
                produced
            )

            remaining_quantity = max(
                produced -
                used_quantity,
                0
            )

            cost_per_item = float(
                row["cost_per_item"]
            )

            used_cost = (
                used_quantity
                *
                cost_per_item
            )

            remaining_cost = (
                remaining_quantity
                *
                cost_per_item
            )

            st.markdown(
                f"### {row['product_name']} — "
                f"{row['tailor_name']}"
            )

            c1, c2, c3, c4 = st.columns(4)

            with c1:

                st.metric(
                    "Given to Tailor",
                    money(
                        row["amount_paid"]
                    )
                )

            with c2:

                st.metric(
                    "Produced",
                    produced
                )

            with c3:

                st.metric(
                    "Used / Sold",
                    used_quantity
                )

            with c4:

                st.metric(
                    "Remaining",
                    remaining_quantity
                )

            c5, c6 = st.columns(2)

            with c5:

                st.metric(
                    "Tailoring Cost Used",
                    money(used_cost)
                )

            with c6:

                st.metric(
                    "Tailoring Cost Remaining",
                    money(remaining_cost)
                )

            st.caption(
                f"Production date: "
                f"{row['production_date']} | "
                f"Cost per item: "
                f"{money(cost_per_item)}"
            )

            st.divider()

    totals_df = fetch_dataframe("""
        SELECT
            COALESCE(
                SUM(amount_paid),
                0
            ) AS total_paid,

            COALESCE(
                SUM(quantity_produced),
                0
            ) AS total_produced

        FROM tailor_production

        WHERE
            school_id = %s;
    """, (
        school_id,
    ))

    if not totals_df.empty:

        total_paid = float(
            totals_df.iloc[0][
                "total_paid"
            ]
        )

        total_produced = int(
            totals_df.iloc[0][
                "total_produced"
            ]
        )

        st.subheader(
            "Overall Tailor Position"
        )

        c1, c2 = st.columns(2)

        with c1:

            st.metric(
                "Total Given To Tailors",
                money(total_paid)
            )

        with c2:

            st.metric(
                "Total Items Produced",
                total_produced
            )


# ============================================================
# BUSINESS FINANCE
# ============================================================

elif page == "Business Finance":

    st.title(
        "💼 Business Finance"
    )

    investors_df = fetch_dataframe("""
        SELECT
            i.investor_id,
            i.investor_name,

            COALESCE(
                SUM(
                    CASE
                        WHEN
                            ft.transaction_type =
                            'Capital Contribution'
                        THEN ft.amount
                        ELSE 0
                    END
                ),
                0
            ) AS contribution

        FROM investors i

        LEFT JOIN
            financial_transactions ft

            ON i.investor_id =
               ft.investor_id

        WHERE
            i.active = TRUE

        AND
            i.investor_name
            IN ('Gift', 'Ken')

        GROUP BY
            i.investor_id,
            i.investor_name

        ORDER BY
            CASE
                WHEN i.investor_name =
                    'Gift'
                THEN 1

                WHEN i.investor_name =
                    'Ken'
                THEN 2

                ELSE 3
            END;
    """)

    st.subheader(
        "👥 Investors"
    )

    investor_order = {
        "Gift": 1,
        "Ken": 2
    }

    if not investors_df.empty:

        investors_df[
            "order"
        ] = investors_df[
            "investor_name"
        ].map(
            investor_order
        )

        investors_df = (
            investors_df
            .sort_values("order")
            .drop(
                columns=["order"]
            )
        )

        investors_df[
            "contribution"
        ] = pd.to_numeric(
            investors_df[
                "contribution"
            ],
            errors="coerce"
        ).fillna(0)

        total_investment = (
            investors_df[
                "contribution"
            ].sum()
        )

        if total_investment > 0:

            investors_df[
                "ownership_%"
            ] = (
                investors_df[
                    "contribution"
                ]
                /
                total_investment
                *
                100
            )

        else:

            investors_df[
                "ownership_%"
            ] = 0.0

        display_df = investors_df[
            [
                "investor_name",
                "contribution",
                "ownership_%"
            ]
        ].copy()

        display_df[
            "contribution"
        ] = display_df[
            "contribution"
        ].apply(money)

        display_df[
            "ownership_%"
        ] = display_df[
            "ownership_%"
        ].apply(
            lambda x:
            f"{float(x):.2f}%"
        )

        st.dataframe(
            display_df,
            use_container_width=True
        )

    with st.expander(
        "➕ Record Additional Investment"
    ):

        investor = st.selectbox(
            "Investor",
            [
                "Gift",
                "Ken"
            ],
            key="investment_investor"
        )

        amount = st.number_input(
            "Amount",
            min_value=0.0,
            step=1000.0,
            key="investment_amount"
        )

        if st.button(
            "Record Investment"
        ):

            investor_row = investors_df.loc[
                investors_df[
                    "investor_name"
                ] == investor
            ]

            if investor_row.empty:

                st.error(
                    "Investor not found."
                )

            else:

                investor_id = int(
                    investor_row.iloc[0][
                        "investor_id"
                    ]
                )

                execute_query("""
                    INSERT INTO
                        financial_transactions
                    (
                        transaction_type,
                        category,
                        description,
                        amount,
                        investor_id,
                        year
                    )
                    VALUES
                    (
                        'Capital Contribution',
                        'Investment',
                        %s,
                        %s,
                        %s,
                        %s
                    );
                """, (
                    f"Additional investment "
                    f"by {investor}",
                    amount,
                    investor_id,
                    datetime.now().year
                ))

                st.success(
                    "Investment recorded."
                )

                st.rerun()

    st.divider()

    st.subheader(
        "➕ Financial Transaction"
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

    transaction_category = st.text_input(
        "Category",
        placeholder=(
            "Transport, electricity, "
            "packaging, etc."
        )
    )

    transaction_description = st.text_input(
        "Description"
    )

    transaction_amount = st.number_input(
        "Amount",
        min_value=0.0,
        step=100.0
    )

    if st.button(
        "Record Transaction"
    ):

        execute_query("""
            INSERT INTO
                financial_transactions
            (
                transaction_type,
                category,
                description,
                amount,
                year
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s
            );
        """, (
            transaction_type,
            transaction_category,
            transaction_description,
            transaction_amount,
            datetime.now().year
        ))

        st.success(
            "Transaction recorded."
        )

        st.rerun()

    st.divider()

    st.subheader(
        "📊 Financial Summary"
    )

    finance_df = fetch_dataframe("""
        SELECT
            transaction_type,

            COALESCE(
                SUM(amount),
                0
            ) AS total

        FROM financial_transactions

        GROUP BY
            transaction_type;
    """)

    def get_finance_value(
        transaction_type
    ):

        if finance_df.empty:
            return 0

        row = finance_df[
            finance_df[
                "transaction_type"
            ] == transaction_type
        ]

        if row.empty:
            return 0

        return float(
            row.iloc[0]["total"]
        )

    capital = get_finance_value(
        "Capital Contribution"
    )

    revenue = get_finance_value(
        "Sales Income"
    )

    stock_purchases = get_finance_value(
        "Stock Purchase"
    )

    tailor_payments = get_finance_value(
        "Tailor Payment"
    )

    expenses = get_finance_value(
        "Expense"
    )

    other_income = get_finance_value(
        "Other Income"
    )

    withdrawals = get_finance_value(
        "Owner Withdrawal"
    )

    distributions = get_finance_value(
        "Profit Distribution"
    )

    cogs_df = fetch_dataframe("""
        SELECT
            COALESCE(
                SUM(
                    si.quantity
                    *
                    COALESCE(
                        p.cost_price,
                        0
                    )
                ),
                0
            ) AS cogs

        FROM sale_items si

        JOIN products p
            ON si.product_id =
               p.product_id

        WHERE
            si.issued = TRUE;
    """)

    cogs = (
        float(
            cogs_df.iloc[0]["cogs"]
        )
        if not cogs_df.empty
        else 0
    )

    gross_profit = (
        revenue -
        cogs
    )

    net_profit = (
        gross_profit
        +
        other_income
        -
        expenses
        -
        tailor_payments
    )

    roi = (
        net_profit
        /
        capital
        *
        100
        if capital > 0
        else 0
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

    inventory_df = fetch_dataframe("""
        SELECT
            COALESCE(
                SUM(
                    s.quantity_brought
                    *
                    s.unit_cost
                ),
                0
            ) AS purchased_inventory

        FROM stock s;
    """)

    purchased_inventory = (
        float(
            inventory_df.iloc[0][
                "purchased_inventory"
            ]
        )
        if not inventory_df.empty
        else 0
    )

    st.metric(
        "Inventory Purchased",
        money(purchased_inventory)
    )

    row1 = st.columns(4)

    with row1[0]:

        st.metric(
            "Capital Invested",
            money(capital)
        )

    with row1[1]:

        st.metric(
            "Sales Revenue",
            money(revenue)
        )

    with row1[2]:

        st.metric(
            "Cash Position",
            money(cash_position)
        )

    with row1[3]:

        st.metric(
            "Tailor Payments",
            money(tailor_payments)
        )

    row2 = st.columns(4)

    with row2[0]:

        st.metric(
            "COGS",
            money(cogs)
        )

    with row2[1]:

        st.metric(
            "Gross Profit",
            money(gross_profit)
        )

    with row2[2]:

        st.metric(
            "Net Profit",
            money(net_profit)
        )

    with row2[3]:

        st.metric(
            "ROI",
            f"{roi:.2f}%"
        )

    st.divider()

    st.subheader(
        "💰 Estimated Investor Profit Share"
    )

    if (
        not investors_df.empty
        and
        net_profit > 0
    ):

        share_df = investors_df[
            [
                "investor_name",
                "contribution",
                "ownership_%"
            ]
        ].copy()

        share_df[
            "estimated_profit_share"
        ] = (
            share_df[
                "ownership_%"
            ]
            /
            100
            *
            net_profit
        )

        share_df[
            "contribution"
        ] = share_df[
            "contribution"
        ].apply(money)

        share_df[
            "ownership_%"
        ] = share_df[
            "ownership_%"
        ].apply(
            lambda x:
            f"{float(x):.2f}%"
        )

        share_df[
            "estimated_profit_share"
        ] = share_df[
            "estimated_profit_share"
        ].apply(money)

        st.dataframe(
            share_df,
            use_container_width=True
        )

    elif net_profit <= 0:

        st.info(
            "There is currently no positive "
            "profit to distribute."
        )

    st.divider()

    st.subheader(
        "📒 Financial Ledger"
    )

    ledger_df = fetch_dataframe("""
        SELECT
            transaction_date,
            transaction_type,
            category,
            description,
            amount,
            term,
            year

        FROM financial_transactions

        ORDER BY
            transaction_date DESC;
    """)

    if not ledger_df.empty:

        st.dataframe(
            ledger_df,
            use_container_width=True
        )


# ============================================================
# SALES OVERVIEW
# ============================================================

elif page == "Sales Overview":

    st.title(
        "📊 Sales Overview"
    )

    summary_df = fetch_dataframe("""
        SELECT
            COUNT(*) AS total_sales,

            COALESCE(
                SUM(total_amount),
                0
            ) AS revenue,

            COALESCE(
                AVG(total_amount),
                0
            ) AS average_sale

        FROM sales;
    """)

    if not summary_df.empty:

        c1, c2, c3 = st.columns(3)

        with c1:

            st.metric(
                "Total Sales",
                int(
                    summary_df.iloc[0][
                        "total_sales"
                    ]
                )
            )

        with c2:

            st.metric(
                "Revenue",
                money(
                    summary_df.iloc[0][
                        "revenue"
                    ]
                )
            )

        with c3:

            st.metric(
                "Average Sale",
                money(
                    summary_df.iloc[0][
                        "average_sale"
                    ]
                )
            )

    st.subheader(
        "Revenue by School"
    )

    school_sales = fetch_dataframe("""
        SELECT
            s.school_name,

            SUM(
                sa.total_amount
            ) AS revenue

        FROM sales sa

        JOIN schools s
            ON sa.school_id =
               s.school_id

        GROUP BY
            s.school_name

        ORDER BY
            revenue DESC;
    """)

    if not school_sales.empty:

        st.dataframe(
            school_sales,
            use_container_width=True
        )

        st.bar_chart(
            school_sales.set_index(
                "school_name"
            )
        )

    st.subheader(
        "Revenue by Term"
    )

    term_sales = fetch_dataframe("""
        SELECT
            year,
            term,

            SUM(
                total_amount
            ) AS revenue

        FROM sales

        GROUP BY
            year,
            term

        ORDER BY
            year,
            term;
    """)

    if not term_sales.empty:

        st.dataframe(
            term_sales,
            use_container_width=True
        )

    st.subheader(
        "Top Selling Products"
    )

    top_products = fetch_dataframe("""
        SELECT
            p.product_name,

            SUM(
                si.quantity
            ) AS quantity_sold,

            SUM(
                si.line_total
            ) AS revenue

        FROM sale_items si

        JOIN products p
            ON si.product_id =
               p.product_id

        WHERE
            si.issued = TRUE

        GROUP BY
            p.product_name

        ORDER BY
            quantity_sold DESC;
    """)

    if not top_products.empty:

        st.dataframe(
            top_products,
            use_container_width=True
        )

        st.bar_chart(
            top_products.set_index(
                "product_name"
            )[
                ["quantity_sold"]
            ]
        )


# ============================================================
# SALES HISTORY
# ============================================================

elif page == "Sales History":

    st.title(
        "📜 Sales History"
    )

    history_df = fetch_dataframe("""
        SELECT
            sa.sale_id,
            sa.sale_date,
            s.school_name,
            c.customer_name,
            c.phone,
            sa.term,
            sa.year,
            sa.total_amount,
            sa.payment_method,
            sa.payment_status

        FROM sales sa

        JOIN schools s
            ON sa.school_id =
               s.school_id

        LEFT JOIN customers c
            ON sa.customer_id =
               c.customer_id

        ORDER BY
            sa.sale_date DESC;
    """)

    if history_df.empty:

        st.info(
            "No sales recorded yet."
        )

    else:

        st.dataframe(
            history_df,
            use_container_width=True
        )

        csv = (
            history_df
            .to_csv(index=False)
            .encode("utf-8")
        )

        st.download_button(
            "⬇️ Download Sales CSV",
            csv,
            "sales_history.csv",
            "text/csv"
        )


# ============================================================
# EDIT DATA
# ============================================================

elif page == "Edit Data":

    st.title("✏️ Edit Data")
    st.write(
        "Edit any record inline and click **Save Changes**. "
        "Nothing is deleted — only updated."
    )

    tab_schools, tab_products, tab_investors, tab_capital, \
    tab_sales, tab_stock, tab_tailor = st.tabs([
        "Schools",
        "Products",
        "Investors",
        "Capital / Transactions",
        "Sales",
        "Stock",
        "Tailor Production"
    ])

    # --------------------------------------------------------
    # SCHOOLS
    # --------------------------------------------------------
    with tab_schools:

        st.subheader("Schools")

        schools_df = fetch_dataframe("""
            SELECT school_id, school_name
            FROM schools
            ORDER BY school_name;
        """)

        if schools_df.empty:
            st.info("No schools.")
        else:
            edited = st.data_editor(
                schools_df,
                use_container_width=True,
                hide_index=True,
                disabled=["school_id"],
                key="edit_schools"
            )

            if st.button("💾 Save Schools"):
                conn = get_connection()
                cur = conn.cursor()
                try:
                    for _, row in edited.iterrows():
                        cur.execute("""
                            UPDATE schools
                            SET school_name = %s
                            WHERE school_id = %s;
                        """, (
                            row["school_name"],
                            int(row["school_id"])
                        ))
                    conn.commit()
                    st.success("Schools updated.")
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"Error: {e}")
                finally:
                    cur.close()
                    conn.close()

    # --------------------------------------------------------
    # PRODUCTS
    # --------------------------------------------------------
    with tab_products:

        st.subheader("Products")

        products_df = fetch_dataframe("""
            SELECT product_id, product_name, price, cost_price
            FROM products
            ORDER BY product_name;
        """)

        edited = st.data_editor(
            products_df,
            use_container_width=True,
            hide_index=True,
            disabled=["product_id"],
            key="edit_products"
        )

        if st.button("💾 Save Products"):
            conn = get_connection()
            cur = conn.cursor()
            try:
                for _, row in edited.iterrows():
                    cur.execute("""
                        UPDATE products
                        SET product_name = %s,
                            price = %s,
                            cost_price = %s
                        WHERE product_id = %s;
                    """, (
                        row["product_name"],
                        float(row["price"]),
                        float(row["cost_price"]),
                        int(row["product_id"])
                    ))
                conn.commit()
                st.success("Products updated.")
                st.rerun()
            except Exception as e:
                conn.rollback()
                st.error(f"Error: {e}")
            finally:
                cur.close()
                conn.close()

    # --------------------------------------------------------
    # INVESTORS
    # --------------------------------------------------------
    with tab_investors:

        st.subheader("Investors")
        st.caption(
            "Rename investors or toggle active."
        )

        investors_df = fetch_dataframe("""
            SELECT investor_id, investor_name, active
            FROM investors
            ORDER BY investor_name;
        """)

        edited = st.data_editor(
            investors_df,
            use_container_width=True,
            hide_index=True,
            disabled=["investor_id"],
            key="edit_investors"
        )

        if st.button("💾 Save Investors"):
            conn = get_connection()
            cur = conn.cursor()
            try:
                for _, row in edited.iterrows():
                    cur.execute("""
                        UPDATE investors
                        SET investor_name = %s,
                            active = %s
                        WHERE investor_id = %s;
                    """, (
                        row["investor_name"],
                        bool(row["active"]),
                        int(row["investor_id"])
                    ))
                conn.commit()
                st.success("Investors updated.")
                st.rerun()
            except Exception as e:
                conn.rollback()
                st.error(f"Error: {e}")
            finally:
                cur.close()
                conn.close()

    # --------------------------------------------------------
    # CAPITAL / FINANCIAL TRANSACTIONS
    # --------------------------------------------------------
    with tab_capital:

        st.subheader("Financial Transactions")
        st.caption(
            "Edit any transaction inline — including "
            "capital contributions."
        )

        all_types = fetch_dataframe("""
            SELECT DISTINCT transaction_type
            FROM financial_transactions
            ORDER BY transaction_type;
        """)

        type_filter = st.selectbox(
            "Filter by type",
            ["All"] + (
                all_types["transaction_type"].tolist()
                if not all_types.empty else []
            ),
            key="txn_type_filter"
        )

        if type_filter == "All":
            txn_df = fetch_dataframe("""
                SELECT
                    ft.transaction_id,
                    ft.transaction_date,
                    ft.transaction_type,
                    ft.category,
                    ft.description,
                    ft.amount,
                    i.investor_name,
                    ft.term,
                    ft.year
                FROM financial_transactions ft
                LEFT JOIN investors i
                    ON ft.investor_id = i.investor_id
                ORDER BY ft.transaction_date DESC;
            """)
        else:
            txn_df = fetch_dataframe("""
                SELECT
                    ft.transaction_id,
                    ft.transaction_date,
                    ft.transaction_type,
                    ft.category,
                    ft.description,
                    ft.amount,
                    i.investor_name,
                    ft.term,
                    ft.year
                FROM financial_transactions ft
                LEFT JOIN investors i
                    ON ft.investor_id = i.investor_id
                WHERE ft.transaction_type = %s
                ORDER BY ft.transaction_date DESC;
            """, (type_filter,))

        if txn_df.empty:
            st.info("No transactions.")
        else:
            investor_lookup = fetch_dataframe("""
                SELECT investor_id, investor_name
                FROM investors
                WHERE active = TRUE;
            """)

            edited = st.data_editor(
                txn_df,
                use_container_width=True,
                hide_index=True,
                disabled=["transaction_id", "transaction_date"],
                column_config={
                    "transaction_type": st.column_config.SelectboxColumn(
                        "Type",
                        options=[
                            "Capital Contribution",
                            "Sales Income",
                            "Stock Purchase",
                            "Tailor Payment",
                            "Expense",
                            "Other Income",
                            "Owner Withdrawal",
                            "Profit Distribution"
                        ],
                        required=True
                    ),
                    "investor_name": st.column_config.SelectboxColumn(
                        "Investor",
                        options=(
                            ["—"] +
                            investor_lookup["investor_name"].tolist()
                            if not investor_lookup.empty else ["—"]
                        )
                    ),
                    "amount": st.column_config.NumberColumn(
                        "Amount",
                        format="%.2f",
                        min_value=0.0
                    )
                },
                key="edit_txns"
            )

            if st.button("💾 Save Transactions"):
                conn = get_connection()
                cur = conn.cursor()
                try:
                    cur.execute("""
                        SELECT investor_id, investor_name
                        FROM investors;
                    """)
                    name_to_id = {
                        name: inv_id
                        for inv_id, name in cur.fetchall()
                    }

                    for _, row in edited.iterrows():
                        inv_name = row["investor_name"]
                        inv_id = (
                            name_to_id.get(inv_name)
                            if inv_name and inv_name != "—"
                            else None
                        )

                        year_val = row["year"]
                        if pd.isna(year_val):
                            year_val = None
                        else:
                            year_val = int(year_val)

                        cur.execute("""
                            UPDATE financial_transactions
                            SET transaction_type = %s,
                                category = %s,
                                description = %s,
                                amount = %s,
                                investor_id = %s,
                                term = %s,
                                year = %s
                            WHERE transaction_id = %s;
                        """, (
                            row["transaction_type"],
                            row["category"],
                            row["description"],
                            float(row["amount"]),
                            inv_id,
                            row["term"] if pd.notna(row["term"]) else None,
                            year_val,
                            int(row["transaction_id"])
                        ))
                    conn.commit()
                    st.success("Transactions updated.")
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"Error: {e}")
                finally:
                    cur.close()
                    conn.close()

    # --------------------------------------------------------
    # SALES
    # --------------------------------------------------------
    with tab_sales:

        st.subheader("Sales")

        sales_df = fetch_dataframe("""
            SELECT
                sa.sale_id,
                sa.sale_date,
                s.school_name,
                c.customer_name,
                c.phone,
                sa.term,
                sa.year,
                sa.total_amount,
                sa.payment_method,
                sa.payment_status
            FROM sales sa
            JOIN schools s ON sa.school_id = s.school_id
            LEFT JOIN customers c ON sa.customer_id = c.customer_id
            ORDER BY sa.sale_date DESC;
        """)

        if sales_df.empty:
            st.info("No sales.")
        else:
            edited = st.data_editor(
                sales_df,
                use_container_width=True,
                hide_index=True,
                disabled=[
                    "sale_id", "sale_date",
                    "school_name", "customer_name", "phone"
                ],
                column_config={
                    "payment_method": st.column_config.SelectboxColumn(
                        "Payment",
                        options=["Cash", "M-Pesa", "Bank", "Other"]
                    ),
                    "payment_status": st.column_config.SelectboxColumn(
                        "Status",
                        options=["Paid", "Partial", "Unpaid"]
                    ),
                    "total_amount": st.column_config.NumberColumn(
                        "Total", format="%.2f", min_value=0.0
                    ),
                    "term": st.column_config.SelectboxColumn(
                        "Term",
                        options=["Term 1", "Term 2", "Term 3"]
                    )
                },
                key="edit_sales"
            )

            if st.button("💾 Save Sales"):
                conn = get_connection()
                cur = conn.cursor()
                try:
                    for _, row in edited.iterrows():
                        year_val = row["year"]
                        year_val = (
                            None if pd.isna(year_val)
                            else int(year_val)
                        )
                        cur.execute("""
                            UPDATE sales
                            SET total_amount = %s,
                                payment_method = %s,
                                payment_status = %s,
                                term = %s,
                                year = %s
                            WHERE sale_id = %s;
                        """, (
                            float(row["total_amount"]),
                            row["payment_method"],
                            row["payment_status"],
                            row["term"] if pd.notna(row["term"]) else None,
                            year_val,
                            int(row["sale_id"])
                        ))
                    conn.commit()
                    st.success("Sales updated.")
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"Error: {e}")
                finally:
                    cur.close()
                    conn.close()

            st.divider()
            st.subheader("Sale Line Items")

            sale_id_pick = st.selectbox(
                "Sale ID",
                sales_df["sale_id"].tolist(),
                key="edit_sale_items_pick"
            )

            items_df = fetch_dataframe("""
                SELECT
                    si.sale_item_id,
                    p.product_name,
                    si.quantity,
                    si.unit_price,
                    si.line_total,
                    si.issued
                FROM sale_items si
                JOIN products p ON si.product_id = p.product_id
                WHERE si.sale_id = %s
                ORDER BY si.sale_item_id;
            """, (int(sale_id_pick),))

            if not items_df.empty:
                edited_items = st.data_editor(
                    items_df,
                    use_container_width=True,
                    hide_index=True,
                    disabled=[
                        "sale_item_id",
                        "product_name",
                        "line_total"
                    ],
                    column_config={
                        "quantity": st.column_config.NumberColumn(
                            min_value=1, step=1
                        ),
                        "unit_price": st.column_config.NumberColumn(
                            format="%.2f", min_value=0.0
                        ),
                        "issued": st.column_config.CheckboxColumn()
                    },
                    key="edit_sale_items"
                )

                if st.button("💾 Save Line Items"):
                    conn = get_connection()
                    cur = conn.cursor()
                    try:
                        for _, row in edited_items.iterrows():
                            new_line_total = (
                                float(row["quantity"]) *
                                float(row["unit_price"])
                            )
                            cur.execute("""
                                UPDATE sale_items
                                SET quantity = %s,
                                    unit_price = %s,
                                    line_total = %s,
                                    issued = %s
                                WHERE sale_item_id = %s;
                            """, (
                                int(row["quantity"]),
                                float(row["unit_price"]),
                                new_line_total,
                                bool(row["issued"]),
                                int(row["sale_item_id"])
                            ))

                        cur.execute("""
                            UPDATE sales
                            SET total_amount = (
                                SELECT COALESCE(SUM(line_total), 0)
                                FROM sale_items
                                WHERE sale_id = %s
                            )
                            WHERE sale_id = %s;
                        """, (int(sale_id_pick), int(sale_id_pick)))

                        conn.commit()
                        st.success("Line items updated, sale total recalculated.")
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"Error: {e}")
                    finally:
                        cur.close()
                        conn.close()

    # --------------------------------------------------------
    # STOCK
    # --------------------------------------------------------
    with tab_stock:

        st.subheader("Stock")

        stock_df = fetch_dataframe("""
            SELECT
                s.stock_id,
                sc.school_name,
                p.product_name,
                s.quantity_brought,
                s.unit_cost,
                s.term,
                s.year,
                s.date_added
            FROM stock s
            JOIN schools sc ON s.school_id = sc.school_id
            JOIN products p ON s.product_id = p.product_id
            ORDER BY s.date_added DESC;
        """)

        if stock_df.empty:
            st.info("No stock.")
        else:
            edited = st.data_editor(
                stock_df,
                use_container_width=True,
                hide_index=True,
                disabled=[
                    "stock_id", "date_added",
                    "school_name", "product_name"
                ],
                column_config={
                    "quantity_brought": st.column_config.NumberColumn(
                        min_value=1, step=1
                    ),
                    "unit_cost": st.column_config.NumberColumn(
                        format="%.2f", min_value=0.0
                    ),
                    "term": st.column_config.SelectboxColumn(
                        options=["Term 1", "Term 2", "Term 3"]
                    )
                },
                key="edit_stock"
            )

            if st.button("💾 Save Stock"):
                conn = get_connection()
                cur = conn.cursor()
                try:
                    for _, row in edited.iterrows():
                        year_val = row["year"]
                        year_val = (
                            None if pd.isna(year_val)
                            else int(year_val)
                        )
                        cur.execute("""
                            UPDATE stock
                            SET quantity_brought = %s,
                                unit_cost = %s,
                                term = %s,
                                year = %s
                            WHERE stock_id = %s;
                        """, (
                            int(row["quantity_brought"]),
                            float(row["unit_cost"]),
                            row["term"] if pd.notna(row["term"]) else None,
                            year_val,
                            int(row["stock_id"])
                        ))
                    conn.commit()
                    st.success("Stock updated.")
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"Error: {e}")
                finally:
                    cur.close()
                    conn.close()

    # --------------------------------------------------------
    # TAILOR PRODUCTION
    # --------------------------------------------------------
    with tab_tailor:

        st.subheader("Tailor Production")

        tailor_df = fetch_dataframe("""
            SELECT
                tp.production_id,
                tp.production_date,
                s.school_name,
                p.product_name,
                tp.tailor_name,
                tp.quantity_produced,
                tp.cost_per_item,
                tp.amount_paid,
                tp.term,
                tp.year,
                tp.notes
            FROM tailor_production tp
            JOIN schools s ON tp.school_id = s.school_id
            JOIN products p ON tp.product_id = p.product_id
            ORDER BY tp.production_date DESC;
        """)

        if tailor_df.empty:
            st.info("No tailor records.")
        else:
            edited = st.data_editor(
                tailor_df,
                use_container_width=True,
                hide_index=True,
                disabled=[
                    "production_id", "production_date",
                    "school_name", "product_name"
                ],
                column_config={
                    "quantity_produced": st.column_config.NumberColumn(
                        min_value=1, step=1
                    ),
                    "cost_per_item": st.column_config.NumberColumn(
                        format="%.2f", min_value=0.0
                    ),
                    "amount_paid": st.column_config.NumberColumn(
                        format="%.2f", min_value=0.0
                    ),
                    "term": st.column_config.SelectboxColumn(
                        options=["Term 1", "Term 2", "Term 3"]
                    )
                },
                key="edit_tailor"
            )

            if st.button("💾 Save Tailor Records"):
                conn = get_connection()
                cur = conn.cursor()
                try:
                    for _, row in edited.iterrows():
                        year_val = row["year"]
                        year_val = (
                            None if pd.isna(year_val)
                            else int(year_val)
                        )
                        notes = row["notes"]
                        notes = None if pd.isna(notes) else notes

                        cur.execute("""
                            UPDATE tailor_production
                            SET tailor_name = %s,
                                quantity_produced = %s,
                                cost_per_item = %s,
                                amount_paid = %s,
                                term = %s,
                                year = %s,
                                notes = %s
                            WHERE production_id = %s;
                        """, (
                            row["tailor_name"],
                            int(row["quantity_produced"]),
                            float(row["cost_per_item"]),
                            float(row["amount_paid"]),
                            row["term"] if pd.notna(row["term"]) else None,
                            year_val,
                            notes,
                            int(row["production_id"])
                        ))
                    conn.commit()
                    st.success("Tailor records updated.")
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"Error: {e}")
                finally:
                    cur.close()
                    conn.close()


# ============================================================
# ML & FORECASTING
# ============================================================

elif page == "ML & Forecasting":

    st.title(
        "🤖 ML & Forecasting"
    )

    st.write(
        "This section uses the business data "
        "to support sales forecasting, "
        "inventory decisions and investment analysis."
    )

    st.subheader(
        "💰 Investment Analysis"
    )

    investment_df = fetch_dataframe("""
        SELECT
            i.investor_name,

            COALESCE(
                SUM(ft.amount),
                0
            ) AS contribution

        FROM investors i

        LEFT JOIN
            financial_transactions ft

            ON i.investor_id =
               ft.investor_id

            AND ft.transaction_type =
                'Capital Contribution'

        WHERE
            i.active = TRUE

        AND
            i.investor_name
            IN ('Gift', 'Ken')

        GROUP BY
            i.investor_name

        ORDER BY
            CASE
                WHEN i.investor_name =
                    'Gift'
                THEN 1

                WHEN i.investor_name =
                    'Ken'
                THEN 2

                ELSE 3
            END;
    """)

    if not investment_df.empty:

        investment_df[
            "contribution"
        ] = pd.to_numeric(
            investment_df[
                "contribution"
            ],
            errors="coerce"
        ).fillna(0)

        total = (
            investment_df[
                "contribution"
            ].sum()
        )

        if total > 0:

            investment_df[
                "ownership_%"
            ] = (
                investment_df[
                    "contribution"
                ]
                /
                total
                *
                100
            )

            investment_df[
                "contribution"
            ] = investment_df[
                "contribution"
            ].apply(money)

            investment_df[
                "ownership_%"
            ] = investment_df[
                "ownership_%"
            ].apply(
                lambda x:
                f"{float(x):.2f}%"
            )

            st.dataframe(
                investment_df,
                use_container_width=True
            )

    st.subheader(
        "📈 Historical Revenue"
    )

    daily_sales = fetch_dataframe("""
        SELECT
            DATE(sale_date)
                AS sale_day,

            SUM(total_amount)
                AS revenue

        FROM sales

        GROUP BY
            DATE(sale_date)

        ORDER BY
            sale_day;
    """)

    if not daily_sales.empty:

        st.line_chart(
            daily_sales.set_index(
                "sale_day"
            )
        )

        if len(daily_sales) >= 3:

            recent_average = (
                daily_sales[
                    "revenue"
                ]
                .tail(7)
                .mean()
            )

            st.metric(
                "Recent Average Daily Revenue",
                money(recent_average)
            )

            st.info(
                "Simple baseline forecast: "
                f"approximately "
                f"{money(recent_average)} "
                "per day based on recent sales."
            )

        else:

            st.info(
                "More sales history is needed "
                "before forecasting."
            )

    st.subheader(
        "📦 Product Demand"
    )

    demand_df = fetch_dataframe("""
        SELECT
            p.product_name,

            SUM(
                si.quantity
            ) AS quantity_sold

        FROM sale_items si

        JOIN products p
            ON si.product_id =
               p.product_id

        WHERE
            si.issued = TRUE

        GROUP BY
            p.product_name

        ORDER BY
            quantity_sold DESC;
    """)

    if not demand_df.empty:

        st.dataframe(
            demand_df,
            use_container_width=True
        )

        st.bar_chart(
            demand_df.set_index(
                "product_name"
            )
        )

    st.divider()

    st.subheader(
        "Future ML Analysis"
    )

    st.write("""
    Planned intelligence for the system:

    • Sales forecasting
    • Product demand prediction
    • Stock replenishment recommendations
    • Financial forecasting
    • Investment performance analysis
    • School-by-school sales analysis
    • Profit prediction
    • Seasonal demand analysis
    """)
