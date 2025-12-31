from flask import Blueprint, render_template, session
import sqlite3
import os

about_pages = Blueprint("about", __name__)

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

@about_pages.route("/about")
def about():
    """About us page"""
    user_email = session.get('user_email')
    company_name = get_company_name(user_email) if user_email else None
    return render_template("aboutus.html", user_email=user_email, company_name=company_name)