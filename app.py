"""
Car Management System - Single-file Flask app
- Auto-creates templates/ and static/ folders and writes HTML templates (Bootstrap)
- Auto-creates MySQL database and tables if missing
- Admin authentication (default admin/admin123)
- CRUD for cars, customers, bookings, services
- Admin dashboard to manage all records (view/update/delete)
Requires:
    pip install flask pymysql werkzeug
MySQL:
    host=localhost, user=root, password=root (as provided)
"""

import os
import pymysql
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date

# ----------------------
# Config
# ----------------------
MYSQL_HOST = 'localhost'
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'root'   # you confirmed "root" is the password
DB_NAME = 'car_management'

SECRET_KEY = 'super_secret_key_please_change'  # change for production
ADMIN_DEFAULT_USERNAME = 'admin'
ADMIN_DEFAULT_PASSWORD = 'admin123'

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

# ----------------------
# Ensure folders exist
# ----------------------
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, 'css'), exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, 'js'), exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, 'images'), exist_ok=True)

# ----------------------
# Flask App
# ----------------------
app = Flask(__name__, template_folder=TEMPLATES_DIR, static_folder=STATIC_DIR)
app.secret_key = SECRET_KEY

# ----------------------
# Database helpers
# ----------------------
def get_connection(with_db=True):
    conn = pymysql.connect(host=MYSQL_HOST, user=MYSQL_USER, password=MYSQL_PASSWORD,
                           charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor,
                           autocommit=True)
    if with_db:
        conn.select_db(DB_NAME)
    return conn

def init_db():
    # Create DB and tables if not exist
    conn = get_connection(with_db=False)
    cur = conn.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;")
    conn.select_db(DB_NAME)

    # users table (admin)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(100) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        role VARCHAR(50) DEFAULT 'admin',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # cars table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS cars (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(120) NOT NULL,
        brand VARCHAR(120),
        model VARCHAR(120),
        year INT,
        price_per_day DECIMAL(10,2) DEFAULT 0,
        status VARCHAR(50) DEFAULT 'available', -- available, rented, maintenance
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # customers table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(150) NOT NULL,
        email VARCHAR(150),
        phone VARCHAR(50),
        license_no VARCHAR(120),
        address TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # bookings table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id INT AUTO_INCREMENT PRIMARY KEY,
        car_id INT NOT NULL,
        customer_id INT NOT NULL,
        start_date DATE NOT NULL,
        end_date DATE NOT NULL,
        total_cost DECIMAL(12,2) DEFAULT 0,
        status VARCHAR(50) DEFAULT 'active', -- active, completed, cancelled
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (car_id) REFERENCES cars(id) ON DELETE CASCADE,
        FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
    );
    """)

    # services table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS services (
        id INT AUTO_INCREMENT PRIMARY KEY,
        car_id INT NOT NULL,
        service_date DATE,
        service_type VARCHAR(200),
        cost DECIMAL(10,2) DEFAULT 0,
        remarks TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (car_id) REFERENCES cars(id) ON DELETE CASCADE
    );
    """)

    # Insert default admin if not exists
    cur.execute("SELECT id FROM users WHERE username=%s", (ADMIN_DEFAULT_USERNAME,))
    if not cur.fetchone():
        pw_hash = generate_password_hash(ADMIN_DEFAULT_PASSWORD)
        cur.execute("INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
                    (ADMIN_DEFAULT_USERNAME, pw_hash, 'admin'))
        print(f"Default admin created -> username: {ADMIN_DEFAULT_USERNAME} password: {ADMIN_DEFAULT_PASSWORD}")

    cur.close()
    conn.close()

# Initialize DB at startup
init_db()

# ----------------------
# Helper functions
# ----------------------
def admin_required(func):
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please login first.", "warning")
            return redirect(url_for('login'))
        # optionally check role
        return func(*args, **kwargs)
    return wrapper

# ----------------------
# Routes - Utility
# ----------------------
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(STATIC_DIR, filename)

# ----------------------
# Authentication
# ----------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = request.form.get('username')
        p = request.form.get('password')
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=%s", (u,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        if user and check_password_hash(user['password_hash'], p):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash("Logged in successfully.", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials.", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for('login'))

# ----------------------
# Home / Public pages
# ----------------------
@app.route('/')
def index():
    # show some summary stats
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as total_cars FROM cars")
    total_cars = cur.fetchone()['total_cars']
    cur.execute("SELECT COUNT(*) as total_customers FROM customers")
    total_customers = cur.fetchone()['total_customers']
    cur.execute("SELECT COUNT(*) as total_bookings FROM bookings")
    total_bookings = cur.fetchone()['total_bookings']
    cur.close()
    conn.close()
    return render_template('index.html', total_cars=total_cars,
                           total_customers=total_customers, total_bookings=total_bookings)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET','POST'])
