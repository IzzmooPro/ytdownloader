# -*- coding: utf-8 -*-
"""YtdlpUpdateService — yt-dlp güncellemesini arka planda yapar (PyQt6)."""

import threading

from PyQt6.QtCore import QObject, pyqtSignal

from ytdownloader.utils import ytdlp_updater


class YtdlpUpdateService(QObject):
    """
    Ağ işlemi daemon thread'de yapılır; sonuç `finished` sinyaliyle
    ana thread'e iletilir (Qt queued connection).

    finished(result: dict, manual: bool)
        result → ytdlp_updater.check_and_install() çıktısı
        manual → kullanıcı menüden mi başlattı (sessiz otomatik kontrol değil)
    """

    finished = pyqtSignal(dict, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    def check(self, manual: bool = False) -> bool:
        """Kontrolü başlatır. Zaten çalışıyorsa ya da otomatik kontrol
        zamanı gelmediyse False döner."""
        if self._running:
            return False
        if not manual and not ytdlp_updater.should_auto_check():
            return False
        self._running = True
        threading.Thread(target=self._worker, args=(manual,), daemon=True).start()
        return True

    def _worker(self, manual: bool) -> None:
        try:
            result = ytdlp_updater.check_and_install()
        except Exception as e:  # check_and_install zaten yakalar; son güvenlik
            result = {"status": "error", "error": str(e), "current": "?"}
        self._running = False
        self.finished.emit(result, manual)
