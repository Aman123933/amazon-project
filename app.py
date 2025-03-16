
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime
import os
import re

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management

def get_db():
    db = sqlite3.connect('amazon_clone.db')
    db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()

    # Drop existing tables
    db.execute('DROP TABLE IF EXISTS cart')
    db.execute('DROP TABLE IF EXISTS orders')
    db.execute('DROP TABLE IF EXISTS order_items')
    db.execute('DROP TABLE IF EXISTS reviews')
    db.execute('DROP TABLE IF EXISTS products')
    db.execute('DROP TABLE IF EXISTS users')

    # Create tables
    db.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )''')

    db.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        manufacturer TEXT NOT NULL,
        price REAL NOT NULL,
        description TEXT NOT NULL,
        release_date DATE NOT NULL
    )''')

    db.execute('''CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
        author TEXT NOT NULL,
        body TEXT NOT NULL,
        release_date DATE NOT NULL,
        release_time TIME NOT NULL,
        FOREIGN KEY (product_id) REFERENCES products (id)
    )''')

    db.execute('''CREATE TABLE IF NOT EXISTS cart (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (product_id) REFERENCES products (id)
    )''')

    db.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        order_date DATETIME NOT NULL,
        status TEXT NOT NULL,
        total_amount REAL NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')

    db.execute('''CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        price_at_time REAL NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders (id),
        FOREIGN KEY (product_id) REFERENCES products (id)
    )''')

    db.commit()