def contact():
    if request.method == 'POST':
        flash("Thank you for contacting us. We'll get back to you.", "success")
        return redirect(url_for('index'))
    return render_template('contact.html')

# ----------------------
# Admin Dashboard (summary + quick links)
# ----------------------
@app.route('/dashboard')
@admin_required
def dashboard():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as total_cars FROM cars")
    total_cars = cur.fetchone()['total_cars']
    cur.execute("SELECT COUNT(*) as total_customers FROM customers")
    total_customers = cur.fetchone()['total_customers']
    cur.execute("SELECT COUNT(*) as total_bookings FROM bookings")
    total_bookings = cur.fetchone()['total_bookings']
    cur.execute("SELECT COUNT(*) as total_services FROM services")
    total_services = cur.fetchone()['total_services']

    # recent bookings
    cur.execute("SELECT b.*, c.name as car_name, cu.name as customer_name FROM bookings b JOIN cars c ON b.car_id=c.id JOIN customers cu ON b.customer_id=cu.id ORDER BY b.created_at DESC LIMIT 6")
    recent_bookings = cur.fetchall()

    cur.close()
    conn.close()
    return render_template('dashboard.html', total_cars=total_cars,
                           total_customers=total_customers, total_bookings=total_bookings,
                           total_services=total_services, recent_bookings=recent_bookings)


# ----------------------
# Cars CRUD
# ----------------------
@app.route('/cars')
@admin_required
def view_cars():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM cars ORDER BY created_at DESC")
    cars = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('view_cars.html', cars=cars)

@app.route('/cars/add', methods=['GET', 'POST'])
@admin_required
def add_car():
    if request.method == 'POST':
        name = request.form.get('name')
        brand = request.form.get('brand')
        model = request.form.get('model')
        year = request.form.get('year') or None
        price = request.form.get('price') or 0
        status = request.form.get('status') or 'available'
        description = request.form.get('description')
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""INSERT INTO cars (name, brand, model, year, price_per_day, status, description)
                       VALUES (%s,%s,%s,%s,%s,%s,%s)""", (name,brand,model,year,price,status,description))
        cur.close()
        conn.close()
        flash("Car added.", "success")
        return redirect(url_for('view_cars'))
    return render_template('add_car.html')

@app.route('/cars/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_car(id):
    conn = get_connection()
    cur = conn.cursor()
    if request.method == 'POST':
        name = request.form.get('name')
        brand = request.form.get('brand')
        model = request.form.get('model')
        year = request.form.get('year') or None
        price = request.form.get('price') or 0
        status = request.form.get('status') or 'available'
        description = request.form.get('description')
        cur.execute("""UPDATE cars SET name=%s, brand=%s, model=%s, year=%s, price_per_day=%s, status=%s, description=%s WHERE id=%s""",
                    (name,brand,model,year,price,status,description, id))
        flash("Car updated.", "success")
        cur.close()
        conn.close()
        return redirect(url_for('view_cars'))
    cur.execute("SELECT * FROM cars WHERE id=%s", (id,))
    car = cur.fetchone()
    cur.close()
    conn.close()
    if not car:
        flash("Car not found.", "danger")
        return redirect(url_for('view_cars'))
    return render_template('edit_car.html', car=car)

@app.route('/cars/delete/<int:id>', methods=['POST'])
@admin_required
def delete_car(id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM cars WHERE id=%s", (id,))
    cur.close()
    conn.close()
    flash("Car deleted.", "info")
    return redirect(url_for('view_cars'))


# ----------------------
# Customers CRUD
# ----------------------
@app.route('/customers')
@admin_required
def view_customers():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM customers ORDER BY created_at DESC")
    customers = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('view_customers.html', customers=customers)

@app.route('/customers/add', methods=['GET','POST'])
@admin_required
def add_customer():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        license_no = request.form.get('license_no')
        address = request.form.get('address')
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""INSERT INTO customers (name,email,phone,license_no,address) VALUES (%s,%s,%s,%s,%s)""",
                    (name,email,phone,license_no,address))
        cur.close()
        conn.close()
        flash("Customer added.", "success")
        return redirect(url_for('view_customers'))
    return render_template('add_customer.html')

@app.route('/customers/edit/<int:id>', methods=['GET','POST'])
@admin_required
def edit_customer(id):
    conn = get_connection()
    cur = conn.cursor()
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        license_no = request.form.get('license_no')
        address = request.form.get('address')
        cur.execute("""UPDATE customers SET name=%s, email=%s, phone=%s, license_no=%s, address=%s WHERE id=%s""",
                    (name,email,phone,license_no,address, id))
        flash("Customer updated.", "success")
        cur.close()
        conn.close()
        return redirect(url_for('view_customers'))
    cur.execute("SELECT * FROM customers WHERE id=%s", (id,))
    cust = cur.fetchone()
    cur.close()
    conn.close()
    if not cust:
        flash("Customer not found.", "danger")
        return redirect(url_for('view_customers'))
    return render_template('edit_customer.html', customer=cust)

