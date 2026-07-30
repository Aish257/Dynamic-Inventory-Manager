PRAGMA foreign_keys = ON;

-- ============================================================
-- TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS Users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin', 'customer', 'salesman')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS Customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    name TEXT NOT NULL,
    phone TEXT,
    address TEXT,
    FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Salesmen (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    name TEXT NOT NULL,
    phone TEXT,
    region TEXT,
    commission_rate REAL NOT NULL DEFAULT 0.05 CHECK(commission_rate >= 0),
    FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    contact_email TEXT,
    phone TEXT,
    address TEXT
);

CREATE TABLE IF NOT EXISTS Products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    price REAL NOT NULL CHECK(price >= 0),
    category TEXT,
    supplier_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (supplier_id) REFERENCES Suppliers(id)
);

CREATE TABLE IF NOT EXISTS Inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL UNIQUE,
    stock_quantity INTEGER NOT NULL DEFAULT 0 CHECK(stock_quantity >= 0),
    max_stock INTEGER NOT NULL DEFAULT 100 CHECK(max_stock > 0),
    restock_date DATE,
    FOREIGN KEY (product_id) REFERENCES Products(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    salesman_id INTEGER,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','accepted','rejected','processing','shipped','delivered','cancelled')),
    total_amount REAL NOT NULL DEFAULT 0 CHECK(total_amount >= 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES Customers(id),
    FOREIGN KEY (salesman_id) REFERENCES Salesmen(id)
);

CREATE TABLE IF NOT EXISTS Order_Items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL CHECK(quantity > 0),
    unit_price REAL NOT NULL CHECK(unit_price >= 0),
    FOREIGN KEY (order_id) REFERENCES Orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES Products(id)
);

CREATE TABLE IF NOT EXISTS Wishlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(customer_id, product_id),
    FOREIGN KEY (customer_id) REFERENCES Customers(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES Products(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Rewards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL UNIQUE,
    points INTEGER NOT NULL DEFAULT 0 CHECK(points >= 0),
    level TEXT NOT NULL DEFAULT 'Bronze',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES Customers(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    is_read INTEGER NOT NULL DEFAULT 0 CHECK(is_read IN (0,1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE
);

-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_orders_customer   ON Orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_salesman   ON Orders(salesman_id);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON Order_Items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_prod  ON Order_Items(product_id);
CREATE INDEX IF NOT EXISTS idx_wishlist_customer ON Wishlist(customer_id);
CREATE INDEX IF NOT EXISTS idx_notif_user        ON Notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_products_category ON Products(category);
CREATE INDEX IF NOT EXISTS idx_inventory_product ON Inventory(product_id);

-- ============================================================
-- VIEWS
-- ============================================================

CREATE VIEW IF NOT EXISTS Product_Inventory_View AS
SELECT
    p.id,
    p.name,
    p.description,
    p.price,
    p.category,
    s.name          AS supplier_name,
    i.stock_quantity,
    i.max_stock,
    ROUND(CAST(i.stock_quantity AS REAL) / CAST(i.max_stock AS REAL) * 100, 2) AS stock_percentage,
    i.restock_date
FROM Products p
LEFT JOIN Inventory  i ON p.id = i.product_id
LEFT JOIN Suppliers  s ON p.supplier_id = s.id;

CREATE VIEW IF NOT EXISTS Customer_Order_Summary AS
SELECT
    c.id            AS customer_id,
    c.name          AS customer_name,
    u.email,
    COUNT(o.id)     AS total_orders,
    COALESCE(SUM(o.total_amount), 0)  AS total_spent,
    COALESCE(AVG(o.total_amount), 0)  AS avg_order_value,
    COALESCE(r.points, 0)             AS reward_points,
    COALESCE(r.level, 'Bronze')       AS loyalty_level
FROM Customers c
JOIN Users    u ON c.user_id = u.id
LEFT JOIN Orders  o ON c.id = o.customer_id AND o.status NOT IN ('cancelled','rejected')
LEFT JOIN Rewards r ON c.id = r.customer_id
GROUP BY c.id, c.name, u.email, r.points, r.level;

CREATE VIEW IF NOT EXISTS Salesman_Performance_View AS
SELECT
    sm.id              AS salesman_id,
    sm.name            AS salesman_name,
    sm.region,
    sm.commission_rate,
    COUNT(o.id)        AS total_orders,
    COALESCE(SUM(o.total_amount), 0) AS total_sales,
    ROUND(COALESCE(SUM(o.total_amount), 0) * sm.commission_rate, 2) AS commission_earned
FROM Salesmen sm
LEFT JOIN Orders o ON sm.id = o.salesman_id AND o.status NOT IN ('rejected','cancelled')
GROUP BY sm.id, sm.name, sm.region, sm.commission_rate;

-- ============================================================
-- TRIGGERS
-- ============================================================

-- Update rewards when an order is marked delivered
CREATE TRIGGER IF NOT EXISTS trg_rewards_on_delivery
AFTER UPDATE OF status ON Orders
WHEN NEW.status = 'delivered' AND OLD.status != 'delivered'
BEGIN
    INSERT INTO Rewards (customer_id, points, level, updated_at)
    VALUES (
        NEW.customer_id,
        CAST(NEW.total_amount / 10 AS INTEGER),
        CASE
            WHEN CAST(NEW.total_amount / 10 AS INTEGER) >= 7000 THEN 'Platinum'
            WHEN CAST(NEW.total_amount / 10 AS INTEGER) >= 3000 THEN 'Gold'
            WHEN CAST(NEW.total_amount / 10 AS INTEGER) >= 1000 THEN 'Silver'
            ELSE 'Bronze'
        END,
        CURRENT_TIMESTAMP
    )
    ON CONFLICT(customer_id) DO UPDATE SET
        points = Rewards.points + CAST(NEW.total_amount / 10 AS INTEGER),
        level  = CASE
            WHEN Rewards.points + CAST(NEW.total_amount / 10 AS INTEGER) >= 7000 THEN 'Platinum'
            WHEN Rewards.points + CAST(NEW.total_amount / 10 AS INTEGER) >= 3000 THEN 'Gold'
            WHEN Rewards.points + CAST(NEW.total_amount / 10 AS INTEGER) >= 1000 THEN 'Silver'
            ELSE 'Bronze'
        END,
        updated_at = CURRENT_TIMESTAMP;
END;

-- Send low-stock notification when inventory drops below 20 %
CREATE TRIGGER IF NOT EXISTS trg_low_stock_notify
AFTER UPDATE OF stock_quantity ON Inventory
WHEN CAST(NEW.stock_quantity AS REAL) / CAST(NEW.max_stock AS REAL) < 0.20
BEGIN
    INSERT INTO Notifications (user_id, message)
    SELECT u.id,
           'Low stock alert: ' || p.name || ' has only ' || NEW.stock_quantity || ' units left.'
    FROM Products p
    JOIN Users u ON u.role = 'admin'
    WHERE p.id = NEW.product_id;
END;
