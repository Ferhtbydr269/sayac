# 🤬 Küfür Sayacı

Arkadaşlar arasında küfür eden kişileri takip etmek için geliştirilmiş eğlenceli bir web uygulaması!

## Özellikler

- ✅ Kullanıcı ekleme/çıkarma
- ✅ Her küfür için 10 TL borç ekleme
- ✅ Küfür sayısını artırma/azaltma
- ✅ Toplam borç takibi
- ✅ Modern ve kullanıcı dostu arayüz
- ✅ SQLite veritabanı ile veri saklama

## Kurulum

1. Python'u bilgisayarınıza yükleyin (Python 3.7+)

2. Gerekli paketleri yükleyin:
```bash
pip install -r requirements.txt
```

3. Uygulamayı çalıştırın:
```bash
python app.py
```

4. Tarayıcınızda `http://localhost:5000` adresine gidin

## Kullanım

1. **Kullanıcı Ekleme**: Üst kısımdaki form ile yeni kullanıcı ekleyin
2. **Küfür Ekleme**: Kullanıcının yanındaki "+1 Küfür" butonuna tıklayın
3. **Küfür Azaltma**: "-1 Küfür" butonu ile sayıyı azaltın
4. **Kullanıcı Silme**: "Sil" butonu ile kullanıcıyı kaldırın
5. **Toplam Borç**: Alt kısımda toplam borç miktarını görebilirsiniz

## Teknolojiler

- **Backend**: Flask (Python)
- **Veritabanı**: SQLite
- **Frontend**: HTML, CSS, JavaScript
- **Tasarım**: Modern ve responsive tasarım

## Dosya Yapısı

```
sayac/
├── app.py              # Ana Flask uygulaması
├── requirements.txt    # Python bağımlılıkları
├── README.md          # Bu dosya
├── templates/         # HTML şablonları
│   └── index.html    # Ana sayfa
└── kufur_sayac.db    # SQLite veritabanı (otomatik oluşur)
```

## Lisans

Bu proje eğitim amaçlı geliştirilmiştir. Eğlenceli kullanımlar dileriz! 😄 