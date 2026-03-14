# -*- coding: utf-8 -*-
"""AuthDialog — Tarayıcıdan YouTube oturumu aktarma."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from ytdownloader.ui.qt.theme import theme_manager
from ytdownloader.ui.qt.icon_helper import make_icon


class _ImportThread(QThread):
    """Cookie aktarımını arka planda yapar — UI donmaz."""
    done = pyqtSignal(bool, str)   # (başarılı, mesaj)

    def __init__(self, auth_service, browser_name: str):
        super().__init__()
        self._auth = auth_service
        self._browser_name = browser_name

    def run(self):
        self._auth.set_cookie_browser(self._browser_name)
        ok, msg = self._auth.test_cookie_browser()
        self.done.emit(ok, msg)


class AuthDialog(QDialog):
    """
    Tarayıcı listeler → seç → aktar → sonuç göster.
    Başarılıysa dialog kapanır ve oturum aktif olur.
    """

    def __init__(self, parent, auth_service):
        super().__init__(parent)
        self._auth    = auth_service
        self._thread  = None
        self._success = False

        self.setWindowTitle("Oturum Yönetimi")
        self.setFixedWidth(400)
        self.setWindowFlags(
            self.windowFlags() &
            ~Qt.WindowType.WindowContextHelpButtonHint
        )
        self._build_ui()

    # ── UI ───────────────────────────────────────────────────────────────────

    def _build_ui(self):
        is_dark = theme_manager.current == "dark"
        self._is_dark = is_dark
        bg     = "#1a1d27" if is_dark else "#f0f2f7"
        border = "#2e3348" if is_dark else "#d0d5e0"
        txt    = "#e8eaf0" if is_dark else "#111827"
        sub    = "#9da3b4" if is_dark else "#6b7280"
        accent = "#4a9eff"

        self.setStyleSheet(f"QDialog {{ background: {bg}; }} QLabel {{ color: {txt}; }}")

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 20)
        root.setSpacing(12)

        # ── Başlık
        lbl_title = QLabel("Tarayıcıdan Oturum Al")
        lbl_title.setStyleSheet(f"font-size:16px;font-weight:700;color:{txt};")
        root.addWidget(lbl_title)

        lbl_desc = QLabel(
            "Tarayıcınızdaki YouTube oturumu aktarılacak.\n"
            "İşlem sırasında tarayıcı kısa süreliğine kapanıp tekrar açılacak."
        )
        lbl_desc.setStyleSheet(f"font-size:12px;color:{sub};line-height:1.5;")
        root.addWidget(lbl_desc)

        # ── Ayırıcı
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background:{border}; max-height:1px;")
        root.addWidget(sep)

        # ── Tarayıcı butonları
        browsers = self._auth.get_available_browsers()
        self._browser_btns: list[QPushButton] = []

        if browsers:
            lbl_pick = QLabel("Tarayıcınızı seçin:")
            lbl_pick.setStyleSheet(f"font-size:12px;color:{sub};")
            root.addWidget(lbl_pick)

            for name in browsers:
                btn = QPushButton(f"  {name}'den Al")
                btn.setFixedHeight(40)
                btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {'#1e2235' if is_dark else '#ffffff'};
                        border: 1px solid {border};
                        border-radius: 8px;
                        color: {txt};
                        font-size: 13px;
                        font-weight: 500;
                        text-align: left;
                        padding-left: 14px;
                    }}
                    QPushButton:hover {{
                        background: {'#252a3d' if is_dark else '#eef0f8'};
                        border-color: {accent};
                    }}
                    QPushButton:disabled {{
                        color: {sub};
                        border-color: {border};
                    }}
                """)
                btn.clicked.connect(lambda checked, n=name: self._on_import(n))
                root.addWidget(btn)
                self._browser_btns.append(btn)

            # Kayıtlı tarayıcı varsa vurgula
            saved = self._auth._cookie_browser
            if saved:
                from ytdownloader.services.auth_service import BROWSERS
                for btn in self._browser_btns:
                    bname = btn.text().strip().replace("'den Al", "").replace("'tan Al", "").replace("'ten Al", "").strip()
                    if BROWSERS.get(bname) == saved:
                        btn.setStyleSheet(btn.styleSheet() + f"""
                            QPushButton {{ border-color: {accent}; }}
                        """)
        else:
            lbl_no = QLabel(
                "⚠  Sistemde desteklenen tarayıcı bulunamadı.\n"
                "Edge, Chrome veya Firefox kurulu olmalı."
            )
            lbl_no.setStyleSheet(f"font-size:13px;color:#f0a500;padding:8px 0;")
            root.addWidget(lbl_no)

        # ── Durum satırı
        self._lbl_status = QLabel("")
        self._lbl_status.setWordWrap(True)
        self._lbl_status.setStyleSheet(f"font-size:12px;color:{sub};min-height:18px;")
        root.addWidget(self._lbl_status)

        # ── Alt buton
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(f"background:{border}; max-height:1px;")
        root.addWidget(sep2)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        # Oturumu kapat butonu — sadece aktif oturum varsa
        if self._auth._cookie_browser:
            btn_clear = QPushButton("Oturumu Kapat")
            btn_clear.setFixedHeight(34)
            btn_clear.setStyleSheet(f"""
                QPushButton {{ background: transparent; border: 1px solid #e05a5a;
                    border-radius: 7px; color: #e05a5a; font-size: 12px; padding: 0 12px; }}
                QPushButton:hover {{ background: #3a1a1a; }}
            """)
            btn_clear.clicked.connect(self._on_clear)
            btn_row.addWidget(btn_clear)
            btn_row.addSpacing(8)

        self._btn_close = QPushButton("Kapat")
        self._btn_close.setFixedSize(80, 34)
        self._btn_close.setStyleSheet(f"""
            QPushButton {{ background: {accent}; border: none;
                border-radius: 7px; color: #fff; font-size: 13px; font-weight: 600; }}
            QPushButton:hover {{ background: #3a8eef; }}
        """)
        self._btn_close.clicked.connect(self.accept)
        btn_row.addWidget(self._btn_close)
        root.addLayout(btn_row)

    # ── Eylemler ─────────────────────────────────────────────────────────────

    def _set_buttons_enabled(self, enabled: bool):
        for btn in self._browser_btns:
            btn.setEnabled(enabled)
        self._btn_close.setEnabled(enabled)

    def _on_import(self, browser_name: str):
        self._set_buttons_enabled(False)
        self._lbl_status.setText(f"⏳  {browser_name} geçici kapatılıyor ve oturum aktarılıyor...")
        self._lbl_status.setStyleSheet("font-size:12px;color:#f0a500;")

        self._thread = _ImportThread(self._auth, browser_name)
        self._thread.done.connect(self._on_import_done)
        self._thread.start()

    @staticmethod
    def _strip_ansi(text: str) -> str:
        import re
        return re.sub(r'\x1b\[[0-9;]*m', '', text).strip()

    def _on_import_done(self, ok: bool, msg: str):
        msg = self._strip_ansi(msg)
        self._set_buttons_enabled(True)
        if ok:
            self._lbl_status.setText(f"✓  Oturum başarıyla aktarıldı.")
            self._lbl_status.setStyleSheet("font-size:12px;color:#28a745;font-weight:600;")
            self._success = True
            # 1.2 saniye sonra dialog kapansın
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(1200, self.accept)
        else:
            self._lbl_status.setText(f"✗  {msg}\nTarayıcınızda YouTube'a giriş yapıp tekrar deneyin.")
            self._lbl_status.setStyleSheet("font-size:12px;color:#e05a5a;")

    def _on_clear(self):
        self._auth.set_cookie_browser(None)
        self._auth.set_logged_in(False)
        self.accept()

    @property
    def success(self) -> bool:
        return self._success
