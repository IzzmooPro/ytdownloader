# -*- coding: utf-8 -*-
"""UpdateService — GitHub Releases API üzerinden güncelleme kontrolü (PyQt6)."""

import threading
import webbrowser
import urllib.request
import json

from ytdownloader.config.constants import APP_VERSION, GITHUB_REPO
from ytdownloader.infrastructure.logger import get_logger

log = get_logger("update_service")


class UpdateService:
    CURRENT_VERSION = APP_VERSION

    def check(self, parent_widget=None, show_no_update: bool = False) -> None:
        """Güncelleme kontrolünü arka planda yapar."""
        if not GITHUB_REPO:
            if show_no_update:
                self._show_no_repo(parent_widget)
            return
        threading.Thread(
            target=self._check_worker,
            args=(parent_widget, show_no_update),
            daemon=True,
        ).start()

    def _check_worker(self, parent, show_no_update: bool) -> None:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ytdownloader"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())
            latest = data.get("tag_name", "").lstrip("v")
            if latest and latest > self.CURRENT_VERSION:
                self._show_update_dialog(parent, latest, data)
            elif show_no_update:
                self._show_info(parent, f"En son sürümü kullanıyorsunuz: v{self.CURRENT_VERSION}")
        except Exception as e:
            log.warning(f"Güncelleme kontrolü başarısız: {e}")
            if show_no_update:
                self._show_info(parent, f"Güncelleme kontrolü yapılamadı:\n{e}")

    @staticmethod
    def _show_update_dialog(parent, latest_version: str, release_info: dict):
        from PyQt6.QtWidgets import QMessageBox, QPushButton
        msg = QMessageBox(parent)
        msg.setWindowTitle("Yeni Sürüm Mevcut")
        notes = release_info.get("body", "")[:400]
        msg.setText(f"<b>v{latest_version}</b> sürümü mevcut!\n\n{notes}")
        btn_dl = msg.addButton("İndir", QMessageBox.ButtonRole.AcceptRole)
        msg.addButton("Daha Sonra", QMessageBox.ButtonRole.RejectRole)
        msg.exec()
        if msg.clickedButton() == btn_dl:
            url = release_info.get("html_url", "")
            if url:
                webbrowser.open(url)

    @staticmethod
    def _show_info(parent, text: str):
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(parent, "Güncelleme Kontrolü", text)

    @staticmethod
    def _show_no_repo(parent):
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(parent, "Güncelleme", "GitHub repo yapılandırılmamış.")
