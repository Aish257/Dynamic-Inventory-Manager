import streamlit as st
import sys
import os

# Ensure our directory is on the path so relative imports work
sys.path.insert(0, os.path.dirname(__file__))

from db import init_db
from auth import show_landing
from customer import show_customer_app
from salesman import show_salesman_app
from admin import show_admin_app


def main() -> None:
    st.set_page_config(
        page_title="Inventory & Order Management",
        page_icon="📦",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Initialise database (creates tables + loads sample data on first run)
    init_db()

    user = st.session_state.get("user")

    if not user:
        show_landing()
        return

    role = user.get("role")

    if role == "customer":
        show_customer_app(user)
    elif role == "salesman":
        show_salesman_app(user)
    elif role == "admin":
        show_admin_app(user)
    else:
        st.error(f"Unknown role: {role}")
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()


if __name__ == "__main__":
    main()
# Jenkins Auto Build Test
