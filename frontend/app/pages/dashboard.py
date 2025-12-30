from flask import Blueprint, render_template, session, redirect, url_for, flash, request
import sqlite3
import os
import pickle
import sys

# Add utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.analytics import generate_product_charts, generate_no_data_message

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


def get_product_historical_data(client_id, product_id):
    """Get historical data for a specific product (aggregated across stores)."""
    products_db_path = os.path.join(os.path.dirname(__file__), "../../../database/products.db")

    if not os.path.exists(products_db_path):
        return []

    try:
        conn = sqlite3.connect(products_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                Date,
                SUM(Inventory_Level) as Inventory_Level,
                SUM(Units_Sold) as Units_Sold,
                AVG(Price) as Price,
                AVG(Discount) as Discount
            FROM inventory
            WHERE client_id = ? AND Product_ID = ?
            GROUP BY Date
            ORDER BY Date ASC
        """, (client_id, product_id))
        data = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return data
    except Exception as e:
        print(f"Error fetching product historical data: {e}")
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

    # Load prediction results from pickle file if available
    predictions_path = os.path.join(
        os.path.dirname(__file__),
        "../../../temp_uploads",
        f"{user_email}_predictions.pkl"
    )

    prediction_data = None
    csv_uploaded = False

    if os.path.exists(predictions_path):
        try:
            with open(predictions_path, 'rb') as f:
                prediction_data = pickle.load(f)
            csv_uploaded = True
        except Exception as e:
            print(f"Error loading predictions: {e}")

    # Prepare data for template
    predictions = prediction_data.get('predictions', {}) if prediction_data else {}
    skipped_products = prediction_data.get('skipped_products', []) if prediction_data else []

    # Get list of all product IDs from predictions (for dropdown)
    product_list = sorted(predictions.keys()) if predictions else []
    
    # Get selected product from query param (default to first product)
    selected_product = request.args.get('product_id')
    if not selected_product and product_list:
        selected_product = product_list[0]
    
    # Generate charts for selected product
    charts = None
    if selected_product and client_id:
        prediction = predictions.get(selected_product)
        if prediction:
            # Get historical data for the product
            historical_data = get_product_historical_data(client_id, selected_product)
            charts = generate_product_charts(selected_product, prediction, historical_data)
        else:
            # Product was skipped (insufficient data)
            charts = generate_no_data_message(selected_product)

    return render_template(
        "dashboard.html",
        user_email=user_email,
        csv_uploaded=csv_uploaded,
        predictions=predictions,
        skipped_products=skipped_products,
        latest_prediction=prediction_data,
        products=products,
        product_list=product_list,
        selected_product=selected_product,
        charts=charts
    )