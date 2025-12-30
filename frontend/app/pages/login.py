from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import subprocess
import os
import glob

login_pages = Blueprint("login", __name__)

@login_pages.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        # Validate inputs
        if not email or not password:
            flash("Email and password are required", "error")
            return render_template("login.html")
        
        script_path = os.path.join(os.path.dirname(__file__), "../../../backend/clients/auth-user.py")
        
        try:
            result = subprocess.run(
                ["python3", script_path, email, password],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                # Login successful
                session.permanent = True
                session["user_email"] = email
                flash("Login successful!", "success")
                return redirect(url_for("dashboard.dashboard"))
            else:
                flash("Invalid email or password", "error")
                return render_template("login.html")
                
        except Exception as e:
            flash(f"Error during login: {str(e)}", "error")
            return render_template("login.html")
    
    return render_template("login.html")

@login_pages.route("/logout")
def logout():
    user_email = session.get("user_email")
    
    # Clean up user files
    if user_email:
        temp_uploads = os.path.join(os.path.dirname(__file__), "../../../temp_uploads")
        
        # Delete CSV pickle
        csv_pickle = os.path.join(temp_uploads, f"{user_email}_csv.pkl")
        if os.path.exists(csv_pickle):
            try:
                os.remove(csv_pickle)
            except Exception as e:
                print(f"Error deleting CSV pickle: {e}")
        
        # Delete predictions pickle
        predictions_pickle = os.path.join(temp_uploads, f"{user_email}_predictions.pkl")
        if os.path.exists(predictions_pickle):
            try:
                os.remove(predictions_pickle)
            except Exception as e:
                print(f"Error deleting predictions pickle: {e}")
        
        # Delete all analytics cache files
        analytics_pattern = os.path.join(temp_uploads, f"{user_email}_analytics_*.pkl")
        for cache_file in glob.glob(analytics_pattern):
            try:
                os.remove(cache_file)
                print(f"Deleted analytics cache: {cache_file}")
            except Exception as e:
                print(f"Error deleting analytics cache: {e}")
    
    session.pop("user_email", None)
    flash("You have been logged out", "success")
    return redirect(url_for("home.home"))