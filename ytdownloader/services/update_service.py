# -*- coding: utf-8 -*-
"""UpdateService — GitHub Releases API üzerinden güncelleme kontrolü (PyQt6)."""

import threading
import webbrowser
import urllib.request
import json

from PyQt6.QtCore import QObject, pyqtSignal

from ytdownloader.config.constants import APP_VERSION, GITHUB_REPO
from ytdownloader.infrastructure.logger import get_logger

log = get_logger("update_service")


def _parse_version(version_str: str) -> tuple:
    """
    Sürüm dizisini karşılaştırılabilir int tuple'ına çevirir.
    "1.10.2" → (1, 10, 2)
    Ayrıştırılamayan parçalar 0 kabul edilir.
    Harici bağımlılık gerektirmez.
    """
    parts = []
    for part in version_str.strip().split("."):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(0)
    return tuple(parts)


class UpdateService(QObject):
    """
    Güncelleme kontrolü.

    Thread güvenliği:
        _check_worker() daemon thread'de ağ işlemi yapar.
        Sonuç iç sinyaller (_sig_*) üzerinden ana thread'e iletilir.
        QMessageBox ve diğer Qt widget'ları yalnızca ana thread'deki
        slot'larda (_on_*) oluşturulur — Qt thread kuralı korunur.
    """

    # İç sinyaller — yalnızca worker → ana thread köprüsü için.
    # object: parent widget (QWidget veya None)
    _sig_update_found = pyqtSignal(object, str, dict)   # parent, latest_version, release_info
    _sig_show_info    = pyqtSignal(object, str)          # parent, message

    CURRENT_VERSION = APP_VERSION

    def __init__(self, parent=None):
        super().__init__(parent)
        # connect() burada — __init__ her zaman ana thread'de çalışır.
        # Bu bağlantı sayesinde emit() hangi thread'den yapılırsa yapılsın
        # slot ana thread event loop'unda işlenir (Qt queued connection).
        self._sig_update_found.connect(self._on_update_found)
        self._sig_show_info.connect(self._on_show_info)

    # ── Public API ────────────────────────────────────────────────────────────

    def check(self, parent_widget=None, show_no_update: bool = False) -> None:
        """Güncelleme kontrolünü arka planda yapar."""
        if not GITHUB_REPO:
            if show_no_update:
                # check() her zaman ana thread'den çağrılır — dialog burada güvenli.
                self._show_no_repo(parent_widget)
            return
        threading.Thread(
            target=self._check_worker,
            args=(parent_widget, show_no_update),
            daemon=True,
        ).start()

    # ── Worker (daemon thread) ────────────────────────────────────────────────

    def _check_worker(self, parent, show_no_update: bool) -> None:
        """
        Yalnızca ağ işlemi yapar ve sinyal emit eder.
        Qt widget oluşturmaz — ana thread'e dokunmaz.
        """
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ytdownloader"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())
            latest = data.get("tag_name", "").lstrip("v")
            if latest and _parse_version(latest) > _parse_version(self.CURRENT_VERSION):
                # emit → slot (_on_update_found) ana thread'de çalışır
                self._sig_update_found.emit(parent, latest, data)
            elif show_no_update:
                self._sig_show_info.emit(
                    parent,
                    f"En son sürümü kullanıyorsunuz: v{self.CURRENT_VERSION}",
                )
        except Exception as e:
            log.warning(f"Güncelleme kontrolü başarısız: {e}")
            if show_no_update:
                self._sig_show_info.emit(parent, f"Güncelleme kontrolü yapılamadı:\n{e}")

    # ── Slot'lar — her zaman ana thread'de çalışır ───────────────────────────

    def _on_update_found(self, parent, latest_version: str, release_info: dict) -> None:
        """Güncelleme bulundu — dialog burada açılır, ana thread garantili."""
        from PyQt6.QtWidgets import QMessageBox
        msg = QMessageBox(parent)
        msg.setWindowTitle("Yeni Sürüm Mevcut")
        notes = release_info.get("body", "")[:400]
        msg.setText(f"<b>v{latest_version}</b> sürümü mevcut!\n\n{notes}")
        btn_dl = msg.addButton("İndir", QMessageBox.ButtonRole.AcceptRole)
        msg.addButton("Daha Sonra", QMessageBox.ButtonRole.RejectRole)
        msg.exec()
        if msg.clickedButton() == btn_dl:
            html_url = release_info.get("html_url", "")
            if html_url:
                webbrowser.open(html_url)

    def _on_show_info(self, parent, text: str) -> None:
        """Bilgi mesajı — ana thread garantili."""
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(parent, "Güncelleme Kontrolü", text)

    @staticmethod
    def _show_no_repo(parent) -> None:
        """check() ana thread'den çağrıldığı için bu da ana thread'de güvenli."""
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(parent, "Güncelleme", "GitHub repo yapılandırılmamış.")
