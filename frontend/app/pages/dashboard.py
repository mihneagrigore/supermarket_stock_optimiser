from flask import Blueprint, render_template, session, redirect, url_for, flash, request
import os
import pickle
from datetime import datetime
import sys

# Add utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.db_queries import get_client_id, get_product_inventory_data
from utils.analytics import generate_product_charts

dashboard_pages = Blueprint("dashboard", __name__)

@dashboard_pages.route("/dashboard")
def dashboard():
    """Dashboard page - requires authentication"""
    if "user_email" not in session:
        flash("Please login to access the dashboard", "error")
        return redirect(url_for("login.login"))
    
    user_email = session.get("user_email")
    
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
    
    # Analytics section
    charts = None
    selected_product = None
    product_list = []
    time_range = request.args.get('range', '90')  # Default to 90 days
    
    if predictions:
        # Get list of products with predictions
        product_list = sorted(predictions.keys())
        
        # Get selected product (default to first)
        selected_product = request.args.get('product_id', product_list[0] if product_list else None)
        
        if selected_product and selected_product in predictions:
            # Check cache
            temp_uploads = os.path.join(os.path.dirname(__file__), "../../../temp_uploads")
            cache_path = os.path.join(temp_uploads, f"{user_email}_analytics_{selected_product}_{time_range}.pkl")
            
            if os.path.exists(cache_path):
                # Load from cache
                try:
                    with open(cache_path, 'rb') as f:
                        charts = pickle.load(f)
                except Exception as e:
                    print(f"Error loading analytics cache: {e}")
            
            if not charts:
                # Generate charts
                client_id = get_client_id(user_email)
                
                if client_id:
                    # Fetch inventory data
                    days_limit = int(time_range) if time_range != 'all' else None
                    inventory_df = get_product_inventory_data(client_id, selected_product, days_limit)
                    
                    if not inventory_df.empty:
                        # Generate charts
                        prediction = predictions[selected_product]
                        charts = generate_product_charts(inventory_df, prediction)
                        
                        # Cache the charts
                        try:
                            with open(cache_path, 'wb') as f:
                                pickle.dump(charts, f)
                        except Exception as e:
                            print(f"Error caching analytics: {e}")
                    else:
                        print(f"No inventory data found for product {selected_product}. Please re-upload CSV to import data into database.")
    
    return render_template(
        "dashboard.html",
        user_email=user_email,
        csv_uploaded=csv_uploaded,
        predictions=predictions,
        skipped_products=skipped_products,
        latest_prediction=prediction_data,
        charts=charts,
        selected_product=selected_product,
        product_list=product_list,
        time_range=time_range
    )