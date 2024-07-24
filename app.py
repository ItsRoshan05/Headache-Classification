from flask import Flask, render_template, redirect, url_for, flash, session
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
from forms import RegistrationForm, LoginForm
from config import Config
from decorators import login_required

app = Flask(__name__)
app.config.from_object(Config)

mysql = MySQL(app)
bcrypt = Bcrypt(app)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO user (username, email, password) VALUES (%s, %s, %s)",
                    (form.username.data, form.email.data, hashed_password))
        mysql.connection.commit()
        cur.close()
        flash('Your account has been created!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM user WHERE email=%s", [form.username.data])
        user = cur.fetchone()
        cur.close()
        if user and bcrypt.check_password_hash(user[3], form.password.data):
            session['username'] = user[1]  # Storing username in session
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Login failed. Check email and/or password', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    session.pop('username', None)  # Removing username from session
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/home')
@login_required
def home():
    username = session.get('username')  # Getting username from session
    return render_template('dashboard.html', username=username)

@app.route('/testing')
@login_required
def testing():
    username = session.get('username')  # Getting username from session
    return render_template('testing.html',username=username)

@app.route('/profile')
@login_required
def profile():
    if 'username' not in session:
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT username, email FROM user WHERE username=%s", [session['username']])
    user = cur.fetchone()
    cur.close()

    if user:
        return render_template('profile.html', username=user[0], email=user[1])
    else:
        flash('User not found.', 'danger')
        return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
