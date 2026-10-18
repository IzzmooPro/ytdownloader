# -*- coding: utf-8 -*-
"""
UpdateDialog — yeni sürüm bulunduğunda: İndir → (ilerleme) → Kur ve Yeniden Başlat.

EXE (frozen) dışında veya release'te kurulum dosyası yoksa eski davranış:
GitHub sürüm sayfası tarayıcıda açılır.
"""

import sys
import threading
import webbrowser

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout,
)

from ytdownloader.infrastructure.logger import get_logger
from ytdownloader.services.i18n_service import get_i18n
from ytdownloader.utils import app_updater

log = get_logger("update_dialog")


class UpdateDialog(QDialog):

    # worker thread → ana thread
    _sig_progress = pyqtSignal(int, int)
    _sig_done     = pyqtSignal(str)        # indirilen dosya yolu
    _sig_failed   = pyqtSignal(str)        # hata mesajı ("" = iptal)

    def __init__(self, parent, latest_version: str, current_version: str, release_info: dict):
        super().__init__(parent)
        self._t        = get_i18n().t
        self._version  = latest_version
        self._release  = release_info
        self._asset    = app_updater.pick_installer_asset(release_info)
        self._cancel   = threading.Event()
        self._file     = None
        self._worker   = None
        # Kaynak koddan çalışırken kurulum dosyası kurmak anlamsız — tarayıcıya yönlendir
        self._in_app   = bool(getattr(sys, "frozen", False) and self._asset)

        self._sig_progress.connect(self._on_progress)
        self._sig_done.connect(self._on_done)
        self._sig_failed.connect(self._on_failed)

        self._build(current_version)

    # ── UI ───────────────────────────────────────────────────────────────────

    def _build(self, current_version: str):
        from ytdownloader.ui.qt.theme import theme_manager
        p = theme_manager.palette
        t = self._t

        self.setWindowTitle(t("guncelleme_mevcut"))
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        self.setFixedWidth(400)
        self.setStyleSheet(f"""
            QDialog {{ background: {p.bg_elevated}; }}
            QLabel#title {{ color: {p.text_primary}; font-size: 15px; font-weight: 700; }}
            QLabel#sub   {{ color: {p.text_secondary}; font-size: 12px; }}
            QLabel#err   {{ color: {p.error}; font-size: 12px; }}
            QProgressBar {{
                background: {p.progress_bg}; border: none; border-radius: 4px;
                height: 8px; max-height: 8px;
            }}
            QProgressBar::chunk {{ background: {p.accent}; border-radius: 4px; }}
            QPushButton#primary {{
                background: {p.accent}; color: #ffffff; border: none; border-radius: 7px;
                font-size: 13px; font-weight: 600; padding: 0 18px; min-height: 36px;
            }}
            QPushButton#primary:hover {{ background: {p.accent_hover}; }}
            QPushButton#primary:disabled {{ background: {p.border}; color: {p.text_muted}; }}
            QPushButton#secondary {{
                background: transparent; color: {p.text_secondary};
                border: 1px solid {p.border}; border-radius: 7px;
                font-size: 13px; padding: 0 18px; min-height: 36px;
            }}
            QPushButton#secondary:hover {{ background: {p.bg_hover}; }}
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 20)
        lay.setSpacing(12)

        title = QLabel(t("yeni_surum", v=self._version))
        title.setObjectName("title")
        lay.addWidget(title)

        self._lbl_sub = QLabel(
            t("mevcut_surum", v=current_version) + "\n"
            + t("guncelleme_aciklama" if self._in_app else "guncelleme_tarayici")
        )
        self._lbl_sub.setObjectName("sub")
        self._lbl_sub.setWordWrap(True)
        lay.addWidget(self._lbl_sub)

        self._bar = QProgressBar()
        self._bar.setTextVisible(False)
        self._bar.setVisible(False)
        lay.addWidget(self._bar)

        self._lbl_err = QLabel("")
        self._lbl_err.setObjectName("err")
        self._lbl_err.setWordWrap(True)
        self._lbl_err.setVisible(False)
        lay.addWidget(self._lbl_err)

        row = QHBoxLayout()
        row.setSpacing(10)
        self._btn_secondary = QPushButton(t("daha_sonra"))
        self._btn_secondary.setObjectName("secondary")
        self._btn_secondary.clicked.connect(self._on_secondary)
        row.addWidget(self._btn_secondary)

        self._btn_primary = QPushButton(t("indir"))
        self._btn_primary.setObjectName("primary")
        self._btn_primary.clicked.connect(self._on_primary)
        row.addWidget(self._btn_primary)
        lay.addLayout(row)

        self._state = "ready"     # ready → downloading → downloaded | failed

    # ── Düğmeler ─────────────────────────────────────────────────────────────

    def _on_primary(self):
        if self._state in ("ready", "failed") and self._in_app:
            self._start_download()
        elif self._state == "downloaded":
            self._install()
        else:
            # Kaynak koddan çalışma / kurulum dosyası yok / hata sonrası
            url = self._release.get("html_url", "")
            if url:
                webbrowser.open(url)
            self.accept()

    def _on_secondary(self):
        if self._state == "downloading":
            self._cancel.set()
        self.reject()

    def reject(self):
        # Esc / pencere kapatma / "Daha Sonra": süren indirmeyi durdur
        self._cancel.set()
        super().reject()

    def closeEvent(self, event):
        self._cancel.set()
        super().closeEvent(event)

    # ── İndirme ──────────────────────────────────────────────────────────────

    def _start_download(self):
        self._state = "downloading"
        self._cancel.clear()
        self._lbl_err.setVisible(False)
        self._bar.setVisible(True)
        self._bar.setValue(0)
        self._btn_primary.setEnabled(False)
        self._btn_secondary.setText(self._t("iptal"))

        def work():
            try:
                path = app_updater.download_installer(
                    self._asset, self._version,
                    progress=lambda d, tot: self._sig_progress.emit(d, tot),
                    cancel=self._cancel,
                )
                self._sig_done.emit(str(path))
            except app_updater.UpdateCancelled:
                self._sig_failed.emit("")
            except Exception as e:
                log.error(f"Güncelleme indirilemedi: {e}")
                self._sig_failed.emit(str(e))

        self._worker = threading.Thread(target=work, daemon=True)
        self._worker.start()

    def _on_progress(self, done: int, total: int):
        if total > 0:
            self._bar.setMaximum(1000)
            self._bar.setValue(int(done * 1000 / total))
            self._lbl_sub.setText(self._t(
                "guncelleme_indiriliyor",
                done=f"{done / 1048576:.0f}", total=f"{total / 1048576:.0f}",
            ))
        else:
            self._bar.setMaximum(0)    # belirsiz

    def _on_done(self, path: str):
        from pathlib import Path
        self._file  = Path(path)
        self._state = "downloaded"
        self._bar.setMaximum(1000)
        self._bar.setValue(1000)
        self._lbl_sub.setText(self._t("guncelleme_hazir"))
        self._btn_primary.setText(self._t("kur_yeniden_baslat"))
        self._btn_primary.setEnabled(True)
        self._btn_secondary.setText(self._t("daha_sonra"))

    def _on_failed(self, message: str):
        if not message:          # kullanıcı iptal etti — pencere zaten kapanıyor
            return
        self._state = "failed"
        self._bar.setVisible(False)
        self._lbl_err.setText(self._t("guncelleme_hata", e=message))
        self._lbl_err.setVisible(True)
        self._btn_primary.setText(self._t("tekrar_dene"))
        self._btn_primary.setEnabled(True)
        self._btn_secondary.setText(self._t("kapat"))

    # ── Kurulum ──────────────────────────────────────────────────────────────

    def _install(self):
        """Kurulumu başlat (UAC burada, pencere öndeyken), sonra uygulamayı kapat."""
        if not app_updater.start_installer(self._file):
            self._lbl_err.setText(self._t("guncelleme_izin_yok"))
            self._lbl_err.setVisible(True)
            return
        self.accept()
        # Güncelleme "Hakkında" penceresinden açıldıysa o da açık — açık bir
        # pencere kalırsa uygulama kapanmaz. Hepsini kapat, sonra çık.
        for w in QApplication.topLevelWidgets():
            if isinstance(w, QDialog) and w is not self and w.isVisible():
                w.reject()
        QTimer.singleShot(0, _quit_app_for_update)


def _quit_app_for_update() -> None:
    window = next(
        (w for w in QApplication.topLevelWidgets() if hasattr(w, "quit_for_update")),
        None,
    )
    if window is None:
        QApplication.quit()
        return
    # Aktif indirme onayında "Hayır" denirse kurulum, süreç kapanmadığı için
    # bekleme süresi dolunca kendiliğinden vazgeçer (Youtube Setup.iss)
    if not window.quit_for_update():
        log.info("Güncelleme kurulumu kullanıcı tarafından ertelendi")
