import sqlite3
import os
from flask import Flask, request, session, render_template, redirect, url_for
SECRET_KEY = os.urandom(24)
print(SECRET_KEY.hex())

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config['SECRET_KEY'] = SECRET_KEY

DATABASE = 'transactions.db'


def create_table():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_card TEXT NOT NULL,
            sender_city TEXT NOT NULL,
            recipient_card TEXT NOT NULL,
            recipient_city TEXT NOT NULL,
            amount REAL NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

create_table()

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def check_suspicious_transaction(sender_card, amount, recipient_city):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        cursor.execute('''
            SELECT COUNT(*) FROM transactions WHERE sender_card = ?
        ''', (sender_card,))
        sender_exists = cursor.fetchone()[0] > 0

        if sender_exists:
            cursor.execute('''
                SELECT recipient_city FROM transactions WHERE sender_card = ?
            ''', (sender_card,))
            previous_cities = [row['recipient_city'] for row in cursor.fetchall()]

            if len(previous_cities) >= 2:  
                counts = {}
                for city in previous_cities:
                    counts[city] = counts.get(city, 0) + 1
                
                if any(count >= 2 for count in counts.values()): 
                    if previous_cities[-1] != recipient_city:
                        return True  
        if amount > 100000:
            return True

        return False 

    finally:
        conn.close()


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        sender_card = request.form['sender_card']
        sender_city = request.form['sender_city']
        recipient_card = request.form['recipient_card']
        recipient_city = request.form['recipient_city']
        amount = float(request.form['amount'])

        is_suspicious = check_suspicious_transaction(sender_card, amount, recipient_city)

        if is_suspicious:
            session['transaction_result'] = 'Перевод отклонен'
            return redirect(url_for('result'))

        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO transactions (sender_card, sender_city, recipient_card, recipient_city, amount)
            VALUES (?, ?, ?, ?, ?)
        ''', (sender_card, sender_city, recipient_card, recipient_city, amount))
        conn.commit()
        conn.close()

        session['transaction_result'] = 'Перевод отправлен'
        return redirect(url_for('result'))

    return render_template('index.html')


@app.route('/result')
def result():
    transaction_result = session.get('transaction_result')
    return render_template('result.html', context={'transaction_result': transaction_result})


if __name__ == '__main__':
    app.run(debug=True)
