# -*- coding: utf-8 -*-
"""
Uygulama genelinde kullanılan değişmez sabitler.
Hiçbir şey import etmez — bağımlılık zincirinin en altı.
"""

APP_NAME = "YouTube İndirici"
APP_VERSION = "1.2.3"
APP_AUTHOR = "IzzmooPro"

# Ayar dizini adı (OS'a göre tam yol infrastructure/settings_service.py'de hesaplanır)
SETTINGS_DIR_NAME = "MyYouTubeDownloader"

# GitHub güncelleme kontrolü
GITHUB_REPO = "IzzmooPro/ytdownloader"
UPDATE_CHECK_DELAY_MS = 2000

# İndirme varsayılanları
DEFAULT_MAX_CONCURRENT = 0  # 0 = otomatik
AUTO_MAX_CONCURRENT    = 4  # "otomatik" seçildiğinde eşzamanlı indirme sayısı
MAX_CONCURRENT_LIMIT   = 5  # ayarlar ekranındaki üst sınır

# Thumbnail cache
THUMBNAIL_MEMORY_LIMIT = 50        # adet
THUMBNAIL_DISK_LIMIT_MB = 200

# Log
LOG_MAX_BYTES  = 10 * 1024 * 1024  # 10 MB
LOG_BACKUP_COUNT = 5

# Desteklenen YouTube domainleri
VALID_YT_DOMAINS = frozenset({
    "youtube.com", "www.youtube.com",
    "youtu.be", "www.youtu.be",
    "youtube-nocookie.com", "www.youtube-nocookie.com",
    "music.youtube.com",
    "m.youtube.com",            # telefondan paylaşılan linkler
})

# yt-dlp ortak HTTP başlıkları
DEFAULT_HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-us,en;q=0.5",
    "Sec-Fetch-Mode": "navigate",
}
