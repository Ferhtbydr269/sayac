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

def get_daily_challenges():
    """Günlük challenge'ları döndürür"""
    challenges = [
        {"id": "clean_day", "name": "Temiz Gün", "desc": "Bugün hiç küfür etme", "xp": 50, "icon": "🌸"},
        {"id": "first_blood", "name": "İlk Kan", "desc": "Günün ilk küfrünü et", "xp": 10, "icon": "⚡"},
        {"id": "social", "name": "Sosyal", "desc": "3 farklı kişiye küfür ekle", "xp": 30, "icon": "👥"},
        {"id": "streak", "name": "Streak", "desc": "3 gün üst üste aktif ol", "xp": 40, "icon": "🔥"}
    ]
    return challenges

def check_and_update_challenges(kullanici_id):
    """Kullanıcının challenge'larını kontrol eder ve günceller"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        today = datetime.now().date()
        
        # Bugünkü challenge'ları kontrol et
        challenges = get_daily_challenges()
        completed_challenges = []
        
        for challenge in challenges:
            # Bu challenge bugün tamamlandı mı?
            if os.getenv('DATABASE_URL') and PSYCOPG2_AVAILABLE:
                cursor.execute('''
                    SELECT * FROM challenges 
                    WHERE kullanici_id = %s AND challenge_type = %s AND date = %s
                ''', (kullanici_id, challenge["id"], today))
            else:
                cursor.execute('''
                    SELECT * FROM challenges 
                    WHERE kullanici_id = ? AND challenge_type = ? AND date = ?
                ''', (kullanici_id, challenge["id"], today))
            
            if not cursor.fetchone():
                # Challenge henüz eklenmemiş, ekle
                if os.getenv('DATABASE_URL') and PSYCOPG2_AVAILABLE:
                    cursor.execute('''
                        INSERT INTO challenges (kullanici_id, challenge_type, date, reward_xp)
                        VALUES (%s, %s, %s, %s)
                    ''', (kullanici_id, challenge["id"], today, challenge["xp"]))
                else:
                    cursor.execute('''
                        INSERT INTO challenges (kullanici_id, challenge_type, date, reward_xp)
                        VALUES (?, ?, ?, ?)
                    ''', (kullanici_id, challenge["id"], today, challenge["xp"]))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error in check_and_update_challenges: {e}")
        return False

def get_user_stats():
    """Kullanıcı istatistiklerini hesaplar"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Haftalık istatistikler - kufur_gecmisi tablosu yoksa boş liste döndür
        try:
            week_ago = datetime.now() - timedelta(days=7)
            if os.getenv('DATABASE_URL') and PSYCOPG2_AVAILABLE:
                cursor.execute('''
                    SELECT kullanici_id, COUNT(*) as haftalik_kufur 
                    FROM kufur_gecmisi 
                    WHERE tarih >= %s 
                    GROUP BY kullanici_id
                ''', (week_ago,))
            else:
                cursor.execute('''
                    SELECT kullanici_id, COUNT(*) as haftalik_kufur 
                    FROM kufur_gecmisi 
                    WHERE tarih >= ? 
                    GROUP BY kullanici_id
                ''', (week_ago,))
            haftalik_stats = cursor.fetchall()
        except:
            haftalik_stats = []
        
        # Leaderboard - XP'ye göre sıralama
        cursor.execute('''
            SELECT k.isim, k.kufur_sayisi, k.toplam_para, k.xp, k.level, k.avatar
            FROM kullanicilar k 
            ORDER BY k.xp DESC, k.kufur_sayisi DESC
            LIMIT 10
        ''')
        leaderboard = cursor.fetchall()
        
        conn.close()
        return haftalik_stats, leaderboard
    except Exception as e:
        print(f"Error in get_user_stats: {e}")
        return [], []

def get_level_info(xp):
    """XP'ye göre seviye bilgilerini döndürür"""
    levels = [
        {"level": 1, "name": "Masum", "icon": "😇", "min_xp": 0, "max_xp": 100},
        {"level": 2, "name": "Acemi", "icon": "🌱", "min_xp": 100, "max_xp": 250},
        {"level": 3, "name": "Orta", "icon": "🎯", "min_xp": 250, "max_xp": 500},
        {"level": 4, "name": "Usta", "icon": "⚔️", "min_xp": 500, "max_xp": 1000},
        {"level": 5, "name": "Efsane", "icon": "🔥", "min_xp": 1000, "max_xp": 999999}
    ]
    
    for level_info in levels:
        if level_info["min_xp"] <= xp < level_info["max_xp"]:
            progress = ((xp - level_info["min_xp"]) / (level_info["max_xp"] - level_info["min_xp"])) * 100
            return {**level_info, "progress": min(progress, 100)}
    
    return levels[-1]  # Max level

