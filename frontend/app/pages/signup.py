from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import subprocess
import os
import json
import sys
from dotenv import load_dotenv

load_dotenv()

signup_pages = Blueprint("signup", __name__)

@signup_pages.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        
        if "cui" in request.form:
            cui = request.form.get("cui")
            
            if not cui:
                flash("CUI is required", "error")
                return render_template("signup.html")
            
            # Call the main.py script to fetch company data
            script_path = os.path.join(os.path.dirname(__file__), "../../../scripts/company_api/main.py")
            
            try:
                env = os.environ.copy()
                if not env.get("API_KEY"):
                    env["API_KEY"] = os.getenv("API_KEY", "")
                
                result = subprocess.run(
                    [sys.executable, script_path, cui],
                    capture_output=True,
                    text=True,
                    cwd=os.path.join(os.path.dirname(__file__), "../../../"),
                    env=env
                )
                
                if result.returncode == 0:
                    json_path = os.path.join(os.path.dirname(__file__), "../../../data/company-details/company-details.json")
                    
                    with open(json_path, "r", encoding="utf-8") as f:
                        company_data = json.load(f)
                    
                    session["company_data"] = company_data
                    session["cui"] = cui
                    
                    flash("Company found! Please complete your registration.", "success")
                    return render_template("signup.html", show_registration=True, company_data=company_data)
                else:
                    error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                    flash(f"CUI not found or API error: {error_msg}", "error")
                    return render_template("signup.html")
                    
            except Exception as e:
                flash(f"Error fetching company data: {str(e)}", "error")
                return render_template("signup.html")
        
        else:
            email = request.form.get("email")
            password = request.form.get("password")
            confirm_password = request.form.get("confirm_password")
            
            if not email or not password or not confirm_password:
                flash("All fields are required", "error")
                company_data = session.get("company_data")
                return render_template("signup.html", show_registration=True, company_data=company_data)
            
            if password != confirm_password:
                flash("Passwords do not match", "error")
                company_data = session.get("company_data")
                return render_template("signup.html", show_registration=True, company_data=company_data)
            
            script_path = os.path.join(os.path.dirname(__file__), "../../../backend/clients/add-client.py")
            
            try:
                result = subprocess.run(
                    [sys.executable, script_path, email, password],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    # Clear session data
                    session.pop("company_data", None)
                    session.pop("cui", None)
                    
                    flash("Account created successfully! Please login.", "success")
                    return redirect(url_for("login.login"))
                else:
                    error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
                    flash(f"Email already exists or registration failed: {error_msg}", "error")
                    company_data = session.get("company_data")
                    return render_template("signup.html", show_registration=True, company_data=company_data)
                    
            except Exception as e:
                flash(f"Error creating account: {str(e)}", "error")
                company_data = session.get("company_data")
                return render_template("signup.html", show_registration=True, company_data=company_data)
    
    return render_template("signup.html")