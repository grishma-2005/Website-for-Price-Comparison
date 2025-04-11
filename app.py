from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask.sessions import SecureCookieSessionInterface
import pymysql
import re
import os
from datetime import timedelta

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Strong random secret key
app.permanent_session_lifetime = timedelta(days=30)  # Session lasts 30 days

# Database Configuration
def get_db_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="",
        database="users_db",
        cursorclass=pymysql.cursors.DictCursor
    )

# Custom session interface for better persistence
class CustomSessionInterface(SecureCookieSessionInterface):
    def should_set_cookie(self, app, session):
        return True  # Always set cookie for persistence

app.session_interface = CustomSessionInterface()

# Helper Functions
def is_gmail(email):
    return re.match(r'^[a-zA-Z0-9._%+-]+@gmail\.com$', email)

def is_valid_phone(phone):
    return phone and len(phone) == 10 and phone.isdigit()

# Check if user exists in database
def user_exists(email, phone):
    db = get_db_connection()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM users WHERE email = %s AND phone = %s",
                (email, phone))
            return cursor.fetchone() is not None
    finally:
        db.close()

# Routes
@app.route('/')
def home():
    # Check if user is already logged in
    if 'email' in session and 'phone' in session:
        if user_exists(session['email'], session['phone']):
            return redirect('/index')
    return redirect('/sign-up')

@app.route('/sign-up', methods=['GET', 'POST'])
def signup():
    # Check if already logged in
    if 'email' in session and 'phone' in session:
        if user_exists(session['email'], session['phone']):
            return redirect('/index')

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()

        if not is_gmail(email):
            flash("Only Gmail addresses (@gmail.com) are allowed")
            return redirect('/sign-up')

        if not is_valid_phone(phone):
            flash("Phone number must be 10 digits")
            return redirect('/sign-up')

        db = get_db_connection()
        try:
            with db.cursor() as cursor:
                # Check if user exists
                cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
                if cursor.fetchone():
                    flash("Email already registered. Please sign in.")
                    return redirect('/sign-in')
                
                # Create new user
                cursor.execute(
                    "INSERT INTO users (email, phone) VALUES (%s, %s)",
                    (email, phone)
                )
                db.commit()
                
                session.permanent = True  # Make session persistent
                session['email'] = email
                session['phone'] = phone
                return redirect('/index')
        except Exception as e:
            db.rollback()
            flash("Registration failed. Please try again.")
            return redirect('/sign-up')
        finally:
            db.close()

    return render_template('sign-up.html')

@app.route('/sign-in', methods=['GET', 'POST'])
def signin():
    # Check if already logged in
    if 'email' in session and 'phone' in session:
        if user_exists(session['email'], session['phone']):
            return redirect('/index')

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()

        db = get_db_connection()
        try:
            with db.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM users WHERE email = %s AND phone = %s",
                    (email, phone)
                )
                user = cursor.fetchone()
                
                if not user:
                    flash("Account not found. Please sign up first.")
                    return redirect('/sign-up')
                
                session.permanent = True  # Make session persistent
                session['email'] = email
                session['phone'] = phone
                return redirect('/index')
        except Exception as e:
            flash("Login failed. Please try again.")
            return redirect('/sign-in')
        finally:
            db.close()

    return render_template('sign-in.html')

@app.route('/index')
def index():
    if 'email' not in session or 'phone' not in session:
        return redirect('/sign-up')
    
    # Verify user still exists in database
    if not user_exists(session['email'], session['phone']):
        session.clear()
        flash("Your account no longer exists. Please sign up.")
        return redirect('/sign-up')
    
    return render_template('index.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/sign-up')

if __name__ == '__main__':
    app.run(debug=True)