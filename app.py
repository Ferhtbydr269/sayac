from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
import os
from datetime import datetime, timedelta
from urllib.parse import urlparse
import hashlib
import time

# PostgreSQL bağlantısı için psycopg2 import
try:
    import psycopg2
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    print("Warning: psycopg2 not available, using SQLite for development")

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Flash mesajları için

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

def is_office_hours():
    """Ofis saatlerinde mi kontrol eder (09:00-21:00)"""
    now = datetime.now()
    start_time = now.replace(hour=9, minute=0, second=0, microsecond=0)
    end_time = now.replace(hour=21, minute=0, second=0, microsecond=0)
    return start_time <= now <= end_time

def get_user_stats():
    """Kullanıcı istatistiklerini hesaplar"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Haftalık istatistikler
    week_ago = datetime.now() - timedelta(days=7)
    cursor.execute('''
        SELECT kullanici_id, COUNT(*) as haftalik_kufur 
        FROM kufur_gecmisi 
        WHERE tarih >= %s 
        GROUP BY kullanici_id
    ''', (week_ago,))
    haftalik_stats = cursor.fetchall()
    
    # En çok küfür edenler
    cursor.execute('''
        SELECT k.isim, k.kufur_sayisi, k.toplam_para 
        FROM kullanicilar k 
        ORDER BY k.kufur_sayisi DESC 
        LIMIT 5
    ''')
    top_kullanicilar = cursor.fetchall()
    
    conn.close()
    return haftalik_stats, top_kullanicilar

def calculate_badges(kufur_sayisi, toplam_para):
    """Başarı rozetlerini hesaplar"""
    badges = []
    
    if kufur_sayisi >= 50:
        badges.append({"name": "Küfür Kralı", "icon": "👑", "color": "#FFD700"})
    elif kufur_sayisi >= 30:
        badges.append({"name": "Küfür Ustası", "icon": "⚔️", "color": "#C0C0C0"})
    elif kufur_sayisi >= 10:
        badges.append({"name": "Küfür Çırağı", "icon": "🔨", "color": "#CD7F32"})
    
    if kufur_sayisi == 0:
        badges.append({"name": "Temiz Dil", "icon": "🌸", "color": "#90EE90"})
    elif kufur_sayisi <= 3:
        badges.append({"name": "Nazik", "icon": "🌺", "color": "#FFB6C1"})
    
    if toplam_para >= 500:
        badges.append({"name": "Borç Kralı", "icon": "💰", "color": "#FFD700"})
    elif toplam_para >= 200:
        badges.append({"name": "Borçlu", "icon": "💸", "color": "#FF6B6B"})
    
    return badges

def init_db():
    """Veritabanını başlatır"""
    try:
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
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS kufur_gecmisi (
                    id SERIAL PRIMARY KEY,
                    kullanici_id INTEGER REFERENCES kullanicilar(id),
                    tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ip_adresi TEXT
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
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS kufur_gecmisi (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kullanici_id INTEGER,
                    tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ip_adresi TEXT,
                    FOREIGN KEY (kullanici_id) REFERENCES kullanicilar (id)
                )
            ''')
        
        conn.commit()
        conn.close()
        print("Database initialized successfully!")
    except Exception as e:
        print(f"Database initialization error: {e}")

@app.route('/')
def index():
    # Her request'te tablo var mı kontrol et
    init_db()
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM kullanicilar ORDER BY kufur_sayisi DESC')
        kullanicilar = cursor.fetchall()
        
        # Toplam para hesaplama
        cursor.execute('SELECT SUM(toplam_para) FROM kullanicilar')
        toplam_para = cursor.fetchone()[0] or 0
        
        # İstatistikler
        haftalik_stats, top_kullanicilar = get_user_stats()
        
        # Her kullanıcı için rozetler
        kullanicilar_with_badges = []
        for kullanici in kullanicilar:
            badges = calculate_badges(kullanici[2], kullanici[3])
            kullanicilar_with_badges.append({
                'data': kullanici,
                'badges': badges
            })
        
        conn.close()
        
        return render_template('index.html', 
                            kullanicilar=kullanicilar_with_badges, 
                            toplam_para=toplam_para,
                            is_office_hours=is_office_hours(),
                            top_kullanicilar=top_kullanicilar,
                            haftalik_stats=haftalik_stats)
    except Exception as e:
        print(f"Error in index: {e}")
        return render_template('index.html', 
                            kullanicilar=[], 
                            toplam_para=0,
                            is_office_hours=is_office_hours(),
                            top_kullanicilar=[],
                            haftalik_stats=[])

@app.route('/kullanici_ekle', methods=['POST'])
def kullanici_ekle():
    isim = request.form['isim']
    if isim.strip():
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            if os.getenv('DATABASE_URL') and PSYCOPG2_AVAILABLE:
                cursor.execute('INSERT INTO kullanicilar (isim) VALUES (%s)', (isim,))
            else:
                cursor.execute('INSERT INTO kullanicilar (isim) VALUES (?)', (isim,))
            conn.commit()
            conn.close()
            flash('Kullanıcı başarıyla eklendi!', 'success')
        except Exception as e:
            print(f"Error adding user: {e}")
            flash('Kullanıcı eklenirken hata oluştu!', 'error')
    return redirect(url_for('index'))

@app.route('/kullanici_sil/<int:kullanici_id>')
def kullanici_sil(kullanici_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if os.getenv('DATABASE_URL') and PSYCOPG2_AVAILABLE:
            cursor.execute('DELETE FROM kullanicilar WHERE id = %s', (kullanici_id,))
        else:
            cursor.execute('DELETE FROM kullanicilar WHERE id = ?', (kullanici_id,))
        conn.commit()
        conn.close()
        flash('Kullanıcı silindi!', 'success')
    except Exception as e:
        print(f"Error deleting user: {e}")
        flash('Kullanıcı silinirken hata oluştu!', 'error')
    return redirect(url_for('index'))

@app.route('/kufur_ekle/<int:kullanici_id>')
def kufur_ekle(kullanici_id):
    # Ofis saatleri kontrolü
    if not is_office_hours():
        flash('❌ Sadece 09:00-21:00 saatleri arasında küfür eklenebilir!', 'error')
        return redirect(url_for('index'))
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Küfür geçmişine ekle
        ip_adresi = request.remote_addr
        if os.getenv('DATABASE_URL') and PSYCOPG2_AVAILABLE:
            cursor.execute('INSERT INTO kufur_gecmisi (kullanici_id, ip_adresi) VALUES (%s, %s)', 
                         (kullanici_id, ip_adresi))
            cursor.execute('UPDATE kullanicilar SET kufur_sayisi = kufur_sayisi + 1, toplam_para = toplam_para + 10 WHERE id = %s', (kullanici_id,))
        else:
            cursor.execute('INSERT INTO kufur_gecmisi (kullanici_id, ip_adresi) VALUES (?, ?)', 
                         (kullanici_id, ip_adresi))
            cursor.execute('UPDATE kullanicilar SET kufur_sayisi = kufur_sayisi + 1, toplam_para = toplam_para + 10 WHERE id = ?', (kullanici_id,))
        
        conn.commit()
        conn.close()
        flash('🤬 Küfür eklendi! +10 TL', 'success')
    except Exception as e:
        print(f"Error adding curse: {e}")
        flash('Küfür eklenirken hata oluştu!', 'error')
    return redirect(url_for('index'))

@app.route('/kufur_azalt/<int:kullanici_id>')
def kufur_azalt(kullanici_id):
    # Ofis saatleri kontrolü
    if not is_office_hours():
        flash('❌ Sadece 09:00-21:00 saatleri arasında küfür azaltılabilir!', 'error')
        return redirect(url_for('index'))
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if os.getenv('DATABASE_URL') and PSYCOPG2_AVAILABLE:
            cursor.execute('UPDATE kullanicilar SET kufur_sayisi = kufur_sayisi - 1, toplam_para = toplam_para - 10 WHERE id = %s AND kufur_sayisi > 0', (kullanici_id,))
        else:
            cursor.execute('UPDATE kullanicilar SET kufur_sayisi = kufur_sayisi - 1, toplam_para = toplam_para - 10 WHERE id = ? AND kufur_sayisi > 0', (kullanici_id,))
        conn.commit()
        conn.close()
        flash('😇 Küfür azaltıldı! -10 TL', 'success')
    except Exception as e:
        print(f"Error reducing curse: {e}")
        flash('Küfür azaltılırken hata oluştu!', 'error')
    return redirect(url_for('index'))

@app.route('/stats')
def stats():
    """İstatistik sayfası"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Haftalık trend
        cursor.execute('''
            SELECT DATE(tarih) as gun, COUNT(*) as kufur_sayisi
            FROM kufur_gecmisi 
            WHERE tarih >= DATE('now', '-7 days')
            GROUP BY DATE(tarih)
            ORDER BY gun
        ''')
        haftalik_trend = cursor.fetchall()
        
        # En çok küfür edenler
        cursor.execute('''
            SELECT k.isim, k.kufur_sayisi, k.toplam_para
            FROM kullanicilar k
            ORDER BY k.kufur_sayisi DESC
        ''')
        siralama = cursor.fetchall()
        
        conn.close()
        
        return render_template('stats.html', 
                            haftalik_trend=haftalik_trend,
                            siralama=siralama)
    except Exception as e:
        print(f"Error in stats: {e}")
        return render_template('stats.html', 
                            haftalik_trend=[],
                            siralama=[])

if __name__ == '__main__':
    init_db()
    app.run(debug=True) 