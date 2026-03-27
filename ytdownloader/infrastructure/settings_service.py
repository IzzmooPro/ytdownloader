# -*- coding: utf-8 -*-
"""
SettingsService — uygulama ayarlarını yönetir.

Faz 0: Orijinal SettingsManager davranışı korundu, sadece doğru
        modüle taşındı ve import'lar güncellendi.
Faz 1'de: şema doğrulama + migration eklenecek.
"""

import os
import json
import threading
from datetime import datetime
from pathlib import Path

from ytdownloader.config.constants import SETTINGS_DIR_NAME
from ytdownloader.config.defaults import DEFAULT_SETTINGS
from ytdownloader.infrastructure.logger import get_logger

log = get_logger("settings_service")


class SettingsService:
    """
    Ayarları diskten okur / diske yazar.
    Thumbnail cache ve indirme geçmişi yollarını da yönetir.
    """

    def __init__(self, base_path: str | Path):
        self.base_path = Path(base_path)

        # Platform bağımsız ayar dizini
        if os.name == "nt":
            appdata = os.getenv("APPDATA")
            root_dir = Path(appdata) if appdata else Path.home()
        else:
            root_dir = Path.home()

        self.settings_dir = root_dir / SETTINGS_DIR_NAME
        self.thumbnail_cache_dir = self.settings_dir / "thumbnail_cache"
        self.history_dir = self.settings_dir / "history"

        for d in (self.settings_dir, self.thumbnail_cache_dir, self.history_dir):
            d.mkdir(parents=True, exist_ok=True)

        self.settings_file = self.settings_dir / "settings.json"
        self.history_file  = self.history_dir  / "download_history.json"

        # Worker thread'lerden eş zamanlı update() çağrılarını korur
        self._settings_lock = threading.Lock()
        # Birden fazla indirme aynı anda tamamlandığında geçmiş dosyasını
        # bozulmaktan korur (worker thread'lerden eş zamanlı çağrı)
        self._history_lock = threading.Lock()

    # ── Ayarlar ────────────────────────────────────────────

    def load(self) -> dict:
        """Ayarları diskten okur. Bozuk / eksik dosyada default döner."""
        if self.settings_file.exists():
            try:
                with self.settings_file.open("r", encoding="utf-8") as f:
                    settings = json.load(f)
                # Yeni eklenen alanları doldur
                for key, value in DEFAULT_SETTINGS.items():
                    if key not in settings:
                        settings[key] = value
                return settings  # type: ignore[no-any-return]
            except Exception as e:
                log.error(f"Ayarlar yüklenemedi: {e}")
        return DEFAULT_SETTINGS.copy()

    def save(self, settings: dict) -> bool:
        """
        Ayarları diske yazar. Başarı durumunu döner.

        Atomic write: önce geçici dosyaya yazar, ardından os.replace() ile
        hedef konuma taşır. Yazma ortasında çökme/kesinti olursa mevcut
        settings.json bozulmadan kalır.
        """
        tmp_file = self.settings_file.with_suffix(".json.tmp")
        try:
            with tmp_file.open("w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)
            # os.replace: POSIX'te atomik, Windows'ta mümkün olan en güvenli yöntem.
            os.replace(tmp_file, self.settings_file)
            return True
        except Exception as e:
            log.error(f"Ayarlar kaydedilemedi: {e}")
            # Geçici dosya kaldıysa temizle — hedef dosyaya dokunma.
            try:
                if tmp_file.exists():
                    tmp_file.unlink()
            except Exception:
                pass
            return False

    def update(self, key: str, value) -> bool:
        """
        Tek bir ayarı günceller. Nokta notasyonu desteklenir.
        Örnek: update("shortcuts.paste_address", "<Control-v>")
        """
        with self._settings_lock:
            settings = self.load()
            if "." in key:
                parts = key.split(".")
                current = settings
                for part in parts[:-1]:
                    current = current.setdefault(part, {})
                current[parts[-1]] = value
            else:
                settings[key] = value
            return self.save(settings)

    def get(self, key: str, default=None):
        """
        Tek bir ayarı okur. Nokta notasyonu desteklenir.
        Örnek: get("shortcuts.paste_address")
        """
        settings = self.load()
        if "." in key:
            parts = key.split(".")
            current = settings
            for part in parts:
                if not isinstance(current, dict) or part not in current:
                    return default
                current = current[part]
            return current
        return settings.get(key, default)

    # ── İndirme Geçmişi ───────────────────────────────────

    def save_history_entry(self, video_info: dict) -> bool:
        """İndirme geçmişine yeni kayıt ekler. Thread-safe, atomic write."""
        with self._history_lock:
            tmp_file = self.history_file.with_suffix(".json.tmp")
            try:
                history = self._load_history_unlocked()
                entry = dict(video_info)
                entry["download_time"] = datetime.now().isoformat()
                history.append(entry)
                with tmp_file.open("w", encoding="utf-8") as f:
                    json.dump(history, f, ensure_ascii=False, indent=4)
                os.replace(tmp_file, self.history_file)
                return True
            except Exception as e:
                log.warning(f"Geçmiş kaydedilemedi: {e}")
                try:
                    if tmp_file.exists():
                        tmp_file.unlink()
                except Exception:
                    pass
                return False

    def load_history(self) -> list[dict]:
        """Tüm indirme geçmişini döner. Hata durumunda boş liste."""
        with self._history_lock:
            return self._load_history_unlocked()

    def _load_history_unlocked(self) -> list[dict]:
        """Lock alınmış bağlamda çağrılır — doğrudan kullanma."""
        try:
            if self.history_file.exists():
                with self.history_file.open("r", encoding="utf-8") as f:
                    return json.load(f)  # type: ignore[no-any-return]
        except Exception as e:
            log.warning(f"Geçmiş yüklenemedi: {e}")
        return []

    # ── Thumbnail Cache ────────────────────────────────────

    def get_thumbnail_cache_path(self, video_id: str) -> Path:
        """Belirtilen video ID için cache dosya yolunu döner."""
        return self.thumbnail_cache_dir / f"{video_id}.jpg"


# ---------------------------------------------------------------------------
# Geriye dönük uyumluluk — eski adla kullanan kod için alias
# Faz 1'de kaldırılacak
# ---------------------------------------------------------------------------
SettingsManager = SettingsService
