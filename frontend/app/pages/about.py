from flask import Blueprint, render_template, session

about_pages = Blueprint("about", __name__)

@about_pages.route("/about")
def about():
    """About us page"""
    user_email = session.get('user_email')
    return render_template("aboutus.html", user_email=user_email)