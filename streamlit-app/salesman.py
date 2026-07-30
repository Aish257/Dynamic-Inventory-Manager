import streamlit as st
from db import get_connection
from utils import format_currency, get_status_color


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_salesman_id(user_id: int) -> int | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id FROM Salesmen WHERE user_id=?", (user_id,)
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

def salesman_dashboard(salesman_id: int, user: dict) -> None:
    st.subheader("📊 Salesman Dashboard")
    conn = get_connection()
    try:
        perf = conn.execute(
            "SELECT * FROM Salesman_Performance_View WHERE salesman_id=?",
            (salesman_id,),
        ).fetchone()
        pending_count = conn.execute(
            "SELECT COUNT(*) FROM Orders WHERE salesman_id=? AND status='pending'",
            (salesman_id,),
        ).fetchone()[0]
    finally:
        conn.close()

    if perf:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Orders",      perf["total_orders"])
        col2.metric("Total Sales",       format_currency(perf["total_sales"] or 0))
        col3.metric("Commission Earned", format_currency(perf["commission_earned"] or 0))
        col4.metric("Pending Orders",    pending_count)

        st.markdown("---")
        st.write(f"**Region:** {perf['region']}  |  **Commission Rate:** {perf['commission_rate']*100:.1f}%")


def salesman_assigned_orders(salesman_id: int, user_id: int) -> None:
    st.subheader("📋 Assigned Orders")

    status_filter = st.selectbox(
        "Filter by status",
        ["All", "pending", "accepted", "rejected", "processing", "shipped", "delivered", "cancelled"],
    )

    conn = get_connection()
    try:
        query = """
            SELECT o.id, o.status, o.total_amount, o.created_at,
                   c.name AS customer_name
            FROM   Orders o
            JOIN   Customers c ON c.id = o.customer_id
            WHERE  o.salesman_id = ?
        """
        params: list = [salesman_id]
        if status_filter != "All":
            query += " AND o.status = ?"
            params.append(status_filter)
        query += " ORDER BY o.created_at DESC"

        orders = conn.execute(query, params).fetchall()
    finally:
        conn.close()

    if not orders:
        st.info("No orders found.")
        return

    for order in orders:
        icon = get_status_color(order["status"])
        with st.expander(
            f"Order #{order['id']} — {icon} {order['status'].capitalize()} — {format_currency(order['total_amount'])}"
        ):
            st.write(f"**Customer:** {order['customer_name']}")
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

            if order["status"] == "pending":
                col1, col2 = st.columns(2)
                if col1.button("✅ Accept", key=f"acc_{order['id']}"):
                    _update_order_status(order["id"], "accepted", user_id, order["id"])
                    st.rerun()
                if col2.button("❌ Reject", key=f"rej_{order['id']}"):
                    _update_order_status(order["id"], "rejected", user_id, order["id"])
                    st.rerun()
            elif order["status"] == "accepted":
                new_status = st.selectbox(
                    "Update status",
                    ["processing", "shipped", "delivered"],
                    key=f"sel_{order['id']}",
                )
                if st.button("Update", key=f"upd_{order['id']}"):
                    _update_order_status(order["id"], new_status, user_id, order["id"])
                    st.rerun()


def _update_order_status(order_id: int, new_status: str, salesman_user_id: int, display_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE Orders SET status=? WHERE id=?",
            (new_status, order_id),
        )
        # Notify customer
        row = conn.execute(
            """SELECT u.id FROM Users u
               JOIN Customers c ON c.user_id = u.id
               JOIN Orders    o ON o.customer_id = c.id
               WHERE o.id = ?""",
            (order_id,),
        ).fetchone()
        if row:
            conn.execute(
                "INSERT INTO Notifications (user_id, message) VALUES (?,?)",
                (row[0], f"Your order #{display_id} status changed to: {new_status}."),
            )
        conn.commit()
        st.success(f"Order #{display_id} updated to {new_status}.")
    except Exception as exc:
        conn.rollback()
        st.error(f"Update failed: {exc}")
    finally:
        conn.close()


