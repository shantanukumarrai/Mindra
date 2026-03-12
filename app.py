from flask import Flask, render_template, request, redirect, session, jsonify
import os
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
load_dotenv()
# Import our modules
from database import (
    init_database,
    register_user,
    get_user_by_email,
    get_streak_data,
    is_completed_today,
    complete_meditation
)
from scheduler import start_scheduler

app = Flask(__name__)
app.secret_key = 'meditation-streak-secret-key-2026'  # Change in production

@app.route('/')
def home():
    return redirect('/login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        reminder_time = request.form['reminder_time']  # HH:MM format

        password_hash = generate_password_hash(password)

        try:
            user_id = register_user(name, email, password_hash, reminder_time)
            session['user_id'] = user_id
            session['name'] = name
            return redirect('/dashboard')
        except Exception as e:
            # Email already exists or DB error
            app.logger.error(f"Registration failed: {e}")
            return render_template('register.html', error="Email already registered or invalid data.")

    return render_template('register.html', error=None)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = get_user_by_email(email)
        if not user:
            app.logger.info(f"Login attempt with unknown email: {email}")
            return render_template('login.html', error="Invalid email or password.")
        if check_password_hash(user[3], password):  # user = (id, name, email, hash)
            session['user_id'] = user[0]
            session['name'] = user[1]
            return redirect('/dashboard')
        else:
            app.logger.info(f"Password mismatch for user {email}")
            return render_template('login.html', error="Invalid email or password.")

    return render_template('login.html', error=None)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('name', None)
    return redirect('/login')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    streak = get_streak_data(user_id)
    completed_today = is_completed_today(user_id)

    return render_template(
        'dashboard.html',
        name=session.get('name'),
        current_streak=streak['current'],
        highest_streak=streak['highest'],
        completed_today=completed_today
    )

@app.route('/meditation')
def meditation():
    if 'user_id' not in session:
        return redirect('/login')
    if is_completed_today(session['user_id']):
        return redirect('/dashboard')  # Already done today
    return render_template('meditation.html')

@app.route('/complete-meditation', methods=['POST'])
def complete_meditation_route():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401

    user_id = session['user_id']
    success = complete_meditation(user_id)

    if success:
        return jsonify({'status': 'success'})
    else:
        return jsonify({'status': 'already_done'})

if __name__ == '__main__':
    init_database()                    # Create tables if not exist
    scheduler = start_scheduler()      # Start email + streak reset scheduler
    print("🚀 Daily 1 Minute Meditation Streak app started!")
    print("Reminder emails checked every minute.")
    print("Streak reset runs daily at 00:00 (server local time).")
    app.run(debug=True, use_reloader=False)  # use_reloader=False prevents duplicate scheduler