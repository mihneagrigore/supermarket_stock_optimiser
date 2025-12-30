from flask import Blueprint, render_template, session, redirect, url_for, flash

dashboard_pages = Blueprint("dashboard", __name__)

@dashboard_pages.route("/dashboard")
def dashboard():
    """Dashboard page - requires authentication"""
    if "user_email" not in session:
        flash("Please login to access the dashboard", "error")
        return redirect(url_for("login.login"))
    
    user_email = session.get("user_email")
    
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
        latest_prediction=latest_prediction
    )