from flask import Blueprint, render_template, session, redirect, url_for, flash
import sqlite3
import os

account_pages = Blueprint("account", __name__)

def get_company_name(email):
    """Fetch company name from database"""
    db_path = os.path.join(os.path.dirname(__file__), "../../../backend/clients/clients.db")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT denumire FROM clients WHERE email = ?", (email,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        print(f"Error fetching company name: {e}")
        return None

@account_pages.route("/account")
def account():
    """Account page - requires authentication"""
    if "user_email" not in session:
        flash("Please login to access your account", "error")
        return redirect(url_for("login.login"))

    user_email = session.get("user_email")
    company_name = get_company_name(user_email)

    return render_template(
        "account.html",
        user_email=user_email,
        company_name=company_name
    )
