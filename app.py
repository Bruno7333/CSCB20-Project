from flask import Flask, request, redirect, render_template
import sqlite3

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('nba.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    email = request.form['email']
    password = request.form['password']

    conn = sqlite3.connect('nba.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                   (username, email, password))
    conn.commit()
    conn.close()

    return "Registration successful! <a href='/'>Go back</a>"

if __name__ == '__main__':
    init_db()
    app.run(debug=True)