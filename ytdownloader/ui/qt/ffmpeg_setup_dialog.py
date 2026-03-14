# -*- coding: utf-8 -*-
"""FFmpeg otomatik kurulum dialog'u."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QWidget,
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QColor, QPainter, QPixmap, QPolygonF, QIcon
from PyQt6.QtCore import QPointF


class _Signals(QObject):
    progress = pyqtSignal(int, str)
    done     = pyqtSignal(bool, str)


class FFmpegSetupDialog(QDialog):
    """
    FFmpeg yoksa gösterilir.
    FFmpeg zorunludur — kurulmadan program çalışamaz.
    Kullanıcı 'Kur' derse indirip kurar, dialog kapatılırsa program çıkar.
    """

    def __init__(self, base_path, parent=None):
        super().__init__(parent)
        self._base_path = base_path
        self._signals = _Signals()
        self._signals.progress.connect(self._on_progress)
        self._signals.done.connect(self._on_done)
        self._installing = False

        self.setWindowTitle("FFmpeg Kurulumu")
        self.setFixedWidth(440)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowCloseButtonHint
        )
        self.setStyleSheet("""
            QDialog { background: #1a1d27; }
            QLabel  { color: #e8eaf0; }
        """)
        self._build_ui()

    def closeEvent(self, event):
        """Dialog kapatılırsa (X veya Esc) program çıkar."""
        if not self._installing:
            import sys
            sys.exit(0)
        event.ignore()  # Kurulum sırasında kapatmayı engelle

    def keyPressEvent(self, event):
        """Esc tuşunu devre dışı bırak."""
        from PyQt6.QtCore import Qt as _Qt
        if event.key() == _Qt.Key.Key_Escape:
            return
        super().keyPressEvent(event)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Başlık şeridi
        header = QWidget()
        header.setStyleSheet("background: #c0392b;")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(20, 14, 20, 14)

        # Küçük YouTube ikonu
        icon_lbl = QLabel()
        px = QPixmap(28, 28)
        px.fill(Qt.GlobalColor.transparent)
        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor("#ffffff"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, 28, 28, 5, 5)
        p.setBrush(QColor("#c0392b"))
        tri = QPolygonF([
            QPointF(10, 7), QPointF(10, 21), QPointF(22, 14)
        ])
        p.drawPolygon(tri)
        p.end()
        icon_lbl.setPixmap(px)
        h_lay.addWidget(icon_lbl)

        lbl_title = QLabel("  FFmpeg Gerekli")
        lbl_title.setStyleSheet("font-size:16px;font-weight:700;color:#ffffff;")
        h_lay.addWidget(lbl_title)
        h_lay.addStretch()
        root.addWidget(header)

        # İçerik
        body = QWidget()
        body.setStyleSheet("background: #1a1d27;")
        b_lay = QVBoxLayout(body)
        b_lay.setContentsMargins(24, 20, 24, 20)
        b_lay.setSpacing(12)

        lbl_desc = QLabel(
            "MP4 video indirme ve MP3 dönüştürme için\n"
            "<b>FFmpeg</b> gereklidir.\n\n"
            "Otomatik olarak indirip kurabilirsiniz (~80 MB).\n"
            "Kurulmadan program çalışamaz."
        )
        lbl_desc.setStyleSheet("font-size:13px;color:#9da3b4;line-height:1.6;")
        lbl_desc.setWordWrap(True)
        lbl_desc.setTextFormat(Qt.TextFormat.RichText)
        b_lay.addWidget(lbl_desc)

        # Progress (başta gizli)
        self._progress_widget = QWidget()
        p_lay = QVBoxLayout(self._progress_widget)
        p_lay.setContentsMargins(0, 0, 0, 0)
        p_lay.setSpacing(6)

        self._lbl_status = QLabel("Hazırlanıyor...")
        self._lbl_status.setStyleSheet("font-size:12px;color:#9da3b4;")
        p_lay.addWidget(self._lbl_status)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFixedHeight(8)
        self._progress.setTextVisible(False)
        self._progress.setStyleSheet("""
            QProgressBar { background: #2e3348; border-radius: 4px; border: none; }
            QProgressBar::chunk { background: #c0392b; border-radius: 4px; }
        """)
        p_lay.addWidget(self._progress)
        self._progress_widget.setVisible(False)
        b_lay.addWidget(self._progress_widget)

        root.addWidget(body)

        # Butonlar — sadece "Kur"
        btn_row = QWidget()
        btn_row.setStyleSheet("background: #12141f; border-top: 1px solid #2e3348;")
        br_lay = QHBoxLayout(btn_row)
        br_lay.setContentsMargins(20, 12, 20, 12)
        br_lay.setSpacing(10)
        br_lay.addStretch()

        self._btn_install = QPushButton("⬇  Kur")
        self._btn_install.setFixedSize(130, 36)
        self._btn_install.setStyleSheet("""
            QPushButton { background: #c0392b; border: none;
                border-radius: 7px; color: #ffffff;
                font-size: 13px; font-weight: 700; }
            QPushButton:hover { background: #a93226; }
            QPushButton:disabled { background: #3d4460; color: #6b7280; }
        """)
        self._btn_install.clicked.connect(self._start_install)
        br_lay.addWidget(self._btn_install)

        root.addWidget(btn_row)

    def _start_install(self):
        if self._installing:
            return
        self._installing = True
        self._btn_install.setEnabled(False)
        self._btn_install.setText("Kuruluyor...")
        self._progress_widget.setVisible(True)
        self.setFixedHeight(self.sizeHint().height())

        from ytdownloader.utils.ffmpeg_installer import download_and_install
        download_and_install(
            self._base_path,
            progress_callback=lambda p, m: self._signals.progress.emit(p, m),
            done_callback=lambda ok, msg: self._signals.done.emit(ok, msg),
        )

    def _on_progress(self, pct: int, msg: str):
        self._progress.setValue(pct)
        self._lbl_status.setText(msg)

    def _on_done(self, success: bool, msg: str):
        self._installing = False
        if success:
            self._lbl_status.setText("✓ FFmpeg başarıyla kuruldu!")
            self._progress.setValue(100)
            self._btn_install.setText("✓ Tamam")
            self._btn_install.setEnabled(True)
            self._btn_install.setStyleSheet("""
                QPushButton { background: #28a745; border: none;
                    border-radius: 7px; color: #ffffff;
                    font-size: 13px; font-weight: 700; }
                QPushButton:hover { background: #1e8035; }
            """)
            self._btn_install.clicked.disconnect()
            self._btn_install.clicked.connect(self.accept)
        else:
            self._lbl_status.setText(f"Hata: {msg[:60]}")
            self._btn_install.setText("Tekrar Dene")
            self._btn_install.setEnabled(True)
            self._installing = False
