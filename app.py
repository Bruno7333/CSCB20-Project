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
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # select leagues
    cursor.execute("SELECT LID as id, leagueName as name FROM PlayerLeague")
    leagues = cursor.fetchall()
    conn.close()

    return render_template('dashboard.html', leagues=leagues)

@app.route('/create_league', methods=['POST'])
def create_league():
    league_name = request.form['leagueName']
    draft_type = request.form['draftType']
    owner_id = 1

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO PlayerLeague (leagueName, draftType, ownerAccount, status) VALUES (?, ?, ?, 'initial')",
        (league_name, draft_type, owner_id)
    )
    conn.commit()
    conn.close()

    return redirect(url_for('dashboard'))

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
        return redirect(url_for('dashboard'))
    else:
        return "Login failed. Check your credentials."

if __name__ == '__main__':
    init_db()
    app.run(debug=True)