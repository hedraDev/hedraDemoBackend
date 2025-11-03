# 🚀 Hızlı Başlangıç Kılavuzu

STM32L011 Test Sistemi'ni 5 dakikada çalıştırın!

## 1️⃣ Kurulum

```bash
# Proje dizinine gidin
cd stm32_test_system

# Bağımlılıkları yükleyin
pip install -r requirements.txt

# PyOCD ve PPK2 API (opsiyonel)
pip install pyocd ppk2-api
```

## 2️⃣ Yapılandırma

`config/config.json` dosyasını kontrol edin:

```json
{
  "hardware": {
    "firmware_path": "./firmware/stm32l011_firmware.hex"
  },
  "database": {
    "mongodb_uri": "mongodb://localhost:27017/"
  }
}
```

## 3️⃣ Firmware Hazırlama

Firmware dosyanızı `firmware/` klasörüne kopyalayın:

```bash
cp /path/to/your/firmware.hex firmware/stm32l011_firmware.hex
```

## 4️⃣ İlk Çalıştırma

```bash
python main_enhanced.py
```

### İlk Açılışta:
1. **Operatör Girişi**: Adınızı ve ID'nizi girin
2. **Ana Ekran**: Test sistemi hazır görünecek
3. **ENTER**: Test başlatmak için ENTER'a basın

## 5️⃣ Test Akışı

```
ENTER → Soket Tak → ENTER → Otomatik (3-4-5) →
Butona Bas → ENTER → Otomatik (BLE) → Solutions → Etiket →
Fotoğraf → Tamamla
```

## ⚙️ MongoDB Olmadan Çalıştırma

MongoDB yoksa endişelenmeyin! Sistem otomatik olarak:
- JSON dosyalarına yedekler
- Test verileri `backup/` klasörüne kaydedilir
- Tüm özellikler çalışmaya devam eder

## 📸 Kamera Olmadan Test

Kamera yoksa:
- Sistem uyarı verecek ama devam edecek
- Fotoğraf aşaması atlanacak
- Diğer tüm testler normal çalışacak

## 🎯 İlk Testiniz

### Simülasyon Modu (Donanım Yok)

Eğer PPK2, ST-Link veya BLE cihazı yoksa:

```python
# Sistem otomatik olarak simülasyon moduna geçer
# Tüm aşamalar simüle edilir
# Test akışını görebilirsiniz
```

### Gerçek Donanımla

1. **PPK2'yi bağlayın** (USB)
2. **ST-Link'i bağlayın** (SWD)
3. **Kamerayı bağlayın** (USB)
4. **Test soketini hazırlayın**
5. **Teste başlayın!**

## 🔍 İlk Sonuçlarınızı Görün

### İstatistikler
- Menü → Görünüm → İstatistikler
- Son testlerinizi görün
- Başarı oranını kontrol edin

### PDF Rapor
- Menü → Dosya → Rapor Oluştur
- Test raporu PDF olarak indirilir
- `reports/` klasöründe bulunur

### Loglar
- `logs/` klasörünü açın
- Tüm işlemler detaylı loglanmıştır
- Hata ayıklama için kullanılabilir

## ⚠️ Sık Karşılaşılan Sorunlar

### "PPK2 bulunamadı"
```
✅ Normal! Sistem simülasyon modunda devam eder
💡 Gerçek ölçüm için PPK2 bağlayın
```

### "MongoDB bağlanamadı"
```
✅ Normal! JSON yedekleme aktif
💡 MongoDB kurmak için: sudo apt install mongodb
```

### "Kamera açılamadı"
```
✅ Test devam eder
💡 USB kamerayı kontrol edin
💡 Başka uygulamanın kullanıp kullanmadığını kontrol edin
```

### "BLE cihaz bulunamadı"
```
✅ UUID simüle edilir
💡 Cihazın açık olduğundan emin olun
💡 Bluetooth'un aktif olduğunu kontrol edin
```

## 🎨 Özelleştirme

### Logo Ekleme

```bash
# Logo dosyanızı kopyalayın
cp /path/to/logo.png resources/hedra_logo.png
```

### Ses Dosyaları

```bash
# WAV dosyalarını ekleyin
cp *.wav sounds/
```

Gerekli sesler:
- `success.wav`
- `error.wav`
- `warning.wav`
- `complete.wav`

### Voltaj Değiştirme

`config/config.json`:
```json
{
  "hardware": {
    "ppk2_voltage": 3300  // 3.3V için
  }
}
```

## 📊 Test Verilerinizi Görüntüleme

### MongoDB ile

```bash
# MongoDB shell'i açın
mongo

# Veritabanını seçin
use stm32_test_db

# Son 5 testi göster
db.test_results.find().sort({start_time: -1}).limit(5)

# Başarılı testleri say
db.test_results.countDocuments({status: "completed"})
```

### JSON Dosyaları ile

```bash
# Yedek klasörünü kontrol edin
ls -lh backup/

# JSON dosyasını görüntüleyin
cat backup/test_XXXXX.json | python -m json.tool
```

## 🎯 İleri Seviye Kullanım

### Birden Fazla Test

```bash
# Test 1
ENTER → ... → Test Tamamla

# 5 saniye sonra otomatik yeni test hazır
ENTER → Test 2 başlar
```

### Toplu İstatistik

```python
# İstatistikler penceresinde:
# - Son 7 gün
# - Son 30 gün
# - Son 90 gün
seçeneklerini kullanın
```

### Export/Import

```bash
# PDF raporları toplu dışa aktarma
ls reports/*.pdf

# Yedekleri başka sisteme taşıma
tar -czf backups.tar.gz backup/
```

## 🆘 Yardım

### Loglara Bakın

```bash
# Son sistem logunu göster
tail -f logs/test_system_$(date +%Y%m%d).log

# Sadece hataları göster
tail -f logs/errors_$(date +%Y%m%d).log
```

### Debug Modu

`config/config.json`:
```json
{
  "logging": {
    "level": "DEBUG"  // Daha detaylı loglar
  }
}
```

## ✅ Kontrol Listesi

İlk çalıştırmadan önce:

- [ ] Python 3.8+ yüklü
- [ ] requirements.txt yüklendi
- [ ] config.json yapılandırıldı
- [ ] firmware/ klasöründe hex dosyası var
- [ ] Dizinler oluşturuldu (otomatik olur)
- [ ] Donanımlar bağlı (varsa)
- [ ] MongoDB çalışıyor (opsiyonel)

## 🎉 İlk Testinizi Tamamladınız!

Tebrikler! Artık:
- ✅ Temel test akışını biliyorsunuz
- ✅ Sonuçları görüntüleyebiliyorsunuz
- ✅ Raporlar oluşturabiliyorsunuz
- ✅ Ayarları özelleştirebiliyorsunuz

Detaylı bilgi için [README.md](README.md) dosyasına bakın.

---

**İyi Testler! 🚀**
