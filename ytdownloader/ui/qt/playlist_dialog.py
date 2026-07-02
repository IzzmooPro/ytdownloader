# -*- coding: utf-8 -*-
"""PlaylistDialog — Playlist / Mix URL algılandığında video seçim penceresi."""

import threading
import urllib.parse as _up

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QProgressBar, QFrame,
    QComboBox, QLineEdit,
)
from PyQt6.QtCore import Qt, pyqtSignal
from ytdownloader.infrastructure.logger import get_logger

log = get_logger("playlist_dialog")

# Mix/Radyo listesi önekleri (YouTube otomatik üretimi)
_MIX_PREFIXES = ("RD", "RL", "TL", "LL", "FL", "WL")

# Mix için varsayılan öğe limiti
_MIX_DEFAULT_LIMIT = 30


class PlaylistDialog(QDialog):
    """Playlist / Mix videolarını listeler; arama, toplu seçim ve indirme desteği."""

    _entries_signal = pyqtSignal(list)
    _error_signal   = pyqtSignal(str)

    def __init__(self, parent, url: str, download_manager):
        super().__init__(parent)
        self.url              = url
        self.download_manager = download_manager
        self.selected_urls:    list[str] = []
        self.selected_format:  str = "MP3"
        self.selected_quality: str = "320 kbps"
        self._all_entries:     list[dict] = []  # tam liste — filtreden bağımsız

        # URL'den tür tespiti
        _list_id = (_up.parse_qs(_up.urlparse(url).query).get("list") or [""])[0]
        self._kind = "mix" if _list_id.startswith(_MIX_PREFIXES) else "playlist"

        # Mix için ilk yükleme sınırlı başlar; "Tam Mix'i Yükle" sonrası False olur
        self._mix_limited = (self._kind == "mix")

        title_word = "Mix" if self._kind == "mix" else "Playlist"
        self.setWindowTitle(f"{title_word} — Video Seç")
        self.setMinimumSize(640, 540)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)

        self._entries_signal.connect(self._populate)
        self._error_signal.connect(self._on_error)

        self._build_ui()
        # Mix: ilk yüklemede sadece ilk 30 öğeyi çek
        limit = _MIX_DEFAULT_LIMIT if self._mix_limited else None
        self._fetch_playlist(limit=limit)

    # ── UI Kurulumu ───────────────────────────────────────────────────────────

    def _build_ui(self):
        # Tema paleti — dialog her açılışta güncel temayla kurulur
        from ytdownloader.ui.qt.theme import theme_manager
        p = theme_manager.palette

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 16)
        root.setSpacing(10)

        # Başlık
        self.lbl_title = QLabel("Yükleniyor...")
        self.lbl_title.setStyleSheet(f"font-size:15px;font-weight:600;color:{p.text_primary};")
        root.addWidget(self.lbl_title)

        self.lbl_sub = QLabel("Video listesi alınıyor, lütfen bekleyin...")
        self.lbl_sub.setStyleSheet(f"font-size:12px;color:{p.text_secondary};")
        root.addWidget(self.lbl_sub)

        # İlerleme çubuğu
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setFixedHeight(4)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(f"""
            QProgressBar {{ background: {p.progress_bg}; border-radius: 2px; }}
            QProgressBar::chunk {{ background: {p.accent}; border-radius: 2px; }}
        """)
        root.addWidget(self.progress)

        # ── Mix bilgi banner'ı (yalnızca mix + sınırlı mod) ─────────────────
        self._mix_banner = QFrame()
        self._mix_banner.setObjectName("mix_banner")
        self._mix_banner.setVisible(False)
        self._mix_banner.setStyleSheet(
            f"QFrame#mix_banner {{ background: {p.bg_surface}; "
            f"border: 1px solid {p.border}; border-radius: 8px; }}"
        )
        mix_lay = QHBoxLayout(self._mix_banner)
        mix_lay.setContentsMargins(12, 6, 8, 6)
        mix_lay.setSpacing(10)

        self._lbl_mix_info = QLabel(
            f"YouTube Mix listeleri dinamik olabilir. "
            f"Başlangıç için ilk {_MIX_DEFAULT_LIMIT} öğe gösteriliyor."
        )
        self._lbl_mix_info.setStyleSheet(
            f"color:{p.text_secondary};font-size:11px;background:transparent;border:none;"
        )
        self._lbl_mix_info.setWordWrap(False)
        mix_lay.addWidget(self._lbl_mix_info, stretch=1)

        self._btn_load_full = QPushButton("Tam Mix'i Yükle")
        self._btn_load_full.setFixedHeight(26)
        self._btn_load_full.clicked.connect(self._load_full_mix)
        mix_lay.addWidget(self._btn_load_full)

        root.addWidget(self._mix_banner)

        # ── Arama kutusu — global QLineEdit stili tema uyumlu, inline stil yok ──
        self._search = QLineEdit()
        self._search.setPlaceholderText("Başlık veya kanal adında ara...")
        self._search.setFixedHeight(32)
        self._search.setVisible(False)  # veriler gelince açılır
        self._search.textChanged.connect(self._on_search_changed)
        root.addWidget(self._search)

        # ── Toplu seçim araç çubuğu ───────────────────────────────────────────
        sel_bar = QHBoxLayout()
        sel_bar.setSpacing(6)

        self.btn_sel_all   = QPushButton("Tümünü Seç")
        self.btn_desel_all = QPushButton("Tüm Seçimleri Kaldır")

        for btn in (self.btn_sel_all, self.btn_desel_all):
            btn.setEnabled(False)
            sel_bar.addWidget(btn)

        self.btn_sel_all.clicked.connect(
            lambda: self._bulk_check(True,  visible_only=False))
        self.btn_desel_all.clicked.connect(
            lambda: self._bulk_check(False, visible_only=False))

        sel_bar.addStretch()
        self.lbl_sel = QLabel("")
        self.lbl_sel.setStyleSheet(f"font-size:12px;color:{p.text_muted};")
        sel_bar.addWidget(self.lbl_sel)
        root.addLayout(sel_bar)

        # ── Video listesi — tema uyumlu satırlar + onay kutuları ─────────────
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: {p.bg_base};
                border: 1px solid {p.border};
                border-radius: 8px;
                outline: none;
            }}
            QListWidget::item {{
                padding: 8px 10px;
                color: {p.text_primary};
                background-color: {p.bg_base};
                border-bottom: 1px solid {p.bg_hover};
            }}
            QListWidget::item:hover {{
                background-color: {p.bg_surface};
            }}
            QListWidget::item:selected {{
                background-color: {p.bg_elevated};
                color: {p.text_primary};
            }}
            QListWidget::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1.5px solid {p.border};
                background: {p.bg_surface};
            }}
            QListWidget::indicator:checked {{
                background-color: {p.accent};
                border-color: {p.accent};
            }}
        """)
        self.list_widget.itemChanged.connect(self._update_sel_label)
        root.addWidget(self.list_widget)

        # ── Alt çubuk ─────────────────────────────────────────────────────────
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"background:{p.border};max-height:1px;")
        root.addWidget(line)

        bot = QHBoxLayout()
        bot.setSpacing(8)

        fmt_lbl = QLabel("Format:")
        fmt_lbl.setStyleSheet(f"font-size:12px;color:{p.text_secondary};")
        bot.addWidget(fmt_lbl)

        self.cmb_format = QComboBox()
        self.cmb_format.addItems(["MP3", "MP4"])
        self.cmb_format.setFixedWidth(80)
        bot.addWidget(self.cmb_format)

        bot.addSpacing(4)

        qual_lbl = QLabel("Kalite:")
        qual_lbl.setStyleSheet(f"font-size:12px;color:{p.text_secondary};")
        bot.addWidget(qual_lbl)

        self.cmb_quality = QComboBox()
        self.cmb_quality.setFixedWidth(120)
        self.cmb_format.currentTextChanged.connect(self._update_quality_options)
        self._update_quality_options("MP3")
        bot.addWidget(self.cmb_quality)

        bot.addStretch()

        btn_cancel = QPushButton("İptal")
        btn_cancel.setFixedSize(90, 34)
        btn_cancel.setStyleSheet(f"""
            QPushButton{{background:transparent;border:1px solid {p.border};
                border-radius:7px;color:{p.text_secondary};}}
            QPushButton:hover{{background:{p.bg_hover};color:{p.text_primary};}}
        """)
        btn_cancel.clicked.connect(self.reject)
        bot.addWidget(btn_cancel)

        self.btn_add = QPushButton("Seçilenleri Ekle")
        self.btn_add.setFixedHeight(34)
        self.btn_add.setMinimumWidth(130)
        self.btn_add.setEnabled(False)
        self.btn_add.setStyleSheet(f"""
            QPushButton{{background:{p.accent};border:none;border-radius:7px;
                color:#fff;font-size:13px;font-weight:600;padding:0 16px;}}
            QPushButton:hover{{background:{p.accent_hover};}}
            QPushButton:disabled{{background:{p.bg_hover};color:{p.text_muted};}}
        """)
        self.btn_add.clicked.connect(self._accept_selected)
        bot.addWidget(self.btn_add)

        root.addLayout(bot)

    # ── Veri Çekme ───────────────────────────────────────────────────────────

    def _fetch_playlist(self, limit: int | None = None):
        """
        Playlist/Mix öğelerini arka planda çeker.

        limit : int → Mix ilk yüklemesinde playlistend=limit ile kısıtlar (hızlı).
                None → sınırsız, tüm öğeleri çeker (playlist + tam mix).
        """
        def worker():
            try:
                from yt_dlp import YoutubeDL
                opts: dict = {
                    "quiet":        True,
                    "no_warnings":  True,
                    "extract_flat": True,
                    "noplaylist":   False,
                }
                if limit is not None:
                    # yt-dlp'ye N öğeden sonra durmasını söyle — gerçekten hızlı
                    opts["playlistend"] = limit

                with YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(self.url, download=False)

                if not info:
                    self._error_signal.emit("Playlist bilgisi alınamadı.")
                    return

                raw_entries = info.get("entries") or []
                try:
                    entries = list(raw_entries)
                except Exception:
                    entries = []

                if not entries:
                    self._error_signal.emit("Playlist boş veya erişilemiyor.")
                    return

                result = []
                for e in entries:
                    if not e or not isinstance(e, dict):
                        continue
                    try:
                        vid_id = e.get("id") or ""
                        title  = e.get("title") or f"Video {len(result) + 1}"
                        url    = (
                            f"https://www.youtube.com/watch?v={vid_id}"
                            if vid_id else (e.get("url") or "")
                        )
                        if not url:
                            continue
                        result.append({
                            "title":    title,
                            "url":      url,
                            "duration": e.get("duration") or 0,
                            "channel":  e.get("channel") or e.get("uploader") or "",
                        })
                    except Exception:
                        continue

                if not result:
                    self._error_signal.emit(
                        "Oynatma listesinde işlenebilir video bulunamadı."
                    )
                    return

                self._entries_signal.emit(result)
            except Exception as exc:
                self._error_signal.emit(str(exc))

        threading.Thread(target=worker, daemon=True).start()

    # ── Liste Doldurma ────────────────────────────────────────────────────────

    def _populate(self, entries: list[dict]):
        """Listeyi doldur. İkinci kez çağrıldığında (tam mix) önceki öğeleri temizler."""
        self.progress.setVisible(False)
        self._all_entries = entries

        # Başlık
        kind_word = "Mix" if self._kind == "mix" else "Playlist"
        self.lbl_title.setText(f"{kind_word} — {len(entries)} video")
        self.lbl_sub.setText("İndirmek istediğiniz videoları seçin:")

        # Listeyi sıfırla (tam mix yüklemesinde gerekli)
        self._search.setText("")
        self.list_widget.blockSignals(True)
        self.list_widget.clear()

        for e in entries:
            dur     = self._fmt_dur(e.get("duration") or 0)
            title   = e.get("title")   or "—"
            channel = e.get("channel") or ""
            url     = e.get("url")     or ""

            label = title
            if channel:
                label += f"  ·  {channel}"
            if dur:
                label += f"  [{dur}]"

            item = QListWidgetItem(label)
            item.setCheckState(Qt.CheckState.Checked)
            item.setData(Qt.ItemDataRole.UserRole, url)
            self.list_widget.addItem(item)

        self.list_widget.blockSignals(False)

        # Mix banner: sınırlı moddaysa göster, tam yükleme sonrası gizle
        if self._kind == "mix" and self._mix_limited:
            self._mix_banner.setVisible(True)
            self._btn_load_full.setEnabled(True)
            self._btn_load_full.setText("Tam Mix'i Yükle")
        else:
            self._mix_banner.setVisible(False)

        # Arama ve seçim araçlarını etkinleştir
        self._search.setVisible(True)
        self.btn_sel_all.setEnabled(True)
        self.btn_desel_all.setEnabled(True)
        self._update_sel_label()

    def _on_error(self, msg: str):
        from ytdownloader.ui.qt.theme import theme_manager
        self.progress.setVisible(False)
        self.lbl_title.setText("Hata")
        self.lbl_sub.setText(msg)
        self.lbl_sub.setStyleSheet(f"color:{theme_manager.palette.error};font-size:12px;")

    # ── Tam Mix Yükleme ───────────────────────────────────────────────────────

    def _load_full_mix(self):
        """Mix için tüm öğeleri sınırsız olarak yeniden çeker."""
        self._mix_limited = False
        self._btn_load_full.setEnabled(False)
        self._btn_load_full.setText("Yükleniyor...")
        self.btn_sel_all.setEnabled(False)
        self.btn_desel_all.setEnabled(False)
        self.btn_add.setEnabled(False)
        self._search.clear()
        self._search.setVisible(False)
        self.progress.setRange(0, 0)
        self.progress.setVisible(True)
        self._fetch_playlist(limit=None)  # sınırsız

    # ── Arama ─────────────────────────────────────────────────────────────────

    def _on_search_changed(self, text: str):
        query = text.strip().lower()
        for i, e in enumerate(self._all_entries):
            if i >= self.list_widget.count():
                break
            title   = (e.get("title")   or "").lower()
            channel = (e.get("channel") or "").lower()
            match   = (not query) or (query in title) or (query in channel)
            self.list_widget.item(i).setHidden(not match)

        self._update_sel_label()

    # ── Toplu Seçim ───────────────────────────────────────────────────────────

    def _bulk_check(self, checked: bool, visible_only: bool = False):
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        self.list_widget.blockSignals(True)
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if visible_only and item.isHidden():
                continue
            item.setCheckState(state)
        self.list_widget.blockSignals(False)
        self._update_sel_label()

    # ── Sayaç ─────────────────────────────────────────────────────────────────

    def _update_sel_label(self):
        total   = len(self._all_entries)
        visible = sum(
            1 for i in range(self.list_widget.count())
            if not self.list_widget.item(i).isHidden()
        )
        checked = sum(
            1 for i in range(self.list_widget.count())
            if self.list_widget.item(i).checkState() == Qt.CheckState.Checked
        )

        query = self._search.text().strip() if hasattr(self, "_search") else ""
        if query and visible < total:
            self.lbl_sel.setText(f"{visible} / {total} eşleşme  ·  {checked} seçili")
        else:
            self.lbl_sel.setText(f"{checked} / {total} seçili")

        self.btn_add.setEnabled(checked > 0)
        self.btn_add.setText(
            f"{checked} Video Ekle" if checked > 0 else "Seçilenleri Ekle"
        )

    # ── Onayla ────────────────────────────────────────────────────────────────

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

    # ── Yardımcılar ───────────────────────────────────────────────────────────

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
