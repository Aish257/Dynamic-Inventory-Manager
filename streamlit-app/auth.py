import streamlit as st
from db import get_connection
from utils import hash_password


def login(email: str, password: str):
    """Return the matching Users row dict, or None."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, email, role FROM Users WHERE email=? AND password_hash=?",
            (email, hash_password(password)),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def register_customer(email: str, password: str, name: str, phone: str, address: str) -> tuple[bool, str]:
    """Create a new customer account. Returns (success, message)."""
    if not email or not password or not name:
        return False, "Email, password and name are required."
    conn = get_connection()
    try:
        existing = conn.execute("SELECT id FROM Users WHERE email=?", (email,)).fetchone()
        if existing:
            return False, "An account with this email already exists."

        conn.execute(
            "INSERT INTO Users (email, password_hash, role) VALUES (?,?,?)",
            (email, hash_password(password), "customer"),
        )
        conn.commit()

        user_id = conn.execute("SELECT id FROM Users WHERE email=?", (email,)).fetchone()[0]

        conn.execute(
            "INSERT INTO Customers (user_id, name, phone, address) VALUES (?,?,?,?)",
            (user_id, name, phone, address),
        )
        conn.execute(
            "INSERT INTO Rewards (customer_id, points, level) VALUES (?,?,?)",
            (conn.execute("SELECT id FROM Customers WHERE user_id=?", (user_id,)).fetchone()[0],
             0, "Bronze"),
        )
        conn.commit()
        return True, "Account created successfully!"
    except Exception as exc:
        conn.rollback()
        return False, f"Registration failed: {exc}"
    finally:
        conn.close()


def show_landing():
    st.title("📦 Inventory & Order Management System")
    st.markdown("---")
    tab_login, tab_register = st.tabs(["🔐 Login", "📝 Register"])

    with tab_login:
        st.subheader("Sign In")
        with st.form("login_form"):
            email    = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")

        if submitted:
            if not email or not password:
                st.error("Please enter both email and password.")
            else:
                user = login(email.strip(), password)
                if user:
                    st.session_state["user"] = user
                    st.rerun()
                else:
                    st.error("Invalid credentials. Please try again.")

        st.caption("null")

    with tab_register:
        st.subheader("Create Customer Account")
        with st.form("register_form"):
            r_name    = st.text_input("Full Name")
            r_email   = st.text_input("Email")
            r_password = st.text_input("Password", type="password")
            r_phone   = st.text_input("Phone (optional)")
            r_address = st.text_area("Address (optional)")
            r_submit  = st.form_submit_button("Register")

        if r_submit:
            ok, msg = register_customer(r_email.strip(), r_password, r_name, r_phone, r_address)
            if ok:
                st.success(msg + " Please login.")
            else:
                st.error(msg)