@app.route('/customers/delete/<int:id>', methods=['POST'])
@admin_required
def delete_customer(id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM customers WHERE id=%s", (id,))
    cur.close()
    conn.close()
    flash("Customer deleted.", "info")
    return redirect(url_for('view_customers'))

# ----------------------
# Bookings CRUD
# ----------------------
def calc_total_cost(car_price_per_day, start_date, end_date):
    sd = datetime.strptime(start_date, "%Y-%m-%d").date()
    ed = datetime.strptime(end_date, "%Y-%m-%d").date()
    days = (ed - sd).days + 1
    if days < 1:
        days = 1
    return float(car_price_per_day) * days

@app.route('/bookings')
@admin_required
def view_bookings():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""SELECT b.*, c.name as car_name, cu.name as customer_name
                   FROM bookings b
                   JOIN cars c ON b.car_id=c.id
                   JOIN customers cu ON b.customer_id=cu.id
                   ORDER BY b.created_at DESC""")
    bookings = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('view_bookings.html', bookings=bookings)

@app.route('/bookings/add', methods=['GET','POST'])
@admin_required
def add_booking():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM cars WHERE status='available' OR status='maintenance' ORDER BY name")
    cars = cur.fetchall()
    cur.execute("SELECT * FROM customers ORDER BY name")
    customers = cur.fetchall()

    if request.method == 'POST':
        car_id = request.form.get('car_id')
        customer_id = request.form.get('customer_id')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        # fetch car price
        cur.execute("SELECT price_per_day FROM cars WHERE id=%s", (car_id,))
        car = cur.fetchone()
        price = float(car['price_per_day']) if car else 0
        total = calc_total_cost(price, start_date, end_date)
        cur.execute("""INSERT INTO bookings (car_id, customer_id, start_date, end_date, total_cost, status)
                       VALUES (%s,%s,%s,%s,%s,%s)""", (car_id, customer_id, start_date, end_date, total, 'active'))
        # mark car as rented
        cur.execute("UPDATE cars SET status=%s WHERE id=%s", ('rented', car_id))
        flash("Booking created.", "success")
        cur.close()
        conn.close()
        return redirect(url_for('view_bookings'))

    cur.close()
    conn.close()
    return render_template('add_booking.html', cars=cars, customers=customers)

@app.route('/bookings/edit/<int:id>', methods=['GET','POST'])
@admin_required
def edit_booking(id):
    conn = get_connection()
    cur = conn.cursor()
    if request.method == 'POST':
        car_id = request.form.get('car_id')
        customer_id = request.form.get('customer_id')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        status = request.form.get('status')
        # fetch car price
        cur.execute("SELECT price_per_day FROM cars WHERE id=%s", (car_id,))
        car = cur.fetchone()
        price = float(car['price_per_day']) if car else 0
        total = calc_total_cost(price, start_date, end_date)
        cur.execute("""UPDATE bookings SET car_id=%s, customer_id=%s, start_date=%s, end_date=%s, total_cost=%s, status=%s WHERE id=%s""",
                    (car_id,customer_id,start_date,end_date,total,status,id))
        # if completed or cancelled, set car status available if not used elsewhere
        if status in ('completed','cancelled'):
            cur.execute("UPDATE cars SET status=%s WHERE id=%s", ('available', car_id))
        flash("Booking updated.", "success")
        cur.close()
        conn.close()
        return redirect(url_for('view_bookings'))

    cur.execute("SELECT * FROM bookings WHERE id=%s", (id,))
    booking = cur.fetchone()
    cur.execute("SELECT * FROM cars ORDER BY name")
    cars = cur.fetchall()
    cur.execute("SELECT * FROM customers ORDER BY name")
    customers = cur.fetchall()
    cur.close()
    conn.close()
    if not booking:
        flash("Booking not found.", "danger")
        return redirect(url_for('view_bookings'))
    return render_template('edit_booking.html', booking=booking, cars=cars, customers=customers)

@app.route('/bookings/delete/<int:id>', methods=['POST'])
@admin_required
def delete_booking(id):
    conn = get_connection()
    cur = conn.cursor()
    # before deleting, set linked car status to available
    cur.execute("SELECT car_id FROM bookings WHERE id=%s", (id,))
    row = cur.fetchone()
    if row:
        car_id = row['car_id']
        cur.execute("UPDATE cars SET status=%s WHERE id=%s", ('available', car_id))
    cur.execute("DELETE FROM bookings WHERE id=%s", (id,))
    cur.close()
    conn.close()
    flash("Booking deleted.", "info")
    return redirect(url_for('view_bookings'))

# ----------------------
# Services CRUD
# ----------------------
@app.route('/services')
@admin_required
def view_services():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""SELECT s.*, c.name as car_name FROM services s JOIN cars c ON s.car_id=c.id ORDER BY s.created_at DESC""")
    services = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('view_services.html', services=services)

