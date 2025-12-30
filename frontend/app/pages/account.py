from flask import Blueprint, render_template, session, redirect, url_for, flash

account_pages = Blueprint("account", __name__)

@account_pages.route("/account")
def account():
    """Account page - requires authentication"""
    if "user_email" not in session:
        flash("Please login to access your account", "error")
        return redirect(url_for("login.login"))

    user_email = session.get("user_email")

    return render_template(
        "account.html",
        user_email=user_email
    )
