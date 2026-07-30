import plotly.express as px
import plotly.graph_objects as go
from db import get_connection


def monthly_revenue_chart():
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT strftime('%Y-%m', created_at) AS month,
                   SUM(total_amount)             AS revenue
            FROM   Orders
            WHERE  status NOT IN ('cancelled','rejected')
            GROUP  BY month
            ORDER  BY month
        """).fetchall()
    finally:
        conn.close()

    if not rows:
        return None
    months   = [r["month"]   for r in rows]
    revenues = [r["revenue"] for r in rows]
    fig = px.bar(
        x=months, y=revenues,
        labels={"x": "Month", "y": "Revenue (₹)"},
        title="Monthly Revenue",
        color=revenues,
        color_continuous_scale="Blues",
    )
    fig.update_layout(coloraxis_showscale=False)
    return fig


def top_selling_products_chart(top_n: int = 5):
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT p.name          AS product,
                   SUM(oi.quantity) AS units_sold
            FROM   Order_Items oi
            JOIN   Products p ON p.id = oi.product_id
            JOIN   Orders   o ON o.id = oi.order_id
            WHERE  o.status NOT IN ('cancelled','rejected')
            GROUP  BY p.id, p.name
            ORDER  BY units_sold DESC
            LIMIT  ?
        """, (top_n,)).fetchall()
    finally:
        conn.close()

    if not rows:
        return None
    products   = [r["product"]    for r in rows]
    units_sold = [r["units_sold"] for r in rows]
    fig = px.bar(
        x=units_sold, y=products,
        orientation="h",
        labels={"x": "Units Sold", "y": "Product"},
        title=f"Top {top_n} Selling Products",
        color=units_sold,
        color_continuous_scale="Greens",
    )
    fig.update_layout(coloraxis_showscale=False, yaxis={"categoryorder": "total ascending"})
    return fig


def top_customers_chart(top_n: int = 5):
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT customer_name,
                   total_spent
            FROM   Customer_Order_Summary
            ORDER  BY total_spent DESC
            LIMIT  ?
        """, (top_n,)).fetchall()
    finally:
        conn.close()

    if not rows:
        return None
    names  = [r["customer_name"] for r in rows]
    spends = [r["total_spent"]   for r in rows]
    fig = px.pie(
        names=names, values=spends,
        title=f"Top {top_n} Customers by Spend",
        hole=0.4,
    )
    return fig


def top_salesmen_chart(top_n: int = 5):
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT salesman_name,
                   total_sales,
                   commission_earned
            FROM   Salesman_Performance_View
            ORDER  BY total_sales DESC
            LIMIT  ?
        """, (top_n,)).fetchall()
    finally:
        conn.close()

    if not rows:
        return None
    names       = [r["salesman_name"]    for r in rows]
    sales       = [r["total_sales"]      for r in rows]
    commissions = [r["commission_earned"] for r in rows]
    fig = go.Figure(data=[
        go.Bar(name="Total Sales",       x=names, y=sales,       marker_color="steelblue"),
        go.Bar(name="Commission Earned", x=names, y=commissions, marker_color="orange"),
    ])
    fig.update_layout(barmode="group", title=f"Top {top_n} Salesmen Performance")
    return fig


def inventory_utilization_chart():
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT name,
                   stock_quantity,
                   max_stock,
                   stock_percentage
            FROM   Product_Inventory_View
        """).fetchall()
    finally:
        conn.close()

    if not rows:
        return None
    names   = [r["name"]             for r in rows]
    pcts    = [r["stock_percentage"] or 0 for r in rows]
    colors  = [
        "red" if p < 20 else ("orange" if p < 50 else "green")
        for p in pcts
    ]
    fig = go.Figure(go.Bar(
        x=names, y=pcts,
        marker_color=colors,
        text=[f"{p:.1f}%" for p in pcts],
        textposition="outside",
    ))
    fig.update_layout(
        title="Inventory Utilization (%)",
        yaxis={"title": "Stock %", "range": [0, 110]},
        xaxis={"title": "Product"},
    )
    fig.add_hline(y=20, line_dash="dash", line_color="red",    annotation_text="Low stock (20%)")
    fig.add_hline(y=50, line_dash="dash", line_color="orange", annotation_text="Medium (50%)")
    return fig