def sync_products():
    db = get_db()

    # List of expected products with columns in correct order (name, manufacturer, price, description, release_date)
    expected_products = [
        # Electronics
        ("MacBook Air M2", "Apple", 94500, "13.6-inch Liquid Retina display, Apple M2 chip, 8GB RAM, 256GB SSD storage.", "2023-06-15"),
        ("PlayStation 5 Digital Edition", "Sony", 54000, "Next-gen gaming console with 825GB SSD, 4K support, and DualSense controller.", "2020-11-12"),
        ("LG C2 65-Inch OLED TV", "LG", 52999, "4K OLED Smart TV with AI-powered processing, perfect blacks, and G-SYNC compatibility.", "2023-03-10"),
        ("Canon EOS R6 Mark II", "Canon", 267999, "Full-frame mirrorless camera with 24.2MP sensor, 4K video, and advanced autofocus.", "2022-11-02"),
        
        # Smart Home
        ("Ring Video Doorbell Pro 2", "Amazon", 7999, "1536p HDR video doorbell with 3D motion detection and Bird's Eye View.", "2023-03-31"),
        ("Philips Hue Starter Kit", "Philips", 2600, "Smart lighting bundle with bridge and 4 color-changing bulbs.", "2023-01-15"),
        ("Nest Learning Thermostat", "Google", 11618, "Smart thermostat that learns your preferences and helps save energy.", "2022-09-20"),
        
        # Kitchen Appliances
        ("Ninja Foodi 9-in-1 Deluxe XL", "Ninja", 21249, "Pressure cooker, air fryer, and more with 9 cooking functions and 8-quart capacity.", "2023-05-01"),
        ("KitchenAid Pro 5 Plus", "KitchenAid", 38250, "Professional 5-quart stand mixer with 10 speeds and bowl-lift design.", "2023-02-28"),
        ("Vitamix A3500 Blender", "Vitamix", 55250, "Smart blender with touchscreen controls, wireless connectivity, and 5 program settings.", "2023-04-15"),
        
        # Fitness
        ("Peloton Bike+", "Peloton", 218580, "Premium smart exercise bike with 24-inch rotating display and auto-follow resistance.", "2022-09-09"),
        ("Fitbit Sense 2", "Fitbit", 19550, "Advanced health smartwatch with ECG, stress tracking, and built-in GPS.", "2022-09-01"),
        ("Bowflex SelectTech 552", "Bowflex", 36550, "Adjustable dumbbells that replace 15 sets of weights, adjustable from 5 to 52.5 lbs.", "2023-01-10"),
        
        # Books and Media
        ("Lessons in Chemistry", "Bonnie Garmus", 1530, "A debut novel about a female chemist who becomes a cooking show host in the 1960s.", "2023-04-05"),
        ("Tomorrow x3", "James Clear", 1700, "A groundbreaking book about building better habits for productivity and success.", "2023-07-11"),
        ("The Light We Carry", "Michelle Obama", 1870, "Practical wisdom and powerful strategies for staying hopeful in uncertain times.", "2022-11-15"),
        
        # Gaming
        ("Xbox Series X", "Microsoft", 42500, "Next-gen gaming console with 1TB SSD, 4K gaming, and Quick Resume feature.", "2020-11-10"),
        ("Nintendo Switch OLED", "Nintendo", 29750, "Gaming console with 7-inch OLED screen and enhanced audio.", "2021-10-08"),
        ("Razer Blade 14", "Razer", 170000, "Gaming laptop with AMD Ryzen 9, RTX 4060, 16GB RAM, and 1TB SSD.", "2023-03-23"),
        
        # Audio
        ("AirPods Max", "Apple", 47600, "Over-ear headphones with active noise cancellation and spatial audio.", "2020-12-15"),
        ("Sonos Era 300", "Sonos", 42500, "Smart speaker with spatial audio and room-filling sound.", "2023-03-28"),
        ("Shure SM7B", "Shure", 34000, "Professional dynamic microphone for broadcasting and podcast recording.", "2023-01-05"),
        
        # Cameras
        ("DJI Air 3", "DJI", 93500 , "Drone with dual cameras, 4K/60fps video, and 46-minute flight time.", "2023-08-09"),
        ("GoPro HERO12 Black", "GoPro", 34000, "Action camera with 5.3K video, HDR, and enhanced stabilization.", "2023-09-15"),
        ("Fujifilm X-T5", "Fujifilm", 144500, "Mirrorless camera with 40MP sensor, 6.2K video, and advanced color science.", "2022-11-17"),
        
        # Smart Home Security
        ("Arlo Pro 5", "Arlo", 21414, "2K security camera with color night vision and built-in spotlight.", "2023-06-20"),
        ("SimpliSafe 8-Piece Kit", "SimpliSafe", 22000, "Home security system with professional monitoring and wireless sensors.", "2023-04-12"),
        ("Eufy Video Doorbell E340", "Eufy", 17114, "Dual camera video doorbell with package detection and local storage.", "2023-07-19"),
        
        # Gift Cards
        ("Amazon Gift Card", "Amazon", 8800, "Digital gift card for use on Amazon.com, never expires.", "2024-01-01"),
        ("Netflix Gift Card", "Netflix", 4400, "Gift card for streaming service subscription.", "2024-01-01"),
        ("Spotify Premium Gift", "Spotify", 2640, "Three months of ad-free music streaming.", "2024-01-01")
    ]

    # Get current products from database
    current_products = db.execute('SELECT name, manufacturer, price, description, release_date FROM products').fetchall()

    # Convert to sets for comparison (using name as unique identifier)
    current_names = {product[0] for product in current_products}
    expected_names = {product[0] for product in expected_products}

    if current_names != expected_names:
        # Clear existing products and insert new ones
        db.execute('DELETE FROM products')
        db.executemany('INSERT INTO products (name, manufacturer, price, description, release_date) VALUES (?, ?, ?, ?, ?)', expected_products)
        db.commit()

def is_logged_in():
    return 'user_id' in session

