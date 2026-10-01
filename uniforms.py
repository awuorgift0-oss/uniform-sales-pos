import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Uniform Sales POS",
    page_icon="🧾",
    layout="wide"
)


# =========================================================
# STYLING
# =========================================================

st.markdown("""
<style>

.main {
    background-color: #f4f8fc;
}

.block-container {
    padding-top: 1.5rem;
}

h1, h2, h3 {
    color: #102a43;
}

section[data-testid="stSidebar"] {
    background-color: #102a43;
}

section[data-testid="stSidebar"] * {
    color: white;
}

.stButton > button {
    background-color: #f28c28;
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 600;
}

.stButton > button:hover {
    background-color: #d97706;
    color: white;
}

.metric-card {
    background: white;
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    text-align: center;
}

.receipt {
    background: white;
    padding: 25px;
    border: 1px solid #ddd;
    border-radius: 10px;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_connection():
    return psycopg2.connect(
        host=st.secrets["postgres"]["host"],
        port=st.secrets["postgres"]["port"],
        database=st.secrets["postgres"]["database"],
        user=st.secrets["postgres"]["user"],
        password=st.secrets["postgres"]["password"],
        sslmode=st.secrets["postgres"].get("sslmode", "require")
    )


# =========================================================
# DATABASE SETUP
# =========================================================

def setup_database():

    conn = get_connection()
    cur = conn.cursor()

    # -----------------------------------------------------
    # SCHOOLS
    # -----------------------------------------------------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS schools (
            school_id SERIAL PRIMARY KEY,
            school_name VARCHAR(100) NOT NULL
        );
    """)

    # Add unique constraint safely
    cur.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'schools_school_name_unique'
            ) THEN
                ALTER TABLE schools
                ADD CONSTRAINT schools_school_name_unique
                UNIQUE (school_name);
            END IF;
        END $$;
    """)

    # -----------------------------------------------------
    # PRODUCTS
    # -----------------------------------------------------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id SERIAL PRIMARY KEY,
            product_name VARCHAR(100) NOT NULL,
            price NUMERIC(10,2) NOT NULL DEFAULT 0
        );
    """)

    cur.execute("""
        ALTER TABLE products
        ADD COLUMN IF NOT EXISTS cost_price NUMERIC(10,2)
        NOT NULL DEFAULT 0;
    """)

    cur.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'products_product_name_unique'
            ) THEN
                ALTER TABLE products
                ADD CONSTRAINT products_product_name_unique
                UNIQUE (product_name);
            END IF;
        END $$;
    """)

    # -----------------------------------------------------
    # CUSTOMERS
    # -----------------------------------------------------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id SERIAL PRIMARY KEY,
            customer_name VARCHAR(100) NOT NULL,
            phone VARCHAR(20)
        );
    """)

    # -----------------------------------------------------
    # SALES
    # -----------------------------------------------------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            sale_id SERIAL PRIMARY KEY,
            sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            school_id INT NOT NULL REFERENCES schools(school_id),
            customer_id INT,
            total_amount NUMERIC(10,2) NOT NULL,
            payment_method VARCHAR(30),
            payment_status VARCHAR(20) DEFAULT 'Paid'
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

    # -----------------------------------------------------
    # SALE ITEMS
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # SCHOOL PRODUCT PRICES
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # STOCK
    # -----------------------------------------------------

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
        ADD COLUMN IF NOT EXISTS unit_cost NUMERIC(10,2) DEFAULT 0;
    """)

    # -----------------------------------------------------
    # UNIFORM SETS
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # INVESTORS
    # -----------------------------------------------------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS investors (
            investor_id SERIAL PRIMARY KEY,
            investor_name VARCHAR(100) NOT NULL UNIQUE,
            active BOOLEAN DEFAULT TRUE
        );
    """)

    # -----------------------------------------------------
    # FINANCIAL TRANSACTIONS
    # -----------------------------------------------------

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

    # =====================================================
    # SEED SCHOOLS
    # =====================================================

    schools = [
        "LOVING BLOOMS SCHOOL",
        "WARIDI UTAWALA SCHOOL"
    ]

    for school in schools:
        cur.execute("""
            INSERT INTO schools (school_name)
            SELECT %s
            WHERE NOT EXISTS (
                SELECT 1 FROM schools WHERE school_name = %s
            );
        """, (school, school))

    # =====================================================
    # SEED PRODUCTS
    # =====================================================

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
            INSERT INTO products (product_name, price)
            SELECT %s, %s
            WHERE NOT EXISTS (
                SELECT 1
                FROM products
                WHERE product_name = %s
            );
        """, (name, price, name))

    # =====================================================
    # INVESTORS
    # =====================================================

    for investor in ["You", "Boyfriend"]:

        cur.execute("""
            INSERT INTO investors (investor_name)
            VALUES (%s)
            ON CONFLICT (investor_name) DO NOTHING;
        """, (investor,))

    # =====================================================
    # FRESH START CAPITAL
    # =====================================================

    cur.execute("""
        SELECT COUNT(*)
        FROM financial_transactions
        WHERE transaction_type = 'Capital Contribution';
    """)

    capital_count = cur.fetchone()[0]

    if capital_count == 0:

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
                investor_id
            )
            VALUES
            (
                'Capital Contribution',
                'Investment',
                'Fresh starting capital',
                150000,
                %s
            ),
            (
                'Capital Contribution',
                'Investment',
                'Fresh starting capital',
                100000,
                %s
            );
        """, (you_id, boyfriend_id))

    conn.commit()

    cur.close()
    conn.close()


