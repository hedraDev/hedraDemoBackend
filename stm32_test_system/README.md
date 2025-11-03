# STM32L011 Cihaz Test Sistemi v2.0

Hedra Technology tarafından geliştirilen profesyonel STM32L011 cihaz test sistemi.

## 🚀 Özellikler

### Gelişmiş Test Süreci
- ✅ 17 aşamalı otomatik test akışı
- ✅ Manuel ve otomatik aşama geçişleri
- ✅ Her aşama için detaylı loglama
- ✅ Retry mekanizması ile hata toleransı

### Donanım Entegrasyonu
- 🔌 **PPK2 Güç Ölçümü**: Nordic PPK2 ile akım ve voltaj ölçümü
- 💾 **Firmware Yükleme**: PyOCD ile otomatik STM32 firmware yükleme
- 🔗 **BLE Bağlantısı**: Bleak ile kablosuz cihaz iletişimi
- 📸 **Kamera Entegrasyonu**: OpenCV ile canlı önizleme ve fotoğraf çekme

### Veri Yönetimi
- 💾 **MongoDB Veritabanı**: Test sonuçlarını veritabanında saklama
- 📁 **Otomatik Yedekleme**: MongoDB bağlantısı yoksa JSON yedekleme
- 📊 **İstatistikler**: Günlük/haftalık/aylık test istatistikleri
- 📄 **PDF Raporlama**: Profesyonel PDF test raporları

### Kullanıcı Arayüzü
- 🎨 **Modern Tasarım**: PyQt5 ile modern ve kullanıcı dostu arayüz
- 📹 **Canlı Önizleme**: Kamera görüntüsünü gerçek zamanlı görüntüleme
- 🔔 **Ses Bildirimleri**: Aşama tamamlama ve hata bildirimleri
- ⚙️ **Yapılandırılabilir**: JSON tabanlı yapılandırma sistemi

### Loglama ve İzleme
- 📝 **Gelişmiş Loglama**: Dosya ve konsol loglama
- 🔍 **Test Takibi**: Her cihaz için ayrı log dosyası
- ⚠️ **Hata Yönetimi**: Detaylı hata loglama ve recovery

### Operatör Yönetimi
- 👤 **Operatör Girişi**: Her test için operatör kimlik doğrulama
- 📊 **Operatör İstatistikleri**: Operatör bazlı performans takibi

## 📦 Kurulum

### Gereksinimler

```bash
Python 3.8+
MongoDB (opsiyonel)
USB Kamera
Nordic PPK2 (opsiyonel)
ST-Link (firmware yükleme için)
```

### Adım 1: Bağımlılıkları Yükleyin

```bash
cd stm32_test_system
pip install -r requirements.txt
```

### Adım 2: PPK2 API Kurulumu

```bash
pip install ppk2-api
```

### Adım 3: PyOCD Kurulumu

```bash
pip install pyocd
```

### Adım 4: MongoDB Kurulumu (Opsiyonel)

MongoDB yükleyin ve başlatın:

```bash
# Ubuntu/Debian
sudo apt-get install mongodb

# Windows
# MongoDB Community Edition'ı indirin ve kurun
# https://www.mongodb.com/try/download/community

# macOS
brew install mongodb-community
```

## ⚙️ Yapılandırma

`config/config.json` dosyasını düzenleyin:

```json
{
  "hardware": {
    "firmware_path": "./firmware/stm32l011_firmware.hex",
    "ppk2_voltage": 3000
  },
  "database": {
    "mongodb_uri": "mongodb://localhost:27017/",
    "backup_enabled": true
  },
  "camera": {
    "width": 640,
    "height": 480
  }
}
```

## 🎯 Kullanım

### Temel Kullanım

```bash
cd stm32_test_system
python main_enhanced.py
```

### Test Akışı

1. **Operatör Girişi**: Sistem başlangıcında operatör bilgileri girilir
2. **Test Başlatma**: ENTER tuşu ile test başlatılır
3. **Soket Takma**: Test soketi takılır ve ENTER
4. **Otomatik Aşamalar**:
   - Güç verme (PPK2)
   - Firmware yükleme
   - UUID okuma
   - Cihaz reset
