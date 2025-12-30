from flask import Blueprint, render_template, session, redirect, url_for, flash
import sqlite3
import os

dashboard_pages = Blueprint("dashboard", __name__)

def get_client_id_by_email(email):
    """Get client ID from clients.db by email"""
    clients_db_path = os.path.join(os.path.dirname(__file__), "../../../backend/clients/clients.db")

    if not os.path.exists(clients_db_path):
        return None

    try:
        conn = sqlite3.connect(clients_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM clients WHERE email = ?", (email,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        print(f"Error fetching client ID: {e}")
        return None

def get_products_by_client_id(client_id):
    """Get all products from products.db for a specific client_id"""
    products_db_path = os.path.join(os.path.dirname(__file__), "../../../database/products.db")

    if not os.path.exists(products_db_path):
        return []

    try:
        conn = sqlite3.connect(products_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                Store_ID,
                Product_ID,
                MAX(Category) as Category,
                MAX(Date) as Latest_Date,
                SUM(Inventory_Level) as Total_Inventory,
                SUM(Units_Sold) as Total_Units_Sold,
                AVG(Price) as Avg_Price,
                COUNT(*) as Record_Count
            FROM inventory
            WHERE client_id = ?
            GROUP BY Store_ID, Product_ID
            ORDER BY Store_ID, Product_ID
        """, (client_id,))
        products = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return products
    except Exception as e:
        print(f"Error fetching products: {e}")
        return []

@dashboard_pages.route("/dashboard")
def dashboard():
    """Dashboard page - requires authentication"""
    if "user_email" not in session:
        flash("Please login to access the dashboard", "error")
        return redirect(url_for("login.login"))

    user_email = session.get("user_email")

    # Get client ID and products
    client_id = get_client_id_by_email(user_email)
    products = get_products_by_client_id(client_id) if client_id else []

    # Mock data for demonstration (replace with actual data from your backend)
    csv_uploaded = session.get("csv_uploaded", False)
    csv_filename = session.get("csv_filename", None)

    # Mock prediction data
    latest_prediction = session.get("latest_prediction", None)

    return render_template(
        "dashboard.html",
        user_email=user_email,
        csv_uploaded=csv_uploaded,
        csv_filename=csv_filename,
        latest_prediction=latest_prediction,
        products=products
    )