# =========================================================
# RUN DATABASE SETUP
# =========================================================

try:
    setup_database()
except Exception as e:
    st.error("Database setup error:")
    st.code(str(e))
    st.stop()


# =========================================================
# SESSION STATE
# =========================================================

if "cart" not in st.session_state:
    st.session_state.cart = []

if "last_receipt" not in st.session_state:
    st.session_state.last_receipt = None


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def query_df(sql, params=None):

    conn = get_connection()

    try:
        return pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()


def execute_query(sql, params=None, fetch=False):

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(sql, params)

        result = None

        if fetch:
            result = cur.fetchall()

        conn.commit()

        return result

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()


def get_schools():

    return query_df("""
        SELECT school_id, school_name
        FROM schools
        ORDER BY school_name
    """)


def get_products():

    return query_df("""
        SELECT
            product_id,
            product_name,
            price,
            cost_price
        FROM products
        ORDER BY product_name
    """)


def get_categories():

    return [
        "Primary",
        "JSS"
    ]


def get_products_for_school_category(school_id, category):

    return query_df("""
        SELECT
            spp.product_id,
            p.product_name,
            spp.price,
            p.cost_price
        FROM school_product_prices spp
        JOIN products p
            ON p.product_id = spp.product_id
        WHERE spp.school_id = %s
        AND spp.category_name = %s
        ORDER BY p.product_name
    """, (school_id, category))


def get_investor_id(name):

    result = query_df("""
        SELECT investor_id
        FROM investors
        WHERE investor_name = %s
    """, (name,))

    if result.empty:
        return None

    return int(result.iloc[0]["investor_id"])


def money(value):

    return f"KSh {float(value):,.2f}"


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title("🧾 Uniform Sales POS")

