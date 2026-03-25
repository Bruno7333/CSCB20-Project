from flask import Flask, send_file, render_template

app = Flask(__name__)
logged_in = True

leagues = [
    {'id': 1, 'name': 'League A'},
    {'id': 2, 'name': 'League B'},
    {'id': 3, 'name': 'League C'},
]

@app.route("/")
def home():
    if(logged_in):
        return render_template("dashboard.html", name="Bruno", leagues=leagues)
    return render_template("index.html")

@app.route("/league/<int:league_id>")
def league(league_id):
    league = None
    for l in leagues:
        if l['id'] == league_id:
            league = l
            break

    if league is None:
        return dashboard()

    return render_template("league.html", league=league)

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/register")
def register():
    return render_template("register.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html", name="Bruno", leagues=leagues)

app.run()