5. **Butona Basma**: Cihaz üzerindeki butona basılır
6. **BLE Bağlantısı**: Otomatik BLE bağlantısı kurulur
7. **Solution 1 İşlemleri**: Doldurma, ölçüm, boşaltma
8. **Solution 2 İşlemleri**: Doldurma, ölçüm, boşaltma
9. **Etiket İşlemleri**: Etiket basma ve yapıştırma
10. **Fotoğraf**: Otomatik fotoğraf çekimi
11. **Test Tamamlama**: Sonuçlar MongoDB'ye kaydedilir

## 📊 Menü ve Özellikler

### Dosya Menüsü
- **Rapor Oluştur**: Mevcut test için PDF raporu oluştur
- **Çıkış**: Uygulamayı kapat

### Görünüm Menüsü
- **İstatistikler**: Test istatistiklerini görüntüle
  - Son 7/30/90 gün istatistikleri
  - Başarı oranları
  - Son testler tablosu

### Ayarlar Menüsü
- **Yapılandırma**: Sistem ayarlarını düzenle
  - Genel ayarlar (ses, animasyon)
  - Donanım ayarları (PPK2 voltaj, firmware yolu)
  - BLE ayarları (timeout değerleri)
  - Veritabanı ayarları
- **Sesleri Aç/Kapat**: Ses bildirimlerini aç/kapat

### Yardım Menüsü
- **Hakkında**: Sistem bilgileri ve özellikler

## 📂 Proje Yapısı

```
stm32_test_system/
├── main_enhanced.py          # Ana uygulama
├── logger.py                 # Loglama modülü
├── config_manager.py         # Yapılandırma yönetimi
├── database_manager.py       # MongoDB yönetimi
├── report_generator.py       # PDF rapor oluşturma
├── sound_manager.py          # Ses bildirimleri
├── requirements.txt          # Python bağımlılıkları
├── config/
│   └── config.json          # Yapılandırma dosyası
├── logs/                    # Log dosyaları
├── photos/                  # Çekilen fotoğraflar
├── backup/                  # JSON yedekleri
├── firmware/                # Firmware dosyaları
├── reports/                 # PDF raporlar
├── sounds/                  # Ses dosyaları
└── resources/               # Logo vb. kaynaklar
```

## 🔧 Sorun Giderme

### Kamera Açılmıyor

```python
# DirectShow backend'i etkinleştir (Windows)
camera_cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
```

### MongoDB Bağlanamıyor

- MongoDB servisinin çalıştığından emin olun
- Sistem otomatik olarak JSON yedeklemesine geçer
- `backup/` klasöründeki dosyaları kontrol edin

### PPK2 Bulunamıyor

- PPK2'nin USB'ye bağlı olduğundan emin olun
- PPK2 sürücülerinin yüklü olduğunu kontrol edin
- Sistem simülasyon modunda devam eder

### BLE Bağlantı Problemi

- Cihazın açık ve yeterince yakın olduğundan emin olun
- Bluetooth'un aktif olduğunu kontrol edin
- Timeout değerlerini artırın (`config.json`)

## 📝 Loglama

### Log Dosyaları

- `logs/test_system_YYYYMMDD.log`: Genel sistem logları
- `logs/errors_YYYYMMDD.log`: Sadece hatalar
- `logs/test_UUID_TIMESTAMP.log`: Cihaz bazlı test logları

### Log Seviyeleri

- `DEBUG`: Detaylı debug bilgisi
- `INFO`: Genel bilgilendirme
- `WARNING`: Uyarılar
- `ERROR`: Hatalar
- `CRITICAL`: Kritik hatalar

## 🎨 Özelleştirme

### Tema Değiştirme

`main_enhanced.py` dosyasındaki `apply_theme()` fonksiyonunu düzenleyin:

```python
def apply_theme(self):
    self.setStyleSheet("""
        QMainWindow {
            background-color: #YOURCOLOR;
        }
        ...
    """)
```

### Yeni Aşama Ekleme

