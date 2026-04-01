# -*- coding: utf-8 -*-
"""HistoryDialog — İndirme geçmişi penceresi."""

import os
import subprocess
import sys
from datetime import datetime

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QLineEdit, QComboBox, QMessageBox, QAbstractItemView, QMenu, QApplication,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QFont, QIcon

from ytdownloader.services.i18n_service import get_i18n


class HistoryDialog(QDialog):

    def __init__(self, parent, settings_manager, re_download_cb=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self._re_download_cb = re_download_cb
        self._i18n = get_i18n()
        self._all_entries: list[dict] = []

        self.setWindowTitle("İndirme Geçmişi")
        self.setMinimumSize(780, 500)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        self._build_ui()
        self._load_history()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # ── Üst bar: arama + filtre ──────────────────────────────────────
        top = QHBoxLayout()

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Video adı veya kanal ara...")
        self.search_box.setFixedHeight(34)
        self.search_box.setStyleSheet("""
            QLineEdit {
                background: #1a1d27; border: 1px solid #2e3348;
                border-radius: 7px; padding: 0 12px;
                color: #e8eaf0; font-size: 13px;
            }
            QLineEdit:focus { border-color: #c0392b; }
        """)
        self.search_box.textChanged.connect(self._apply_filter)
        top.addWidget(self.search_box, stretch=1)

        self.cmb_format = QComboBox()
        self.cmb_format.setFixedSize(110, 34)
        self.cmb_format.addItems(["Tüm Formatlar", "MP3", "MP4"])
        self.cmb_format.currentTextChanged.connect(self._apply_filter)
        top.addWidget(self.cmb_format)

        btn_clear_hist = QPushButton("Geçmişi Temizle")
        btn_clear_hist.setFixedHeight(34)
        btn_clear_hist.setStyleSheet("""
            QPushButton {
                background: transparent; border: 1px solid #3d1a1a;
                border-radius: 7px; color: #e05a5a; font-size: 12px; padding: 0 12px;
            }
            QPushButton:hover { background: #3d1a1a; }
        """)
        btn_clear_hist.clicked.connect(self._clear_history)
        top.addWidget(btn_clear_hist)

        root.addLayout(top)

        # ── Tablo ────────────────────────────────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Video", "Kanal", "Format", "Boyut", "Tarih"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 70)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 80)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setStyleSheet("""
            QTableWidget {
                background: #12141f; border: 1px solid #2e3348;
                border-radius: 8px; gridline-color: transparent;
                selection-background-color: #272c40;
            }
            QTableWidget::item { padding: 8px 10px; color: #e8eaf0; }
            QTableWidget::item:alternate { background: #161926; }
            QHeaderView::section {
                background: #1a1d27; color: #6b7280;
                font-size: 11px; font-weight: 700;
                letter-spacing: 0.8px; padding: 8px 10px;
                border: none; border-bottom: 1px solid #2e3348;
            }
        """)
        self.table.doubleClicked.connect(self._open_file_row)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_row_menu)
        root.addWidget(self.table)

        # ── Alt bar: sayaç + aç butonu ───────────────────────────────────
        bot = QHBoxLayout()

        self.lbl_count = QLabel()
        self.lbl_count.setStyleSheet("color: #6b7280; font-size: 12px;")
        bot.addWidget(self.lbl_count)
        bot.addStretch()

        btn_open = QPushButton("Dosyayı Göster")
        btn_open.setFixedHeight(34)
        btn_open.setToolTip("Seçili dosyayı klasörde göster")
        btn_open.clicked.connect(self._open_selected)
        bot.addWidget(btn_open)

        btn_close = QPushButton("Kapat")
        btn_close.setFixedHeight(34)
        btn_close.clicked.connect(self.accept)
        bot.addWidget(btn_close)

        root.addLayout(bot)

    def _load_history(self):
        self._all_entries = self.settings_manager.load_history()
        # En yeni üstte
        self._all_entries.sort(
            key=lambda e: e.get("download_time", ""), reverse=True
        )
        self._apply_filter()

    def _apply_filter(self):
        query  = self.search_box.text().lower()
        fmt    = self.cmb_format.currentText()

        filtered = []
        for e in self._all_entries:
            title   = (e.get("title", "") or "").lower()
            channel = (e.get("channel", "") or "").lower()
            e_fmt   = (e.get("format", "") or "").upper()

            if query and query not in title and query not in channel:
                continue
            if fmt != "Tüm Formatlar" and e_fmt != fmt:
                continue
            filtered.append(e)

        self._populate(filtered)

    def _populate(self, entries: list[dict]):
        self.table.setRowCount(len(entries))

        for row, e in enumerate(entries):
            title   = e.get("title", "—")
            channel = e.get("channel", "—")
            fmt     = (e.get("format", "—") or "—").upper()
            size    = self._fmt_size(e.get("size_bytes", 0))
            dt_raw  = e.get("download_time", "")
            dt      = self._fmt_date(dt_raw)
            fpath   = e.get("file", "") or e.get("file_path", "")

            items = [
                QTableWidgetItem(title),
                QTableWidgetItem(channel),
                QTableWidgetItem(fmt),
                QTableWidgetItem(size),
                QTableWidgetItem(dt),
            ]

            url = e.get("url", "")
            for col, item in enumerate(items):
                item.setData(Qt.ItemDataRole.UserRole, fpath)
                item.setData(Qt.ItemDataRole.UserRole + 1, url)
                if col == 2:  # format badge rengi
                    color = "#4a9eff" if fmt == "MP4" else "#28a745"
                    item.setForeground(QColor(color))
                    f = item.font(); f.setBold(True); item.setFont(f)
                self.table.setItem(row, col, item)

        for row in range(self.table.rowCount()):
            self.table.setRowHeight(row, 40)

        total = len(self._all_entries)
        shown = len(entries)
        if total == 0:
            self.lbl_count.setText("Henüz indirme kaydı yok")
        elif shown == 0:
            self.lbl_count.setText("Arama sonucu bulunamadı")
        elif shown == total:
            self.lbl_count.setText(f"{shown} indirme")
        else:
            self.lbl_count.setText(f"{shown} / {total} sonuç")

    def _open_file_row(self, index):
        item = self.table.item(index.row(), 0)
        if not item:
            return
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self._open_path(path)

    def _open_selected(self):
        rows = self.table.selectedItems()
        if not rows:
            return
        path = rows[0].data(Qt.ItemDataRole.UserRole)
        if path:
            self._open_path(path)

    @staticmethod
    def _open_path(path: str):
        if not path or not os.path.exists(path):
            QMessageBox.warning(None, "Dosya Bulunamadı",
                                f"Dosya artık mevcut değil:\n{path}")
            return
        if sys.platform == "win32":
            subprocess.Popen(f'explorer /select,"{path}"')
        elif sys.platform == "darwin":
            subprocess.run(["open", "-R", path])
        else:
            subprocess.run(["xdg-open", os.path.dirname(path)])

    def _show_row_menu(self, pos):
        """Sağ tık menüsü — seçili satır üzerinde işlem seçenekleri."""
        index = self.table.indexAt(pos)
        if not index.isValid():
            return
        row = index.row()
        item = self.table.item(row, 0)
        if not item:
            return
        fpath = item.data(Qt.ItemDataRole.UserRole)
        url   = item.data(Qt.ItemDataRole.UserRole + 1) or ""

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: #1a1d27; border: 1px solid #2e3348;
                    border-radius: 10px; padding: 5px 4px; font-size: 13px; }
            QMenu::item { padding: 7px 18px 7px 12px; color: #e8eaf0; border-radius: 5px; margin: 1px 4px; }
            QMenu::item:selected { background: #2e3348; }
        """)

        if fpath and os.path.exists(fpath):
            a = menu.addAction("Klasörde Göster")
            a.triggered.connect(lambda: self._open_path(fpath))
        if url and self._re_download_cb:
            a = menu.addAction("Yeniden İndir")
            a.triggered.connect(lambda: (self.accept(), self._re_download_cb(url)))
        if url:
            a = menu.addAction("URL'yi Kopyala")
            a.triggered.connect(lambda: QApplication.clipboard().setText(url))
        title_text = item.text()
        if title_text:
            a = menu.addAction("Başlığı Kopyala")
            a.triggered.connect(lambda: QApplication.clipboard().setText(title_text))

        if not menu.isEmpty():
            menu.exec(self.table.viewport().mapToGlobal(pos))

    def _clear_history(self):
        reply = QMessageBox.question(
            self, "Geçmişi Temizle",
            "Tüm indirme geçmişi silinecek. Emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                import json
                with open(self.settings_manager.history_file, "w", encoding="utf-8") as f:
                    json.dump([], f)
                self._all_entries.clear()
                self._populate([])
            except Exception as e:
                QMessageBox.warning(self, "Hata", str(e))

    @staticmethod
    def _fmt_size(b) -> str:
        try:
            b = float(b)
        except (TypeError, ValueError):
            return "—"
        if b <= 0:
            return "—"
        for unit in ("B", "KB", "MB", "GB"):
            if b < 1024:
                return f"{b:.1f} {unit}"
            b /= 1024
        return f"{b:.1f} TB"

    @staticmethod
    def _fmt_date(dt_str: str) -> str:
        try:
            dt = datetime.fromisoformat(dt_str)
            return dt.strftime("%d.%m.%Y %H:%M")
        except Exception:
            return dt_str[:16] if dt_str else "—"
