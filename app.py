from flask import Flask, render_template, redirect, url_for, flash, session, request, jsonify
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
from forms import RegistrationForm, LoginForm
from config import Config
from decorators import login_required
from wp import normalize_weights, calculate_weighted_product, load_data, validate_columns, map_age_group
import pandas as pd
import numpy as np

app = Flask(__name__)
app.config.from_object(Config)

mysql = MySQL(app)
bcrypt = Bcrypt(app)

df = pd.read_csv('data/dataset_int.csv')

# Route Client 
@app.route('/')
def client():
   return render_template('client/index.html')

@app.route('/prediksiclient', methods=['GET', 'POST'])
def prediksiclient():
    if request.method == 'POST':
        # Mengambil data dari formulir
        form_data = {
            'name': request.form['name'],
            'age': int(request.form['age']),
            'age_group': map_age_group(request.form['age_group']),
            'efektifitas': int(request.form['efektifitas']),
            'dosis': int(request.form['dosis']),
            'efek_samping': int(request.form['efek_samping']),
            'harga': int(request.form['harga']),
            'bagian_sakit_kepala': int(request.form['bagian_sakit_kepala'])
        }

        # Mendefinisikan variabel sesuai dengan form_data
        name = form_data['name']
        age = form_data['age']
        age_group = form_data['age_group']
        efektivitas = form_data['efektifitas']
        dosis = form_data['dosis']
        efek_samping = form_data['efek_samping']
        harga = form_data['harga']
        bagian_sakit_kepala = form_data['bagian_sakit_kepala']

        # Bobot kriteria
        criteria_weights = normalize_weights([
            form_data['efektifitas'],
            form_data['dosis'],
            form_data['efek_samping'],
            form_data['harga'],
            form_data['bagian_sakit_kepala']
        ])

        # Memuat data dan memeriksa kolom
        df = load_data(form_data['age_group'])
        required_columns = ['Nama Obat', 'Efektivitas', 'Dosis', 'Efek Samping', 'Harga', 'Bagian Sakit Kepala']
        if not validate_columns(df, required_columns):
            return "Data tidak sesuai format. Kolom yang diharapkan: 'Nama Obat', 'Efektivitas', 'Dosis', 'Efek Samping', 'Harga', 'Bagian Sakit Kepala'."

        # Hitung WP dan tambahkan kolom 'Score'
        wp_columns = ['Efektivitas', 'Dosis', 'Efek Samping', 'Harga', 'Bagian Sakit Kepala']
        df['Score'] = calculate_weighted_product(criteria_weights, df[wp_columns])

        # Sort dan reset index
        result = df.sort_values(by='Score', ascending=False).reset_index(drop=True)

        recommended_medication = result.iloc[0]['Nama Obat']  # Assuming 'Obat' is the column name for medication
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO prediksi (name, age, id_kategori_umur, efektifitas, dosis, efek_samping, harga, bagian_sakit_kepala, score, recommended_medication)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, ( name, age, age_group, efektivitas, dosis, efek_samping, harga, bagian_sakit_kepala, result.iloc[0]['Score'], recommended_medication))
        mysql.connection.commit()
        cur.close()

        # Konversi DataFrame ke HTML
        columns_to_include = ['Nama Obat', 'Efektivitas', 'Dosis', 'Efek Samping', 'Harga', 'Bagian Sakit Kepala', 'Score']
        result_html = result[columns_to_include].to_html(classes='table table-striped table-hover', index=False)

        # Ambil rekomendasi teratas
        top_recommendation = result.iloc[0] if not result.empty else None
        top_recommendation_dict = top_recommendation.to_dict() if top_recommendation is not None else None

        return render_template('client/result.html', name=form_data['name'], age=form_data['age'], 
                               result_html=result_html, top_recommendation=top_recommendation_dict)

    return render_template('client/prediksi.html')

# end of route client 



# Route admin 
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

@app.route('/api/user_growth')
@login_required
def user_growth():
    cur = mysql.connection.cursor()
    cur.execute("SELECT DATE(created_at) as date, COUNT(*) as count FROM user GROUP BY DATE(created_at) ORDER BY DATE(created_at)")
    result = cur.fetchall()
    cur.close()
    
    dates = [row[0].strftime("%Y-%m-%d") for row in result]
    counts = [row[1] for row in result]
    
    return jsonify({'dates': dates, 'counts': counts})

@app.route('/api/recommendation_distribution')
@login_required
def recommendation_distribution():
    cur = mysql.connection.cursor()
    cur.execute("SELECT recommended_medication, COUNT(*) as count FROM prediksi GROUP BY recommended_medication")
    result = cur.fetchall()
    cur.close()
    
    labels = [row[0] for row in result]
    data = [row[1] for row in result]
    
    return jsonify({'labels': labels, 'data': data})