def validate_address(address, city, state, zip_code):
    # Validate ZIP code
    indian_states = [
        'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 
    'Chhattisgarh', 'Goa', 'Gujarat', 'Haryana', 
    'Himachal Pradesh', 'Jharkhand', 'Karnataka', 'Kerala', 
    'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 
    'Mizoram', 'Nagaland', 'Odisha', 'Punjab', 
    'Rajasthan', 'Sikkim', 'Tamil Nadu', 'Telangana', 
    'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal',
    'Andaman and Nicobar Islands', 'Chandigarh', 
    'Dadra and Nagar Haveli and Daman and Diu', 'Delhi', 
    'Jammu and Kashmir', 'Ladakh', 'Lakshadweep', 
    'Puducherry'
    ]

    # Validate PIN code (Indian postal code)
    if not re.match(r'^\d{6}$', zip_code):
        return False, "Invalid PIN code format. Please enter a 6-digit PIN code"

    # Validate state code
    if state.upper() not in indian_states:
        return False, "Invalid state code. Please use standard state codes (e.g., MH for Maharashtra)"

    # Basic address validation
    if len(address.strip()) < 5:
        return False, "Address is too short"

    # Basic city validation
    if not city.strip() or len(city) < 2:
        return False, "Invalid city name"

    return True, "Valid address"


def validate_card_expiration(expiration):
    try:
        if not re.match(r'^(0[1-9]|1[0-2])\/([0-9]{2})$', expiration):
            return False, "Invalid expiration format (use MM/YY)"

        month, year = map(int, expiration.split('/'))
        exp_date = datetime(2000 + year, month, 1)
        if exp_date <= datetime.now():
            return False, "Card has expired"

        return True, "Valid expiration date"
    except:
        return False, "Invalid expiration date"

@app.route('/')
def landing():
    if 'user_id' in session:
        return redirect(url_for('home'))
    return render_template('landing.html')

