# -*- coding: utf-8 -*-
"""
AuthService — YouTube cookie yönetimi.

Strateji:
  1. Cookie dosyası zaten varsa direkt kullan
  2. Yoksa: tarayıcıyı geçici kapat → cookie al → tarayıcıyı tekrar aç
     Kullanıcı sadece "İzin Ver" der, geri kalanı otomatik.
"""

import os
import shutil
import tempfile
import subprocess
import time
from pathlib import Path
from ytdownloader.infrastructure.logger import get_logger

log = get_logger("auth_service")

BROWSERS = {
    "Microsoft Edge":  "edge",
    "Google Chrome":   "chrome",
    "Mozilla Firefox": "firefox",
    "Opera":           "opera",
    "Brave":           "brave",
    "Vivaldi":         "vivaldi",
}

# Windows process isimleri
_PROCESS_NAMES = {
    "edge":    "msedge.exe",
    "chrome":  "chrome.exe",
    "firefox": "firefox.exe",
    "opera":   "opera.exe",
    "brave":   "brave.exe",
    "vivaldi": "vivaldi.exe",
}

# Windows'ta tarayıcıların varsayılan açılış komutları
_BROWSER_EXES = {
    "edge":    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "chrome":  r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "firefox": r"C:\Program Files\Mozilla Firefox\firefox.exe",
    "opera":   os.path.expandvars(r"%LOCALAPPDATA%\Programs\Opera\opera.exe"),
    "brave":   r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    "vivaldi": os.path.expandvars(r"%LOCALAPPDATA%\Vivaldi\Application\vivaldi.exe"),
}