menu = st.sidebar.radio(
    "Navigation",
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

st.sidebar.markdown("---")
st.sidebar.caption("Uniform Sales Management System")


# =========================================================
# NEW SALE
# =========================================================

if menu == "New Sale":

    st.title("🧾 New Sale")

    schools_df = get_schools()

    if schools_df.empty:
        st.error("No schools found.")
        st.stop()

    school_name = st.selectbox(
        "School",
        schools_df["school_name"].tolist()
    )

    school_id = int(
        schools_df.loc[
            schools_df["school_name"] == school_name,
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
            min_value=2024,
            max_value=2100,
            value=datetime.now().year
        )

    category = st.selectbox(
        "Category",
        get_categories()
    )

    assigned_products = get_products_for_school_category(
        school_id,
        category
    )

    if assigned_products.empty:

        st.warning(
            "No products have been assigned to this school/category yet."
        )

        st.info(
            "Go to Price Management and assign products first."
        )

    else:

        col1, col2 = st.columns(2)

        with col1:

            customer_name = st.text_input(
                "Student / Customer Name"
            )

        with col2:

            phone = st.text_input(
                "Phone Number"
            )

        class_name = st.text_input(
            "Class / Grade"
        )

        product_name = st.selectbox(
            "Product",
            assigned_products["product_name"].tolist()
        )

        selected_product = assigned_products[
            assigned_products["product_name"] == product_name
        ].iloc[0]

        unit_price = float(selected_product["price"])

        st.write(
            f"Selling price: **{money(unit_price)}**"
        )

        col1, col2 = st.columns(2)

        with col1:

            quantity = st.number_input(
                "Quantity",
                min_value=1,
                value=1,
                step=1
            )

        with col2:

            issued = st.checkbox(
                "Issued to customer",
                value=True
            )

        if st.button("➕ Add to Cart"):

            st.session_state.cart.append({
                "product_id": int(selected_product["product_id"]),
                "product_name": product_name,
                "quantity": int(quantity),
                "unit_price": unit_price,
                "line_total": unit_price * quantity,
                "issued": issued
            })

            st.success(
                f"{quantity} × {product_name} added."
            )

    # -----------------------------------------------------
    # CART
    # -----------------------------------------------------

    st.subheader("🛒 Current Cart")

    if st.session_state.cart:

        cart_df = pd.DataFrame(
            st.session_state.cart
        )

        st.dataframe(
            cart_df[
                [
                    "product_name",
                    "quantity",
                    "unit_price",
                    "line_total",
                    "issued"
                ]
            ],
            use_container_width=True
        )

        total = sum(
            item["line_total"]
            for item in st.session_state.cart
        )

        st.markdown(
            f"### Total: {money(total)}"
        )

        col1, col2 = st.columns(2)

        with col1:

            payment_method = st.selectbox(
                "Payment Method",
                [
                    "Cash",
                    "M-Pesa",
                    "Bank",
                    "Other"
                ]
            )

        with col2:

            if st.button("🗑️ Clear Cart"):

                st.session_state.cart = []

                st.rerun()

        if st.button(
            "✅ Complete Sale",
            type="primary"
        ):

            if not customer_name.strip():

                st.error(
                    "Enter the student/customer name."
                )

            else:

                conn = get_connection()
                cur = conn.cursor()

                try:

                    # Customer
                    cur.execute("""
                        INSERT INTO customers
                        (
                            customer_name,
                            phone
                        )
                        VALUES (%s, %s)
                        RETURNING customer_id;
                    """, (
                        customer_name,
                        phone
                    ))

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
                        (
                            %s,
                            %s,
                            %s,
                            %s,
                            'Paid',
                            %s,
                            %s
                        )
                        RETURNING sale_id;
                    """, (
                        school_id,
                        customer_id,
                        total,
                        payment_method,
                        term,
                        year
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

                    # Financial transaction
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
                            'Revenue',
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
                        "date": datetime.now().strftime(
                            "%d/%m/%Y %H:%M"
                        ),
                        "school": school_name,
                        "customer": customer_name,
                        "phone": phone,
                        "term": term,
                        "year": year,
                        "payment": payment_method,
                        "items": st.session_state.cart.copy(),
                        "total": total
                    }

                    st.session_state.cart = []

                    st.success(
                        f"Sale #{sale_id} completed successfully."
                    )

                except Exception as e:

                    conn.rollback()

                    st.error(
                        "Sale could not be completed."
                    )

                    st.code(str(e))

                finally:

                    cur.close()
                    conn.close()

    else:

        st.info("Cart is empty.")


# =========================================================
# RECEIPT
# =========================================================

if menu == "New Sale" and st.session_state.last_receipt:

    receipt = st.session_state.last_receipt

    st.markdown("---")
    st.subheader("🧾 Receipt")

    items_html = ""

    for item in receipt["items"]:

        items_html += f"""
        <tr>
            <td>{item['product_name']}</td>
            <td>{item['quantity']}</td>
            <td>{money(item['unit_price'])}</td>
            <td>{money(item['line_total'])}</td>
        </tr>
        """

    receipt_html = f"""
    <div class="receipt">

        <h2>UNIFORM SALES</h2>

        <p>
        <strong>School:</strong> {receipt['school']}<br>
        <strong>Receipt No:</strong> {receipt['sale_id']}<br>
        <strong>Date:</strong> {receipt['date']}<br>
        <strong>Term:</strong> {receipt['term']} {receipt['year']}<br>
        <strong>Customer:</strong> {receipt['customer']}<br>
        <strong>Phone:</strong> {receipt['phone']}<br>
        <strong>Payment:</strong> {receipt['payment']}
        </p>

        <table style="width:100%; border-collapse:collapse;">
            <tr>
                <th style="text-align:left;">Item</th>
                <th>Qty</th>
                <th>Price</th>
                <th>Total</th>
            </tr>

            {items_html}

        </table>

        <h3 style="text-align:right;">
            TOTAL: {money(receipt['total'])}
        </h3>

    </div>
    """

    components.html(
        receipt_html,
        height=500,
        scrolling=True
    )


# =========================================================
# PRICE MANAGEMENT
# =========================================================

elif menu == "Price Management":

    st.title("💰 Price Management")

    schools_df = get_schools()

    school_name = st.selectbox(
        "School",
        schools_df["school_name"].tolist()
    )

    school_id = int(
        schools_df.loc[
            schools_df["school_name"] == school_name,
            "school_id"
        ].iloc[0]
    )

    category = st.selectbox(
        "Category",
        get_categories()
    )

    st.subheader("Assigned Products")

    products_df = get_products_for_school_category(
        school_id,
        category
    )

    if not products_df.empty:

        edited = st.data_editor(
            products_df[
                [
                    "product_id",
                    "product_name",
                    "price"
                ]
            ],
            use_container_width=True,
            hide_index=True,
            disabled=["product_id", "product_name"]
        )

        if st.button("💾 Save Prices"):

            conn = get_connection()
            cur = conn.cursor()

            try:

                for _, row in edited.iterrows():

                    cur.execute("""
                        UPDATE school_product_prices
                        SET price = %s
                        WHERE school_id = %s
                        AND category_name = %s
                        AND product_id = %s;
                    """, (
                        float(row["price"]),
                        school_id,
                        category,
                        int(row["product_id"])
                    ))

                conn.commit()

                st.success(
                    "Prices updated successfully."
                )

            except Exception as e:

                conn.rollback()

                st.error(str(e))

            finally:

                cur.close()
                conn.close()

    else:

        st.info(
            "No products assigned to this category yet."
        )

    # -----------------------------------------------------
    # ASSIGN PRODUCT
    # -----------------------------------------------------

    st.markdown("---")
    st.subheader("➕ Assign Product")

    all_products = get_products()

    product_name = st.selectbox(
        "Product to assign",
        all_products["product_name"].tolist()
    )

    selected = all_products[
        all_products["product_name"] == product_name
    ].iloc[0]

    default_price = float(selected["price"])

    selling_price = st.number_input(
        "Selling Price",
        min_value=0.0,
        value=default_price,
        step=50.0
    )

    if st.button("Assign Product"):

        try:

            execute_query("""
                INSERT INTO school_product_prices
                (
                    school_id,
                    category_name,
                    product_id,
                    price
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s
                )
                ON CONFLICT
                (
                    school_id,
                    category_name,
                    product_id
                )
                DO UPDATE SET
                    price = EXCLUDED.price;
            """, (
                school_id,
                category,
                int(selected["product_id"]),
                selling_price
            ))

            st.success(
                f"{product_name} assigned to {school_name}."
            )

            st.rerun()

        except Exception as e:

            st.error(str(e))

    # -----------------------------------------------------
    # CREATE PRODUCT
    # -----------------------------------------------------

    st.markdown("---")
    st.subheader("🆕 Add New Product")

    col1, col2, col3 = st.columns(3)

    with col1:

        new_product = st.text_input(
            "Product Name"
        )

    with col2:

        new_price = st.number_input(
            "Selling Price",
            min_value=0.0,
            step=50.0
        )

    with col3:

        new_cost = st.number_input(
            "Cost Price",
            min_value=0.0,
            step=50.0
        )

    if st.button("Create Product"):

        if not new_product.strip():

            st.error("Enter a product name.")

        else:

            try:

                execute_query("""
                    INSERT INTO products
                    (
                        product_name,
                        price,
                        cost_price
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        %s
                    )
                    ON CONFLICT (product_name)
                    DO UPDATE SET
                        price = EXCLUDED.price,
                        cost_price = EXCLUDED.cost_price;
                """, (
                    new_product.strip(),
                    new_price,
                    new_cost
                ))

                st.success(
                    "Product created/updated successfully."
                )

                st.rerun()

            except Exception as e:

                st.error(str(e))


# =========================================================
# STOCK MANAGEMENT
# =========================================================

elif menu == "Stock Management":

    st.title("📦 Stock Management")

    schools_df = get_schools()

    school_name = st.selectbox(
        "School",
        schools_df["school_name"].tolist()
    )

    school_id = int(
        schools_df.loc[
            schools_df["school_name"] == school_name,
            "school_id"
        ].iloc[0]
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
            min_value=2024,
            max_value=2100,
            value=datetime.now().year,
            key="stock_year"
        )

    products_df = get_products()

    product_name = st.selectbox(
        "Product",
        products_df["product_name"].tolist()
    )

    selected = products_df[
        products_df["product_name"] == product_name
    ].iloc[0]

    quantity = st.number_input(
        "Quantity brought in",
        min_value=1,
        step=1
    )

    unit_cost = st.number_input(
        "Cost per item",
        min_value=0.0,
        value=float(selected["cost_price"]),
        step=50.0
    )

    if st.button("📦 Add Stock"):

        conn = get_connection()
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
                int(selected["product_id"]),
                quantity,
                term,
                year,
                unit_cost
            ))

            # Update product cost
            cur.execute("""
                UPDATE products
                SET cost_price = %s
                WHERE product_id = %s;
            """, (
                unit_cost,
                int(selected["product_id"])
            ))

            purchase_value = quantity * unit_cost

            # Finance transaction
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
                f"Stock: {quantity} × {product_name}",
                purchase_value,
                term,
                year
            ))

            conn.commit()

            st.success(
                f"{quantity} units of {product_name} added."
            )

        except Exception as e:

            conn.rollback()
            st.error(str(e))

        finally:

            cur.close()
            conn.close()

    # -----------------------------------------------------
    # STOCK REPORT
    # -----------------------------------------------------

    st.markdown("---")
    st.subheader("📊 Current Stock")

    stock_report = query_df("""
        SELECT
            p.product_name,

            COALESCE(
                SUM(s.quantity_brought),
                0
            ) AS brought,

            COALESCE(
                (
                    SELECT SUM(si.quantity)
                    FROM sale_items si
                    JOIN sales sa
                        ON sa.sale_id = si.sale_id
                    WHERE si.product_id = p.product_id
                    AND sa.school_id = %s
                ),
                0
            ) AS sold,

            p.cost_price

        FROM products p

        LEFT JOIN stock s
            ON s.product_id = p.product_id
            AND s.school_id = %s

        GROUP BY
            p.product_id,
            p.product_name,
            p.cost_price

        ORDER BY p.product_name;
    """, (school_id, school_id))

    if not stock_report.empty:

        stock_report["remaining"] = (
            stock_report["brought"]
            - stock_report["sold"]
        )

        stock_report["stock_value"] = (
            stock_report["remaining"]
            * stock_report["cost_price"]
        )

        st.dataframe(
            stock_report,
            use_container_width=True
        )

        low_stock = stock_report[
            stock_report["remaining"] <= 5
        ]

        if not low_stock.empty:

            st.warning(
                "⚠️ Some products have 5 or fewer units remaining."
            )


# =========================================================
# BUSINESS FINANCE
# =========================================================

elif menu == "Business Finance":

    st.title("💰 Business Finance")

    # -----------------------------------------------------
    # INVESTOR CONTRIBUTIONS
    # -----------------------------------------------------

    investors_df = query_df("""
        SELECT
            i.investor_id,
            i.investor_name,
            COALESCE(
                SUM(
                    CASE
                        WHEN ft.transaction_type =
                        'Capital Contribution'
                        THEN ft.amount
                        ELSE 0
                    END
                ),
                0
            ) AS contribution

        FROM investors i

        LEFT JOIN financial_transactions ft
            ON ft.investor_id = i.investor_id

        WHERE i.active = TRUE

        GROUP BY
            i.investor_id,
            i.investor_name

        ORDER BY i.investor_id;
    """)

    total_capital = investors_df["contribution"].sum()

    if total_capital > 0:

        investors_df["ownership_percent"] = (
            investors_df["contribution"]
            / total_capital
            * 100
        )

    st.subheader("👥 Investors")

    st.dataframe(
        investors_df,
        use_container_width=True
    )

    # -----------------------------------------------------
    # ADD CAPITAL
    # -----------------------------------------------------

    st.subheader("➕ Record Investment")

    investor = st.selectbox(
        "Investor",
        ["You", "Boyfriend"]
    )

    investment_amount = st.number_input(
        "Amount",
        min_value=0.0,
        step=5000.0
    )

    investment_term = st.selectbox(
        "Term",
        ["Term 1", "Term 2", "Term 3"],
        key="investment_term"
    )

    investment_year = st.number_input(
        "Year",
        min_value=2024,
        max_value=2100,
        value=datetime.now().year,
        key="investment_year"
    )

    if st.button("Record Investment"):

        investor_id = get_investor_id(investor)

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
            (
                'Capital Contribution',
                'Investment',
                'Additional capital',
                %s,
                %s,
                %s,
                %s
            );
        """, (
            investment_amount,
            investor_id,
            investment_term,
            investment_year
        ))

        st.success("Investment recorded.")
        st.rerun()

    # -----------------------------------------------------
    # FINANCE METRICS
    # -----------------------------------------------------

    finance_df = query_df("""
        SELECT
            transaction_type,
            COALESCE(SUM(amount), 0) AS total
        FROM financial_transactions
        GROUP BY transaction_type
    """)

    def finance_total(transaction_type):

        row = finance_df[
            finance_df["transaction_type"]
            == transaction_type
        ]

        if row.empty:
            return 0

        return float(row.iloc[0]["total"])

    capital = finance_total("Capital Contribution")
    revenue = finance_total("Sales Income")
    expenses = finance_total("Expense")
    other_income = finance_total("Other Income")
    withdrawals = finance_total("Owner Withdrawal")
    distributions = finance_total("Profit Distribution")

    # COGS
    cogs_df = query_df("""
        SELECT
            COALESCE(
                SUM(
                    si.quantity * p.cost_price
                ),
                0
            ) AS cogs

        FROM sale_items si

        JOIN products p
            ON p.product_id = si.product_id;
    """)

    cogs = float(cogs_df.iloc[0]["cogs"])

    gross_profit = revenue - cogs

    net_profit = (
        gross_profit
        + other_income
        - expenses
    )

    roi = 0

    if capital > 0:
        roi = (
            net_profit
            / capital
            * 100
        )

    # Inventory
    inventory_df = query_df("""
        SELECT
            COALESCE(
                SUM(
                    s.quantity_brought
                    * s.unit_cost
                ),
                0
            ) AS inventory_value
        FROM stock s;
    """)

    inventory_value = float(
        inventory_df.iloc[0]["inventory_value"]
    )

    cash_position = (
        capital
        + revenue
        + other_income
        - expenses
        - withdrawals
        - distributions
        - cogs
    )

    # -----------------------------------------------------
    # METRICS
    # -----------------------------------------------------

    st.markdown("---")
    st.subheader("📊 Financial Position")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Capital Invested",
        money(capital)
    )

    c2.metric(
        "Sales Revenue",
        money(revenue)
    )

    c3.metric(
        "Inventory Value",
        money(inventory_value)
    )

    c4.metric(
        "Cash Position",
        money(cash_position)
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "COGS",
        money(cogs)
    )

    c2.metric(
        "Gross Profit",
        money(gross_profit)
    )

    c3.metric(
        "Net Profit",
        money(net_profit)
    )

    c4.metric(
        "ROI",
        f"{roi:.2f}%"
    )

    # -----------------------------------------------------
    # PROFIT EXPLANATION
    # -----------------------------------------------------

    st.markdown("---")

    st.subheader("📈 Business Performance")

    performance = pd.DataFrame({
        "Metric": [
            "Capital Invested",
            "Sales Revenue",
            "Cost of Goods Sold",
            "Gross Profit",
            "Operating Expenses",
            "Other Income",
            "Net Profit",
            "Inventory Value",
            "Cash Position",
            "ROI"
        ],
        "Amount": [
            capital,
            revenue,
            cogs,
            gross_profit,
            expenses,
            other_income,
            net_profit,
            inventory_value,
            cash_position,
            roi
        ]
    })

    st.dataframe(
        performance,
        use_container_width=True
    )

    # -----------------------------------------------------
    # PROFIT SHARE
    # -----------------------------------------------------

    st.subheader("👥 Estimated Profit Share")

    if total_capital > 0:

        share_df = investors_df[
            [
                "investor_name",
                "contribution",
                "ownership_percent"
            ]
        ].copy()

        share_df["estimated_profit_share"] = (
            share_df["ownership_percent"]
            / 100
            * net_profit
        )

        st.dataframe(
            share_df,
            use_container_width=True
        )

        st.caption(
            "This is an estimated contribution-based share. "
            "Actual profit distributions should be agreed by the investors."
        )

    # -----------------------------------------------------
    # MANUAL TRANSACTION
    # -----------------------------------------------------

    st.markdown("---")
    st.subheader("📝 Record Business Transaction")

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
        value="General"
    )

    transaction_description = st.text_input(
        "Description"
    )

    transaction_amount = st.number_input(
        "Amount",
        min_value=0.0,
        step=100.0
    )

    transaction_term = st.selectbox(
        "Term",
        ["Term 1", "Term 2", "Term 3"],
        key="manual_term"
    )

    transaction_year = st.number_input(
        "Year",
        min_value=2024,
        max_value=2100,
        value=datetime.now().year,
        key="manual_year"
    )

    if st.button("Save Transaction"):

        execute_query("""
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
                %s,
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
            transaction_term,
            transaction_year
        ))

        st.success(
            "Transaction saved."
        )

        st.rerun()

    # -----------------------------------------------------
    # LEDGER
    # -----------------------------------------------------

    st.markdown("---")
    st.subheader("📒 Financial Ledger")

    ledger = query_df("""
        SELECT
            ft.transaction_date,
            ft.transaction_type,
            ft.category,
            ft.description,
            ft.amount,
            COALESCE(i.investor_name, '') AS investor,
            ft.term,
            ft.year

        FROM financial_transactions ft

        LEFT JOIN investors i
            ON i.investor_id = ft.investor_id

        ORDER BY ft.transaction_date DESC;
    """)

    st.dataframe(
        ledger,
        use_container_width=True
    )


# =========================================================
# SALES OVERVIEW
# =========================================================

elif menu == "Sales Overview":

    st.title("📊 Sales Overview")

    summary = query_df("""
        SELECT
            COUNT(*) AS total_sales,
            COALESCE(SUM(total_amount), 0) AS revenue,
            COALESCE(AVG(total_amount), 0) AS average_sale
        FROM sales;
    """)

    total_sales = int(
        summary.iloc[0]["total_sales"]
    )

    revenue = float(
        summary.iloc[0]["revenue"]
    )

    average_sale = float(
        summary.iloc[0]["average_sale"]
    )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Number of Sales",
        total_sales
    )

    c2.metric(
        "Revenue",
        money(revenue)
    )

    c3.metric(
        "Average Sale",
        money(average_sale)
    )

    # -----------------------------------------------------
    # BY TERM
    # -----------------------------------------------------

    st.subheader("Revenue by Term")

    term_df = query_df("""
        SELECT
            year,
            term,
            SUM(total_amount) AS revenue
        FROM sales
        GROUP BY year, term
        ORDER BY year, term;
    """)

    if not term_df.empty:

        st.dataframe(
            term_df,
            use_container_width=True
        )

        st.bar_chart(
            term_df.set_index(
                ["year", "term"]
            )["revenue"]
        )

    # -----------------------------------------------------
    # BY SCHOOL
    # -----------------------------------------------------

    st.subheader("Revenue by School")

    school_sales = query_df("""
        SELECT
            s.school_name,
            COUNT(sa.sale_id) AS sales,
            SUM(sa.total_amount) AS revenue

        FROM sales sa

        JOIN schools s
            ON s.school_id = sa.school_id

        GROUP BY s.school_name

        ORDER BY revenue DESC;
    """)

    st.dataframe(
        school_sales,
        use_container_width=True
    )

    if not school_sales.empty:

        st.bar_chart(
            school_sales.set_index(
                "school_name"
            )["revenue"]
        )

    # -----------------------------------------------------
    # TOP PRODUCTS
    # -----------------------------------------------------

    st.subheader("Top Selling Products")

    top_products = query_df("""
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

    st.dataframe(
        top_products,
        use_container_width=True
    )


# =========================================================
# SALES HISTORY
# =========================================================

elif menu == "Sales History":

    st.title("📜 Sales History")

    history = query_df("""
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
            ON s.school_id = sa.school_id

        LEFT JOIN customers c
            ON c.customer_id = sa.customer_id

        ORDER BY sa.sale_date DESC;
    """)

    if history.empty:

        st.info(
            "No sales have been recorded yet."
        )

    else:

        st.dataframe(
            history,
            use_container_width=True
        )

        st.download_button(
            "Download Sales CSV",
            history.to_csv(index=False),
            "sales_history.csv",
            "text/csv"
        )


# =========================================================
# ML & FORECASTING
# =========================================================

elif menu == "ML & Forecasting":

    st.title("🤖 ML & Forecasting")

    st.write(
        "This section prepares the business data for predictive analysis."
    )

    # -----------------------------------------------------
    # REVENUE TREND
    # -----------------------------------------------------

    st.subheader("📈 Revenue Trend")

    daily_sales = query_df("""
        SELECT
            DATE(sale_date) AS sale_date,
            SUM(total_amount) AS revenue
        FROM sales
        GROUP BY DATE(sale_date)
        ORDER BY sale_date;
    """)

    if daily_sales.empty:

        st.info(
            "More sales data is needed before forecasting can begin."
        )

    else:

        daily_sales["sale_date"] = pd.to_datetime(
            daily_sales["sale_date"]
        )

        st.line_chart(
            daily_sales.set_index(
                "sale_date"
            )["revenue"]
        )

        # -------------------------------------------------
        # SIMPLE FORECAST
        # -------------------------------------------------

        if len(daily_sales) >= 3:

            recent_average = daily_sales[
                "revenue"
            ].tail(7).mean()

            st.metric(
                "Recent Average Daily Revenue",
                money(recent_average)
            )

            forecast_days = st.slider(
                "Forecast Days",
                1,
                30,
                7
            )

            forecast = pd.DataFrame({
                "Day": range(
                    1,
                    forecast_days + 1
                ),
                "Forecast Revenue": [
                    recent_average
                    for _ in range(forecast_days)
                ]
            })

            st.dataframe(
                forecast,
                use_container_width=True
            )

        # -------------------------------------------------
        # PRODUCT DEMAND
        # -------------------------------------------------

        st.subheader("📦 Product Demand")

        demand = query_df("""
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

        st.dataframe(
            demand,
            use_container_width=True
        )

        if not demand.empty:

            st.bar_chart(
                demand.set_index(
                    "product_name"
                )["quantity_sold"]
            )

    # -----------------------------------------------------
    # INVESTMENT ANALYSIS
    # -----------------------------------------------------

    st.markdown("---")
    st.subheader("💰 Investment Analysis")

    investment = query_df("""
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
                ),
                0
            ) AS invested

        FROM investors i

        LEFT JOIN financial_transactions ft
            ON ft.investor_id = i.investor_id

        GROUP BY i.investor_name;
    """)

    if not investment.empty:

        total_investment = investment[
            "invested"
        ].sum()

        investment["ownership_percent"] = (
            investment["invested"]
            / total_investment
            * 100
        )

        st.dataframe(
            investment,
            use_container_width=True
        )

    # -----------------------------------------------------
    # FUTURE ML
    # -----------------------------------------------------

    st.markdown("---")

    st.subheader("🚀 Planned Intelligence")

    st.write("""
    The system can later use machine learning for:

    - Sales forecasting
    - Product demand forecasting
    - Stock replenishment prediction
    - School-by-school sales analysis
    - Profit forecasting
    - Investment return analysis
    - Seasonal demand patterns
    - Identifying fast-moving and slow-moving products
    """)
