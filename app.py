from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('kufur_sayac.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS kullanicilar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            isim TEXT NOT NULL,
            kufur_sayisi INTEGER DEFAULT 0,
            toplam_para REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    conn = sqlite3.connect('kufur_sayac.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM kullanicilar ORDER BY kufur_sayisi DESC')
    kullanicilar = cursor.fetchall()
    
    # Toplam para hesaplama
    cursor.execute('SELECT SUM(toplam_para) FROM kullanicilar')
    toplam_para = cursor.fetchone()[0] or 0
    
    conn.close()
    return render_template('index.html', kullanicilar=kullanicilar, toplam_para=toplam_para)

@app.route('/kullanici_ekle', methods=['POST'])
def kullanici_ekle():
    isim = request.form['isim']
    if isim.strip():
        conn = sqlite3.connect('kufur_sayac.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO kullanicilar (isim) VALUES (?)', (isim,))
        conn.commit()
        conn.close()
    return redirect(url_for('index'))

@app.route('/kullanici_sil/<int:kullanici_id>')
def kullanici_sil(kullanici_id):
    conn = sqlite3.connect('kufur_sayac.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM kullanicilar WHERE id = ?', (kullanici_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/kufur_ekle/<int:kullanici_id>')
def kufur_ekle(kullanici_id):
    conn = sqlite3.connect('kufur_sayac.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE kullanicilar SET kufur_sayisi = kufur_sayisi + 1, toplam_para = toplam_para + 10 WHERE id = ?', (kullanici_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/kufur_azalt/<int:kullanici_id>')
def kufur_azalt(kullanici_id):
    conn = sqlite3.connect('kufur_sayac.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE kullanicilar SET kufur_sayisi = kufur_sayisi - 1, toplam_para = toplam_para - 10 WHERE id = ? AND kufur_sayisi > 0', (kullanici_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True) 