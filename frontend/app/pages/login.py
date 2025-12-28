from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import subprocess
import os

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
                return redirect(url_for("home.home"))
            else:
                flash("Invalid email or password", "error")
                return render_template("login.html")
                
        except Exception as e:
            flash(f"Error during login: {str(e)}", "error")
            return render_template("login.html")
    
    return render_template("login.html")

@login_pages.route("/logout")
def logout():
    session.pop("user_email", None)
    flash("You have been logged out", "success")
    return redirect(url_for("home.home"))