from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
from datetime import datetime
from urllib.parse import urlparse

# PostgreSQL bağlantısı için psycopg2 import
try:
    import psycopg2
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    print("Warning: psycopg2 not available, using SQLite for development")

app = Flask(__name__)

def get_db_connection():
    """Veritabanı bağlantısını alır - PostgreSQL veya SQLite"""
    # Render'da DATABASE_URL environment variable'ı olacak
    database_url = os.getenv('DATABASE_URL')
    
    if database_url and PSYCOPG2_AVAILABLE:
        # PostgreSQL için (production)
        result = urlparse(database_url)
        conn = psycopg2.connect(
            host=result.hostname,
            database=result.path[1:],
            user=result.username,
            password=result.password,
            port=result.port
        )
    else:
        # SQLite için (local development veya psycopg2 yoksa)
        import sqlite3
        conn = sqlite3.connect('kufur_sayac.db')
    
    return conn

def init_db():
    """Veritabanını başlatır"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # PostgreSQL için tablo oluşturma
    if os.getenv('DATABASE_URL') and PSYCOPG2_AVAILABLE:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS kullanicilar (
                id SERIAL PRIMARY KEY,
                isim TEXT NOT NULL,
                kufur_sayisi INTEGER DEFAULT 0,
                toplam_para REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    else:
        # SQLite için tablo oluşturma
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
    conn = get_db_connection()
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
        conn = get_db_connection()
        cursor = conn.cursor()
        if os.getenv('DATABASE_URL') and PSYCOPG2_AVAILABLE:
            cursor.execute('INSERT INTO kullanicilar (isim) VALUES (%s)', (isim,))
        else:
            cursor.execute('INSERT INTO kullanicilar (isim) VALUES (?)', (isim,))
        conn.commit()
        conn.close()
    return redirect(url_for('index'))

@app.route('/kullanici_sil/<int:kullanici_id>')
def kullanici_sil(kullanici_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    if os.getenv('DATABASE_URL') and PSYCOPG2_AVAILABLE:
        cursor.execute('DELETE FROM kullanicilar WHERE id = %s', (kullanici_id,))
    else:
        cursor.execute('DELETE FROM kullanicilar WHERE id = ?', (kullanici_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/kufur_ekle/<int:kullanici_id>')
def kufur_ekle(kullanici_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    if os.getenv('DATABASE_URL') and PSYCOPG2_AVAILABLE:
        cursor.execute('UPDATE kullanicilar SET kufur_sayisi = kufur_sayisi + 1, toplam_para = toplam_para + 10 WHERE id = %s', (kullanici_id,))
    else:
        cursor.execute('UPDATE kullanicilar SET kufur_sayisi = kufur_sayisi + 1, toplam_para = toplam_para + 10 WHERE id = ?', (kullanici_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/kufur_azalt/<int:kullanici_id>')
def kufur_azalt(kullanici_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    if os.getenv('DATABASE_URL') and PSYCOPG2_AVAILABLE:
        cursor.execute('UPDATE kullanicilar SET kufur_sayisi = kufur_sayisi - 1, toplam_para = toplam_para - 10 WHERE id = %s AND kufur_sayisi > 0', (kullanici_id,))
    else:
        cursor.execute('UPDATE kullanicilar SET kufur_sayisi = kufur_sayisi - 1, toplam_para = toplam_para - 10 WHERE id = ? AND kufur_sayisi > 0', (kullanici_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True) 