def salesman_customers(salesman_id: int) -> None:
    st.subheader("👥 My Customers")
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT DISTINCT c.name, u.email, c.phone, c.address,
                   COUNT(o.id) AS orders_count,
                   SUM(o.total_amount) AS total_spent
            FROM   Orders o
            JOIN   Customers c ON c.id = o.customer_id
            JOIN   Users     u ON u.id = c.user_id
            WHERE  o.salesman_id = ?
            GROUP  BY c.id, c.name, u.email, c.phone, c.address
            ORDER  BY total_spent DESC
        """, (salesman_id,)).fetchall()
    finally:
        conn.close()

    if not rows:
        st.info("No customers assigned yet.")
        return

    for row in rows:
        with st.expander(f"**{row['name']}** — {row['email']}"):
            st.write(f"Phone: {row['phone'] or 'N/A'}")
            st.write(f"Address: {row['address'] or 'N/A'}")
            st.write(f"Orders: {row['orders_count']}  |  Total Spent: {format_currency(row['total_spent'] or 0)}")


def salesman_performance(salesman_id: int) -> None:
    st.subheader("🏅 Performance Dashboard")
    conn = get_connection()
    try:
        perf = conn.execute(
            "SELECT * FROM Salesman_Performance_View WHERE salesman_id=?",
            (salesman_id,),
        ).fetchone()
        monthly = conn.execute("""
            SELECT strftime('%Y-%m', o.created_at) AS month,
                   COUNT(o.id)                     AS orders,
                   SUM(o.total_amount)             AS revenue
            FROM   Orders o
            WHERE  o.salesman_id = ? AND o.status NOT IN ('cancelled','rejected')
            GROUP  BY month
            ORDER  BY month
        """, (salesman_id,)).fetchall()
    finally:
        conn.close()

    if perf:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Sales",       format_currency(perf["total_sales"] or 0))
        col2.metric("Commission",        format_currency(perf["commission_earned"] or 0))
        col3.metric("Total Orders",      perf["total_orders"])

    if monthly:
        import plotly.express as px
        months   = [r["month"]   for r in monthly]
        revenues = [r["revenue"] for r in monthly]
        fig = px.line(
            x=months, y=revenues,
            markers=True,
            labels={"x": "Month", "y": "Revenue (₹)"},
            title="My Monthly Sales",
        )
        st.plotly_chart(fig, use_container_width=True)


def salesman_reports(salesman_id: int) -> None:
    st.subheader("📑 Reports")
    conn = get_connection()
    try:
        status_counts = conn.execute("""
            SELECT status, COUNT(*) AS cnt
            FROM   Orders
            WHERE  salesman_id = ?
            GROUP  BY status
        """, (salesman_id,)).fetchall()
    finally:
        conn.close()

    if status_counts:
        import plotly.express as px
        statuses = [r["status"] for r in status_counts]
        counts   = [r["cnt"]    for r in status_counts]
        fig = px.pie(
            names=statuses, values=counts,
            title="Order Status Distribution",
            hole=0.3,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No order data available.")


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------

def show_salesman_app(user: dict) -> None:
    salesman_id = _get_salesman_id(user["id"])
    if salesman_id is None:
        st.error("Salesman profile not found.")
        return

    with st.sidebar:
        st.title("📦 Salesman Portal")
        st.markdown("**Welcome!**")
        page = st.radio(
            "Navigate",
            ["Dashboard", "Assigned Orders", "Customers", "Performance", "Reports"],
            label_visibility="collapsed",
        )
        st.markdown("---")
        if st.button("🚪 Logout"):
            st.session_state.clear()
            st.rerun()

    if page == "Dashboard":
        salesman_dashboard(salesman_id, user)
    elif page == "Assigned Orders":
        salesman_assigned_orders(salesman_id, user["id"])
    elif page == "Customers":
        salesman_customers(salesman_id)
    elif page == "Performance":
        salesman_performance(salesman_id)
    elif page == "Reports":
        salesman_reports(salesman_id)
