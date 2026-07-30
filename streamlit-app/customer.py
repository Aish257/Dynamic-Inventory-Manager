import streamlit as st
from db import get_connection
from utils import format_currency, get_status_color, level_badge, calculate_reward_points, get_loyalty_level


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_customer_id(user_id: int) -> int | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id FROM Customers WHERE user_id=?", (user_id,)
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def _get_rewards(customer_id: int) -> dict:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT points, level FROM Rewards WHERE customer_id=?", (customer_id,)
        ).fetchone()
        if row:
            return {"points": row["points"], "level": row["level"]}
        return {"points": 0, "level": "Bronze"}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

def customer_dashboard(customer_id: int, user: dict) -> None:
    st.subheader("🏠 Customer Dashboard")

    conn = get_connection()
    try:
        summary = conn.execute(
            "SELECT * FROM Customer_Order_Summary WHERE customer_id=?",
            (customer_id,),
        ).fetchone()
        notifs = conn.execute(
            "SELECT message, created_at FROM Notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 5",
            (user["id"],),
        ).fetchall()
    finally:
        conn.close()

    if summary:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Orders",   summary["total_orders"])
        col2.metric("Total Spent",    format_currency(summary["total_spent"] or 0))
        col3.metric("Reward Points",  summary["reward_points"])
        col4.metric("Loyalty Level",  level_badge(summary["loyalty_level"]))

    st.markdown("---")
    st.subheader("🔔 Recent Notifications")
    if notifs:
        for n in notifs:
            st.info(f"**{n['created_at'][:10]}** — {n['message']}")
    else:
        st.caption("No notifications yet.")


def customer_products(customer_id: int) -> None:
    st.subheader("🛒 Products")
    search = st.text_input("Search products", "")

    conn = get_connection()
    try:
        query = """
            SELECT id, name, description, price, category,
                   supplier_name, stock_quantity, stock_percentage
            FROM   Product_Inventory_View
            WHERE  stock_quantity > 0
        """
        params: list = []
        if search:
            query += " AND (name LIKE ? OR category LIKE ?)"
            params += [f"%{search}%", f"%{search}%"]

        rows = conn.execute(query, params).fetchall()

        # Wishlist lookup for current customer
        wishlist_ids = {
            r[0] for r in conn.execute(
                "SELECT product_id FROM Wishlist WHERE customer_id=?", (customer_id,)
            ).fetchall()
        }
    finally:
        conn.close()

    if not rows:
        st.info("No products available.")
        return

    # Cart init
    if "cart" not in st.session_state:
        st.session_state["cart"] = {}

    for row in rows:
        with st.expander(f"**{row['name']}**  —  {format_currency(row['price'])}"):
            col1, col2, col3 = st.columns([2, 1, 1])
            col1.write(row["description"] or "")
            col1.caption(f"Category: {row['category']} | Supplier: {row['supplier_name']}")
            col1.caption(
                f"Stock: {row['stock_quantity']} units ({row['stock_percentage']:.1f}%)"
                if row["stock_percentage"] is not None else f"Stock: {row['stock_quantity']} units"
            )

            qty = col2.number_input(
                "Qty", min_value=1, max_value=int(row["stock_quantity"]),
                value=1, key=f"qty_{row['id']}"
            )
            if col2.button("Add to Cart", key=f"cart_{row['id']}"):
                cart = st.session_state["cart"]
                if row["id"] in cart:
                    cart[row["id"]]["qty"] += qty
                else:
                    cart[row["id"]] = {"name": row["name"], "price": row["price"], "qty": qty}
                st.success(f"Added {qty}x {row['name']} to cart.")

            in_wish = row["id"] in wishlist_ids
            btn_label = "💔 Remove Wishlist" if in_wish else "❤️ Wishlist"
            if col3.button(btn_label, key=f"wish_{row['id']}"):
                _toggle_wishlist(customer_id, row["id"], in_wish)
                st.rerun()

    # Cart panel
    cart = st.session_state.get("cart", {})
    if cart:
        st.markdown("---")
        st.subheader("🛒 Your Cart")
        total = 0.0
        for pid, item in list(cart.items()):
            col1, col2, col3 = st.columns([3, 1, 1])
            col1.write(f"**{item['name']}** × {item['qty']}")
            subtotal = item["price"] * item["qty"]
            col2.write(format_currency(subtotal))
            total += subtotal
            if col3.button("Remove", key=f"rm_{pid}"):
                del cart[pid]
                st.rerun()

        st.write(f"**Total: {format_currency(total)}**")
        st.caption(f"You'll earn {calculate_reward_points(total)} reward points.")
        if st.button("Place Order", type="primary"):
            _place_order(customer_id, cart)