@app.route('/services/add', methods=['GET','POST'])
@admin_required
def add_service():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM cars ORDER BY name")
    cars = cur.fetchall()
    if request.method == 'POST':
        car_id = request.form.get('car_id')
        service_date = request.form.get('service_date') or None
        service_type = request.form.get('service_type')
        cost = request.form.get('cost') or 0
        remarks = request.form.get('remarks')
        cur.execute("""INSERT INTO services (car_id, service_date, service_type, cost, remarks)
                       VALUES (%s,%s,%s,%s,%s)""", (car_id, service_date, service_type, cost, remarks))
        # set car to maintenance
        cur.execute("UPDATE cars SET status=%s WHERE id=%s", ('maintenance', car_id))
        flash("Service record added.", "success")
        cur.close()
        conn.close()
        return redirect(url_for('view_services'))
    cur.close()
    conn.close()
    return render_template('add_service.html', cars=cars)

@app.route('/services/edit/<int:id>', methods=['GET','POST'])
@admin_required
def edit_service(id):
    conn = get_connection()
    cur = conn.cursor()
    if request.method == 'POST':
        car_id = request.form.get('car_id')
        service_date = request.form.get('service_date') or None
        service_type = request.form.get('service_type')
        cost = request.form.get('cost') or 0
        remarks = request.form.get('remarks')
        cur.execute("""UPDATE services SET car_id=%s, service_date=%s, service_type=%s, cost=%s, remarks=%s WHERE id=%s""",
                    (car_id,service_date,service_type,cost,remarks,id))
        flash("Service record updated.", "success")
        cur.close()
        conn.close()
        return redirect(url_for('view_services'))

    cur.execute("SELECT * FROM services WHERE id=%s", (id,))
    service = cur.fetchone()
    cur.execute("SELECT * FROM cars ORDER BY name")
    cars = cur.fetchall()
    cur.close()
    conn.close()
    if not service:
        flash("Service not found.", "danger")
        return redirect(url_for('view_services'))
    return render_template('edit_service.html', service=service, cars=cars)

