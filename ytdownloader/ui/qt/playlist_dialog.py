# -*- coding: utf-8 -*-
"""PlaylistDialog — Playlist URL algılandığında video seçim penceresi."""

import threading
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QProgressBar, QCheckBox, QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal
from ytdownloader.infrastructure.logger import get_logger

log = get_logger("playlist_dialog")


class PlaylistDialog(QDialog):
    """Playlist videolarını listeler, kullanıcı hangilerini ekleyeceğini seçer."""

    _entries_signal = pyqtSignal(list)   # thread-safe
    _error_signal   = pyqtSignal(str)

    def __init__(self, parent, url: str, download_manager):
        super().__init__(parent)
        self.url = url
        self.download_manager = download_manager
        self.selected_urls: list[str] = []
        self.selected_format: str = "MP3"
        self.selected_quality: str = "320 kbps"

        self.setWindowTitle("Playlist Algılandı")
        self.setMinimumSize(600, 480)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)

        self._entries_signal.connect(self._populate)
        self._error_signal.connect(self._on_error)

        self._build_ui()
        self._fetch_playlist()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 16)
        root.setSpacing(12)

        # Başlık
        lbl = QLabel("Playlist yükleniyor...")
        lbl.setStyleSheet("font-size: 15px; font-weight: 600; color: #e8eaf0;")
        self.lbl_title = lbl
        root.addWidget(lbl)

        self.lbl_sub = QLabel("Video listesi alınıyor, lütfen bekleyin...")
        self.lbl_sub.setStyleSheet("font-size: 12px; color: #6b7280;")
        root.addWidget(self.lbl_sub)

        # Progress
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)   # belirsiz
        self.progress.setFixedHeight(4)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar { background: #2e3348; border-radius: 2px; }
            QProgressBar::chunk { background: #4a9eff; border-radius: 2px; }
        """)
        root.addWidget(self.progress)

        # Seç / Kaldır çubuğu
        sel_bar = QHBoxLayout()
        self.chk_all = QCheckBox("Tümünü Seç")
        self.chk_all.setStyleSheet("font-size:13px;color:#e8eaf0;")
        self.chk_all.stateChanged.connect(self._toggle_all)
        sel_bar.addWidget(self.chk_all)
        sel_bar.addStretch()
        self.lbl_sel = QLabel("")
        self.lbl_sel.setStyleSheet("font-size:12px;color:#6b7280;")
        sel_bar.addWidget(self.lbl_sel)
        root.addLayout(sel_bar)

        # Video listesi
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background: #12141f; border: 1px solid #2e3348;
                border-radius: 8px;
            }
            QListWidget::item {
                padding: 8px 12px; color: #e8eaf0;
                border-bottom: 1px solid #1e2030;
            }
            QListWidget::item:selected { background: #1e2d4a; }
            QListWidget::item:hover { background: #1a1d2e; }
        """)
        self.list_widget.itemChanged.connect(self._update_sel_label)
        root.addWidget(self.list_widget)

        # Ayırıcı
        line = QFrame(); line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background:#2e3348;max-height:1px;")
        root.addWidget(line)

        # Alt butonlar
        bot = QHBoxLayout()

        # Format seçici
        fmt_lbl = QLabel("Format:")
        fmt_lbl.setStyleSheet("font-size:12px;color:#9da3b4;")
        bot.addWidget(fmt_lbl)

        self.cmb_format = QComboBox()
        self.cmb_format.addItems(["MP3", "MP4"])
        self.cmb_format.setFixedWidth(80)
        self.cmb_format.setStyleSheet("""
            QComboBox{background:#1a1d27;border:1px solid #2e3348;border-radius:6px;
                color:#e8eaf0;padding:4px 8px;font-size:12px;}
            QComboBox::drop-down{border:none;}
            QComboBox QAbstractItemView{background:#1a1d27;color:#e8eaf0;border:1px solid #2e3348;}
        """)
        bot.addWidget(self.cmb_format)

        bot.addSpacing(8)

        # Kalite seçici
        qual_lbl = QLabel("Kalite:")
        qual_lbl.setStyleSheet("font-size:12px;color:#9da3b4;")
        bot.addWidget(qual_lbl)

        self.cmb_quality = QComboBox()
        self.cmb_quality.setFixedWidth(110)
        self.cmb_quality.setStyleSheet("""
            QComboBox{background:#1a1d27;border:1px solid #2e3348;border-radius:6px;
                color:#e8eaf0;padding:4px 8px;font-size:12px;}
            QComboBox::drop-down{border:none;}
            QComboBox QAbstractItemView{background:#1a1d27;color:#e8eaf0;border:1px solid #2e3348;}
        """)
        self.cmb_format.currentTextChanged.connect(self._update_quality_options)
        self._update_quality_options("MP3")
        bot.addWidget(self.cmb_quality)

        bot.addStretch()

        btn_cancel = QPushButton("İptal")
        btn_cancel.setFixedSize(100, 36)
        btn_cancel.setStyleSheet("""
            QPushButton{background:transparent;border:1px solid #2e3348;
                border-radius:7px;color:#9da3b4;}
            QPushButton:hover{background:#2e3348;color:#e8eaf0;}
        """)
        btn_cancel.clicked.connect(self.reject)
        bot.addWidget(btn_cancel)

        self.btn_add = QPushButton("Seçilenleri Ekle")
        self.btn_add.setFixedSize(140, 36)
        self.btn_add.setEnabled(False)
        self.btn_add.clicked.connect(self._accept_selected)
        bot.addWidget(self.btn_add)
        root.addLayout(bot)

    def _fetch_playlist(self):
        def worker():
            try:
                from yt_dlp import YoutubeDL
                opts = {
                    "quiet": True,
                    "no_warnings": True,
                    "extract_flat": True,   # sadece meta — hızlı
                    "noplaylist": False,
                }
                with YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(self.url, download=False)

                if not info:
                    self._error_signal.emit("Playlist bilgisi alınamadı.")
                    return

                entries = info.get("entries", [])
                if not entries:
                    self._error_signal.emit("Playlist boş veya erişilemiyor.")
                    return

                # Sadece gerekli alanları al
                result = []
                for e in entries:
                    if not e:
                        continue
                    vid_id = e.get("id", "")
                    result.append({
                        "title":    e.get("title", f"Video {len(result)+1}"),
                        "url":      f"https://www.youtube.com/watch?v={vid_id}" if vid_id else e.get("url",""),
                        "duration": e.get("duration", 0),
                        "channel":  e.get("channel") or e.get("uploader", ""),
                    })

                self._entries_signal.emit(result)
            except Exception as e:
                self._error_signal.emit(str(e))

        threading.Thread(target=worker, daemon=True).start()

    def _populate(self, entries: list[dict]):
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        self.progress.setVisible(False)

        playlist_title = f"Playlist — {len(entries)} video"
        self.lbl_title.setText(playlist_title)
        self.lbl_sub.setText("İndirmek istediğiniz videoları seçin:")

        self._entries = entries
        for e in entries:
            dur = self._fmt_dur(e.get("duration", 0))
            label = f"{e['title']}"
            if dur:
                label += f"  [{dur}]"
            item = QListWidgetItem(label)
            item.setCheckState(Qt.CheckState.Checked)
            item.setData(Qt.ItemDataRole.UserRole, e["url"])
            self.list_widget.addItem(item)

        self.chk_all.setChecked(True)
        self.btn_add.setEnabled(True)
        self._update_sel_label()

    def _on_error(self, msg: str):
        self.progress.setVisible(False)
        self.lbl_title.setText("Hata")
        self.lbl_sub.setText(msg)
        self.lbl_sub.setStyleSheet("color: #e05a5a; font-size: 12px;")

    def _toggle_all(self, state):
        check = Qt.CheckState.Checked if state == 2 else Qt.CheckState.Unchecked
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(check)

    def _update_sel_label(self):
        total   = self.list_widget.count()
        checked = sum(
            1 for i in range(total)
            if self.list_widget.item(i).checkState() == Qt.CheckState.Checked
        )
        self.lbl_sel.setText(f"{checked} / {total} seçili")
        self.btn_add.setEnabled(checked > 0)
        self.btn_add.setText(f"{checked} Video Ekle" if checked > 0 else "Seçilenleri Ekle")

    def _accept_selected(self):
        self.selected_urls = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                url = item.data(Qt.ItemDataRole.UserRole)
                if url:
                    self.selected_urls.append(url)
        self.selected_format  = self.cmb_format.currentText()
        self.selected_quality = self.cmb_quality.currentText()
        self.accept()

    def _update_quality_options(self, fmt: str):
        self.cmb_quality.clear()
        if fmt == "MP3":
            self.cmb_quality.addItems(["320 kbps", "192 kbps", "128 kbps"])
        else:
            self.cmb_quality.addItems(["En İyi Kalite", "1080p", "720p", "480p", "360p"])

    @staticmethod
    def _fmt_dur(secs) -> str:
        try:
            secs = int(secs)
            m, s = divmod(secs, 60)
            h, m = divmod(m, 60)
            return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
        except Exception:
            return ""
