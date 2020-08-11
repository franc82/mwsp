from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
import secrets
import os
from flask_mail import Mail

mail = Mail()
app = Flask(__name__, static_url_path='')
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'data.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_TYPE'] = 'redis'
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'myweddingseatingplanner@gmail.com'
app.config['MAIL_PASSWORD'] = 'ireland4c'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

mail.init_app(app)
db = SQLAlchemy(app)
app.secret_key = secrets.token_urlsafe(16)
stripekey = 'sk_test_51HDuHyKfKC2ONPsdR2fZjJ6nZEsJ6rGpGiV6s6HNKJjqvch3mhlIqyus6VZjwHw8RnFpEZCNxXbyZaLORP1hSwBw00mV32lWlQ'
#app.secret_key = 'any key to be used'

SESSION_TYPE = 'redis'
sess = Session()

sess.init_app(app)

# from .util import assets
from my_app.catalog.views import catalog
app.register_blueprint(catalog)
db.create_all()
