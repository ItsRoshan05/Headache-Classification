from flask import Flask, request, render_template
import numpy as np
import pandas as pd

app = Flask(__name__)

# Contoh data obat sakit kepala

df = pd.read_csv('data/dataset_int.csv')

# Fungsi WP (Weight Product)
def weight_product(criteria_weights, data):
    data = np.array(data)
    criteria_weights = np.array(criteria_weights)
    weighted_product = np.prod(np.power(data, criteria_weights), axis=1)
    return weighted_product

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/', methods=['GET', 'POST'])
def index():
    result = pd.DataFrame()
    if request.method == 'POST':
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
    
    return render_template('index.html', result=result, data=df)

if __name__ == '__main__':
    app.run(debug=True)
