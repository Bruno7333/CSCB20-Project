from flask import Flask, send_file, render_template

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html", name="Bruno")

@app.route("/login")
def home():
    return render_template("login.html")

@app.route("/register")
def home():
    return render_template("register.html")

@app.route("/dashboard")
def home():
    return render_template("index.html", name="Bruno")

app.run()