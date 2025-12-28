from flask import Flask
from app.pages.home import home_pages
from app.pages.login import login_pages
from app.pages.signup import signup_pages
import os

app = Flask(__name__, static_folder="../css", template_folder="../Templates")
app.secret_key = os.getenv("SECRET_KEY")

app.register_blueprint(home_pages)
app.register_blueprint(login_pages)
app.register_blueprint(signup_pages)