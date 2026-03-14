# YouTube İndirici — Proje Notu
**Son Güncelleme:** 7 Mart 2026  
**Mevcut Versiyon:** v207  
**Dil:** Python + PyQt6  
**Platform:** Windows (EXE olarak dağıtılıyor)

---

## PROJE HEDEFİ

Tamamen Türkçe arayüzlü, YouTube videolarını MP4/MP3 olarak indirebilen,
lisanslı (yasal key sistemi ile satılacak) bir masaüstü uygulaması.

Temel özellikler:
- YouTube URL'den video/ses indirme
- Paralel (aynı anda 8 video) indirme
- MP3 ID3 tag + thumbnail gömme
- Koyu/Açık tema
- Windows toast bildirimleri
- FFmpeg otomatik kurulumu
- Drag & drop ile sıralama
- Lisans key sistemi (henüz geliştirilmedi — planlanan)

---

## DOSYA YAPISI

```
build/
├── main.py                          # Giriş noktası
├── build_exe.spec                   # PyInstaller build konfigürasyonu
├── BUILD.bat                        # EXE derleme script'i
├── Başlat.bat                       # Geliştirme ortamında çalıştırma
├── pyproject.toml                   # Bağımlılıklar
└── ytdownloader/
    ├── assets/
    │   ├── ffmpeg/                  # ffmpeg.exe, ffprobe.exe (boş — otomatik indirilir)
    │   └── icons/svg/               # Uygulama ikonları
    ├── config/
    │   ├── constants.py             # Sabit değerler
    │   └── defaults.py              # Varsayılan ayarlar
    ├── core/
    │   ├── download_engine.py       # yt-dlp wrapper, indirme motoru
    │   ├── download_manager.py      # Paralel indirme yöneticisi (8 thread)
    │   └── retry_engine.py         # Hata sonrası yeniden deneme
    ├── infrastructure/
    │   ├── event_bus.py             # Uygulama içi mesajlaşma
    │   ├── logger.py                # Log sistemi
    │   ├── settings_service.py      # JSON tabanlı ayar kaydetme
    │   └── state_manager.py         # Uygulama durumu
    ├── models/
    │   ├── download_item.py         # İndirme öğesi modeli
    │   └── download_state.py        # Durum enum'ları
    ├── services/
    │   ├── auth_service.py          # YouTube cookie/auth
    │   ├── i18n_service.py          # Dil desteği (TR)
    │   ├── sound_service.py         # Ses bildirimleri
    │   ├── toast_service.py         # Windows toast bildirimleri (kalıcı PS process)
    │   └── update_service.py        # Güncelleme kontrolü
    └── ui/qt/
        ├── main_window.py           # Ana pencere
        ├── video_card.py            # Her indirme öğesinin kartı
        ├── youtube_tab.py           # YouTube sekmesi (URL girişi vb.)
        ├── splash_screen.py         # Açılış ekranı + FFmpeg kurulum
        ├── theme.py                 # Koyu/Açık tema renk paleti
        ├── speed_graph.py           # İndirme hızı grafiği
        ├── dialogs.py               # Çeşitli dialog'lar
        ├── settings_dialog.py       # (main_window içine entegre)
        ├── playlist_dialog.py       # Playlist seçim dialog'u
        ├── history_dialog.py        # İndirme geçmişi
        ├── auth_dialog.py           # YouTube oturum açma
        ├── tray_icon.py             # Sistem tepsisi
        ├── notification.py          # Bildirim wrapper
        ├── icon_helper.py           # SVG ikon yükleyici
        └── ffmpeg_setup_dialog.py   # FFmpeg kurulum UI (artık splash'te)
```

---

## VERSİYON GEÇMİŞİ (Özet)

### v1 → v143 (28 Şubat 2026)
- Tkinter'dan PyQt6'ya tam geçiş
- YouTube kırmızı renk şeması
- Shorts desteği
- Kullanım kılavuzu dialog'u
- Açık/Koyu tema altyapısı
- EXE paketleme (PyInstaller)

