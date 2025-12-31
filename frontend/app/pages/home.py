from flask import Blueprint, render_template, session, redirect, url_for
import sqlite3
import os

home_pages = Blueprint("home", __name__)

def get_company_name(email):
    """Fetch company name from database"""
    if not email:
        return None
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

@home_pages.route("/")
def home():
    user_email = session.get("user_email")
    company_name = get_company_name(user_email) if user_email else None
    return render_template("homepage.html", user_email=user_email, company_name=company_name)