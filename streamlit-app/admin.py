import streamlit as st
from db import get_connection
from utils import format_currency, get_status_color, level_badge
import analytics


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

def admin_products() -> None:
    st.subheader("🏷️ Products Management")
    tab_list, tab_add = st.tabs(["Product List", "Add Product"])

    conn = get_connection()
    try:
        products = conn.execute(
            "SELECT * FROM Product_Inventory_View ORDER BY id"
        ).fetchall()
        suppliers = conn.execute("SELECT id, name FROM Suppliers").fetchall()
    finally:
        conn.close()

    with tab_list:
        for p in products:
            with st.expander(f"**#{p['id']} {p['name']}** — {format_currency(p['price'])}"):
                col1, col2 = st.columns(2)
                col1.write(f"Category: {p['category']}")
                col1.write(f"Supplier: {p['supplier_name'] or 'N/A'}")
                col1.write(f"Description: {p['description'] or 'N/A'}")
                col2.write(f"Stock: {p['stock_quantity']} / {p['max_stock']}")
                col2.write(f"Stock %: {p['stock_percentage']:.1f}%" if p['stock_percentage'] is not None else "N/A")
                col2.write(f"Restock Date: {p['restock_date'] or 'N/A'}")

                with st.form(f"edit_prod_{p['id']}"):
                    new_price = st.number_input("Price (₹)", value=float(p["price"]), min_value=0.0, key=f"pr_{p['id']}")
                    new_desc  = st.text_input("Description", value=p["description"] or "", key=f"desc_{p['id']}")
                    if st.form_submit_button("Update Product"):
                        conn2 = get_connection()
                        try:
                            conn2.execute(
                                "UPDATE Products SET price=?, description=? WHERE id=?",
                                (new_price, new_desc, p["id"]),
                            )
                            conn2.commit()
                            st.success("Product updated.")
                            st.rerun()
                        finally:
                            conn2.close()

    with tab_add:
        sup_options = {s["name"]: s["id"] for s in suppliers}
        with st.form("add_product_form"):
            name        = st.text_input("Product Name")
            description = st.text_area("Description")
            price       = st.number_input("Price (₹)", min_value=0.0, value=100.0)
            category    = st.text_input("Category")
            supplier    = st.selectbox("Supplier", list(sup_options.keys()))
            stock_qty   = st.number_input("Initial Stock", min_value=0, value=50)
            max_stock   = st.number_input("Max Stock",     min_value=1, value=100)
            restock_dt  = st.date_input("Expected Restock Date")
            submitted   = st.form_submit_button("Add Product")

        if submitted:
            if not name:
                st.error("Product name is required.")
            else:
                conn3 = get_connection()
                try:
                    conn3.execute(
                        "INSERT INTO Products (name, description, price, category, supplier_id) VALUES (?,?,?,?,?)",
                        (name, description, price, category, sup_options[supplier]),
                    )
                    conn3.commit()
                    prod_id = conn3.execute("SELECT last_insert_rowid()").fetchone()[0]
                    conn3.execute(
                        "INSERT INTO Inventory (product_id, stock_quantity, max_stock, restock_date) VALUES (?,?,?,?)",
                        (prod_id, stock_qty, max_stock, restock_dt.isoformat()),
                    )
                    conn3.commit()
                    st.success(f"Product '{name}' added.")
                    st.rerun()
                except Exception as exc:
                    conn3.rollback()
                    st.error(f"Failed: {exc}")
                finally:
                    conn3.close()


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------

def admin_inventory() -> None:
    st.subheader("📦 Inventory Management")
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM Product_Inventory_View ORDER BY stock_percentage ASC"
        ).fetchall()
    finally:
        conn.close()

    for row in rows:
        pct = row["stock_percentage"] or 0
        color = "🔴" if pct < 20 else ("🟡" if pct < 50 else "🟢")
        with st.expander(f"{color} **{row['name']}** — {row['stock_quantity']}/{row['max_stock']} units ({pct:.1f}%)"):
            st.write(f"Restock Date: {row['restock_date'] or 'N/A'}")
            with st.form(f"inv_{row['id']}"):
                new_qty      = st.number_input("Stock Quantity",  value=int(row["stock_quantity"]), min_value=0, key=f"sq_{row['id']}")
                new_max      = st.number_input("Max Stock",       value=int(row["max_stock"]),      min_value=1, key=f"ms_{row['id']}")
                new_restock  = st.text_input("Restock Date (YYYY-MM-DD)", value=row["restock_date"] or "", key=f"rd_{row['id']}")
                if st.form_submit_button("Update Inventory"):
                    conn2 = get_connection()
                    try:
                        conn2.execute(
                            "UPDATE Inventory SET stock_quantity=?, max_stock=?, restock_date=? WHERE product_id=?",
                            (new_qty, new_max, new_restock or None, row["id"]),
                        )
                        conn2.commit()
                        st.success("Inventory updated.")
                        st.rerun()
                    finally:
                        conn2.close()


