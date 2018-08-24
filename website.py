#!//usr/bin/python3.6
import hashlib
import random
import requests
import json
import threading
from flask import *
from flask_cors import CORS
from db import Connection

c = Connection()
c.connect()
members = c.fetch("members")
if not members:
    c.create("members", {"username": None, "password": None, "salt": None, "admin": 0})

pepper = "efoijxewioufhaewprofwefz;dorfgjlakesdf;;yesIhitmyheadonmykeyboard"

app = Flask(__name__, template_folder='templates', static_folder='templates/static')
CORS(app)

def set_admin(username):
    c.connect()
    members = c.fetch("members")
    members.add({"admin":1}, {"username":username})    
    return True

def signup(username, password):
    c.connect()
    members = c.fetch("members")
    user = members.fetch({"username": username})
    if user:
        return "User already exists"

    salt = ''.join(random.choice('0123456789') for _ in range(6))
    added_spices = pepper + password + salt
    hashed_spices = hashlib.md5(added_spices.encode('utf-8')).hexdigest()
    members.add({"username": username, "password": hashed_spices, "salt": salt, "admin": 0})

    session['admin'] = 0
    return True

def authenticate(username, password):
    c.connect()
    members = c.fetch("members")
    user = members.fetch({"username": username})
    print(user)
    if not user:
        return "User doesn't exist"

    user_password = user[0]["password"]
    user_salt = str(user[0]["salt"])

    added_spices = pepper + password + user_salt
    hashed_spices = hashlib.md5(added_spices.encode('utf-8')).hexdigest()

    if user_password != hashed_spices:
        return "Passwords don't match"

    session['admin'] = user[0]["admin"]
    return True

@app.route('/')
def main():
    levels = json.load(open('levels.json', 'r'))
    return render_template('index.html', levels=levels["queue"], records=levels["records"])

@app.route('/played')
def played():
    levels = json.load(open('levels.json', 'r'))
    return render_template('played.html', levels=levels["queue"], records=levels["records"])

@app.route('/admin')
def admin_panel():
    c.connect()
    members = c.fetch("members")
    if session.get('logged_in') == True:
        return render_template('admin.html', users=members.fetch())
    else:
        return redirect(url_for('login'), code=302)

@app.route('/make_admin', methods=['POST'])
def make_admin():
    if session.get('admin') == True:
        return abort(401)
        
    set_admin(request.form['username'])
    return redirect(url_for('admin_panel'), code=302)

@app.route('/register')
def register():
    if session.get('logged_in') == True:
        return redirect(url_for('main'), code=302)
    else:
        return render_template('register.html')

@app.route('/register_process', methods=['POST'])
def register_process():
    response = signup(request.form['username'], request.form['password'])
    if response == True:
        session['logged_in'] = True
    else:
        flash(response)
    
    return redirect(url_for('register'), code=302)

@app.route('/login')
def login():
    if session.get('logged_in') == True:
        return redirect(url_for('main'), code=302)
    else:
        return render_template('login.html')

@app.route('/login_process', methods=['POST'])
def login_process():
    response = authenticate(request.form['username'], request.form['password'])
    if response == True:
        session['logged_in'] = True
    else:
        flash(response)

    return redirect(url_for('login'), code=302)

@app.route("/logout")
def logout():
    session['logged_in'] = False
    return redirect(url_for('login'), code=302)

@app.route("/removeq/<levelq>")
def removeq(levelq):
    if session.get('logged_in') == True:
        levels = json.load(open("levels.json"))
        del levels['queue'][int(levelq)]
        with open('levels.json', 'w') as f:
            json.dump(levels, f, indent=2)
    return redirect(url_for('main'), code=302)

print("Server starting up...")
app.secret_key = 'super_secret_key'
app.run(host="0.0.0.0", debug=False, port=8880)