@app.route('/home')
def home():
    db = get_db()
    products = db.execute('''
        SELECT p.*,
               COALESCE(AVG(r.rating), 0) as avg_rating,
               COUNT(r.id) as review_count
        FROM products p
        LEFT JOIN reviews r ON p.id = r.product_id
        GROUP BY p.id
        ORDER BY p.release_date DESC
    ''').fetchall()
    return render_template('home.html', products=products)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match')
            return redirect(url_for('register'))

        if len(password) < 6:
            flash('Password must be at least 6 characters long')
            return redirect(url_for('register'))

        db = get_db()
        try:
            db.execute('INSERT INTO users (first_name, last_name, email, password) VALUES (?, ?, ?, ?)',
                      [first_name, last_name, email, generate_password_hash(password)])
            db.commit()

            # Get the newly created user
            user = db.execute('SELECT * FROM users WHERE email = ?', [email]).fetchone()

            # Automatically log them in
            session['user_id'] = user['id']
            session['user_email'] = user['email']
            session['user_name'] = f"{user['first_name']} {user['last_name']}"
            session['first_name'] = user['first_name']
            session['last_name'] = user['last_name']
            session.permanent = True  # Make session permanent

            flash(f'Welcome, {first_name}! Your account has been created.')
            return redirect(url_for('home'))
        except sqlite3.IntegrityError:
            flash('Email already exists')
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        db = get_db()
        user = db.execute('SELECT * FROM users WHERE email = ?', [email]).fetchone()

        if user and check_password_hash(user['password'], password):
            # Store user info in session
            session['user_id'] = user['id']
            session['user_email'] = user['email']
            session['user_name'] = f"{user['first_name']} {user['last_name']}"
            session['first_name'] = user['first_name']
            session['last_name'] = user['last_name']
            session.permanent = True  # Make session permanent
            flash(f'Welcome back, {user["first_name"]}!')
            return redirect(url_for('home'))

        flash('Invalid email or password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    # Clear all session data
    session.clear()
    flash('You have been logged out.')
    return redirect(url_for('login'))


@app.route('/category/<category>')
def category(category):
    return f'Category: {category}'

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    db = get_db()
    product = db.execute(
        'SELECT p.*, '
        'COALESCE((SELECT COUNT(*) FROM reviews r WHERE r.product_id = p.id), 0) as review_count, '
        'COALESCE((SELECT AVG(CAST(rating AS FLOAT)) FROM reviews r WHERE r.product_id = p.id), 0.0) as avg_rating '
        'FROM products p WHERE p.id = ?',
        (product_id,)
    ).fetchone()


    # Get all reviews for the product
    reviews = db.execute(
        'SELECT r.*, r.body as body, r.author as author, '
        'r.release_date, r.rating '
        'FROM reviews r '
        'WHERE r.product_id = ? '
        'ORDER BY r.release_date DESC, r.release_time DESC',
        (product_id,)
    ).fetchall()

    return render_template('product_detail.html', product=dict(product), reviews=reviews)

@app.route('/product/<int:product_id>/add_review', methods=['POST'])
def add_review(product_id):
    if not session.get('user_id'):
        return redirect(url_for('login'))

    rating = request.form.get('rating')
    body = request.form.get('comment')  # Getting 'comment' from form but using as 'body' in DB

    if not rating or not body:
        flash('Both rating and review text are required')
        return redirect(url_for('product_detail', product_id=product_id))

    try:
        db = get_db()
        # Get user info
        user = db.execute(
            'SELECT first_name, last_name FROM users WHERE id = ?',
            (session['user_id'],)
        ).fetchone()

        author = f"{user['first_name']} {user['last_name']}"

        # Insert review
        db.execute(
            'INSERT INTO reviews (product_id, rating, author, body, release_date, release_time) VALUES (?, ?, ?, ?, date("now"), time("now"))',
            (product_id, rating, author, body)
        )
        db.commit()
        flash('Review added successfully!')
    except sqlite3.Error as e:
        flash(f'Error adding review: {str(e)}')
        print(f"Database error: {e}")

    return redirect(url_for('product_detail', product_id=product_id))

@app.route('/search')
def search():
    query = request.args.get('q', '')
    db = get_db()
    products = db.execute('''
        SELECT p.*,
               COALESCE(AVG(r.rating), 0) as avg_rating,
               COUNT(r.id) as review_count
        FROM products p
        LEFT JOIN reviews r ON p.id = r.product_id
        WHERE p.name LIKE ? OR p.manufacturer LIKE ? OR p.description LIKE ?
        GROUP BY p.id
        ORDER BY p.release_date DESC
    ''', [f'%{query}%', f'%{query}%', f'%{query}%']).fetchall()
    return render_template('home.html', products=products, search_query=query)

@app.route('/add_to_cart/<int:product_id>', methods=['GET', 'POST'])
def add_to_cart(product_id):
    if 'user_id' not in session:
        flash('Please login first')
        return redirect(url_for('login'))

    db = get_db()
    try:
        # Add item to cart
        db.execute('INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, 1)',
                  [session['user_id'], product_id])
        db.commit()
        flash('Added to cart!')
    except Exception as e:
        print(f"Error: {str(e)}")
        flash('Error adding to cart')
        return redirect(url_for('product_detail', product_id=product_id))

    # If buy_now is set, clear any other items from cart and go to checkout
    if request.method == 'POST' and request.form.get('buy_now'):
        try:
            # Remove all other items from cart
            db.execute('DELETE FROM cart WHERE user_id = ? AND product_id != ?',
                      [session['user_id'], product_id])
            db.commit()
            return redirect(url_for('checkout'))
        except Exception as e:
            print(f"Error clearing cart: {str(e)}")
            flash('Error processing buy now')

    return redirect(url_for('product_detail', product_id=product_id))

@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    cart_items = db.execute('''
        SELECT c.id as cart_item_id, c.quantity,
               p.id as product_id, p.name, p.price, p.manufacturer
        FROM cart c
        JOIN products p ON c.product_id = p.id
        WHERE c.user_id = ?
    ''', [session['user_id']]).fetchall()

    total = sum(item['price'] * item['quantity'] for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/remove_from_cart/<int:item_id>')
def remove_from_cart(item_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    try:
        # First verify that this cart item belongs to the current user
        cart_item = db.execute('''
            SELECT * FROM cart
            WHERE id = ? AND user_id = ?
        ''', [item_id, session['user_id']]).fetchone()

        if cart_item:
            db.execute('DELETE FROM cart WHERE id = ?', [item_id])
            db.commit()
            flash('Item removed from cart')
        else:
            flash('Item not found in cart')
    except:
        flash('Failed to remove item from cart')

    return redirect(url_for('cart'))

@app.route('/checkout')
def checkout():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    cart_items = db.execute('''
        SELECT c.*, p.name, p.price, p.manufacturer
        FROM cart c
        JOIN products p ON c.product_id = p.id
        WHERE c.user_id = ?
    ''', [session['user_id']]).fetchall()

    total = sum(item['price'] * item['quantity'] for item in cart_items)
    return render_template('checkout.html', cart_items=cart_items, total=total)

@app.route('/place_order', methods=['POST'])
def place_order():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    cart_items = db.execute('''
        SELECT p.id, p.name, p.price, c.quantity
        FROM cart c
        JOIN products p ON c.product_id = p.id
        WHERE c.user_id = ?
    ''', [session['user_id']]).fetchall()

    if not cart_items:
        flash('Your cart is empty')
        return redirect(url_for('cart'))

    # Validate form data
    address = request.form.get('address', '').strip()
    city = request.form.get('city', '').strip()
    state = request.form.get('state', '').strip()
    zip_code = request.form.get('zip', '').strip()
    expiration = request.form.get('cc-expiration', '').strip()

    # Validate address
    is_valid_address, address_msg = validate_address(address, city, state, zip_code)
    if not is_valid_address:
        flash(address_msg)
        return redirect(url_for('checkout'))

    # Validate card expiration
    is_valid_exp, exp_msg = validate_card_expiration(expiration)
    if not is_valid_exp:
        flash(exp_msg)
        return redirect(url_for('checkout'))

    # Calculate total amount
    total_amount = sum(item['price'] * item['quantity'] for item in cart_items)

    # Format shipping address
    shipping_address = f"{address}, {city}, {state}, {zip_code}"

    try:
        # Create order
        db.execute('''
            INSERT INTO orders (user_id, order_date, total_amount, shipping_address, status)
            VALUES (?, datetime('now'), ?, ?, 'On its way')
        ''', [session['user_id'], total_amount, shipping_address])

        # Get the order id
        order_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]

        # Add order items
        for item in cart_items:
            db.execute('''
                INSERT INTO order_items (order_id, product_id, quantity, price_at_time)
                VALUES (?, ?, ?, ?)
            ''', [order_id, item['id'], item['quantity'], item['price']])

        # Clear cart
        db.execute('DELETE FROM cart WHERE user_id = ?', [session['user_id']])
        db.commit()

        flash('Order placed successfully!')
        return redirect(url_for('orders'))

    except sqlite3.Error as e:
        db.rollback()
        flash('Failed to place order. Please try again.')
        return redirect(url_for('cart'))

@app.route('/orders')
def orders():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    # Get all orders with their items
    orders = db.execute('''
        SELECT o.*, COUNT(oi.id) as item_count
        FROM orders o
        LEFT JOIN order_items oi ON o.id = oi.order_id
        WHERE o.user_id = ?
        GROUP BY o.id
        ORDER BY o.order_date DESC
    ''', [session['user_id']]).fetchall()

    return render_template('orders.html', orders=orders)

@app.route('/order/<int:order_id>')
def order_detail(order_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    # Get order details
    order = db.execute('''
        SELECT * FROM orders WHERE id = ? AND user_id = ?
    ''', [order_id, session['user_id']]).fetchone()

    if not order:
        flash('Order not found')
        return redirect(url_for('orders'))

    # Get order items with product details
    items = db.execute('''
        SELECT oi.*, p.name, p.manufacturer
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = ?
    ''', [order_id]).fetchall()

    return render_template('order_detail.html', order=order, items=items)


@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        
        # Here you would typically handle the contact form submission
        # For now, we'll just show a success message
        flash('Thank you for your message! We will get back to you soon.', 'success')
        return redirect(url_for('contact'))
        
    return render_template('contact.html')

if __name__ == '__main__':
    init_db()  # Initialize database tables
    sync_products()  # Sync products if needed
    app.run(debug=True)