# ---------------------------------------------------------------------------
# Suppliers
# ---------------------------------------------------------------------------

def admin_suppliers() -> None:
    st.subheader("🚚 Suppliers")
    tab_list, tab_add = st.tabs(["Supplier List", "Add Supplier"])

    conn = get_connection()
    try:
        suppliers = conn.execute("SELECT * FROM Suppliers ORDER BY id").fetchall()
    finally:
        conn.close()

    with tab_list:
        if not suppliers:
            st.info("No suppliers.")
        for s in suppliers:
            with st.expander(f"**{s['name']}**"):
                st.write(f"Email: {s['contact_email'] or 'N/A'}")
                st.write(f"Phone: {s['phone'] or 'N/A'}")
                st.write(f"Address: {s['address'] or 'N/A'}")

    with tab_add:
        with st.form("add_supplier_form"):
            s_name  = st.text_input("Supplier Name")
            s_email = st.text_input("Contact Email")
            s_phone = st.text_input("Phone")
            s_addr  = st.text_area("Address")
            if st.form_submit_button("Add Supplier"):
                if not s_name:
                    st.error("Supplier name is required.")
                else:
                    conn2 = get_connection()
                    try:
                        conn2.execute(
                            "INSERT INTO Suppliers (name, contact_email, phone, address) VALUES (?,?,?,?)",
                            (s_name, s_email, s_phone, s_addr),
                        )
                        conn2.commit()
                        st.success(f"Supplier '{s_name}' added.")
                        st.rerun()
                    finally:
                        conn2.close()


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------

def admin_customers() -> None:
    st.subheader("👥 Customer Management")
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM Customer_Order_Summary ORDER BY total_spent DESC"
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        st.info("No customers.")
        return

    for row in rows:
        with st.expander(f"**{row['customer_name']}** — {row['email']}"):
            col1, col2 = st.columns(2)
            col1.write(f"Orders: {row['total_orders']}")
            col1.write(f"Total Spent: {format_currency(row['total_spent'] or 0)}")
            col2.write(f"Rewards: {row['reward_points']} pts")
            col2.write(f"Level: {level_badge(row['loyalty_level'])}")


# ---------------------------------------------------------------------------
# Salesmen
# ---------------------------------------------------------------------------

def admin_salesmen() -> None:
    st.subheader("🧑‍💼 Salesman Management")
    tab_list, tab_add = st.tabs(["Salesman List", "Add Salesman"])

    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM Salesman_Performance_View ORDER BY total_sales DESC").fetchall()
    finally:
        conn.close()

    with tab_list:
        if not rows:
            st.info("No salesmen.")
        for row in rows:
            with st.expander(f"**{row['salesman_name']}** — {row['region']}"):
                col1, col2 = st.columns(2)
                col1.write(f"Total Orders: {row['total_orders']}")
                col1.write(f"Total Sales: {format_currency(row['total_sales'] or 0)}")
                col2.write(f"Commission Rate: {row['commission_rate']*100:.1f}%")
                col2.write(f"Commission Earned: {format_currency(row['commission_earned'] or 0)}")

    with tab_add:
        with st.form("add_salesman_form"):
            sm_name   = st.text_input("Full Name")
            sm_email  = st.text_input("Email")
            sm_pass   = st.text_input("Password", type="password")
            sm_phone  = st.text_input("Phone")
            sm_region = st.text_input("Region")
            sm_comm   = st.slider("Commission Rate (%)", 1, 20, 5)
            if st.form_submit_button("Add Salesman"):
                if not sm_name or not sm_email or not sm_pass:
                    st.error("Name, email, and password are required.")
                else:
                    from utils import hash_password
                    conn2 = get_connection()
                    try:
                        existing = conn2.execute("SELECT id FROM Users WHERE email=?", (sm_email,)).fetchone()
                        if existing:
                            st.error("Email already exists.")
                        else:
                            conn2.execute(
                                "INSERT INTO Users (email, password_hash, role) VALUES (?,?,?)",
                                (sm_email, hash_password(sm_pass), "salesman"),
                            )
                            conn2.commit()
                            u_id = conn2.execute("SELECT last_insert_rowid()").fetchone()[0]
                            conn2.execute(
                                "INSERT INTO Salesmen (user_id, name, phone, region, commission_rate) VALUES (?,?,?,?,?)",
                                (u_id, sm_name, sm_phone, sm_region, sm_comm / 100),
                            )
                            conn2.commit()
                            st.success(f"Salesman '{sm_name}' added.")
                            st.rerun()
                    except Exception as exc:
                        conn2.rollback()
                        st.error(f"Failed: {exc}")
                    finally:
                        conn2.close()


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

