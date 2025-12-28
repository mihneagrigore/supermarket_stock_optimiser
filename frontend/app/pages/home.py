from flask import Blueprint, render_template, session, redirect, url_for

home_pages = Blueprint("home", __name__)

@home_pages.route("/")
def home():
    return render_template("homepage.html")