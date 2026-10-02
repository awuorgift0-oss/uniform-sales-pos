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
            "Rename investors or toggle active. "
            "Gift and Ken are seeded by setup."
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
            "Fix test capital (150,000 / 100,000) to the "
            "real amounts. Edit any transaction inline."
        )

        # Optional filter by type
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
            # Build investor lookup for the dropdown
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
                    # Build name → id map
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

            # Line items
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

                # Recompute line_total on save
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

                        # Recompute sale total
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
