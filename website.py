#!//usr/bin/python3.6
import hashlib
import random
import requests
import json
import threading
from OpenSSL import SSL
from flask import *
from flask_cors import CORS
from db import Connection
from bs4 import BeautifulSoup
import urllib.request as urllib2
import re
from smmbget import get_level_info, check_valid_level, write_level_info, check_level_duplicate

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

@app.route('/chart')
def chart():
    youtube = 0
    twitch = 0
    levels = json.load(open('levels.json', 'r'))
    for platform in levels["records"]:
	    if "YouTube" == platform["platform"]:
		    youtube += 1
	    elif platform["platform"] == "Twitch":
		    twitch += 1
    labels = ["January","February","March","April","May","June","July","August"]
    values = [10,9,8,7,6,4,7,8]
    return render_template('test.html', levels=levels["queue"], records=levels["records"], youtube = youtube, twitch = twitch, values = values, labels = labels)

@app.route('/api/test', methods=['GET', 'POST'])
def test():
    level = request.args.get('level', type = str)
    platform = request.args.get('platform', type = str)
    userid = request.args.get('user', type = str)
    
    if check_level_duplicate(level) == True:
        return userid + ' Sorry this level has already been played'
    
    if check_valid_level(level) == False:
        return userid + ' Level ID is invalid or not found. Please check the ID and try again. Example: !add EEBD-0000-01CE-4CB6'
    else:
        temp_level = get_level_info(level)
        write_level_info(temp_level, userid, platform)
        return userid + ' Your level ' + temp_level["coursename"] + ' has been submited'
    
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
    if session.get('admin') != True:
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
#, ssl_context=('/home/rmcfarlane/MarioMakerHelper/fullchain.pem', '/home/rmcfarlane/MarioMakerHelper/privkey.pem'))