@app.route('/services/delete/<int:id>', methods=['POST'])
@admin_required
def delete_service(id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM services WHERE id=%s", (id,))
    cur.close()
    conn.close()
    flash("Service record deleted.", "info")
    return redirect(url_for('view_services'))


# ----------------------
# Create templates if missing (simple Bootstrap layout + pages)
# ----------------------
# NOTE: templates are intentionally straightforward so you can customize them.
TEMPLATE_CONTENT = {
"layout.html": """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Car Management System - {% block title %}{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
  </head>
  <body>
  <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
    <div class="container-fluid">
      <a class="navbar-brand" href="{{ url_for('index') }}">CarMgmt</a>
      <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navmenu">
        <span class="navbar-toggler-icon"></span>
      </button>
      <div class="collapse navbar-collapse" id="navmenu">
        <ul class="navbar-nav me-auto mb-2 mb-lg-0">
          {% if session.get('user_id') %}
          <li class="nav-item"><a class="nav-link" href="{{ url_for('dashboard') }}">Dashboard</a></li>
          <li class="nav-item"><a class="nav-link" href="{{ url_for('view_cars') }}">Cars</a></li>
          <li class="nav-item"><a class="nav-link" href="{{ url_for('view_customers') }}">Customers</a></li>
          <li class="nav-item"><a class="nav-link" href="{{ url_for('view_bookings') }}">Bookings</a></li>
          <li class="nav-item"><a class="nav-link" href="{{ url_for('view_services') }}">Services</a></li>
          {% endif %}
          <li class="nav-item"><a class="nav-link" href="{{ url_for('about') }}">About</a></li>
          <li class="nav-item"><a class="nav-link" href="{{ url_for('contact') }}">Contact</a></li>
        </ul>
        <ul class="navbar-nav">
          {% if session.get('user_id') %}
            <li class="nav-item"><span class="nav-link">Hi, {{ session.get('username') }}</span></li>
            <li class="nav-item"><a class="nav-link" href="{{ url_for('logout') }}">Logout</a></li>
          {% else %}
            <li class="nav-item"><a class="nav-link" href="{{ url_for('login') }}">Admin Login</a></li>
          {% endif %}
        </ul>
      </div>
    </div>
  </nav>

  <div class="container mt-4">
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for category, msg in messages %}
          <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
            {{ msg }}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
          </div>
        {% endfor %}
      {% endif %}
    {% endwith %}
    {% block content %}{% endblock %}
  </div>

  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
  </body>
</html>
""",

"index.html": """{% extends 'layout.html' %}
{% block title %}Home{% endblock %}
{% block content %}
  <div class="row">
    <div class="col-md-8">
      <h1>Welcome to Car Management System</h1>
      <p>Manage cars, customers, bookings and services from the admin dashboard.</p>
    </div>
    <div class="col-md-4">
      <div class="card">
        <div class="card-body">
          <h5>Summary</h5>
          <p>Cars: <strong>{{ total_cars }}</strong></p>
          <p>Customers: <strong>{{ total_customers }}</strong></p>
          <p>Bookings: <strong>{{ total_bookings }}</strong></p>
          <a href="{{ url_for('login') }}" class="btn btn-primary">Admin Login</a>
        </div>
      </div>
    </div>
  </div>
{% endblock %}
""",

"login.html": """{% extends 'layout.html' %}
{% block title %}Login{% endblock %}
{% block content %}
  <div class="row justify-content-center">
    <div class="col-md-5">
      <h3>Admin Login</h3>
      <form method="post">
        <div class="mb-3"><label class="form-label">Username</label>
          <input class="form-control" name="username" required></div>
        <div class="mb-3"><label class="form-label">Password</label>
          <input class="form-control" name="password" type="password" required></div>
        <button class="btn btn-success">Login</button>
      </form>
      <hr>
      <p>Default admin: <strong>admin</strong> / <strong>admin123</strong></p>
    </div>
  </div>
{% endblock %}
""",

"dashboard.html": """{% extends 'layout.html' %}
{% block title %}Dashboard{% endblock %}
{% block content %}
  <h2>Admin Dashboard</h2>
  <div class="row">
    <div class="col-md-3"><div class="card p-3"><h5>Cars</h5><p>{{ total_cars }}</p><a class="btn btn-sm btn-primary" href="{{ url_for('view_cars') }}">Manage</a></div></div>
    <div class="col-md-3"><div class="card p-3"><h5>Customers</h5><p>{{ total_customers }}</p><a class="btn btn-sm btn-primary" href="{{ url_for('view_customers') }}">Manage</a></div></div>
    <div class="col-md-3"><div class="card p-3"><h5>Bookings</h5><p>{{ total_bookings }}</p><a class="btn btn-sm btn-primary" href="{{ url_for('view_bookings') }}">Manage</a></div></div>
    <div class="col-md-3"><div class="card p-3"><h5>Services</h5><p>{{ total_services }}</p><a class="btn btn-sm btn-primary" href="{{ url_for('view_services') }}">Manage</a></div></div>
  </div>

  <h4 class="mt-4">Recent Bookings</h4>
  <table class="table table-striped">
    <thead><tr><th>ID</th><th>Car</th><th>Customer</th><th>Period</th><th>Total</th><th>Status</th></tr></thead>
    <tbody>
    {% for b in recent_bookings %}
      <tr>
        <td>{{ b.id }}</td>
        <td>{{ b.car_name }}</td>
        <td>{{ b.customer_name }}</td>
        <td>{{ b.start_date }} to {{ b.end_date }}</td>
        <td>{{ b.total_cost }}</td>
        <td>{{ b.status }}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
{% endblock %}
""",

"view_cars.html": """{% extends 'layout.html' %}
{% block title %}Cars{% endblock %}
{% block content %}
  <div class="d-flex justify-content-between align-items-center">
    <h3>Cars</h3>
    <a class="btn btn-success" href="{{ url_for('add_car') }}">Add Car</a>
  </div>
  <table class="table table-bordered mt-3">
    <thead><tr><th>ID</th><th>Name</th><th>Brand</th><th>Model</th><th>Year</th><th>Price/day</th><th>Status</th><th>Actions</th></tr></thead>
    <tbody>
    {% for c in cars %}
      <tr>
        <td>{{ c.id }}</td>
        <td>{{ c.name }}</td>
        <td>{{ c.brand }}</td>
        <td>{{ c.model }}</td>
        <td>{{ c.year }}</td>
        <td>{{ c.price_per_day }}</td>
        <td>{{ c.status }}</td>
        <td>
          <a class="btn btn-sm btn-primary" href="{{ url_for('edit_car', id=c.id) }}">Edit</a>
          <form method="post" action="{{ url_for('delete_car', id=c.id) }}" style="display:inline-block" onsubmit="return confirm('Delete this car?')">
            <button class="btn btn-sm btn-danger">Delete</button>
          </form>
        </td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
{% endblock %}
""",

"add_car.html": """{% extends 'layout.html' %}
{% block title %}Add Car{% endblock %}
{% block content %}
  <h3>Add Car</h3>
  <form method="post">
    <div class="mb-3"><label class="form-label">Name</label><input class="form-control" name="name" required></div>
    <div class="mb-3"><label class="form-label">Brand</label><input class="form-control" name="brand"></div>
    <div class="mb-3"><label class="form-label">Model</label><input class="form-control" name="model"></div>
    <div class="mb-3"><label class="form-label">Year</label><input class="form-control" name="year" type="number"></div>
    <div class="mb-3"><label class="form-label">Price per day</label><input class="form-control" name="price" type="number" step="0.01"></div>
    <div class="mb-3"><label class="form-label">Status</label>
      <select class="form-select" name="status"><option value="available">Available</option><option value="rented">Rented</option><option value="maintenance">Maintenance</option></select>
    </div>
    <div class="mb-3"><label class="form-label">Description</label><textarea class="form-control" name="description"></textarea></div>
    <button class="btn btn-success">Add Car</button>
  </form>
{% endblock %}
""",

"edit_car.html": """{% extends 'layout.html' %}
{% block title %}Edit Car{% endblock %}
{% block content %}
  <h3>Edit Car</h3>
  <form method="post">
    <div class="mb-3"><label class="form-label">Name</label><input class="form-control" name="name" required value="{{ car.name }}"></div>
    <div class="mb-3"><label class="form-label">Brand</label><input class="form-control" name="brand" value="{{ car.brand }}"></div>
    <div class="mb-3"><label class="form-label">Model</label><input class="form-control" name="model" value="{{ car.model }}"></div>
    <div class="mb-3"><label class="form-label">Year</label><input class="form-control" name="year" type="number" value="{{ car.year }}"></div>
    <div class="mb-3"><label class="form-label">Price per day</label><input class="form-control" name="price" type="number" step="0.01" value="{{ car.price_per_day }}"></div>
    <div class="mb-3"><label class="form-label">Status</label>
      <select class="form-select" name="status">
        <option value="available" {% if car.status=='available' %}selected{% endif %}>Available</option>
        <option value="rented" {% if car.status=='rented' %}selected{% endif %}>Rented</option>
        <option value="maintenance" {% if car.status=='maintenance' %}selected{% endif %}>Maintenance</option>
      </select>
    </div>
    <div class="mb-3"><label class="form-label">Description</label><textarea class="form-control" name="description">{{ car.description }}</textarea></div>
    <button class="btn btn-primary">Save</button>
  </form>
{% endblock %}
""",

"view_customers.html": """{% extends 'layout.html' %}
{% block title %}Customers{% endblock %}
{% block content %}
  <div class="d-flex justify-content-between align-items-center">
    <h3>Customers</h3>
    <a class="btn btn-success" href="{{ url_for('add_customer') }}">Add Customer</a>
  </div>
  <table class="table table-bordered mt-3">
    <thead><tr><th>ID</th><th>Name</th><th>Email</th><th>Phone</th><th>License</th><th>Actions</th></tr></thead>
    <tbody>
    {% for c in customers %}
      <tr>
        <td>{{ c.id }}</td>
        <td>{{ c.name }}</td>
        <td>{{ c.email }}</td>
        <td>{{ c.phone }}</td>
        <td>{{ c.license_no }}</td>
        <td>
          <a class="btn btn-sm btn-primary" href="{{ url_for('edit_customer', id=c.id) }}">Edit</a>
          <form method="post" action="{{ url_for('delete_customer', id=c.id) }}" style="display:inline-block" onsubmit="return confirm('Delete this customer?')">
            <button class="btn btn-sm btn-danger">Delete</button>
          </form>
        </td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
{% endblock %}
""",

"add_customer.html": """{% extends 'layout.html' %}
{% block title %}Add Customer{% endblock %}
{% block content %}
  <h3>Add Customer</h3>
  <form method="post">
    <div class="mb-3"><label class="form-label">Name</label><input class="form-control" name="name" required></div>
    <div class="mb-3"><label class="form-label">Email</label><input class="form-control" name="email" type="email"></div>
    <div class="mb-3"><label class="form-label">Phone</label><input class="form-control" name="phone"></div>
    <div class="mb-3"><label class="form-label">License No</label><input class="form-control" name="license_no"></div>
    <div class="mb-3"><label class="form-label">Address</label><textarea class="form-control" name="address"></textarea></div>
    <button class="btn btn-success">Add Customer</button>
  </form>
{% endblock %}
""",

"edit_customer.html": """{% extends 'layout.html' %}
{% block title %}Edit Customer{% endblock %}
{% block content %}
  <h3>Edit Customer</h3>
  <form method="post">
    <div class="mb-3"><label class="form-label">Name</label><input class="form-control" name="name" required value="{{ customer.name }}"></div>
    <div class="mb-3"><label class="form-label">Email</label><input class="form-control" name="email" type="email" value="{{ customer.email }}"></div>
    <div class="mb-3"><label class="form-label">Phone</label><input class="form-control" name="phone" value="{{ customer.phone }}"></div>
    <div class="mb-3"><label class="form-label">License No</label><input class="form-control" name="license_no" value="{{ customer.license_no }}"></div>
    <div class="mb-3"><label class="form-label">Address</label><textarea class="form-control" name="address">{{ customer.address }}</textarea></div>
    <button class="btn btn-primary">Save</button>
  </form>
{% endblock %}
""",

"view_bookings.html": """{% extends 'layout.html' %}
{% block title %}Bookings{% endblock %}
{% block content %}
  <div class="d-flex justify-content-between align-items-center">
    <h3>Bookings</h3>
    <a class="btn btn-success" href="{{ url_for('add_booking') }}">Add Booking</a>
  </div>
  <table class="table table-bordered mt-3">
    <thead><tr><th>ID</th><th>Car</th><th>Customer</th><th>Start</th><th>End</th><th>Total</th><th>Status</th><th>Actions</th></tr></thead>
    <tbody>
    {% for b in bookings %}
      <tr>
        <td>{{ b.id }}</td>
        <td>{{ b.car_name }}</td>
        <td>{{ b.customer_name }}</td>
        <td>{{ b.start_date }}</td>
        <td>{{ b.end_date }}</td>
        <td>{{ b.total_cost }}</td>
        <td>{{ b.status }}</td>
        <td>
          <a class="btn btn-sm btn-primary" href="{{ url_for('edit_booking', id=b.id) }}">Edit</a>
          <form method="post" action="{{ url_for('delete_booking', id=b.id) }}" style="display:inline-block" onsubmit="return confirm('Delete this booking?')">
            <button class="btn btn-sm btn-danger">Delete</button>
          </form>
        </td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
{% endblock %}
""",

"add_booking.html": """{% extends 'layout.html' %}
{% block title %}Add Booking{% endblock %}
{% block content %}
  <h3>Add Booking</h3>
  <form method="post">
    <div class="mb-3"><label class="form-label">Car</label>
      <select class="form-select" name="car_id" required>
        {% for c in cars %}
          <option value="{{ c.id }}">{{ c.name }} ({{ c.status }}) - {{ c.price_per_day }}/day</option>
        {% endfor %}
      </select>
    </div>
    <div class="mb-3"><label class="form-label">Customer</label>
      <select class="form-select" name="customer_id" required>
        {% for cu in customers %}
          <option value="{{ cu.id }}">{{ cu.name }}</option>
        {% endfor %}
      </select>
    </div>
    <div class="mb-3"><label class="form-label">Start Date</label><input class="form-control" name="start_date" type="date" required></div>
    <div class="mb-3"><label class="form-label">End Date</label><input class="form-control" name="end_date" type="date" required></div>
    <button class="btn btn-success">Create Booking</button>
  </form>
{% endblock %}
""",

"edit_booking.html": """{% extends 'layout.html' %}
{% block title %}Edit Booking{% endblock %}
{% block content %}
  <h3>Edit Booking</h3>
  <form method="post">
    <div class="mb-3"><label class="form-label">Car</label>
      <select class="form-select" name="car_id" required>
        {% for c in cars %}
          <option value="{{ c.id }}" {% if booking.car_id==c.id %}selected{% endif %}>{{ c.name }}</option>
        {% endfor %}
      </select>
    </div>
    <div class="mb-3"><label class="form-label">Customer</label>
      <select class="form-select" name="customer_id" required>
        {% for cu in customers %}
          <option value="{{ cu.id }}" {% if booking.customer_id==cu.id %}selected{% endif %}>{{ cu.name }}</option>
        {% endfor %}
      </select>
    </div>
    <div class="mb-3"><label class="form-label">Start Date</label><input class="form-control" name="start_date" type="date" required value="{{ booking.start_date }}"></div>
    <div class="mb-3"><label class="form-label">End Date</label><input class="form-control" name="end_date" type="date" required value="{{ booking.end_date }}"></div>
    <div class="mb-3"><label class="form-label">Status</label>
      <select class="form-select" name="status">
        <option value="active" {% if booking.status=='active' %}selected{% endif %}>Active</option>
        <option value="completed" {% if booking.status=='completed' %}selected{% endif %}>Completed</option>
        <option value="cancelled" {% if booking.status=='cancelled' %}selected{% endif %}>Cancelled</option>
      </select>
    </div>
    <button class="btn btn-primary">Save</button>
  </form>
{% endblock %}
""",

"view_services.html": """{% extends 'layout.html' %}
{% block title %}Services{% endblock %}
{% block content %}
  <div class="d-flex justify-content-between align-items-center">
    <h3>Services</h3>
    <a class="btn btn-success" href="{{ url_for('add_service') }}">Add Service</a>
  </div>
  <table class="table table-bordered mt-3">
    <thead><tr><th>ID</th><th>Car</th><th>Date</th><th>Type</th><th>Cost</th><th>Remarks</th><th>Actions</th></tr></thead>
    <tbody>
    {% for s in services %}
      <tr>
        <td>{{ s.id }}</td>
        <td>{{ s.car_name }}</td>
        <td>{{ s.service_date }}</td>
        <td>{{ s.service_type }}</td>
        <td>{{ s.cost }}</td>
        <td>{{ s.remarks }}</td>
        <td>
          <a class="btn btn-sm btn-primary" href="{{ url_for('edit_service', id=s.id) }}">Edit</a>
          <form method="post" action="{{ url_for('delete_service', id=s.id) }}" style="display:inline-block" onsubmit="return confirm('Delete this service?')">
            <button class="btn btn-sm btn-danger">Delete</button>
          </form>
        </td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
{% endblock %}
""",

"add_service.html": """{% extends 'layout.html' %}
{% block title %}Add Service{% endblock %}
{% block content %}
  <h3>Add Service</h3>
  <form method="post">
    <div class="mb-3"><label class="form-label">Car</label>
      <select class="form-select" name="car_id" required>
        {% for c in cars %}
          <option value="{{ c.id }}">{{ c.name }}</option>
        {% endfor %}
      </select>
    </div>
    <div class="mb-3"><label class="form-label">Service Date</label><input class="form-control" name="service_date" type="date"></div>
    <div class="mb-3"><label class="form-label">Service Type</label><input class="form-control" name="service_type"></div>
    <div class="mb-3"><label class="form-label">Cost</label><input class="form-control" name="cost" type="number" step="0.01"></div>
    <div class="mb-3"><label class="form-label">Remarks</label><textarea class="form-control" name="remarks"></textarea></div>
    <button class="btn btn-success">Add Service</button>
  </form>
{% endblock %}
""",

"edit_service.html": """{% extends 'layout.html' %}
{% block title %}Edit Service{% endblock %}
{% block content %}
  <h3>Edit Service</h3>
  <form method="post">
    <div class="mb-3"><label class="form-label">Car</label>
      <select class="form-select" name="car_id" required>
        {% for c in cars %}
          <option value="{{ c.id }}" {% if service.car_id==c.id %}selected{% endif %}>{{ c.name }}</option>
        {% endfor %}
      </select>
    </div>
    <div class="mb-3"><label class="form-label">Service Date</label><input class="form-control" name="service_date" type="date" value="{{ service.service_date }}"></div>
    <div class="mb-3"><label class="form-label">Service Type</label><input class="form-control" name="service_type" value="{{ service.service_type }}"></div>
    <div class="mb-3"><label class="form-label">Cost</label><input class="form-control" name="cost" type="number" step="0.01" value="{{ service.cost }}"></div>
    <div class="mb-3"><label class="form-label">Remarks</label><textarea class="form-control" name="remarks">{{ service.remarks }}</textarea></div>
    <button class="btn btn-primary">Save</button>
  </form>
{% endblock %}
""",

"about.html": """{% extends 'layout.html' %}
{% block title %}About{% endblock %}
{% block content %}
  <h3>About</h3>
  <p>This Car Management System is a demo app to manage cars, customers, bookings, and maintenance/service records. Built with Flask and MySQL.</p>
{% endblock %}
""",

"contact.html": """{% extends 'layout.html' %}
{% block title %}Contact{% endblock %}
{% block content %}
  <h3>Contact</h3>
  <form method="post">
    <div class="mb-3"><label class="form-label">Your Name</label><input class="form-control" name="name" required></div>
    <div class="mb-3"><label class="form-label">Email</label><input class="form-control" name="email" type="email" required></div>
    <div class="mb-3"><label class="form-label">Message</label><textarea class="form-control" name="message" required></textarea></div>
    <button class="btn btn-primary">Send</button>
  </form>
{% endblock %}
""",

"error.html": """{% extends 'layout.html' %}
{% block title %}Error{% endblock %}
{% block content %}
  <h3>An error occurred</h3>
{% endblock %}
""",
}

# Write templates to files if missing
for fname, content in TEMPLATE_CONTENT.items():
    path = os.path.join(TEMPLATES_DIR, fname)
    if not os.path.exists(path):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

# ----------------------
# Run
# ----------------------
if __name__ == '__main__':
    # start the flask app
    app.run(debug=True, host='0.0.0.0', port=5000)