@app.route('/api/age_category_distribution')
@login_required
def age_category_distribution():
    cur = mysql.connection.cursor()
    # Query to get distribution of age categories with names
    cur.execute("""
        SELECT k.nm_kategori AS age_category, COUNT(*) AS count
        FROM prediksi p
        JOIN kategori_umur k ON p.id_kategori_umur = k.id
        GROUP BY k.nm_kategori
    """)
    results = cur.fetchall()
    cur.close()
    
    # Extract labels and data from results using indices
    labels = [row[0] for row in results]  # `age_category` is at index 0
    data = [row[1] for row in results]    # `count` is at index 1

    # Return JSON response
    return jsonify({'labels': labels, 'data': data})

@app.route('/api/drug_effectiveness')
@login_required
def drug_effectiveness():
    cur = mysql.connection.cursor()
    # Query to get effectiveness of drugs (adjust based on your schema)
    cur.execute("""
        SELECT recommended_medication, AVG(score) AS avg_score
        FROM prediksi
        GROUP BY recommended_medication
    """)
    results = cur.fetchall()
    cur.close()
    
    labels = [row[0] for row in results]
    data = [row[1] for row in results]

    return jsonify({'labels': labels, 'data': data})



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

@app.route('/prediksi', methods=['GET', 'POST'])
@login_required
def prediksi():
    username = session.get('username')  # Getting username from session
    result = pd.DataFrame()
    if request.method == 'POST':
        name = request.form['name']
        age = int(request.form['age'])
        efektifitas = float(request.form['efektifitas'])
        efek_samping = float(request.form['efek_samping'])
        harga = float(request.form['harga'])
        
        # Bobot kriteria
        criteria_weights = [efektifitas, efek_samping, harga]
        
        # Normalisasi bobot kriteria
        criteria_weights = [w / sum(criteria_weights) for w in criteria_weights]
        
        # Hitung WP
        df['Score'] = weight_product(criteria_weights, df[['Efektifitas', 'Efek Samping', 'Harga']])
        
        # Sort berdasarkan score tertinggi
        result = df.sort_values(by='Score', ascending=False).reset_index(drop=True)
    
        # Simpan hasil prediksi dan rekomendasi ke database
        recommended_medication = result.iloc[0]['Obat']  # Assuming 'Obat' is the column name for medication
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO prediksi (username, name, age, efektifitas, efek_samping, harga, score, recommended_medication)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (session['username'], name, age, efektifitas, efek_samping, harga, result.iloc[0]['Score'], recommended_medication))
        mysql.connection.commit()
        cur.close()
    return render_template('prediksi.html', result=result, data=df, username=username)


# users 
@app.route('/users')
@login_required
def users():
    username = session.get('username')  # Getting username from session
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM user")
    users = cur.fetchall()
    cur.close()
    return render_template('users/list_users.html', users=users, username=username)

@app.route('/user/new', methods=['GET', 'POST'])
@login_required
def create_user():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO user (username, email, password) VALUES (%s, %s, %s)", (name, email, hashed_password))
        mysql.connection.commit()
        cur.close()
        flash('User created successfully!')
        return redirect(url_for('users'))
    return render_template('create_user.html')

@app.route('/user/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_user(id):
    username = session.get('username')  # Getting username from session
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        if password:
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            cur.execute("UPDATE user SET username = %s, email = %s, password = %s WHERE id = %s", 
                        (name, email, hashed_password, id))
        else:
            cur.execute("UPDATE user SET username = %s, email = %s WHERE id = %s", 
                        (name, email, id))

        mysql.connection.commit()
        cur.close()
        flash('User updated successfully!')
        return redirect(url_for('users'))
    cur.execute("SELECT * FROM user WHERE id = %s", [id])
    user = cur.fetchone()
    cur.close()
    return render_template('users/edit_user.html', user=user, username=username)

@app.route('/user/delete/<int:id>', methods=['POST'])
@login_required
def delete_user(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM user WHERE id = %s", [id])
    mysql.connection.commit()
    cur.close()
    flash('User deleted successfully!')
    return redirect(url_for('users'))
# end of users

# Predictions
@app.route('/predictions')
@login_required
def predictions():
    username = session.get('username')  # Getting username from session
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT p.*, k.nm_kategori
        FROM prediksi p
        JOIN kategori_umur k ON p.id_kategori_umur = k.id
    """)
    predictions = cur.fetchall()
    cur.close()
    return render_template('predictions/list_predictions.html', predictions=predictions, username=username)


@app.route('/predictions/delete/<int:id>', methods=['POST'])
@login_required
def delete_prediction(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM prediksi WHERE id = %s", [id])
    mysql.connection.commit()
    cur.close()
    flash('User deleted successfully!')
    return redirect(url_for('predictions'))

# end of predictions



# end of route admin

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
