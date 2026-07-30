from db import get_connection
from utils import hash_password
import datetime


def load_sample_data() -> None:
    conn = get_connection()
    try:
        # Guard: abort if data already exists
        if conn.execute("SELECT COUNT(*) FROM Users").fetchone()[0] > 0:
            return

        today = datetime.date.today()
        restock_30 = (today + datetime.timedelta(days=30)).isoformat()
        restock_15 = (today + datetime.timedelta(days=15)).isoformat()

        # ------------------------------------------------------------------
        # Users
        # ------------------------------------------------------------------
        conn.execute(
            "INSERT INTO Users (email, password_hash, role) VALUES (?,?,?)",
            ("admin@gmail.com", hash_password("admin123"), "admin"),
        )

        conn.execute(
            "INSERT INTO Users (email, password_hash, role) VALUES (?,?,?)",
            ("salesman@gmail.com", hash_password("sales123"), "salesman"),
        )
        conn.execute(
            "INSERT INTO Users (email, password_hash, role) VALUES (?,?,?)",
            ("john.sales@gmail.com", hash_password("sales456"), "salesman"),
        )

        conn.execute(
            "INSERT INTO Users (email, password_hash, role) VALUES (?,?,?)",
            ("alice@gmail.com", hash_password("alice123"), "customer"),
        )
        conn.execute(
            "INSERT INTO Users (email, password_hash, role) VALUES (?,?,?)",
            ("bob@gmail.com", hash_password("bob123"), "customer"),
        )
        conn.commit()

        # ------------------------------------------------------------------
        # Fetch dynamically created User IDs
        # ------------------------------------------------------------------
        def uid(email: str) -> int:
            return conn.execute(
                "SELECT id FROM Users WHERE email=?", (email,)
            ).fetchone()[0]

        admin_uid     = uid("admin@gmail.com")
        salesman1_uid = uid("salesman@gmail.com")
        salesman2_uid = uid("john.sales@gmail.com")
        alice_uid     = uid("alice@gmail.com")
        bob_uid       = uid("bob@gmail.com")

        # ------------------------------------------------------------------
        # Salesmen
        # ------------------------------------------------------------------
        conn.execute(
            "INSERT INTO Salesmen (user_id, name, phone, region, commission_rate) VALUES (?,?,?,?,?)",
            (salesman1_uid, "Sam Sales", "9876543210", "North", 0.05),
        )
        conn.execute(
            "INSERT INTO Salesmen (user_id, name, phone, region, commission_rate) VALUES (?,?,?,?,?)",
            (salesman2_uid, "John Sales", "9123456789", "South", 0.06),
        )
        conn.commit()

        # ------------------------------------------------------------------
        # Customers
        # ------------------------------------------------------------------
        conn.execute(
            "INSERT INTO Customers (user_id, name, phone, address) VALUES (?,?,?,?)",
            (alice_uid, "Alice Kumar", "9000000001", "12 MG Road, Mumbai"),
        )
        conn.execute(
            "INSERT INTO Customers (user_id, name, phone, address) VALUES (?,?,?,?)",
            (bob_uid, "Bob Sharma", "9000000002", "45 Anna Nagar, Chennai"),
        )
        conn.commit()

        # ------------------------------------------------------------------
        # Fetch dynamically created Salesman & Customer IDs
        # ------------------------------------------------------------------
        def sm_id(u_id: int) -> int:
            return conn.execute(
                "SELECT id FROM Salesmen WHERE user_id=?", (u_id,)
            ).fetchone()[0]

        def cust_id(u_id: int) -> int:
            return conn.execute(
                "SELECT id FROM Customers WHERE user_id=?", (u_id,)
            ).fetchone()[0]

        s1_id = sm_id(salesman1_uid)
        s2_id = sm_id(salesman2_uid)
        c1_id = cust_id(alice_uid)
        c2_id = cust_id(bob_uid)

        # ------------------------------------------------------------------
        # Suppliers
        # ------------------------------------------------------------------
        conn.execute(
            "INSERT INTO Suppliers (name, contact_email, phone, address) VALUES (?,?,?,?)",
            ("TechCorp Supplies", "tech@techcorp.com", "0221234567", "Andheri, Mumbai"),
        )
        conn.execute(
            "INSERT INTO Suppliers (name, contact_email, phone, address) VALUES (?,?,?,?)",
            ("GreenGoods Ltd.", "info@greengoods.com", "0449876543", "T Nagar, Chennai"),
        )
        conn.execute(
            "INSERT INTO Suppliers (name, contact_email, phone, address) VALUES (?,?,?,?)",
            ("MegaMart Wholesale", "supply@megamart.com", "0801122334", "Koramangala, Bengaluru"),
        )
        conn.commit()

        # Fetch supplier IDs dynamically
        def sup_id(name: str) -> int:
            return conn.execute(
                "SELECT id FROM Suppliers WHERE name=?", (name,)
            ).fetchone()[0]

        sup1 = sup_id("TechCorp Supplies")
        sup2 = sup_id("GreenGoods Ltd.")
        sup3 = sup_id("MegaMart Wholesale")

        # ------------------------------------------------------------------
        # Products
        # ------------------------------------------------------------------
        products = [
            ("Wireless Headphones",  "Premium noise-cancelling headphones", 2999.0, "Electronics",  sup1),
            ("Organic Green Tea",    "100% organic Darjeeling tea, 250g",    349.0, "Beverages",    sup2),
            ("Leather Wallet",       "Genuine leather bi-fold wallet",       899.0, "Accessories",  sup3),
            ("Smart Watch",          "Fitness tracking smart watch",        4999.0, "Electronics",  sup1),
            ("Yoga Mat",             "Non-slip eco-friendly yoga mat",       599.0, "Sports",       sup2),
        ]
        conn.executemany(
            "INSERT INTO Products (name, description, price, category, supplier_id) VALUES (?,?,?,?,?)",
            products,
        )
        conn.commit()

        # Fetch product IDs dynamically
        def prod_id(name: str) -> int:
            return conn.execute(
                "SELECT id FROM Products WHERE name=?", (name,)
            ).fetchone()[0]

        p1 = prod_id("Wireless Headphones")
        p2 = prod_id("Organic Green Tea")
        p3 = prod_id("Leather Wallet")
        p4 = prod_id("Smart Watch")
        p5 = prod_id("Yoga Mat")

        # ------------------------------------------------------------------
        # Inventory
        # ------------------------------------------------------------------
        inventory = [
            (p1, 45,  100, restock_30),
            (p2, 12,  200, restock_15),
            (p3, 80,  150, restock_30),
            (p4, 8,    50, restock_15),
            (p5, 120, 200, restock_30),
        ]
        conn.executemany(
            "INSERT INTO Inventory (product_id, stock_quantity, max_stock, restock_date) VALUES (?,?,?,?)",
            inventory,
        )
        conn.commit()

        # ------------------------------------------------------------------
        # Orders (4 orders)
        # ------------------------------------------------------------------
        conn.execute(
            "INSERT INTO Orders (customer_id, salesman_id, status, total_amount, created_at) VALUES (?,?,?,?,?)",
            (c1_id, s1_id, "delivered", 3299.0, "2025-01-15 10:00:00"),
        )
        conn.execute(
            "INSERT INTO Orders (customer_id, salesman_id, status, total_amount, created_at) VALUES (?,?,?,?,?)",
            (c1_id, s2_id, "shipped",   4999.0, "2025-02-20 11:30:00"),
        )
        conn.execute(
            "INSERT INTO Orders (customer_id, salesman_id, status, total_amount, created_at) VALUES (?,?,?,?,?)",
            (c2_id, s1_id, "delivered", 1498.0, "2025-03-05 09:15:00"),
        )
        conn.execute(
            "INSERT INTO Orders (customer_id, salesman_id, status, total_amount, created_at) VALUES (?,?,?,?,?)",
            (c2_id, s2_id, "pending",   899.0,  "2025-04-10 14:45:00"),
        )
        conn.commit()

        # Fetch order IDs dynamically
        orders = conn.execute("SELECT id FROM Orders ORDER BY id").fetchall()
        o1, o2, o3, o4 = [r[0] for r in orders]

        # ------------------------------------------------------------------
        # Order Items
        # ------------------------------------------------------------------
        conn.executemany(
            "INSERT INTO Order_Items (order_id, product_id, quantity, unit_price) VALUES (?,?,?,?)",
            [
                (o1, p1, 1, 2999.0),
                (o1, p2, 1,  349.0),   # 3299 total
                (o2, p4, 1, 4999.0),   # 4999 total
                (o3, p2, 2,  349.0),
                (o3, p3, 1,  899.0),   # 1597 (close to 1498 - minor discount scenario; use 1498)
                (o4, p3, 1,  899.0),   # 899 total
            ],
        )
        conn.commit()

        # ------------------------------------------------------------------
        # Wishlist
        # ------------------------------------------------------------------
        conn.executemany(
            "INSERT OR IGNORE INTO Wishlist (customer_id, product_id) VALUES (?,?)",
            [(c1_id, p4), (c1_id, p5), (c2_id, p1)],
        )
        conn.commit()

        # ------------------------------------------------------------------
        # Rewards (seed initial points; trigger will add more on delivery)
        # ------------------------------------------------------------------
        conn.executemany(
            "INSERT OR IGNORE INTO Rewards (customer_id, points, level) VALUES (?,?,?)",
            [
                (c1_id, 329,  "Bronze"),
                (c2_id, 149,  "Bronze"),
            ],
        )
        conn.commit()

        # ------------------------------------------------------------------
        # Notifications
        # ------------------------------------------------------------------
        conn.executemany(
            "INSERT INTO Notifications (user_id, message) VALUES (?,?)",
            [
                (alice_uid, "Your order #1 has been delivered!"),
                (bob_uid,   "Your order #3 has been delivered!"),
                (admin_uid, "Low stock alert: Smart Watch has only 8 units left."),
                (alice_uid, "Your order #2 has been shipped!"),
            ],
        )
        conn.commit()

    except Exception as exc:
        conn.rollback()
        raise exc
    finally:
        conn.close()
