from flask import Blueprint, render_template, session, redirect, url_for, flash
import os
import pickle

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
    
    return render_template(
        "dashboard.html",
        user_email=user_email,
        csv_uploaded=csv_uploaded,
        predictions=predictions,
        skipped_products=skipped_products,
        latest_prediction=prediction_data
    )