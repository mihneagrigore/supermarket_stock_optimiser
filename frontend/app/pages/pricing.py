from flask import Blueprint, render_template, session

pricing = Blueprint('pricing', __name__)

@pricing.route('/pricing')
def pricing_page():
    user_email = session.get('user_email')
    return render_template('pricing.html', user_email=user_email)
