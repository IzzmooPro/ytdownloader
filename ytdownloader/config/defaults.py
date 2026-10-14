# -*- coding: utf-8 -*-
"""
Varsayılan uygulama ayarları.
SettingsService bunu temel referans olarak kullanır.
"""

DEFAULT_SETTINGS: dict = {
    "version":                 1,
    "language":                "tr",
    # "auto" = Windows'un koyu/açık ayarını takip et. Kullanıcı temayı elle
    # değiştirirse "dark"/"light" olarak kaydedilir ve artık o hatırlanır.
    "theme":                   "auto",

    # İndirme
    "last_download_folder":    None,
    "default_format":          "MP3",
    "default_quality":         "320 kbps",
    "max_concurrent":          0,          # 0 = otomatik (AUTO_MAX_CONCURRENT)
    "sequential_mode":         False,      # True = sıralı indirme
    "speed_limit_enabled":     False,
    "speed_limit_mbps":        5,          # MB/s

    # Bildirim & Ses
    "notify_complete":         True,
    "notify_error":            True,
    "sound_enabled":           True,

    # Davranış
    "open_folder_on_complete": False,
    "start_minimized":         False,
    "confirm_exit":            True,
    "minimize_to_tray":        True,
    "auto_close_completed":    False,

    # Güncelleme
    "check_for_updates":       True,
}
