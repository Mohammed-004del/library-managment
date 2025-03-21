from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import sqlite3
import os

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('library.db')
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        contact TEXT,
                        membership_status TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS books (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT,
                        author TEXT,
                        available INTEGER DEFAULT 1)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        book_id INTEGER,
                        checkout_date TEXT,
                        due_date TEXT,
                        returned INTEGER DEFAULT 0,
                        fine REAL DEFAULT 0,
                        damaged INTEGER DEFAULT 0,
                        reservation INTEGER DEFAULT 0,
                        FOREIGN KEY(user_id) REFERENCES users(id),
                        FOREIGN KEY(book_id) REFERENCES books(id))''')

    conn.commit()
    conn.close()

# Add new user
@app.route('/add_user', methods=['POST'])
def add_user():
    data = request.json
    name, contact, membership_status = data['name'], data['contact'], data['membership_status']
    conn = sqlite3.connect('library.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (name, contact, membership_status) VALUES (?, ?, ?)",
                   (name, contact, membership_status))
    conn.commit()
    conn.close()
    return jsonify({'message': 'User added successfully'})

# List available books
@app.route('/books', methods=['GET'])
def list_books():
    conn = sqlite3.connect('library.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM books WHERE available=1")
    books = cursor.fetchall()
    conn.close()
    return jsonify(books)

# Reserve book if not available
@app.route('/reserve', methods=['POST'])
def reserve_book():
    data = request.json
    user_id, book_id = data['user_id'], data['book_id']
    conn = sqlite3.connect('library.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO transactions (user_id, book_id, reservation) VALUES (?, ?, 1)", (user_id, book_id))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Book reserved successfully'})

# Checkout book
@app.route('/checkout', methods=['POST'])
def checkout_book():
    data = request.json
    user_id, book_id = data['user_id'], data['book_id']
    checkout_date = datetime.now().strftime('%Y-%m-%d')
    due_date = (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d')

    conn = sqlite3.connect('library.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE books SET available=0 WHERE id=?", (book_id,))
    cursor.execute("INSERT INTO transactions (user_id, book_id, checkout_date, due_date) VALUES (?, ?, ?, ?)",
                   (user_id, book_id, checkout_date, due_date))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Book checked out successfully', 'due_date': due_date})

# Return book
@app.route('/return', methods=['POST'])
def return_book():
    data = request.json
    transaction_id = data['transaction_id']
    damaged = data.get('damaged', 0)
    return_date = datetime.now()

    conn = sqlite3.connect('library.db')
    cursor = conn.cursor()
    cursor.execute("SELECT book_id, due_date FROM transactions WHERE id=? AND returned=0", (transaction_id,))
    transaction = cursor.fetchone()

    if not transaction:
        conn.close()
        return jsonify({'error': 'Invalid transaction or book already returned'})

    book_id, due_date = transaction
    due_date = datetime.strptime(due_date, '%Y-%m-%d')
    fine = max((return_date - due_date).days, 0) * 5
    if damaged:
        fine += 20  # Add damage fine

    cursor.execute("UPDATE transactions SET returned=1, fine=?, damaged=? WHERE id=?", (fine, damaged, transaction_id))
    cursor.execute("UPDATE books SET available=1 WHERE id=?", (book_id,))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Book returned successfully', 'fine': fine})

# Extend due date
@app.route('/extend_due_date', methods=['POST'])
def extend_due_date():
    data = request.json
    transaction_id = data['transaction_id']
    conn = sqlite3.connect('library.db')
    cursor = conn.cursor()
    cursor.execute("SELECT due_date FROM transactions WHERE id=? AND returned=0", (transaction_id,))
    record = cursor.fetchone()

    if not record:
        conn.close()
        return jsonify({'error': 'Invalid transaction or already returned'})

    due_date = datetime.strptime(record[0], '%Y-%m-%d')
    if datetime.now() > due_date:
        conn.close()
        return jsonify({'error': 'Cannot extend due date, book is already overdue'})

    new_due_date = (due_date + timedelta(days=7)).strftime('%Y-%m-%d')
    cursor.execute("UPDATE transactions SET due_date=? WHERE id=?", (new_due_date, transaction_id))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Due date extended', 'new_due_date': new_due_date})

# Overdue report
@app.route('/overdue_report', methods=['GET'])
def overdue_report():
    today = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect('library.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transactions WHERE due_date<? AND returned=0", (today,))
    overdue_books = cursor.fetchall()
    conn.close()
    return jsonify(overdue_books)

# Inventory report
@app.route('/inventory_report', methods=['GET'])
def inventory_report():
    conn = sqlite3.connect('library.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, author, available FROM books")
    books = cursor.fetchall()
    conn.close()
    return jsonify(books)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, use_reloader=False)
