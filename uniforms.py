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

        cur.execute("""
            CREATE TABLE IF NOT EXISTS schools (
                school_id SERIAL PRIMARY KEY,
                school_name VARCHAR(100) NOT NULL UNIQUE
            );
        """)

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

        cur.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                customer_id SERIAL PRIMARY KEY,
                customer_name VARCHAR(100) NOT NULL,
                phone VARCHAR(20)
            );
        """)

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

        cur.execute("""
            CREATE TABLE IF NOT EXISTS investors (
                investor_id SERIAL PRIMARY KEY,
                investor_name VARCHAR(100) NOT NULL UNIQUE,
                active BOOLEAN DEFAULT TRUE
            );
        """)

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
        # NOTE: Initial capital seeding (Gift 150,000 and
        # Ken 100,000) has been REMOVED. Real contributions
        # are entered via Business Finance -> Record Additional
        # Investment, or edited via Edit Data.
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
        "Settings",
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
            "Tail