def calculate_badges(kufur_sayisi, toplam_para, streak):
    """Başarı rozetlerini hesaplar"""
    badges = []
    
    # Küfür rozetleri
    if kufur_sayisi >= 50:
        badges.append({"name": "Küfür Kralı", "icon": "👑", "color": "#FFD700"})
    elif kufur_sayisi >= 30:
        badges.append({"name": "Küfür Ustası", "icon": "⚔️", "color": "#C0C0C0"})
    elif kufur_sayisi >= 10:
        badges.append({"name": "Küfür Çırağı", "icon": "🔨", "color": "#CD7F32"})
    
    # Temiz dil rozetleri
    if kufur_sayisi == 0:
        badges.append({"name": "Temiz Dil", "icon": "🌸", "color": "#90EE90"})
    elif kufur_sayisi <= 3:
        badges.append({"name": "Nazik", "icon": "🌺", "color": "#FFB6C1"})
    
    # Borç rozetleri
    if toplam_para >= 500:
        badges.append({"name": "Borç Kralı", "icon": "💰", "color": "#FFD700"})
    elif toplam_para >= 200:
        badges.append({"name": "Borçlu", "icon": "💸", "color": "#FF6B6B"})
    
    # Streak rozetleri
    if streak >= 7:
        badges.append({"name": "Haftalık Streak", "icon": "🔥", "color": "#FF4500"})
    elif streak >= 3:
        badges.append({"name": "Streak Master", "icon": "⭐", "color": "#FFA500"})
    
    return badges

