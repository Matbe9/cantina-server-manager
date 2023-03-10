from flask import Flask, render_template, request, make_response, redirect, url_for
from Utils import database
from hashlib import sha256
from argon2 import argon2_hash
from json import load
from datetime import datetime
from os import getcwd, path


def salt_password(passwordtohash, user_name, new_account=False):
    try:
        if not new_account:
            data = database_administration.select('''SELECT salt FROM user WHERE user_name=%s''', (user_name,), 1)
            passw = sha256(argon2_hash(passwordtohash, data[0])).hexdigest().encode()
            return passw
        else:
            passw = sha256(argon2_hash(passwordtohash, user_name)).hexdigest().encode()
            return passw

    except AttributeError as e:
        make_log('Error', request.remote_addr, request.cookies.get('userID'), 2, str(e))
        return None


def make_log(action_name, user_ip, user_token, log_level, argument=None, content=None):
    if content:
        database_administration.insert('''INSERT INTO log(name, user_ip, user_token, argument, log_level) VALUES (%s,
        %s, %s,%s,%s)''', (str(action_name), str(user_ip), str(content), argument, log_level))
    else:
        database_administration.insert('''INSERT INTO log(name, user_ip, user_token, argument, log_level) VALUES (%s,
        %s, %s,%s,%s)''', (str(action_name), str(user_ip), str(user_token), argument, log_level))


app = Flask(__name__)
with open(path.abspath(getcwd()) + "/config.json") as conf_file:
    config_data = load(conf_file)

database_administration = database.DataBase(user=config_data['database'][0]['database_username'],
                                            password=config_data['database'][0]['database_password'],
                                            host="localhost", port=3306,
                                            database=config_data['database'][0]['database_administration_name'])
database_server_manager = database.DataBase(user=config_data['database'][0]['database_username'],
                                            password=config_data['database'][0]['database_password'],
                                            host="localhost", port=3306,
                                            database=config_data['database'][0]['database_server_manager_name'])
database_administration.connection()
database_server_manager.connection()
database_administration.create_table("CREATE TABLE IF NOT EXISTS user(id INT PRIMARY KEY NOT NULL AUTO_INCREMENT, "
                                     "token TEXT,  user_name TEXT, salt TEXT, password TEXT, admin BOOL, "
                                     "work_Dir TEXT, last_online TEXT)")
database_administration.create_table("CREATE TABLE IF NOT EXISTS log(id INT PRIMARY KEY NOT NULL AUTO_INCREMENT, "
                                     "name TEXT,  user_ip text, user_token TEXT, argument TEXT, log_level INT, "
                                     "date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)")
database_server_manager.create_table("CREATE TABLE IF NOT EXISTS server(id INT PRIMARY KEY NOT NULL AUTO_INCREMENT,"
                                     "name TEXT, owner_token TEXT, run_command TEXT, path TEXT)")


@app.route('/')
def home():
    if not request.cookies.get('userID'):
        return redirect(url_for('login'))
    data = database_administration.select('''SELECT user_name, admin FROM user WHERE token = %s''',
                                          (request.cookies.get('userID'),), 1)
    try:
        return render_template('home.html', cur=data)
    except IndexError:
        return redirect(url_for('login'))


@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        user = request.form['nm']
        passwd = request.form['passwd']

        row = database_administration.select(f'''SELECT user_name, password, token FROM user WHERE password = %s 
        AND user_name = %s''', (salt_password(passwd, user), user), 1)

        try:
            make_log('login', request.remote_addr, row[2], 1)
            resp = make_response(redirect(url_for('home')))
            resp.set_cookie('userID', row[2])
            database_administration.insert(f'''UPDATE user SET last_online=%s WHERE token=%s''',
                                           (datetime.now(), row[2]))
            return resp
        except Exception as e:
            make_log('Error', request.remote_addr, request.cookies.get('userID'), 2, str(e))
            return redirect(url_for("home"))

    elif request.method == 'GET':
        return render_template('login.html')


@app.route('/logout', methods=['POST', 'GET'])
def logout():
    make_log('logout', request.remote_addr, request.cookies.get('userID'), 1)
    resp = make_response(redirect(url_for('home')))
    resp.set_cookie('userID', '', expires=0)
    return resp


@app.route('/server/<server_id>')
def server(server_id=None):
    user_token = request.cookies.get('userID')
    if not user_token:
        return redirect(url_for('login'))

    if server_id:
        data = database_server_manager.select('SELECT * FROM cantina_server_manager.server WHERE id=%s', (server_id,), 1)
        return render_template('server_data.html', data=data)
    else:
        return redirect(url_for('home'))


if __name__ == '__main__':
    app.run()