1. `create_stages_panel()` metoduna yeni aşamayı ekleyin
2. Yeni aşama metodunu oluşturun (`stage_X_...()`)
3. `on_stage_complete()` metodunda yönlendirme ekleyin

### Ses Dosyaları Ekleme

WAV formatında ses dosyalarını `sounds/` klasörüne ekleyin:
- `success.wav`
- `error.wav`
- `warning.wav`
- `info.wav`
- `complete.wav`
- `stage_complete.wav`

## 📊 Veritabanı Şeması

### Test Kaydı

```json
{
  "start_time": "2024-10-26T10:30:00",
  "end_time": "2024-10-26T10:35:00",
  "device_uuid": "1234ABCD5678EF",
  "operator_name": "Ahmet Yılmaz",
  "operator_id": "OP001",
  "status": "completed",
  "total_duration": 300.5,
  "initial_current": 125.5,
  "measurements": [
    {
      "timestamp": "2024-10-26T10:32:00",
      "solution": 1,
      "raw": 1234,
      "temperature": 25.5
    }
  ],
  "stage_durations": {
    "power_on": 2.5,
    "flash_uuid": 15.3,
    "reset": 3.0
  },
  "photo": "device_1234ABCD_20241026.jpg"
}
```

## 🔐 Güvenlik

- Operatör girişi zorunludur
- Tüm işlemler loglanır
- Veritabanı bağlantısı şifreleme ile yapılabilir
- Hassas veriler için `.env` dosyası kullanılabilir

## 🤝 Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Değişikliklerinizi commit edin (`git commit -m 'Add some amazing feature'`)
4. Branch'inizi push edin (`git push origin feature/amazing-feature`)
5. Pull Request açın

## 📄 Lisans

Bu proje Hedra Technology tarafından geliştirilmiştir.

## 📞 İletişim

**Hedra Technology**
- Website: https://hedra.com
- Email: support@hedra.com

## 📚 Ek Kaynaklar

- [PyQt5 Dokümantasyonu](https://www.riverbankcomputing.com/static/Docs/PyQt5/)
- [PyOCD Kullanımı](https://pyocd.io/)
- [Nordic PPK2](https://www.nordicsemi.com/Products/Development-hardware/Power-Profiler-Kit-2)
- [MongoDB Python Driver](https://pymongo.readthedocs.io/)
- [ReportLab PDF Oluşturma](https://www.reportlab.com/docs/reportlab-userguide.pdf)

## 🎯 Gelecek Özellikler

- [ ] E-posta ile rapor gönderimi
- [ ] Bulut veritabanı desteği
- [ ] QR kod etiket basma
- [ ] Çoklu dil desteği
- [ ] Web dashboard
- [ ] Otomatik kalibrasyon
- [ ] Batch test modu

## ⚡ Performans İpuçları

1. **MongoDB İndeksleme**: UUID üzerine indeks oluşturun
2. **Kamera Çözünürlüğü**: Yüksek çözünürlük yerine standart kullanın
3. **Log Temizleme**: Eski logları düzenli olarak temizleyin
4. **Veritabanı Bakımı**: Düzenli olarak eski kayıtları silin

## 🐛 Bilinen Sorunlar

- BLE bağlantısı bazı platformlarda yavaş olabilir
- Kamera bazı USB hub'larla çalışmayabilir
- PPK2 sürücüleri Windows'ta manuel kurulum gerektirebilir

## 📈 Versiyon Geçmişi

### v2.0.0 (2024-10-26)
- ✨ Operatör yönetimi eklendi
- ✨ PDF rapor oluşturma
- ✨ İstatistik paneli
- ✨ Gelişmiş loglama
- ✨ Ses bildirimleri
- ✨ Yapılandırma dosyası
- ✨ Retry mekanizması
- ✨ MongoDB yedekleme
- 🎨 Modern UI tasarımı
- 🐛 Çeşitli hata düzeltmeleri

### v1.0.0 (2024-10-01)
- 🎉 İlk sürüm
- ✅ Temel test akışı
- ✅ PPK2 entegrasyonu
- ✅ BLE bağlantısı
- ✅ Kamera desteği

---

**Made with ❤️ by Hedra Technology**