def admin_orders() -> None:
    st.subheader("📋 All Orders")
    status_filter = st.selectbox(
        "Filter by status",
        ["All", "pending", "accepted", "rejected", "processing", "shipped", "delivered", "cancelled"],
    )

    conn = get_connection()
    try:
        query = """
            SELECT o.id, o.status, o.total_amount, o.created_at,
                   c.name  AS customer_name,
                   sm.name AS salesman_name,
                   sm.id   AS salesman_id
            FROM   Orders o
            JOIN   Customers c ON c.id = o.customer_id
            LEFT JOIN Salesmen sm ON sm.id = o.salesman_id
        """
        params: list = []
        if status_filter != "All":
            query += " WHERE o.status = ?"
            params.append(status_filter)
        query += " ORDER BY o.created_at DESC"
        orders = conn.execute(query, params).fetchall()

        salesmen = conn.execute("SELECT id, name FROM Salesmen").fetchall()
    finally:
        conn.close()

    salesman_map = {s["name"]: s["id"] for s in salesmen}
    salesman_options = list(salesman_map.keys())

    if not orders:
        st.info("No orders found.")
        return

    for order in orders:
        icon = get_status_color(order["status"])
        with st.expander(
            f"Order #{order['id']} — {icon} {order['status'].capitalize()} — {format_currency(order['total_amount'])}"
        ):
            st.write(f"**Customer:** {order['customer_name']}")
            st.write(f"**Salesman:** {order['salesman_name'] or 'Unassigned'}")
            st.write(f"**Date:** {order['created_at'][:10]}")

            conn2 = get_connection()
            try:
                items = conn2.execute("""
                    SELECT p.name, oi.quantity, oi.unit_price
                    FROM   Order_Items oi
                    JOIN   Products p ON p.id = oi.product_id
                    WHERE  oi.order_id = ?
                """, (order["id"],)).fetchall()
            finally:
                conn2.close()
            for item in items:
                st.write(f"  • {item['name']} × {item['quantity']} @ {format_currency(item['unit_price'])}")

            col1, col2 = st.columns(2)
            # Status update
            with col1.form(f"status_form_{order['id']}"):
                new_status = st.selectbox(
                    "Update Status",
                    ["pending","accepted","rejected","processing","shipped","delivered","cancelled"],
                    index=["pending","accepted","rejected","processing","shipped","delivered","cancelled"].index(order["status"]),
                    key=f"st_sel_{order['id']}",
                )
                if st.form_submit_button("Update Status"):
                    conn3 = get_connection()
                    try:
                        conn3.execute("UPDATE Orders SET status=? WHERE id=?", (new_status, order["id"]))
                        conn3.commit()
                        st.success("Status updated.")
                        st.rerun()
                    finally:
                        conn3.close()

            # Assign salesman
            if salesman_options:
                with col2.form(f"assign_form_{order['id']}"):
                    sel_sm = st.selectbox("Assign Salesman", salesman_options, key=f"sm_sel_{order['id']}")
                    if st.form_submit_button("Assign"):
                        conn3 = get_connection()
                        try:
                            conn3.execute(
                                "UPDATE Orders SET salesman_id=? WHERE id=?",
                                (salesman_map[sel_sm], order["id"]),
                            )
                            conn3.commit()
                            st.success(f"Assigned to {sel_sm}.")
                            st.rerun()
                        finally:
                            conn3.close()


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

def admin_dashboard() -> None:
    st.subheader("📊 Admin Dashboard")
    conn = get_connection()
    try:
        total_products  = conn.execute("SELECT COUNT(*) FROM Products").fetchone()[0]
        total_orders    = conn.execute("SELECT COUNT(*) FROM Orders").fetchone()[0]
        total_customers = conn.execute("SELECT COUNT(*) FROM Customers").fetchone()[0]
        total_salesmen  = conn.execute("SELECT COUNT(*) FROM Salesmen").fetchone()[0]
        total_revenue   = conn.execute(
            "SELECT COALESCE(SUM(total_amount),0) FROM Orders WHERE status NOT IN ('cancelled','rejected')"
        ).fetchone()[0]
        pending_orders  = conn.execute(
            "SELECT COUNT(*) FROM Orders WHERE status='pending'"
        ).fetchone()[0]
    finally:
        conn.close()

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Products",  total_products)
    col2.metric("Total Orders",    total_orders)
    col3.metric("Total Revenue",   format_currency(total_revenue))

    col4, col5, col6 = st.columns(3)
    col4.metric("Customers",       total_customers)
    col5.metric("Salesmen",        total_salesmen)
    col6.metric("Pending Orders",  pending_orders)

    st.markdown("---")
    fig = analytics.monthly_revenue_chart()
    if fig:
        st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

