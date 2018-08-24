#!//usr/bin/python3.6
import requests, json, threading
from flask import *
from flask_cors import CORS

app = Flask(__name__, template_folder='templates', static_folder='templates/static')
CORS(app)

@app.route('/')
def main():
    levels = json.load(open('levels.json', 'r'))
    return render_template('index.html', levels=levels["queue"], records=levels["records"])

@app.route('/played')
def played():
	levels = json.load(open('levels.json', 'r'))
	return render_template('played.html', levels=levels["queue"], records=levels["records"])

@app.route('/login')
def login():
    if not session.get('logged_in'):
        return render_template('login.html')
    else:
        return redirect(url_for('main'), code=302)
 
@app.route('/login_process', methods=['POST'])
def login_process():
    # let's hook up a database to this later :D
    if request.form['username'] == 'randall' and request.form['password'] == 'yeah':
        session['logged_in'] = True
    else:
        flash('wrong password!')
    return redirect(url_for('login'), code=302)

@app.route("/logout")
def logout():
    session['logged_in'] = False
    return login()

@app.route("/removeq/<levelq>")
def removeq(levelq):
	if session['logged_in']:
		levels = json.load(open("levels.json"))
		del levels['queue'][int(levelq)]
		with open('levels.json', 'w') as f:
			json.dump(levels, f, indent=2)
	return redirect(url_for('main'), code=302)

print("Server starting up...")
app.secret_key = 'super_secret_key'
app.run(host="0.0.0.0", debug=False, port=8880)
