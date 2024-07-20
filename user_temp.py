from dotenv import load_dotenv
from openai import OpenAI
from db import db
from db import Events, Users
from flask import Flask, jsonify
from flask import request
import os
import requests
import openai
from openai import OpenAI
import json
from flask import Flask, render_template, url_for, flash, redirect, request, session
from forms import RegistrationForm, LoginForm
from flask_behind_proxy import FlaskBehindProxy
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from functools import wraps
import re
from sqlalchemy import desc
import datetime
from datetime import datetime
from tzlocal import get_localzone
import os.path
import urllib3
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from flask import Flask, render_template, url_for, flash, redirect, request, session
from flask_migrate import Migrate

load_dotenv()



app = Flask(__name__)
proxied = FlaskBehindProxy(app)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db.init_app(app)
with app.app_context():
    db.create_all()

migrate = Migrate(app, db)

db.init_app(app)
with app.app_context():
    db.create_all()

@app.route('/')
def root():
    return redirect(url_for('home'))

@app.route("/register", methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():  
        existing_user = Users.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('Email already taken. Please use a different email.', 'danger')
            return redirect(url_for('register'))
        user = Users(email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(f'Account created for {form.email.data}!', 'success')
        return redirect(url_for('login'))  
    return render_template('register.html', title='Register', form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = Users.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            session['user_id'] = user.id
            flash(f'Login successful for {form.email.data}', 'success')
            return redirect(url_for('chat'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
            return redirect(url_for('chat'))
    return render_template('login.html', title='Login', form=form)


@app.route("/logout")
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/chat')
@login_required
def chat():
    return render_template('chat.html')
    
@app.route('/voice')
def voice():
  return render_template('voice.html', title='Record')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True, ssl_context='adhoc')
