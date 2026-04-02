# -*- coding: utf-8 -*-
"""UpdateService — GitHub Releases API üzerinden güncelleme kontrolü (PyQt6)."""

import threading
import webbrowser
import urllib.request
import urllib.error
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
        except urllib.error.HTTPError as e:
            if e.code == 404:
                # Henüz hiç release yayınlanmamış — sessizce geç.
                log.debug("Güncelleme kontrolü: henüz release yok (404)")
                if show_no_update:
                    self._sig_show_info.emit(
                        parent,
                        f"En son sürümü kullanıyorsunuz: v{self.CURRENT_VERSION}",
                    )
            else:
                log.warning(f"Güncelleme kontrolü başarısız: {e}")
                if show_no_update:
                    self._sig_show_info.emit(parent, f"Güncelleme kontrolü yapılamadı:\n{e}")
        except Exception as e:
            log.warning(f"Güncelleme kontrolü başarısız: {e}")
            if show_no_update:
                self._sig_show_info.emit(parent, f"Güncelleme kontrolü yapılamadı:\n{e}")

    # ── Slot'lar — her zaman ana thread'de çalışır ───────────────────────────

    def _on_update_found(self, parent, latest_version: str, release_info: dict) -> None:
        """Güncelleme bulundu — dialog burada açılır, ana thread garantili."""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
        from PyQt6.QtCore import Qt
        from ytdownloader.ui.qt.theme import theme_manager

        p = theme_manager.palette
        html_url = release_info.get("html_url", "")

        dlg = QDialog(parent)
        dlg.setWindowTitle("Güncelleme Mevcut")
        dlg.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        dlg.setFixedWidth(360)
        dlg.setStyleSheet(f"""
            QDialog {{
                background: {p.bg_elevated};
                border: 1px solid {p.border};
                border-radius: 12px;
            }}
            QLabel#title {{
                color: {p.text_primary};
                font-size: 15px;
                font-weight: 700;
            }}
            QLabel#sub {{
                color: {p.text_secondary};
                font-size: 12px;
            }}
            QPushButton#btn_dl {{
                background: {p.accent};
                color: #ffffff;
                border: none;
                border-radius: 7px;
                font-size: 13px;
                font-weight: 600;
                padding: 0 20px;
                height: 36px;
                min-height: 36px;
            }}
            QPushButton#btn_dl:hover {{ background: {p.accent_hover}; }}
            QPushButton#btn_later {{
                background: transparent;
                color: {p.text_secondary};
                border: 1px solid {p.border};
                border-radius: 7px;
                font-size: 13px;
                padding: 0 20px;
                height: 36px;
                min-height: 36px;
            }}
            QPushButton#btn_later:hover {{ background: {p.bg_hover}; }}
        """)

        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(24, 24, 24, 20)
        lay.setSpacing(16)

        lbl_title = QLabel(f"Yeni sürüm: v{latest_version}")
        lbl_title.setObjectName("title")
        lay.addWidget(lbl_title)

        lbl_sub = QLabel(f"Mevcut sürümünüz: v{self.CURRENT_VERSION}\nGüncellemek için İndir'e tıklayın.")
        lbl_sub.setObjectName("sub")
        lbl_sub.setWordWrap(True)
        lay.addWidget(lbl_sub)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        btn_later = QPushButton("Daha Sonra")
        btn_later.setObjectName("btn_later")
        btn_later.setFixedHeight(36)
        btn_later.clicked.connect(dlg.reject)
        btn_row.addWidget(btn_later)

        btn_dl = QPushButton("İndir")
        btn_dl.setObjectName("btn_dl")
        btn_dl.setFixedHeight(36)
        btn_dl.clicked.connect(dlg.accept)
        btn_row.addWidget(btn_dl)

        lay.addLayout(btn_row)

        if dlg.exec() == QDialog.DialogCode.Accepted and html_url:
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
