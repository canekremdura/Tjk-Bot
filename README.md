# TJK Bot

TJK yarış sonuçları verilerini çeken Python botu.

## Özellikler

- Belirli bir tarihe göre TJK yarış sonuçları verilerini çeker
- Selenium ile veri çekme (requests kaldırıldı)
- Detaylı yarış ve at bilgilerini ayrıştırır
- Verileri JSON ve CSV formatlarında kaydeder
- Aylık veri saklama yapısı

## Kurulum

### Gereksinimler

- Python 3.6+
- pip
- Chrome/Chromium tarayıcı

### Kurulum Adımları

1. Repoyu klonlayın:
```bash
git clone <repo-url>
cd tjk-bot
```

2. Gerekli paketleri yükleyin:
```bash
pip install -r requirements.txt
```

3. Selenium için gerekli sürücüyü yükleyin:
```bash
pip install -r requirements-selenium.txt
```

## Kullanım

Botu çalıştırmak için:

```bash
python scraper.py
```

Bot sizden tarih bilgisi isteyecektir. GG/AA/YYYY formatında tarih girin (örnek: 23/08/2025).

Oluşturulan dosyalar:
- JSON formatında veri dosyası
- CSV formatında veri dosyası

## Gereksinimler

```bash
pip install beautifulsoup4 pandas lxml
```

Selenium kullanımı için (zorunlu):
```bash
pip install selenium undetected-chromedriver
```

## Lisans

Bu proje MIT Lisansı ile lisanslanmıştır - detaylar için [LICENSE](LICENSE) dosyasına bakınız.

## Katkı

Katkılarınızı memnuniyetle karşılıyoruz. Lütfen bir pull request oluşturun veya bir issue açın.