def update_user_xp(kullanici_id, xp_change):
    """Kullanıcının XP'sini günceller ve seviye kontrolü yapar"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Mevcut XP ve level'ı al
        if os.getenv('DATABASE_URL') and PSYCOPG2_AVAILABLE:
            cursor.execute('SELECT xp, level FROM kullanicilar WHERE id = %s', (kullanici_id,))
        else:
            cursor.execute('SELECT xp, level FROM kullanicilar WHERE id = ?', (kullanici_id,))
        
        result = cursor.fetchone()
        if not result:
            return False
            
        current_xp, current_level = result
        new_xp = max(0, current_xp + xp_change)
        
        # Yeni seviye hesapla
        level_info = get_level_info(new_xp)
        new_level = level_info["level"]
        
        # Güncelle
        if os.getenv('DATABASE_URL') and PSYCOPG2_AVAILABLE:
            cursor.execute('UPDATE kullanicilar SET xp = %s, level = %s WHERE id = %s', 
                         (new_xp, new_level, kullanici_id))
        else:
            cursor.execute('UPDATE kullanicilar SET xp = ?, level = ? WHERE id = ?', 
                         (new_xp, new_level, kullanici_id))
        
        conn.commit()
        conn.close()
        
        # Seviye atladı mı?
        level_up = new_level > current_level
        return {"level_up": level_up, "new_level": new_level, "new_xp": new_xp}
        
    except Exception as e:
        print(f"Error updating XP: {e}")
        return False

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
                    xp INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    avatar TEXT DEFAULT '😊',
                    streak INTEGER DEFAULT 0,
                    last_activity DATE,
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
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS challenges (
                    id SERIAL PRIMARY KEY,
                    kullanici_id INTEGER REFERENCES kullanicilar(id),
                    challenge_type TEXT NOT NULL,
                    completed BOOLEAN DEFAULT FALSE,
                    date DATE DEFAULT CURRENT_DATE,
                    reward_xp INTEGER DEFAULT 0
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
                    xp INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    avatar TEXT DEFAULT '😊',
                    streak INTEGER DEFAULT 0,
                    last_activity DATE,
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
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS challenges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kullanici_id INTEGER,
                    challenge_type TEXT NOT NULL,
                    completed BOOLEAN DEFAULT FALSE,
                    date DATE DEFAULT CURRENT_DATE,
                    reward_xp INTEGER DEFAULT 0,
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
        
        # Kullanıcıları getir (yeni alanlarla birlikte)
        cursor.execute('''
            SELECT id, isim, kufur_sayisi, toplam_para, xp, level, avatar, streak, created_at 
            FROM kullanicilar 
            ORDER BY xp DESC, kufur_sayisi DESC
        ''')
        kullanicilar = cursor.fetchall()
        
        # Toplam para hesaplama
        cursor.execute('SELECT SUM(toplam_para) FROM kullanicilar')
        toplam_para = cursor.fetchone()[0] or 0
        
        # İstatistikler ve leaderboard
        haftalik_stats, leaderboard = get_user_stats()
        
        # Günlük challenge'lar
        daily_challenges = get_daily_challenges()
        
        # Her kullanıcı için detaylı bilgiler
        kullanicilar_with_details = []
        for kullanici in kullanicilar:
            # Challenge'ları kontrol et
            check_and_update_challenges(kullanici[0])
            
            # Seviye bilgisi
            level_info = get_level_info(kullanici[4])  # xp
            
            # Rozetler
            badges = calculate_badges(kullanici[2], kullanici[3], kullanici[7])  # kufur, para, streak
            
            kullanicilar_with_details.append({
                'data': kullanici,
                'level_info': level_info,
                'badges': badges
            })
        
        conn.close()
        
        return render_template('index.html', 
                            kullanicilar=kullanicilar_with_details, 
                            toplam_para=toplam_para,
                            is_office_hours=is_office_hours(),
                            leaderboard=leaderboard,
                            daily_challenges=daily_challenges,
                            haftalik_stats=haftalik_stats)
    except Exception as e:
        print(f"Error in index: {e}")
        return render_template('index.html', 
                            kullanicilar=[], 
                            toplam_para=0,
                            is_office_hours=is_office_hours(),
                            leaderboard=[],
                            daily_challenges=[],
                            haftalik_stats=[])

@app.route('/kullanici_ekle', methods=['POST'])
def kullanici_ekle():
    isim = request.form['isim']
    print(f"Kullanıcı ekleme isteği: {isim}")
    
    if isim.strip():
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Kullanıcıyı ekle
            if os.getenv('DATABASE_URL') and PSYCOPG2_AVAILABLE:
                cursor.execute('INSERT INTO kullanicilar (isim) VALUES (%s)', (isim,))
            else:
                cursor.execute('INSERT INTO kullanicilar (isim) VALUES (?)', (isim,))
            
            conn.commit()
            
            # Eklenen kullanıcıyı kontrol et
            if os.getenv('DATABASE_URL') and PSYCOPG2_AVAILABLE:
                cursor.execute('SELECT * FROM kullanicilar WHERE isim = %s', (isim,))
            else:
                cursor.execute('SELECT * FROM kullanicilar WHERE isim = ?', (isim,))
            
            eklenen_kullanici = cursor.fetchone()
            print(f"Eklenen kullanıcı: {eklenen_kullanici}")
            
            conn.close()
            flash(f'Kullanıcı "{isim}" başarıyla eklendi!', 'success')
        except Exception as e:
            print(f"Error adding user: {e}")
            flash(f'Kullanıcı eklenirken hata oluştu: {e}', 'error')
    else:
        flash('Kullanıcı adı boş olamaz!', 'error')
    
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
        
        # XP güncelle (küfür için -5 XP)
        xp_result = update_user_xp(kullanici_id, -5)
        
        message = '🤬 Küfür eklendi! +10 TL, -5 XP'
        if xp_result and xp_result.get('level_up'):
            message += f' 🎉 Seviye {xp_result["new_level"]}!'
        
        flash(message, 'success')
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
        
        # XP güncelle (küfür azaltma için +10 XP)
        xp_result = update_user_xp(kullanici_id, 10)
        
        message = '😇 Küfür azaltıldı! -10 TL, +10 XP'
        if xp_result and xp_result.get('level_up'):
            message += f' 🎉 Seviye {xp_result["new_level"]}!'
            
        flash(message, 'success')
    except Exception as e:
        print(f"Error reducing curse: {e}")
        flash('Küfür azaltılırken hata oluştu!', 'error')
    return redirect(url_for('index'))

@app.route('/change_avatar/<int:kullanici_id>/<avatar>')
def change_avatar(kullanici_id, avatar):
    """Avatar değiştirme"""
    try:
        # Güvenli avatar listesi
        safe_avatars = ['😊', '😎', '🤓', '😇', '🤔', '😴', '🤯', '🥳', '🤠', '🤖', '👻', '🎭', '🦄', '🐱', '🐶', '🦊']
        
        if avatar not in safe_avatars:
            flash('Geçersiz avatar!', 'error')
            return redirect(url_for('index'))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if os.getenv('DATABASE_URL') and PSYCOPG2_AVAILABLE:
            cursor.execute('UPDATE kullanicilar SET avatar = %s WHERE id = %s', (avatar, kullanici_id))
        else:
            cursor.execute('UPDATE kullanicilar SET avatar = ? WHERE id = ?', (avatar, kullanici_id))
        
        conn.commit()
        conn.close()
        
        flash(f'Avatar değiştirildi! {avatar}', 'success')
    except Exception as e:
        print(f"Error changing avatar: {e}")
        flash('Avatar değiştirilemedi!', 'error')
    
    return redirect(url_for('index'))

@app.route('/stats')
def stats():
    """İstatistik sayfası"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Haftalık trend - kufur_gecmisi tablosu yoksa boş liste döndür
        try:
            if os.getenv('DATABASE_URL') and PSYCOPG2_AVAILABLE:
                cursor.execute('''
                    SELECT DATE(tarih) as gun, COUNT(*) as kufur_sayisi
                    FROM kufur_gecmisi 
                    WHERE tarih >= DATE('now', '-7 days')
                    GROUP BY DATE(tarih)
                    ORDER BY gun
                ''')
            else:
                cursor.execute('''
                    SELECT DATE(tarih) as gun, COUNT(*) as kufur_sayisi
                    FROM kufur_gecmisi 
                    WHERE tarih >= DATE('now', '-7 days')
                    GROUP BY DATE(tarih)
                    ORDER BY gun
                ''')
            haftalik_trend = cursor.fetchall()
        except:
            haftalik_trend = []
        
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