def admin_analytics() -> None:
    st.subheader("📈 Analytics")
    col1, col2 = st.columns(2)
    with col1:
        fig = analytics.monthly_revenue_chart()
        if fig:
            st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = analytics.top_selling_products_chart()
        if fig:
            st.plotly_chart(fig, use_container_width=True)

    fig = analytics.inventory_utilization_chart()
    if fig:
        st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Low Stock
# ---------------------------------------------------------------------------

def admin_low_stock() -> None:
    st.subheader("⚠️ Low Stock Alerts")
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT name, stock_quantity, max_stock, stock_percentage, restock_date
            FROM   Product_Inventory_View
            WHERE  stock_percentage < 20
            ORDER  BY stock_percentage ASC
        """).fetchall()
    finally:
        conn.close()

    if not rows:
        st.success("All products are well-stocked!")
        return

    for row in rows:
        pct = row["stock_percentage"] or 0
        st.error(
            f"🔴 **{row['name']}** — {row['stock_quantity']}/{row['max_stock']} units "
            f"({pct:.1f}%) | Restock: {row['restock_date'] or 'N/A'}"
        )


# ---------------------------------------------------------------------------
# Top Customers / Salesmen
# ---------------------------------------------------------------------------

def admin_top_customers() -> None:
    st.subheader("🏆 Top Customers")
    fig = analytics.top_customers_chart(top_n=10)
    if fig:
        st.plotly_chart(fig, use_container_width=True)

    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT customer_name, email, total_orders,
                   total_spent, reward_points, loyalty_level
            FROM   Customer_Order_Summary
            ORDER  BY total_spent DESC
            LIMIT  10
        """).fetchall()
    finally:
        conn.close()

    for i, row in enumerate(rows, 1):
        with st.expander(f"#{i} {row['customer_name']} — {format_currency(row['total_spent'] or 0)}"):
            st.write(f"Email: {row['email']}")
            st.write(f"Orders: {row['total_orders']}  |  Points: {row['reward_points']}  |  Level: {level_badge(row['loyalty_level'])}")


def admin_top_salesmen() -> None:
    st.subheader("🥇 Top Salesmen")
    fig = analytics.top_salesmen_chart(top_n=10)
    if fig:
        st.plotly_chart(fig, use_container_width=True)

    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT salesman_name, region, total_orders,
                   total_sales, commission_rate, commission_earned
            FROM   Salesman_Performance_View
            ORDER  BY total_sales DESC
            LIMIT  10
        """).fetchall()
    finally:
        conn.close()

    for i, row in enumerate(rows, 1):
        with st.expander(f"#{i} {row['salesman_name']} — {format_currency(row['total_sales'] or 0)}"):
            st.write(f"Region: {row['region']}")
            st.write(f"Orders: {row['total_orders']}  |  Commission: {row['commission_rate']*100:.1f}%  |  Earned: {format_currency(row['commission_earned'] or 0)}")


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------

def show_admin_app(user: dict) -> None:
    with st.sidebar:
        st.title("📦 Admin Portal")
        st.markdown("**Welcome, Admin!**")
        page = st.radio(
            "Navigate",
            [
                "Dashboard", "Products", "Inventory", "Customers",
                "Salesmen", "Orders", "Suppliers", "Analytics",
                "Low Stock", "Top Customers", "Top Salesmen",
            ],
            label_visibility="collapsed",
        )
        st.markdown("---")
        if st.button("🚪 Logout"):
            st.session_state.clear()
            st.rerun()

    routing = {
        "Dashboard":    admin_dashboard,
        "Products":     admin_products,
        "Inventory":    admin_inventory,
        "Customers":    admin_customers,
        "Salesmen":     admin_salesmen,
        "Orders":       admin_orders,
        "Suppliers":    admin_suppliers,
        "Analytics":    admin_analytics,
        "Low Stock":    admin_low_stock,
        "Top Customers": admin_top_customers,
        "Top Salesmen": admin_top_salesmen,
    }
    routing[page]()
