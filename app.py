from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
import pyodbc
import bcrypt
from datetime import datetime
import os
import traceback
import json
from werkzeug.utils import secure_filename

app = Flask(__name__, 
            static_folder='static', 
            static_url_path='/static')
app.secret_key = 'your-secret-key-here'  # Change this to a secure secret key

# SQL Server connection configuration
conn_str = (
    "Driver={SQL Server};"
    "Server=DESKTOP-GKCGUOK;"
    "Database=MyWebsiteDB;"
    "Trusted_Connection=yes;"
)

def get_db_connection():
    return pyodbc.connect(conn_str)

# User model functions
def create_user(username, email, phone, password_hash):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check if username or email already exists
        cursor.execute("SELECT * FROM Users WHERE Username = ? OR Email = ?", (username, email))
        if cursor.fetchone():
            return False
        
        # Insert new user
        cursor.execute("""
            INSERT INTO Users (Username, Email, Phone, PasswordHash)
            VALUES (?, ?, ?, ?)
        """, (username, email, phone, password_hash))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error creating user: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def get_user_by_username(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT UserID, Username, Email, Phone, PasswordHash FROM Users WHERE Username = ?", (username,))
        user = cursor.fetchone()
        
        if user:
            return {
                'UserID': user[0],
                'Username': user[1],
                'Email': user[2],
                'Phone': user[3],
                'PasswordHash': user[4]
            }
        return None
    except Exception as e:
        print(f"Error in get_user_by_username: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

# Create cart table if it doesn't exist
def create_cart_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Cart' AND xtype='U')
            CREATE TABLE Cart (
                CartID INT IDENTITY(1,1) PRIMARY KEY,
                UserID INT,
                ProductID INT,
                Quantity INT DEFAULT 1,
                FOREIGN KEY (UserID) REFERENCES Users(UserID),
                FOREIGN KEY (ProductID) REFERENCES Products(ProductID)
            )
        """)
        conn.commit()
    except Exception as e:
        print(f"Error creating cart table: {e}")
    finally:
        cursor.close()
        conn.close()

# Create cart table when app starts
create_cart_table()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT Username, Email FROM Users WHERE UserID = ?", (session['user_id'],))
        user = cursor.fetchone()
        
        return render_template('dashboard.html', 
                               username=user[0], 
                               email=user[1], 
                               registration_date=datetime.now().strftime('%d.%m.%Y'))
    except Exception as e:
        print(f"Dashboard error: {e}")
        return redirect(url_for('index'))
    finally:
        cursor.close()
        conn.close()

@app.route('/register', methods=['POST'])
def register():
    try:
        # Ensure the request contains JSON data
        if not request.is_json:
            return jsonify({'error': 'Неверный формат запроса'}), 400

        data = request.get_json()
        
        # Validate required fields
        username = data.get('username')
        email = data.get('email')
        phone = data.get('phone', '')
        password = data.get('password')

        # Check for missing required fields
        if not username or not email or not password:
            return jsonify({'error': 'Заполните все обязательные поля'}), 400

        # Hash password
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

        # Create new user
        if create_user(username, email, phone, password_hash):
            return jsonify({'message': 'Регистрация успешна'}), 201
        else:
            return jsonify({'error': 'Пользователь с таким именем или email уже существует'}), 400

    except Exception as e:
        # Log the full error for debugging
        print(f"Registration error: {traceback.format_exc()}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

@app.route('/login', methods=['POST'])
def login():
    try:
        # Ensure the request contains JSON data
        if not request.is_json:
            return jsonify({'error': 'Неверный формат запроса'}), 400

        data = request.get_json()
        
        # Validate required fields
        username = data.get('username')
        password = data.get('password')

        # Check for missing required fields
        if not username or not password:
            return jsonify({'error': 'Заполните все поля'}), 400

        # Admin login
        if username == 'A' and password == 'A':
            session['admin'] = True
            return redirect(url_for('admin_panel'))

        user = get_user_by_username(username)
        if user and bcrypt.checkpw(password.encode('utf-8'), user['PasswordHash'].encode('utf-8')):
            session['user_id'] = user['UserID']
            return redirect(url_for('products'))
        else:
            return jsonify({'error': 'Неверное имя пользователя или пароль'}), 401

    except Exception as e:
        # Log the full error for debugging
        print(f"Login error: {traceback.format_exc()}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('admin', None)
    return redirect(url_for('index'))

@app.route('/products')
def products():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Fetch user details for profile display
        cursor.execute("SELECT Username FROM Users WHERE UserID = ?", (session['user_id'],))
        user = cursor.fetchone()
        
        # Fetch all products
        cursor.execute("SELECT ProductID, Name, Description, Price, Quantity, Category, ImageURL FROM Products")
        products = cursor.fetchall()
        
        # Convert products to list of dictionaries for easier template rendering
        product_list = [
            {
                'id': product[0],
                'name': product[1],
                'description': product[2],
                'price': product[3],
                'quantity': product[4],
                'category': product[5],
                'image_url': product[6]
            }
            for product in products
        ]
        
        return render_template('products.html', 
                               username=user[0], 
                               products=product_list)
    except Exception as e:
        print(f"Products page error: {e}")
        return redirect(url_for('index'))
    finally:
        cursor.close()
        conn.close()

@app.route('/admin')
def admin_panel():
    if not session.get('admin'):
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Fetch all products
        cursor.execute("SELECT ProductID, Name, Description, Price, Quantity, Category, ImageURL FROM Products")
        products = cursor.fetchall()
        
        # Convert products to list of dictionaries for easier template rendering
        product_list = [
            {
                'id': product[0],
                'name': product[1],
                'description': product[2],
                'price': product[3],
                'quantity': product[4],
                'category': product[5],
                'image_url': product[6]
            }
            for product in products
        ]
        
        return render_template('admin.html', products=product_list)
    except Exception as e:
        print(f"Admin panel error: {e}")
        return redirect(url_for('index'))
    finally:
        cursor.close()
        conn.close()

@app.route('/admin/add_product', methods=['POST'])
def add_product():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        data = request.form
        image = request.files.get('image')
        
        # Handle image upload
        image_url = None
        if image:
            filename = secure_filename(image.filename)
            filepath = os.path.join(app.static_folder, 'product_images', filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            image.save(filepath)
            image_url = f'/static/product_images/{filename}'

        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO Products (Name, Description, Price, Quantity, Category, ImageURL)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data.get('name'),
            data.get('description'),
            float(data.get('price', 0)),
            int(data.get('quantity', 0)),
            data.get('category'),
            image_url
        ))
        
        conn.commit()
        return jsonify({'message': 'Товар успешно добавлен'}), 200
    
    except Exception as e:
        print(f"Error adding product: {e}")
        return jsonify({'error': 'Ошибка при добавлении товара'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/admin/edit_product/<int:product_id>', methods=['POST'])
def edit_product(product_id):
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        data = request.form
        image = request.files.get('image')
        
        # Handle image upload
        image_url = None
        if image:
            filename = secure_filename(image.filename)
            filepath = os.path.join(app.static_folder, 'product_images', filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            image.save(filepath)
            image_url = f'/static/product_images/{filename}'

        conn = get_db_connection()
        cursor = conn.cursor()
        
        update_query = """
            UPDATE Products 
            SET Name = ?, Description = ?, Price = ?, Quantity = ?, Category = ?
            """
        params = [
            data.get('name'),
            data.get('description'),
            float(data.get('price', 0)),
            int(data.get('quantity', 0)),
            data.get('category')
        ]

        if image_url:
            update_query += ", ImageURL = ?"
            params.append(image_url)

        update_query += " WHERE ProductID = ?"
        params.append(product_id)

        cursor.execute(update_query, params)
        conn.commit()

        return jsonify({'message': 'Товар успешно обновлен'}), 200
    
    except Exception as e:
        print(f"Error editing product: {e}")
        return jsonify({'error': 'Ошибка при редактировании товара'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/admin/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM Products WHERE ProductID = ?", (product_id,))
        conn.commit()

        return jsonify({'message': 'Товар успешно удален'}), 200
    
    except Exception as e:
        print(f"Error deleting product: {e}")
        return jsonify({'error': 'Ошибка при удалении товара'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/cart/add', methods=['POST'])
def add_to_cart():
    if 'user_id' not in session:
        return jsonify({'error': 'Необходимо войти в систему'}), 401

    try:
        data = request.get_json()
        product_id = data.get('product_id')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if product exists in cart
        cursor.execute("""
            SELECT CartID, Quantity FROM Cart 
            WHERE UserID = ? AND ProductID = ?
        """, (session['user_id'], product_id))
        
        cart_item = cursor.fetchone()
        
        if cart_item:
            # Update quantity if product already in cart
            cursor.execute("""
                UPDATE Cart 
                SET Quantity = Quantity + 1 
                WHERE CartID = ?
            """, (cart_item[0],))
        else:
            # Add new item to cart
            cursor.execute("""
                INSERT INTO Cart (UserID, ProductID, Quantity)
                VALUES (?, ?, 1)
            """, (session['user_id'], product_id))
        
        conn.commit()
        return jsonify({'message': 'Товар добавлен в корзину'}), 200
    
    except Exception as e:
        print(f"Error adding to cart: {e}")
        return jsonify({'error': 'Ошибка при добавлении в корзину'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/cart/count')
def get_cart_count():
    if 'user_id' not in session:
        return jsonify({'count': 0})

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT SUM(Quantity) FROM Cart 
            WHERE UserID = ?
        """, (session['user_id'],))
        
        count = cursor.fetchone()[0] or 0
        return jsonify({'count': count})
    
    except Exception as e:
        print(f"Error getting cart count: {e}")
        return jsonify({'count': 0})
    finally:
        cursor.close()
        conn.close()

@app.route('/cart')
def view_cart():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get cart items with product details
        cursor.execute("""
            SELECT p.ProductID, p.Name, p.Description, p.Price, p.ImageURL, c.Quantity
            FROM Cart c
            JOIN Products p ON c.ProductID = p.ProductID
            WHERE c.UserID = ?
        """, (session['user_id'],))
        
        cart_items = []
        total_price = 0
        
        for row in cursor.fetchall():
            product = {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'price': row[3],
                'image_url': row[4]
            }
            quantity = row[5]
            cart_items.append({
                'product': product,
                'quantity': quantity
            })
            total_price += product['price'] * quantity

        # Get username for display
        cursor.execute("SELECT Username FROM Users WHERE UserID = ?", (session['user_id'],))
        username = cursor.fetchone()[0]
        
        return render_template('cart.html', 
                             cart_items=cart_items,
                             total_price=total_price,
                             username=username)
    
    except Exception as e:
        print(f"Error viewing cart: {e}")
        return redirect(url_for('products'))
    finally:
        cursor.close()
        conn.close()

@app.route('/cart/update', methods=['POST'])
def update_cart():
    if 'user_id' not in session:
        return jsonify({'error': 'Необходимо войти в систему'}), 401

    try:
        data = request.get_json()
        product_id = data.get('product_id')
        change = data.get('change', 0)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get current quantity
        cursor.execute("""
            SELECT Quantity FROM Cart 
            WHERE UserID = ? AND ProductID = ?
        """, (session['user_id'], product_id))
        
        current_qty = cursor.fetchone()
        
        if current_qty:
            new_qty = current_qty[0] + change
            if new_qty > 0:
                cursor.execute("""
                    UPDATE Cart 
                    SET Quantity = ?
                    WHERE UserID = ? AND ProductID = ?
                """, (new_qty, session['user_id'], product_id))
            else:
                cursor.execute("""
                    DELETE FROM Cart 
                    WHERE UserID = ? AND ProductID = ?
                """, (session['user_id'], product_id))
            
            conn.commit()
            return jsonify({'message': 'Корзина обновлена'}), 200
        
        return jsonify({'error': 'Товар не найден в корзине'}), 404
    
    except Exception as e:
        print(f"Error updating cart: {e}")
        return jsonify({'error': 'Ошибка при обновлении корзины'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/cart/remove', methods=['POST'])
def remove_from_cart():
    if 'user_id' not in session:
        return jsonify({'error': 'Необходимо войти в систему'}), 401

    try:
        data = request.get_json()
        product_id = data.get('product_id')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM Cart 
            WHERE UserID = ? AND ProductID = ?
        """, (session['user_id'], product_id))
        
        conn.commit()
        return jsonify({'message': 'Товар удален из корзины'}), 200
    
    except Exception as e:
        print(f"Error removing from cart: {e}")
        return jsonify({'error': 'Ошибка при удалении из корзины'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/cart/checkout', methods=['POST'])
def checkout():
    if 'user_id' not in session:
        return jsonify({'error': 'Необходимо войти в систему'}), 401

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all items from cart
        cursor.execute("""
            SELECT ProductID, Quantity FROM Cart 
            WHERE UserID = ?
        """, (session['user_id'],))
        
        cart_items = cursor.fetchall()
        
        # Insert each cart item into Orders table
        for product_id, quantity in cart_items:
            cursor.execute("""
                INSERT INTO Orders (UserID, ProductID, Quantity, OrderDate)
                VALUES (?, ?, ?, ?)
            """, (session['user_id'], product_id, quantity, datetime.now()))
        
        # Clear user's cart
        cursor.execute("DELETE FROM Cart WHERE UserID = ?", (session['user_id'],))
        conn.commit()
        
        return jsonify({'message': 'Заказ успешно оформлен'}), 200
    
    except Exception as e:
        print(f"Error during checkout: {e}")
        return jsonify({'error': 'Ошибка при оформлении заказа'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/admin/orders')
def admin_orders():
    if not session.get('admin'):
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Fetch all orders with product and user details
        cursor.execute("""
            SELECT 
                o.OrderID,
                u.Username,
                p.Name as ProductName,
                o.Quantity,
                p.Price,
                o.OrderDate,
                p.Price * o.Quantity as TotalPrice
            FROM Orders o
            JOIN Users u ON o.UserID = u.UserID
            JOIN Products p ON o.ProductID = p.ProductID
            ORDER BY o.OrderDate DESC
        """)
        
        orders = []
        for row in cursor.fetchall():
            orders.append({
                'id': row[0],
                'username': row[1],
                'product_name': row[2],
                'quantity': row[3],
                'price': row[4],
                'order_date': row[5].strftime('%d.%m.%Y %H:%M'),
                'total_price': row[6]
            })
        
        return render_template('admin_orders.html', orders=orders)
    except Exception as e:
        print(f"Admin orders error: {e}")
        return redirect(url_for('admin_panel'))
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