### v144 → v151 (1 Mart 2026 sabah)
- Tema renk tutarlılığı (mavi → kırmızı)
- Ayarlar dialog buton stilleri
- Mouse lag düzeltme (thread safety)
- **FFmpeg otomatik kurulum** (GitHub'dan indirip kurar)

### v152 → v156
- FFmpeg EXE içine gömme
- Duplicate kod temizliği
- Mimari kod review

### v157 → v160
- 7 günlük deneme sistemi (Registry + AppData) — sonra kaldırıldı
- Üretim için temizlik

### v161 → v164
- Hakkında dialog (geliştirici bilgisi)
- Windows toast bildirimleri
- Splash screen optimizasyonu
- Ayarlar kalıcılığı düzeltmesi
- Playlist format seçimi
- Çift tıkla indirme kontrolü
- **FFmpeg zorunlu hale getirildi** (olmadan açılmaz)

### v165 → v169
- **FFmpeg paralel race indirme** (en hızlı FFmpeg'i bul)
- Hız limiti (KB/s)
- Toplam indirilen boyut göstergesi
- Yol kopyalama butonu
- **MP3 ID3 tag + thumbnail gömme**
- Bulk format menüsü kaldırıldı

### v170 → v175
- Açık temada buton görünürlüğü
- Boş durum ekranı yeniden tasarımı (SVG ikonlar)
- FFmpeg ilerleme sabitlendi
- Ayarlar dialog crash düzeltmesi
- Menü hover-to-open
- Çıkış dialog buton boyutları

### v176 → v182
- **Sıralı indirme modu** (kuyruk sistemi)
- **Drag & drop kart sıralama** (hayalet önizleme ile)
- Dialog metin görünürlüğü
- Drag state temizleme

### v183 → v187
- Çift border sorunu düzeltmesi
- Video kartı yeniden tasarımı (büyük thumbnail, styled butonlar)
- Modern sekme tasarımı (SVG ikonlar)
- Drag sırasında otomatik scroll
- Hakkında dialog tema entegrasyonu

### v188 → v190
- Ayarlar dialog tam tema yeniden yazımı
- Cookie menüsü ayarlar sekmesine taşındı
- Context menu yeniden tasarımı
- Dropdown stilleri düzeltmesi
- Tüm hardcoded renkler tema değişkenleriyle değiştirildi

### v191 → v197
- **Kalıcı PowerShell process** (toast_service.py) — bildirimler anında gelir
- AppUserModelID ile bildirim kimliği
- Theme-aware dropdown QPalette ile
- Ayarlar dialog temizliği
- %100 ilerleme anında bildirim

### v198 → v206
- **Tamamlanan kartlarda buton hover** (completed → butonlar gizli, hover'da görünür)
- **Sağ tık crash düzeltmesi** (QMenu parent=None, QWidgetAction)
- Açık temada buton görünürlüğü (inline stil, bg_elevated)
- **FFmpeg kurulumu splash screen'e taşındı** (ayrı dialog yok)
- İndirme sırasında butonlar her zaman görünür
- Speed graph butonları aşağı itmez (fixed height)
- Sağ tık menüsü temiz (emoji yok, Listeden Kaldır kırmızı)

### v207 (7 Mart 2026)
- **Python DLL hatası düzeltmesi** — başka PC'de "Failed to load Python DLL" hatası
- build_exe.spec: python3xx.dll + MSVC runtime DLL'leri otomatik pakete ekleniyor
- BUILD.bat: Build sonrası DLL'leri _internal klasörüne manuel kopyalama
- UPX kapatıldı (DLL'leri bozabiliyordu)

---

## MEVCUT SORUNLAR / YAPILACAKLAR

### Planlanan — Lisans Sistemi (Henüz Yapılmadı)
Tartışıldı, tasarlandı ama kodlanmadı:

**Hedef:** Her key sadece 1 PC'de çalışsın
**Yöntem:** Hibrit + Periyodik Online Doğrulama
**Mimari:**
```
İlk kurulum: Key + HWID → Sunucu → Onay → Şifreli token local'e yaz
Her açılışta: Sunucuya doğrulama (internet yoksa → açılmaz)
Heartbeat: Her 30dk sunucuya sinyal, ban gelirse kapat
```

**HWID Kaynakları:** MAC + Disk Seri No + Anakart UUID kombinasyonu

**Güvenlik Katmanları:**
1. Çoklu HWID bağlama
2. Online zorunluluk (internet yoksa açılmaz)
3. Sunucu anomali tespiti (farklı HWID → ban)
4. Şifreli local token (HWID ile AES)

**Altyapı İhtiyacı:** FastAPI + SQLite — aylık 5-10$ VPS

**Not:** HWID spoofing araçları mevcut, %100 kırılamaz sistem yok.
Ama teknik olmayan kullanıcılar için yeterince caydırıcı.

### Bilinen Küçük Sorunlar
- console=True build_exe.spec'te (debug için açık kaldı) → production'da False yapılmalı
- VM tespiti eklenmedi (lisans sistemi için önerilen)

---

## BUILD TALİMATI

```
1. BUILD.bat çalıştır
2. dist\YouTube Indirici\ klasörü oluşur
3. Bu klasörü ZIP'le ve dağıt
```

**Gereksinimler (build makinesi):**
- Python 3.11–3.13
- PyQt6, yt-dlp, mutagen, requests, certifi
- PyInstaller

**Son kullanıcı:** Python gerekmez, FFmpeg otomatik indirilir.

---

## ÖNEMLİ TEKNİK NOTLAR

### Toast Bildirimleri
`toast_service.py` — kalıcı PowerShell process'i pipe ile yönetir.
AppUserModelID: `YTDownloader.YouTubeIndirici.1.0`
Program açıkken servis başlar, kapanınca durur.

### FFmpeg
Splash screen'de otomatik kurulur → `ytdownloader/assets/ffmpeg/`
Yoksa program açılmaz.
Build'de EXE'ye gömülü.

### Tema Sistemi
`theme.py` → DARK / LIGHT palette
Tüm widget'lar `_apply_theme()` ile güncellenir.
`video_card.py` → `_apply_btn_styles()` inline stil (tema-aware).

### İndirme Motoru
`download_manager.py` → 8 paralel worker thread
`download_engine.py` → yt-dlp wrapper, format seçimi, hız limiti
`retry_engine.py` → otomatik yeniden deneme (3 kez)

---

## SOHBET GEÇMİŞİ DOSYALARI

Önceki oturumların tüm detayları şu transcript dosyalarında:
```
/mnt/transcripts/
├── 2026-02-28-00-39-42-session-continuation-attempt.txt
├── 2026-02-28-00-41-02-youtube-downloader-pyqt6-migration.txt
├── 2026-02-28-01-04-22-pyinstaller-exe-build-fix.txt
├── 2026-02-28-21-12-33-youtube-downloader-ui-improvements.txt
├── 2026-02-28-21-17-50-ytdownloader-v143-ui-improvements.txt
├── 2026-03-01-13-22-11-ytdownloader-v144-151-ui-fixes-ffmpeg-auto-install.txt
├── 2026-03-01-13-46-15-ytdownloader-v156-ffmpeg-code-review.txt
├── 2026-03-01-14-04-52-ytdownloader-v157-160-cleanup-trial.txt
├── 2026-03-01-14-17-23-ytdownloader-v161-164-ui-polish-ffmpeg-mandatory.txt
├── 2026-03-01-15-06-14-ytdownloader-v165-169-features-ffmpeg-race.txt
├── 2026-03-01-19-42-34-ytdownloader-v170-175-ui-polish.txt
├── 2026-03-01-20-08-00-ytdownloader-v176-182-sequential-drag-drop.txt
├── 2026-03-01-20-29-34-ytdownloader-v183-187-ui-polish-tabs-scroll.txt
├── 2026-03-01-20-46-16-ytdownloader-v188-190-settings-dialog-theme-fix.txt
├── 2026-03-01-21-02-03-ytdownloader-v191-197-toast-notifications-theme-fixes.txt
└── 2026-03-07-09-12-57-ytdownloader-v198-206-ui-fixes.txt
```

---

## YENİ SOHBET BAŞLATIRKEN CLAUDE'A VER

Bu dosyayı upload et ve şunu söyle:
> "Bu dosya projemizin notudur. v207 kodunu da upload ediyorum.
> [yapmak istediğin şeyi söyle]"

Kodun son hali: ytdownloader_207.zip
