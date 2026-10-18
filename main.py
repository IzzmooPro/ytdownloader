# -*- coding: utf-8 -*-
"""
YouTube İndirici — Giriş noktası (PyQt6)
"""

import sys
import os
from pathlib import Path

# EXE (frozen) modunda __file__ geçici temp klasörüne işaret eder.
# sys.executable her zaman gerçek EXE'nin bulunduğu kalıcı dizini verir.
if getattr(sys, "frozen", False):
    _root = Path(sys.executable).resolve().parent   # kurulu EXE'nin dizini
else:
    _root = Path(__file__).resolve().parent         # geliştirme ortamı
_base = _root / "ytdownloader"
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

# Log dizini
if os.name == "nt":
    _log_dir = Path(os.environ.get("APPDATA", _root)) / "MyYouTubeDownloader" / "logs"
else:
    _log_dir = Path.home() / ".my_youtube_downloader" / "logs"

from ytdownloader.infrastructure.logger import setup_logger, get_logger
setup_logger(_log_dir)
log = get_logger("main")

from ytdownloader.config.constants import APP_NAME, APP_VERSION

log.info("=" * 50)
log.info(f"YouTube Indirici {APP_VERSION} baslatiliyor")
log.info(f"Python: {sys.version.split()[0]}")
log.info(f"Root path: {_root}")
log.info(f"Log dizini: {_log_dir}")
log.info("=" * 50)

try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QFont
    log.debug("PyQt6 import OK")
except ImportError as e:
    log.error(f"PyQt6 bulunamadi: {e}")
    print("HATA: PyQt6 kurulu degil. 'pip install PyQt6' komutunu calistirin.")
    input("Devam etmek icin Enter'a basin...")
    sys.exit(1)

# İndirilmiş güncel yt-dlp varsa, yt_dlp ilk kez import edilmeden ÖNCE devreye al
try:
    from ytdownloader.utils.ytdlp_updater import activate_override
    activate_override()
except Exception as e:
    log.warning(f"yt-dlp güncellemesi etkinleştirilemedi: {e}")

log.debug("Uygulama modulleri import ediliyor...")
try:
    from ytdownloader.infrastructure.settings_service import SettingsService
    from ytdownloader.core.download_manager import DownloadManager
    from ytdownloader.utils.file_utils import is_ffmpeg_available
    from ytdownloader.ui.qt.main_window import MainWindow
    from ytdownloader.ui.qt.theme import theme_manager
    log.debug("Tum moduller basariyla import edildi")
except Exception as e:
    log.error(f"Modul import hatasi: {e}", exc_info=True)
    input("Devam etmek icin Enter'a basin...")
    sys.exit(1)


def _cleanup_leftovers() -> None:
    """Eski sürümlerden kalan gereksiz dosyalar (tek instance garanti edildikten sonra)."""
    import shutil
    from ytdownloader.utils.ffmpeg_installer import _get_install_dir, remove_leftovers
    freed = remove_leftovers(_get_install_dir(_root))
    if freed:
        log.info(f"Gereksiz FFmpeg dosyaları silindi ({freed / 1048576:.0f} MB)")
    # Kaldırılan YouTube sekmesinin (WebEngine) profil ve önbelleği
    for name in ("browser_profile", "browser_profile_cache"):
        d = _log_dir.parent / name
        if d.is_dir():
            shutil.rmtree(d, ignore_errors=True)
            log.info(f"Eski YouTube sekmesi verisi silindi: {d}")


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # Windows: tek instance kontrolü + AppUserModelID
    if sys.platform == "win32":
        try:
            import ctypes
            _mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "YTDownloader_SingleInstance_v1")
            if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
                # Sessizce ölme — çalışan pencereye "öne gel" işareti bırak.
                # MainWindow status timer'ı bu dosyayı görüp pencereyi öne getirir.
                try:
                    from ytdownloader.config.constants import SETTINGS_DIR_NAME
                    _flag_dir = Path(os.environ.get("APPDATA", str(_root))) / SETTINGS_DIR_NAME
                    _flag_dir.mkdir(parents=True, exist_ok=True)
                    (_flag_dir / "show_window.flag").touch()
                except Exception:
                    pass
                sys.exit(0)
        except Exception:
            pass
        try:
            import ctypes
            APP_ID = "YTDownloader.YouTubeIndirici.1.1"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setStyle("Fusion")

    font = QFont("Segoe UI", 10)
    app.setFont(font)

    import time as _time
    from ytdownloader.ui.qt.splash_screen import SplashScreen
    splash = SplashScreen()
    splash.show()
    app.processEvents()

    def _step(idx, wait=0.05):
        splash.advance(idx)
        _time.sleep(wait)
        app.processEvents()

    _step(1, 0.05)
    log.info("Ayarlar yukleniyor...")
    settings_manager = SettingsService(_base)
    settings = settings_manager.load()

    _step(2, 0.05)
    # "auto" → Windows koyu/açık ayarını takip eder (ThemeManager çözümler).
    # Kullanıcı elle tema seçtiyse ("dark"/"light") o tercih aynen uygulanır.
    saved_theme = settings.get("theme", "auto")
    theme_manager.set_theme(saved_theme)
    app.setStyleSheet(theme_manager.stylesheet())
    log.info(f"Tema: {theme_manager.current}")

    _step(3, 0.05)
    log.info("Download manager baslatiliyor...")
    download_manager = DownloadManager(settings_manager, _base)

    _step(4, 0.05)
    _cleanup_leftovers()
    _ffmpeg_ok = is_ffmpeg_available(_base)
    log.info("FFmpeg: " + ("MEVCUT" if _ffmpeg_ok else "YOK — arka planda kuruluyor"))

    # FFmpeg yoksa splash'ta sessizce kur — dialog yok
    if not _ffmpeg_ok:
        log.info("FFmpeg yok — splash'ta otomatik kurulum başlıyor")
        import threading
        from ytdownloader.utils.ffmpeg_installer import download_and_install

        _ffmpeg_done  = threading.Event()
        _ffmpeg_result = [False]

        def _on_progress(pct, msg):
            splash.set_status(pct, f"FFmpeg: {msg}")

        def _on_done(ok, msg):
            _ffmpeg_result[0] = ok
            _ffmpeg_done.set()

        download_and_install(_root, progress_callback=_on_progress, done_callback=_on_done)

        # Kurulum bitene kadar splash'ta bekle, UI donmasın
        while not _ffmpeg_done.wait(timeout=0.05):
            app.processEvents()

        _ffmpeg_ok = _ffmpeg_result[0]
        if _ffmpeg_ok:
            log.info("FFmpeg kuruldu, download manager güncelleniyor...")
        else:
            log.warning("FFmpeg kurulamadı — program kısıtlı çalışacak")
        splash.set_status(100, "Hazır!")

    _step(5, 0.05)
    log.info("Ana pencere olusturuluyor...")
    window = MainWindow(download_manager, settings_manager)

    _step(6, 0.05)
    log.info("Uygulama hazir")
    log.info("-" * 50)

    splash.finish(window)

    # FFmpeg kurulduysa download manager'ı güncelle
    if _ffmpeg_ok:
        download_manager.refresh_ffmpeg()

    exit_code = app.exec()

    # Worker thread'leri durdur — duraklatılmış (bloklu) indirme varsa
    # uyandırılmadan çıkılırsa non-daemon executor thread'leri kapanışı asar.
    try:
        download_manager.shutdown()
    except Exception:
        pass

    # Toast service'i temizle
    try:
        from ytdownloader.services.toast_service import shutdown as toast_shutdown
        toast_shutdown()
    except Exception:
        pass

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
