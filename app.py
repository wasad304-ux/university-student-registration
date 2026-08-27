from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
import os
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)

# Secret key for session management
app.secret_key = 'your_secret_key_change_this'

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'university_registration'

mysql = MySQL(app)

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'loggedin' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ==================== HOME PAGE ====================
@app.route('/')
def home():
    """Home page"""
    return render_template('home.html')

# ==================== REGISTRATION ====================
@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page"""
    if request.method == 'POST':
        try:
            # Get form data
            fullname = request.form.get('fullname')
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            phone = request.form.get('phone')
            date_of_birth = request.form.get('date_of_birth')
            gender = request.form.get('gender')
            address = request.form.get('address')
            city = request.form.get('city')
            state = request.form.get('state')
            zipcode = request.form.get('zipcode')
            program = request.form.get('program')

            # Validation
            if not all([fullname, email, password, confirm_password, phone, date_of_birth, gender, program]):
                return jsonify({'success': False, 'message': 'All fields are required'}), 400

            if password != confirm_password:
                return jsonify({'success': False, 'message': 'Passwords do not match'}), 400

            if len(password) < 6:
                return jsonify({'success': False, 'message': 'Password must be at least 6 characters'}), 400

            # Email validation
            email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_regex, email):
                return jsonify({'success': False, 'message': 'Invalid email format'}), 400

            # Check if email already exists
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * FROM students WHERE email = %s', (email,))
            account = cursor.fetchone()

            if account:
                return jsonify({'success': False, 'message': 'Email already registered'}), 400

            # Insert new student
            cursor.execute(
                '''INSERT INTO students 
                (fullname, email, password, phone, date_of_birth, gender, address, city, state, zipcode, program, registration_date, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                (fullname, email, password, phone, date_of_birth, gender, address, city, state, zipcode, program, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'Active')
            )
            mysql.connection.commit()
            cursor.close()

            return jsonify({'success': True, 'message': 'Registration successful! Please login.'}), 201

        except Exception as e:
            return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

    return render_template('register.html')

# ==================== LOGIN ====================
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            password = request.form.get('password')

            if not email or not password:
                return jsonify({'success': False, 'message': 'Email and password are required'}), 400

            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * FROM students WHERE email = %s AND password = %s', (email, password))
            account = cursor.fetchone()
            cursor.close()

            if account:
                session['loggedin'] = True
                session['id'] = account['id']
                session['email'] = account['email']
                session['fullname'] = account['fullname']
                return jsonify({'success': True, 'message': 'Login successful!'}), 200
            else:
                return jsonify({'success': False, 'message': 'Invalid email or password'}), 401

        except Exception as e:
            return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

    return render_template('login.html')

# ==================== DASHBOARD ====================
@app.route('/dashboard')
@login_required
def dashboard():
    """Student dashboard"""
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM students WHERE id = %s', (session['id'],))
        student = cursor.fetchone()
        
        # Get courses if table exists
        cursor.execute('SELECT * FROM courses WHERE student_id = %s LIMIT 10', (session['id'],))
        courses = cursor.fetchall()
        
        cursor.close()
        
        return render_template('dashboard.html', student=student, courses=courses)
    except Exception as e:
        return render_template('dashboard.html', student=None, error=str(e))

# ==================== PROFILE ====================
@app.route('/profile')
@login_required
def profile():
    """Student profile"""
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM students WHERE id = %s', (session['id'],))
        student = cursor.fetchone()
        cursor.close()
        return render_template('profile.html', student=student)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== UPDATE PROFILE ====================
@app.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    """Update student profile"""
    try:
        fullname = request.form.get('fullname')
        phone = request.form.get('phone')
        address = request.form.get('address')
        city = request.form.get('city')
        state = request.form.get('state')
        zipcode = request.form.get('zipcode')

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(
            '''UPDATE students SET fullname = %s, phone = %s, address = %s, city = %s, state = %s, zipcode = %s 
            WHERE id = %s''',
            (fullname, phone, address, city, state, zipcode, session['id'])
        )
        mysql.connection.commit()
        cursor.close()

        session['fullname'] = fullname
        return jsonify({'success': True, 'message': 'Profile updated successfully!'}), 200

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== LOGOUT ====================
@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    return redirect(url_for('login'))

# ==================== ERROR HANDLERS ====================
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True)
