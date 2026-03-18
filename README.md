# YouTube İndirici

Türkçe arayüzlü, YouTube videolarını MP4 ve MP3 olarak indirebilen Windows masaüstü uygulaması.

---

## Özellikler

- YouTube URL'den video (MP4) ve ses (MP3) indirme
- Aynı anda 8 paralel indirme desteği
- MP3 ID3 tag ve kapak resmi (thumbnail) gömme
- Koyu / Açık tema
- Windows toast bildirimleri
- FFmpeg otomatik kurulumu (internet bağlantısı ile)
- Drag & drop ile indirme sırası yönetimi
- İndirme hızı grafiği ve hız limiti
- Playlist desteği (seçili videolar)
- İndirme geçmişi
- Sistem tepsisi (tray) entegrasyonu

---

## Kurulum (Son Kullanıcı)

1. ZIP dosyasını istediğiniz bir klasöre çıkartın
2. `YouTube Indirici.exe` dosyasını çalıştırın
3. İlk açılışta FFmpeg otomatik olarak indirilip kurulur
4. Hazır — Python veya başka bir kurulum gerekmez

---

## Geliştirici Kurulumu

**Gereksinimler:**
- Python 3.11 – 3.13
- PyQt6, yt-dlp, mutagen, requests, certifi

**Kurulum:**
```bash
pip install pyqt6 yt-dlp mutagen requests certifi
```

**Çalıştırma:**
```bash
python main.py
```

---

## Teknik Yığın

| Katman | Teknoloji |
|---|---|
| Arayüz | PyQt6 |
| İndirme | yt-dlp |
| Ses işleme | FFmpeg, mutagen |
| Paketleme | PyInstaller |
| Platform | Windows 10/11 |

---

## Proje Yapısı

```
ytdownloader/
├── core/          # İndirme motoru ve thread yönetimi
├── infrastructure/# Ayarlar, log, event bus
├── models/        # Veri modelleri
├── services/      # Bildirim, güncelleme, ses servisleri
├── ui/qt/         # Tüm arayüz bileşenleri
└── assets/        # İkonlar ve FFmpeg
```

---

## Lisans

Bu yazılım özel mülkiyete aittir. İzinsiz dağıtım ve kullanım yasaktır.

---

# YouTube Downloader

A Turkish-interface Windows desktop application for downloading YouTube videos as MP4 or MP3.

## Features

- Download videos (MP4) and audio (MP3) from YouTube URLs
- Up to 8 simultaneous parallel downloads
- MP3 ID3 tag and thumbnail embedding
- Dark / Light theme
- Windows toast notifications
- Automatic FFmpeg installation
- Drag & drop queue management
- Download speed graph and speed limiter
- Playlist support
- Download history
- System tray integration

## Requirements

- Windows 10 / 11
- No Python required (standalone EXE)

## License

Proprietary software. Unauthorized distribution or use is prohibited.
