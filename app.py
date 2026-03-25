from flask import Flask, request, redirect, url_for, render_template
import sqlite3

app = Flask(__name__)
DB_FILE = "./SQLite/nba.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("INSERT OR IGNORE INTO PlayerAccount (username, email, password) VALUES (?, ?, ?)",
                   ("admin", "admin@nba.com", "secret123"))

    conn.commit()
    conn.close()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')

@app.route('/register', methods=['GET'])
def register_page():
    return render_template('register.html')

@app.route('/dashboard', methods=['GET'])
def dashboard():
    return render_template('dashboard.html')

@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    email = request.form['email']
    password = request.form['password']

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('INSERT INTO PlayerAccount (username, email, password) VALUES (?, ?, ?)',
                   (username, email, password))

    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Use PlayerAccount table
    query = "SELECT * FROM PlayerAccount WHERE username = ? AND password = ?"
    cursor.execute(query, (username, password))
    user = cursor.fetchone()
    conn.close()

    if user:
        return render_template(dashboard.html)
    else:
        return "Login failed. Check your credentials."

if __name__ == '__main__':
    init_db()
    app.run(debug=True)