def _toggle_wishlist(customer_id: int, product_id: int, in_wish: bool) -> None:
    conn = get_connection()
    try:
        if in_wish:
            conn.execute(
                "DELETE FROM Wishlist WHERE customer_id=? AND product_id=?",
                (customer_id, product_id),
            )
        else:
            conn.execute(
                "INSERT OR IGNORE INTO Wishlist (customer_id, product_id) VALUES (?,?)",
                (customer_id, product_id),
            )
        conn.commit()
    finally:
        conn.close()


def _place_order(customer_id: int, cart: dict) -> None:
    if not cart:
        st.warning("Cart is empty.")
        return

    conn = get_connection()
    try:
        # Pick the salesman with fewest pending orders
        salesman_row = conn.execute("""
            SELECT sm.id
            FROM   Salesmen sm
            LEFT JOIN Orders o ON sm.id = o.salesman_id AND o.status = 'pending'
            GROUP  BY sm.id
            ORDER  BY COUNT(o.id) ASC
            LIMIT  1
        """).fetchone()
        salesman_id = salesman_row[0] if salesman_row else None

        total = sum(item["price"] * item["qty"] for item in cart.values())

        conn.execute(
            "INSERT INTO Orders (customer_id, salesman_id, status, total_amount) VALUES (?,?,?,?)",
            (customer_id, salesman_id, "pending", total),
        )
        conn.commit()

        order_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        for pid, item in cart.items():
            conn.execute(
                "INSERT INTO Order_Items (order_id, product_id, quantity, unit_price) VALUES (?,?,?,?)",
                (order_id, pid, item["qty"], item["price"]),
            )
            # Reduce stock
            conn.execute(
                "UPDATE Inventory SET stock_quantity = MAX(0, stock_quantity - ?) WHERE product_id=?",
                (item["qty"], pid),
            )

        # Notify customer
        conn.execute(
            "INSERT INTO Notifications (user_id, message) VALUES (?,?)",
            (
                conn.execute(
                    "SELECT u.id FROM Users u JOIN Customers c ON c.user_id=u.id WHERE c.id=?",
                    (customer_id,),
                ).fetchone()[0],
                f"Your order #{order_id} has been placed successfully!",
            ),
        )
        conn.commit()

        st.session_state["cart"] = {}
        st.success(f"Order #{order_id} placed! Total: {format_currency(total)}")
        st.rerun()

    except Exception as exc:
        conn.rollback()
        st.error(f"Order failed: {exc}")
    finally:
        conn.close()


def customer_orders(customer_id: int) -> None:
    st.subheader("📦 My Orders")
    conn = get_connection()
    try:
        orders = conn.execute("""
            SELECT o.id, o.status, o.total_amount, o.created_at,
                   sm.name AS salesman_name
            FROM   Orders o
            LEFT JOIN Salesmen sm ON sm.id = o.salesman_id
            WHERE  o.customer_id = ?
            ORDER  BY o.created_at DESC
        """, (customer_id,)).fetchall()
    finally:
        conn.close()

    if not orders:
        st.info("No orders yet.")
        return

    for order in orders:
        icon = get_status_color(order["status"])
        with st.expander(
            f"Order #{order['id']} — {icon} {order['status'].capitalize()} — {format_currency(order['total_amount'])}"
        ):
            st.write(f"**Date:** {order['created_at'][:10]}")
            st.write(f"**Salesman:** {order['salesman_name'] or 'Not assigned'}")
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
                st.write(
                    f"  • {item['name']} × {item['quantity']} @ {format_currency(item['unit_price'])}"
                )


