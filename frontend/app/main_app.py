from flask import Flask
from app.pages.home import home_pages
from app.pages.login import login_pages
from app.pages.signup import signup_pages
from app.pages.upload import upload_pages
from app.pages.dashboard import dashboard_pages
from app.pages.about import about_pages
import os
import secrets

app = Flask(__name__, static_folder="../css", template_folder="../Templates")
app.secret_key = os.getenv("SECRET_KEY") or secrets.token_hex(32)

app.register_blueprint(home_pages)
app.register_blueprint(login_pages)
app.register_blueprint(signup_pages)
app.register_blueprint(upload_pages)
app.register_blueprint(dashboard_pages)
app.register_blueprint(about_pages)