class AuthService:

    def __init__(self, settings_service):
        self._settings       = settings_service
        self._cookie_browser: str | None = None
        self._cookie_file:   str | None = None
        self._logged_in:     bool       = False
        self._username:      str        = ""

        saved = self._settings.get("cookie_browser")
        if saved:
            self._cookie_browser = saved
            saved_file = self._settings.get("cookie_file")
            if saved_file and Path(saved_file).exists():
                self._cookie_file = saved_file
                log.info(f"Kayıtlı cookie dosyası: {saved_file}")
            log.info(f"Kayıtlı cookie tarayıcısı: {saved}")

    # ── Tarayıcı tespiti ──────────────────────────────────────────────────────

    def get_available_browsers(self) -> list[str]:
        available = []
        user = os.environ.get("USERNAME", "")
        for name, key in BROWSERS.items():
            if self._is_browser_installed(key, user):
                available.append(name)
        return available

    def _is_browser_installed(self, key: str, user: str = "") -> bool:
        if os.name == "nt":
            exe = _BROWSER_EXES.get(key, "")
            if exe and os.path.exists(exe):
                return True
        for cmd in [key, key.replace(".", "")]:
            if shutil.which(cmd):
                return True
        return False

    # ── Process yönetimi ──────────────────────────────────────────────────────

    def _is_browser_running(self, browser_key: str) -> bool:
        """Tarayıcı process'i çalışıyor mu?"""
        proc = _PROCESS_NAMES.get(browser_key, "")
        if not proc:
            return False
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq {proc}", "/NH"],
                capture_output=True, text=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return proc.lower() in result.stdout.lower()
        except Exception:
            return False

    def _close_browser(self, browser_key: str) -> bool:
        """Tarayıcıyı kapat. True = başarılı."""
        proc = _PROCESS_NAMES.get(browser_key, "")
        if not proc:
            return False
        try:
            subprocess.run(
                ["taskkill", "/F", "/IM", proc, "/T"],
                capture_output=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            time.sleep(1.5)  # Process tam kapansın
            log.info(f"{proc} kapatıldı")
            return True
        except Exception as e:
            log.warning(f"Tarayıcı kapatma hatası: {e}")
            return False

    def _reopen_browser(self, browser_key: str):
        """Tarayıcıyı arka planda tekrar aç."""
        exe = _BROWSER_EXES.get(browser_key, "")
        if exe and os.path.exists(exe):
            try:
                subprocess.Popen(
                    [exe],
                    creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
                )
                log.info(f"{browser_key} yeniden açıldı")
            except Exception as e:
                log.warning(f"Tarayıcı açma hatası: {e}")

    # ── Cookie aktarımı ───────────────────────────────────────────────────────

    def set_cookie_browser(self, browser_name: str | None):
        if browser_name is None:
            self._cookie_browser = None
            self._cookie_file    = None
            self._settings.update("cookie_browser", None)
            self._settings.update("cookie_file", None)
            log.info("Cookie devre dışı")
        else:
            key = BROWSERS.get(browser_name)
            if key:
                self._cookie_browser = key
                self._settings.update("cookie_browser", key)
                log.info(f"Cookie tarayıcısı: {key}")

    def test_cookie_browser(self) -> tuple[bool, str]:
        """
        Cookie aktarımı. Eğer tarayıcı açıksa geçici kapatır,
        cookie'yi alır, sonra tekrar açar.
        """
        if not self._cookie_browser:
            return False, "Tarayıcı seçilmedi"

        appdata = os.environ.get("APPDATA", tempfile.gettempdir())
        cookie_dir  = Path(appdata) / "MyYouTubeDownloader"
        cookie_dir.mkdir(parents=True, exist_ok=True)
        cookie_path = cookie_dir / f"cookies_{self._cookie_browser}.txt"

        was_running = self._is_browser_running(self._cookie_browser)
        closed_ok   = False

        # Tarayıcı açıksa kapat
        if was_running:
            log.info(f"{self._cookie_browser} açık — geçici kapatılıyor...")
            closed_ok = self._close_browser(self._cookie_browser)
            if not closed_ok:
                log.warning("Tarayıcı kapatılamadı, yine de deneniyor...")

        # Cookie al
        ok, msg = self._do_extract(cookie_path)

        # Tarayıcıyı tekrar aç
        if was_running and closed_ok:
            self._reopen_browser(self._cookie_browser)

        if ok:
            self._cookie_file = str(cookie_path)
            self._settings.update("cookie_file", str(cookie_path))

        return ok, msg

    def _do_extract(self, cookie_path: Path) -> tuple[bool, str]:
        """Gerçek cookie extraction — console penceresi açmadan."""
        try:
            import yt_dlp

            # Windows'ta subprocess console penceresini gizle
            if os.name == "nt":
                import subprocess  # noqa: F401
                import ctypes
                try:
                    ctypes.windll.kernel32.SetConsoleWindowInfo  # noqa
                    os.environ.setdefault("PYTHONUTF8", "1")
                except Exception:
                    pass

            opts = {
                "quiet":              True,
                "no_warnings":        True,
                "cookiesfrombrowser": (self._cookie_browser, None, None, "basic"),
                "cookiefile":         str(cookie_path),
                "skip_download":      True,
                "extract_flat":       True,
                "ignoreerrors":       True,
                "noprogress":         True,
                # nocheckcertificate kaldırıldı — cookie extraction her zaman
                # doğrudan youtube.com'a bağlanır ve geçerli sertifikaya sahiptir.
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.extract_info(
                    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    download=False
                )

            if cookie_path.exists() and cookie_path.stat().st_size > 50:
                log.info(f"Cookie kaydedildi: {cookie_path} ({cookie_path.stat().st_size} byte)")
                return True, "Oturum başarıyla aktarıldı"

            return False, "Tarayıcınızda YouTube'a giriş yapılı değil. Önce tarayıcıda giriş yapın."

        except Exception as e:
            import re
            err = re.sub(r'\x1b\[[0-9;]*m', '', str(e))
            log.warning(f"Cookie extract hatası: {err[:100]}")

            if "not logged in" in err.lower():
                return False, "Tarayıcınızda YouTube'a giriş yapılı değil."
            if "Could not copy" in err or "database is locked" in err.lower():
                return False, "Cookie alınamadı. Lütfen tekrar deneyin."
            return False, "Cookie alınamadı. Tarayıcınızda YouTube'a giriş yapılı olduğundan emin olun."

    # ── yt-dlp parametreleri ──────────────────────────────────────────────────

    def get_ydl_cookie_opts(self) -> dict:
        if self._cookie_file and Path(self._cookie_file).exists():
            return {"cookiefile": self._cookie_file}
        if self._cookie_browser:
            return {"cookiesfrombrowser": (self._cookie_browser,)}
        return {}

    # ── Oturum durumu ─────────────────────────────────────────────────────────

    def set_logged_in(self, logged_in: bool, username: str = ""):
        self._logged_in = logged_in
        self._username  = username
        log.info(f"Oturum: {'açık' if logged_in else 'kapalı'} — {username}")

    @property
    def is_logged_in(self) -> bool:
        return self._logged_in

    @property
    def username(self) -> str:
        return self._username