def customer_wishlist(customer_id: int) -> None:
    st.subheader("❤️ My Wishlist")
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT p.id, p.name, p.price, p.category,
                   i.stock_quantity
            FROM   Wishlist w
            JOIN   Products p   ON p.id = w.product_id
            LEFT JOIN Inventory i ON i.product_id = p.id
            WHERE  w.customer_id = ?
        """, (customer_id,)).fetchall()
    finally:
        conn.close()

    if not rows:
        st.info("Your wishlist is empty.")
        return

    for row in rows:
        col1, col2 = st.columns([4, 1])
        col1.write(f"**{row['name']}** — {format_currency(row['price'])} | Stock: {row['stock_quantity'] or 0}")
        if col2.button("Remove", key=f"rwish_{row['id']}"):
            _toggle_wishlist(customer_id, row["id"], True)
            st.rerun()


def customer_rewards(customer_id: int) -> None:
    st.subheader("🏆 Rewards & Loyalty")
    rewards = _get_rewards(customer_id)
    points  = rewards["points"]
    level   = rewards["level"]

    col1, col2 = st.columns(2)
    col1.metric("Your Points", points)
    col2.metric("Loyalty Level", level_badge(level))

    st.markdown("---")
    st.markdown("""
| Level    | Points Required |
|----------|----------------|
| 🥉 Bronze  | 0 – 999        |
| 🥈 Silver  | 1,000 – 2,999  |
| 🥇 Gold    | 3,000 – 6,999  |
| 💎 Platinum | 7,000+         |
""")
    st.caption("Earn 1 point for every ₹10 spent on delivered orders.")

    if level != "Platinum":
        next_thresholds = {"Bronze": 1000, "Silver": 3000, "Gold": 7000}
        needed = next_thresholds[level] - points
        st.info(f"You need {needed:,} more points to reach the next level!")


def customer_profile(customer_id: int, user: dict) -> None:
    st.subheader("👤 My Profile")
    conn = get_connection()
    try:
        cust = conn.execute(
            "SELECT name, phone, address FROM Customers WHERE id=?", (customer_id,)
        ).fetchone()
    finally:
        conn.close()

    if not cust:
        st.error("Profile not found.")
        return

    with st.form("profile_form"):
        name    = st.text_input("Full Name",    value=cust["name"])
        phone   = st.text_input("Phone",        value=cust["phone"] or "")
        address = st.text_area("Address",       value=cust["address"] or "")
        save    = st.form_submit_button("Save Changes")

    st.caption(f"Email: {user['email']}")

    if save:
        conn2 = get_connection()
        try:
            conn2.execute(
                "UPDATE Customers SET name=?, phone=?, address=? WHERE id=?",
                (name, phone, address, customer_id),
            )
            conn2.commit()
            st.success("Profile updated.")
        finally:
            conn2.close()


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------

def show_customer_app(user: dict) -> None:
    customer_id = _get_customer_id(user["id"])
    if customer_id is None:
        st.error("Customer profile not found.")
        return

    with st.sidebar:
        st.title("📦 Customer Portal")
        st.markdown(f"**Welcome!**")
        page = st.radio(
            "Navigate",
            ["Dashboard", "Products", "Orders", "Wishlist", "Rewards", "Profile"],
            label_visibility="collapsed",
        )
        st.markdown("---")
        if st.button("🚪 Logout"):
            st.session_state.clear()
            st.rerun()

    if page == "Dashboard":
        customer_dashboard(customer_id, user)
    elif page == "Products":
        customer_products(customer_id)
    elif page == "Orders":
        customer_orders(customer_id)
    elif page == "Wishlist":
        customer_wishlist(customer_id)
    elif page == "Rewards":
        customer_rewards(customer_id)
    elif page == "Profile":
        customer_profile(customer_id, user)
