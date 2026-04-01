# -*- coding: utf-8 -*-
"""
VideoCard — tek bir indirme satırı için PyQt6 widget'ı.

Her kart kendi içinde:
  - Thumbnail (async yükleme)
  - Başlık, kanal, süre, görüntülenme
  - Format / çözünürlük seçimi
  - Progress bar + hız + ETA + durum rozeti
  - İndir / Duraklat / İptal butonları
"""

import os
import uuid
from pathlib import Path

from PyQt6.QtWidgets import (
    QFrame, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QProgressBar, QComboBox, QSizePolicy,
    QFileDialog, QMessageBox, QMenu, QApplication,
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation,
    QEasingCurve, QSize,
)
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen, QFont

from ytdownloader.infrastructure.logger import get_logger
from ytdownloader.services.sound_service import play_complete, play_error
from ytdownloader.ui.qt.icon_helper import set_icon
from ytdownloader.ui.qt.speed_graph import SpeedGraph
from ytdownloader.utils.url_utils import format_duration

log = get_logger("video_card")


# ── Thumbnail yükleyici (arka plan thread) ────────────────────────────────────
class ThumbnailLoader(QThread):
    loaded = pyqtSignal(QPixmap)

    def __init__(self, urls: list[str]):
        super().__init__()
        self.urls = urls

    def run(self):
        for url in self.urls:
            try:
                import urllib.request
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                )
                with urllib.request.urlopen(req, timeout=4) as resp:
                    data = resp.read()
                if data:
                    px = QPixmap()
                    if px.loadFromData(data):
                        px = px.scaled(140, 94, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                       Qt.TransformationMode.SmoothTransformation)
                        if px.width() > 140 or px.height() > 94:
                            x = (px.width() - 140) // 2
                            y = (px.height() - 94) // 2
                            px = px.copy(x, y, 140, 94)
                        self.loaded.emit(px)
                        return
            except Exception:
                continue


# ── Accent şerit (sol renkli çizgi) ──────────────────────────────────────────
class AccentBar(QFrame):
    def __init__(self, color: str = "#c0392b"):
        super().__init__()
        self.setFixedWidth(4)
        self.setStyleSheet(f"background-color: {color}; border-radius: 2px;")

    def set_color(self, color: str):
        self.setStyleSheet(f"background-color: {color}; border-radius: 2px;")


# ── Ana Kart ──────────────────────────────────────────────────────────────────
class VideoCard(QFrame):
    # Sinyaller
    remove_requested        = pyqtSignal(str)          # download_id
    playlist_open_requested = pyqtSignal(str)          # url — kart içinden kullanıcı istedi
    _progress_signal        = pyqtSignal(dict)          # thread-safe progress
    _completed_signal       = pyqtSignal(bool, object)  # thread-safe completed
    _info_signal            = pyqtSignal(bool, dict, str)  # thread-safe info

    # Durum → accent rengi
    STATE_COLORS = {
        "idle":        "#c0392b",
        "downloading": "#c0392b",
        "paused":      "#fd7e14",
        "retrying":    "#fd7e14",
        "completed":   "#28a745",
        "error":       "#dc3545",
    }

    # Durum → rozet metni
    STATE_BADGES = {
        "idle":        "",
        "downloading": "⬇ İndiriliyor",
        "paused":      "⏸ Duraklatıldı",
        "retrying":    "↺ Yeniden Deneniyor",
        "completed":   "✓ Tamamlandı",
        "error":       "⚠ Hata",
    }

    def __init__(self, url: str, download_manager, notification_center,
                 settings_manager, parent=None):
        super().__init__(parent)
        self.setObjectName("VideoCard")

        self.url = url
        self.download_manager = download_manager
        self.notification_center = notification_center
        self.settings_manager = settings_manager
        self.settings = settings_manager.load()

        # Faz 1: URL'deki list= parametresinden playlist türünü belirle.
        # "playlist"  — kullanıcı/kanal listesi (PL*, UU*)
        # "mix"       — YouTube otomatik üretimi (RD*, RL*, TL*, LL*, FL*, WL)
        # None        — liste yok
        import urllib.parse as _up
        _list_id = (_up.parse_qs(_up.urlparse(url).query).get("list") or [""])[0]
        _MIX_PREFIXES = ("RD", "RL", "TL", "LL", "FL", "WL")
        if not _list_id:
            self._playlist_type = None
        elif _list_id.startswith(_MIX_PREFIXES):
            self._playlist_type = "mix"
        else:
            self._playlist_type = "playlist"

        self.download_id   = str(uuid.uuid4())
        self.download_state = "idle"
        self.download_folder = ""
        self._final_file = ""
        self.full_title    = ""
        self.video_info    = {}
        self.resolution_list = []
        self.format_options  = {}
        self._thumb_loader  = None
        self._fetch_in_progress = False  # re-entrant fetch koruması

        self._build_ui()
        self._load_thumbnail()
        self._fetch_info()

        # Worker thread → UI thread köprüsü
        self._progress_signal.connect(self._apply_progress)
        self._completed_signal.connect(self._apply_completed)
        self._info_signal.connect(self._on_info_received)

    # ── UI Kurulumu ───────────────────────────────────────────────────────────

    def _build_ui(self):
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMaximumHeight(200)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        # Ana yatay layout
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # İçerik alanı
        content = QFrame()
        content.setObjectName("VideoCardContent")
        content.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        content.customContextMenuRequested.connect(
            lambda pos: self._show_context_menu(content.mapTo(self, pos))
        )
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(12, 10, 12, 10)
        content_layout.setSpacing(6)

        # ── Başlık satırı ──────────────────────────────────────────────
        header = QHBoxLayout()
        header.setSpacing(6)

        self.lbl_title = QLabel("Yükleniyor...")
        self.lbl_title.setObjectName("card_title")
        self.lbl_title.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        header.addWidget(self.lbl_title)

        self.btn_remove = QPushButton()
        self.btn_remove.setObjectName("btn_remove")
        self.btn_remove.setFixedSize(28, 28)
        self.btn_remove.clicked.connect(self._on_remove)
        set_icon(self.btn_remove, "close", "#6b7280", 12)
        header.addWidget(self.btn_remove)

        content_layout.addLayout(header)

        # ── Orta alan: thumbnail | bilgi | kontroller ───────────────────
        middle = QHBoxLayout()
        middle.setSpacing(10)

        # Thumbnail
        self.lbl_thumb = QLabel()
        self.lbl_thumb.setFixedSize(140, 94)
        self.lbl_thumb.setStyleSheet(
            "background-color: #1a1d27; border-radius: 10px;"
        )
        self.lbl_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._set_placeholder_thumb()
        middle.addWidget(self.lbl_thumb)

        # Bilgi sütunu
        info_col = QVBoxLayout()
        info_col.setSpacing(3)
        info_col.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.lbl_channel = QLabel("")
        self.lbl_channel.setObjectName("card_channel")
        info_col.addWidget(self.lbl_channel)

        self.lbl_meta = QLabel("")
        self.lbl_meta.setObjectName("card_meta")
        info_col.addWidget(self.lbl_meta)

        # Format satırı
        fmt_row = QHBoxLayout()
        fmt_row.setSpacing(8)

        self.btn_format = QPushButton("MP3 ▾")
        self.btn_format.setObjectName("btn_icon")
        self.btn_format.setFixedHeight(24)
        self.btn_format.clicked.connect(self._toggle_format)
        self._format = "MP3"
        fmt_row.addWidget(self.btn_format)

        self.cmb_resolution = QComboBox()
        self.cmb_resolution.setFixedHeight(24)
        self.cmb_resolution.addItems(["128 kbps", "192 kbps", "320 kbps"])
        self.cmb_resolution.setCurrentIndex(2)
        self.cmb_resolution.setEnabled(True)
        self._apply_resolution_style()
        fmt_row.addWidget(self.cmb_resolution)
        fmt_row.addStretch()

        info_col.addLayout(fmt_row)

        middle.addLayout(info_col, stretch=1)

        # Kontrol sütunu (sağ) — sabit genişlik ve yükseklik
        ctrl_widget = QWidget()
        ctrl_widget.setFixedWidth(240)
        ctrl_widget.setFixedHeight(94)
        ctrl_col = QVBoxLayout(ctrl_widget)
        ctrl_col.setSpacing(4)
        ctrl_col.setContentsMargins(0, 0, 0, 0)
        ctrl_col.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

        # Hız grafiği — compact, sabit yükseklik alanı içinde
        self.speed_graph = SpeedGraph(self)
        self.speed_graph.setVisible(False)
        ctrl_col.addWidget(self.speed_graph, alignment=Qt.AlignmentFlag.AlignRight)

        # Progress bar — kalın ve belirgin
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(220)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        ctrl_col.addWidget(self.progress_bar, alignment=Qt.AlignmentFlag.AlignRight)

        # Yüzde + hız + badge tek satırda
        pct_row = QHBoxLayout()
        pct_row.setContentsMargins(0, 0, 0, 0)
        pct_row.setSpacing(4)
        self.lbl_pct = QLabel("")
        self.lbl_pct.setObjectName("card_meta")
        self.lbl_pct.setFixedWidth(36)
        pct_row.addWidget(self.lbl_pct)
        self.lbl_speed = QLabel("")
        self.lbl_speed.setObjectName("card_meta")
        pct_row.addWidget(self.lbl_speed)
        pct_row.addStretch()
        self.lbl_badge = QLabel("")
        self.lbl_badge.setObjectName("badge_queued")
        pct_row.addWidget(self.lbl_badge)
        ctrl_col.addLayout(pct_row)

        # Hata satırı — sadece error state'inde görünür
        self.lbl_error = QLabel("")
        self.lbl_error.setObjectName("card_meta")
        self.lbl_error.setWordWrap(True)
        self.lbl_error.setFixedWidth(220)
        self.lbl_error.setStyleSheet("color: #e05a5a; font-size: 11px;")
        self.lbl_error.setVisible(False)
        ctrl_col.addWidget(self.lbl_error, alignment=Qt.AlignmentFlag.AlignRight)

        # Butonları aşağıya it
        ctrl_col.addStretch(1)

        # Buton satırı — hover'da görünür
        self._btn_bar = QWidget()
        self._btn_bar.setStyleSheet("background: transparent;")
        btn_row = QHBoxLayout(self._btn_bar)
        btn_row.setSpacing(6)
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.addStretch()

        self.btn_folder = QPushButton()
        self.btn_folder.setObjectName("btn_icon")
        self.btn_folder.setFixedSize(38, 38)
        self.btn_folder.setToolTip("Kayıt klasörünü seç")
        self.btn_folder.clicked.connect(self._choose_folder)
        set_icon(self.btn_folder, "folder", "#9da3b4", 17)
        btn_row.addWidget(self.btn_folder)

        self.btn_action = QPushButton()
        self.btn_action.setObjectName("btn_action")
        self.btn_action.setFixedSize(38, 38)
        self.btn_action.setToolTip("İndirmeyi başlat")
        self.btn_action.clicked.connect(self._on_action)
        set_icon(self.btn_action, "download", "#ffffff", 17)
        btn_row.addWidget(self.btn_action)

        self.btn_open_file = QPushButton()
        self.btn_open_file.setObjectName("btn_icon")
        self.btn_open_file.setFixedSize(38, 38)
        self.btn_open_file.setToolTip("Klasörde göster")
        self.btn_open_file.clicked.connect(self._open_file)
        set_icon(self.btn_open_file, "folder", "#28a745", 17)
        self.btn_open_file.setVisible(False)
        btn_row.addWidget(self.btn_open_file)

        self.btn_copy_path = QPushButton()
        self.btn_copy_path.setObjectName("btn_icon")
        self.btn_copy_path.setFixedSize(38, 38)
        self.btn_copy_path.setToolTip("Dosya yolunu kopyala")
        self.btn_copy_path.clicked.connect(self._copy_path)
        set_icon(self.btn_copy_path, "paste", "#9da3b4", 17)
        self.btn_copy_path.setVisible(False)
        btn_row.addWidget(self.btn_copy_path)

        # idle/downloading dışında başlangıçta gizle
        self._btn_bar.setVisible(True)
        ctrl_col.addWidget(self._btn_bar)
        self._apply_btn_styles()

        middle.addWidget(ctrl_widget)
        content_layout.addLayout(middle)

        # ── Playlist banner — URL veya metadata ile tetiklenir, başta gizli ───
        self._playlist_banner = QFrame()
        self._playlist_banner.setObjectName("playlist_banner")
        self._playlist_banner.setVisible(False)
        from ytdownloader.ui.qt.theme import theme_manager as _tm
        _border = _tm.palette.border
        self._playlist_banner.setStyleSheet(
            f"QFrame#playlist_banner {{ border-top: 1px solid {_border}; background: transparent; }}"
        )
        banner_lay = QHBoxLayout(self._playlist_banner)
        banner_lay.setContentsMargins(2, 4, 2, 0)
        banner_lay.setSpacing(8)

        self._lbl_playlist_info = QLabel("Bu video bir oynatma listesine ait")
        self._lbl_playlist_info.setStyleSheet("color: #6b7280; font-size: 11px;")

        self._btn_open_playlist = QPushButton("Playlist olarak aç")
        self._btn_open_playlist.setFixedHeight(22)
        self._btn_open_playlist.setStyleSheet("""
            QPushButton {
                background: transparent; border: 1px solid #3d4460;
                border-radius: 5px; color: #6b7280;
                font-size: 11px; padding: 0 8px;
            }
            QPushButton:hover { border-color: #c0392b; color: #c0392b; }
        """)
        self._btn_open_playlist.clicked.connect(
            lambda: self.playlist_open_requested.emit(self.url)
        )

        banner_lay.addWidget(self._lbl_playlist_info)
        banner_lay.addStretch()
        banner_lay.addWidget(self._btn_open_playlist)
        content_layout.addWidget(self._playlist_banner)

        # Faz 1: tür biliniyorsa baştan göster — metadata bekleme
        if self._playlist_type:
            self._show_playlist_banner("", self._playlist_type)

        root_layout.addWidget(content, stretch=1)

    # ── Thumbnail ─────────────────────────────────────────────────────────────

    def _show_playlist_banner(self, playlist_title: str = "", kind: str = "playlist"):
        """
        Playlist/Mix banner'ını türüne göre gösterir.

        kind="playlist"  → kullanıcı listesi: belirgin ton, kırmızı hover
        kind="mix"       → YouTube otomatik mix: pasif ton, gri hover
        """
        is_mix = (kind == "mix")

        if is_mix:
            info_text = (
                f"YouTube Mix'ine ait  ·  {playlist_title}"
                if playlist_title
                else "Bu bağlantı YouTube'un otomatik oynatma listesini içeriyor"
            )
            btn_text  = "Mix'i Aç"
            # Pasif — gri ton, hover kırmızıya gitmiyor
            info_css  = "color: #4e5568; font-size: 11px;"
            btn_css   = """
                QPushButton {
                    background: transparent; border: 1px solid #2e3348;
                    border-radius: 5px; color: #4e5568;
                    font-size: 11px; padding: 0 8px;
                }
                QPushButton:hover { border-color: #5a6080; color: #6b7280; }
            """
        else:
            info_text = (
                f"Oynatma listesine ait  ·  {playlist_title}"
                if playlist_title
                else "Bu video bir oynatma listesine ait"
            )
            btn_text  = "Playlist olarak aç"
            # Normal — mevcut stil
            info_css  = "color: #6b7280; font-size: 11px;"
            btn_css   = """
                QPushButton {
                    background: transparent; border: 1px solid #3d4460;
                    border-radius: 5px; color: #6b7280;
                    font-size: 11px; padding: 0 8px;
                }
                QPushButton:hover { border-color: #c0392b; color: #c0392b; }
            """

        self._lbl_playlist_info.setText(info_text)
        self._lbl_playlist_info.setStyleSheet(info_css)
        self._btn_open_playlist.setText(btn_text)
        self._btn_open_playlist.setStyleSheet(btn_css)
        self._playlist_banner.setVisible(True)
        self.setMaximumHeight(230)

    def _apply_btn_styles(self):
        """Buton stillerini temaya göre uygula — her iki temada görünür."""
        from ytdownloader.ui.qt.theme import theme_manager
        dark = theme_manager.current == "dark"
        btn_bg  = "#2e3348" if dark else "#e8ecf4"
        btn_brd = "#3d4460" if dark else "#b8bfc8"
        btn_hov = "#3d4460" if dark else "#dce2ef"
        icon_clr = "#9da3b4" if dark else "#374151"
        self.btn_folder.setStyleSheet(
            f"QPushButton {{ background-color: {btn_bg}; border: 1.5px solid {btn_brd}; border-radius: 8px; }}"
            f"QPushButton:hover {{ background-color: {btn_hov}; border-color: #c0392b; }}"
        )
        set_icon(self.btn_folder, "folder", icon_clr, 17)

    def _apply_resolution_style(self):
        """Kalite dropdown'ını temaya göre stillendir — QSS + QPalette ile popup rengi garantili."""
        from ytdownloader.ui.qt.theme import theme_manager
        from PyQt6.QtGui import QPalette, QColor
        _dark = theme_manager.current == "dark"
        bg  = "#1a1d27" if _dark else "#ffffff"
        txt = "#e8eaf0" if _dark else "#111827"
        brd = "#2e3348" if _dark else "#d0d5e0"
        sel = "#c0392b"

        self.cmb_resolution.setStyleSheet(f"""
            QComboBox {{
                background-color: transparent;
                border: 1px solid {brd};
                border-radius: 7px;
                padding: 0px 8px;
                font-size: 12px;
                color: {txt};
                min-width: 80px;
            }}
            QComboBox:hover {{ border-color: #c0392b; }}
            QComboBox::drop-down {{ border: none; width: 18px; }}
            QComboBox::down-arrow {{
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid {txt};
                width: 0; height: 0; margin-right: 4px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {bg};
                border: 1px solid {brd};
                selection-background-color: {sel};
                selection-color: #ffffff;
                color: {txt};
                outline: none;
                padding: 2px;
            }}
            QComboBox QAbstractItemView::item {{
                background-color: {bg};
                color: {txt};
                padding: 5px 8px;
                min-height: 22px;
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: {sel};
                color: #ffffff;
            }}
        """)

        # QPalette ile popup arka planını zorla — QSS bazen yetmez
        pal = self.cmb_resolution.palette()
        pal.setColor(QPalette.ColorRole.Base,   QColor(bg))
        pal.setColor(QPalette.ColorRole.Window, QColor(bg))
        pal.setColor(QPalette.ColorRole.Text,   QColor(txt))
        pal.setColor(QPalette.ColorRole.ButtonText, QColor(txt))
        pal.setColor(QPalette.ColorRole.Highlight,       QColor(sel))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        self.cmb_resolution.setPalette(pal)
        # View'e de uygula
        view = self.cmb_resolution.view()
        if view:
            view.setPalette(pal)

    def _set_placeholder_thumb(self):
        px = QPixmap(140, 94)
        px.fill(QColor("#1a1d27"))
        p = QPainter(px)
        p.setPen(QPen(QColor("#3d4460"), 2))
        p.setFont(QFont("Segoe UI", 26))
        p.drawText(px.rect(), Qt.AlignmentFlag.AlignCenter, "🎵")
        p.end()
        self.lbl_thumb.setPixmap(px)

    def _load_thumbnail(self):
        from ytdownloader.utils.url_utils import extract_video_id, get_thumbnail_urls
        video_id = extract_video_id(self.url)
        if not video_id:
            return
        urls = get_thumbnail_urls(video_id)
        self._thumb_loader = ThumbnailLoader(urls)
        self._thumb_loader.loaded.connect(self._on_thumb_loaded)
        self._thumb_loader.start()

    def _on_thumb_loaded(self, px: QPixmap):
        rounded = self._round_pixmap(px, 6)
        self.lbl_thumb.setPixmap(rounded)

    @staticmethod
    def _round_pixmap(px: QPixmap, radius: int) -> QPixmap:
        """Pixmap'e yuvarlatılmış köşe uygular."""
        result = QPixmap(px.size())
        result.fill(Qt.GlobalColor.transparent)
        p = QPainter(result)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        from PyQt6.QtGui import QPainterPath
        path = QPainterPath()
        path.addRoundedRect(0, 0, px.width(), px.height(), radius, radius)
        p.setClipPath(path)
        p.drawPixmap(0, 0, px)
        p.end()
        return result

    # ── Video Bilgisi ─────────────────────────────────────────────────────────

    def _fetch_info(self):
        if self._fetch_in_progress:
            return
        self._fetch_in_progress = True
        self.download_manager.fetch_video_info(self.url, self._on_info_received_thread)

    def _retry_fetch(self):
        """Metadata fetch'i yeniden başlat."""
        self.lbl_title.setText("Yeniden yükleniyor...")
        self.lbl_channel.setText("")
        self.lbl_channel.setTextFormat(Qt.TextFormat.AutoText)
        self.lbl_channel.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        try:
            self.lbl_channel.linkActivated.disconnect()
        except Exception:
            pass
        self._fetch_info()

    def _on_info_received_thread(self, success: bool, data):
        """Worker thread'den gelir — sinyal ile ana thread'e ilet."""
        self._fetch_in_progress = False
        self._info_signal.emit(success, data if success else {}, "" if success else str(data))

    def _on_info_received(self, success: bool, data: dict, err: str):
        if not success:
            self.lbl_title.setText("Video bilgisi yüklenemedi")
            self.lbl_channel.setText(
                '<a href="#retry" style="color:#c0392b;text-decoration:none;">↺ Yeniden dene</a>'
            )
            self.lbl_channel.setTextFormat(Qt.TextFormat.RichText)
            self.lbl_channel.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextBrowserInteraction
            )
            self.lbl_channel.linkActivated.connect(lambda _: self._retry_fetch())
            return

        info = data
        self.video_info = info

        title = info.get("title", "")
        self.full_title = title
        duration = info.get("duration", 0)
        self._video_duration = duration  # saniye cinsinden sakla
        dur_str = f" [{format_duration(duration)}]" if duration else ""
        self.lbl_title.setText(title + dur_str)

        channel = info.get("channel", "")
        self.lbl_channel.setText(channel)

        upload = info.get("upload_date", "")
        if upload and len(upload) == 8:
            upload = f"{upload[6:8]}.{upload[4:6]}.{upload[:4]}"
        views = info.get("view_count")
        meta_parts = []
        if upload:
            meta_parts.append(upload)
        if views:
            meta_parts.append(f"{views:,} görüntülenme")
        self.lbl_meta.setText("  ·  ".join(meta_parts))

        # Çözünürlük listesi
        self._parse_formats(info.get("formats", []))

        # Faz 2: metadata'dan playlist türü doğrulaması
        playlist_title = info.get("playlist_title") or info.get("playlist", "")
        playlist_id    = info.get("playlist_id") or ""
        if playlist_title or playlist_id:
            _MIX_PREFIXES = ("RD", "RL", "TL", "LL", "FL", "WL")
            meta_kind = (
                "mix" if playlist_id.startswith(_MIX_PREFIXES) else "playlist"
            )
            self._show_playlist_banner(playlist_title, meta_kind)

        # Playlist'ten gelen preset format/quality varsa uygula, yoksa ayarlardan al
        settings = self.settings_manager.load()
        preset_fmt = getattr(self, "_preset_format", None) or settings.get("default_format", "MP3")
        preset_qty = getattr(self, "_preset_quality", None) or settings.get("default_quality", "320 kbps")
        if preset_fmt and self._format != preset_fmt:
            self._format = preset_fmt
            self.btn_format.setText(f"{self._format} ▾")
            self._update_quality_combo()
        if preset_qty:
            idx = self.cmb_resolution.findText(preset_qty)
            if idx >= 0:
                self.cmb_resolution.setCurrentIndex(idx)

    def _parse_formats(self, formats: list):
        # Standart çözünürlükler — YouTube'un garip değerlerini en yakına yuvarla
        STANDARD = [144, 240, 360, 480, 720, 1080, 1440, 2160, 4320]

        def snap_to_standard(h):
            """Yüksekliği en yakın standart değere yuvarla (±20% tolerans)."""
            if not h:
                return None
            closest = min(STANDARD, key=lambda s: abs(s - h))
            # Tolerans: standart değerin %25'i kadar sapma kabul et
            if abs(closest - h) <= closest * 0.25:
                return closest
            return None

        res_map = {}   # "1080p" -> (format_id, tbr)
        for f in formats:
            h    = f.get("height") or 0
            fmt_id = f.get("format_id", "")
            vcodec = f.get("vcodec", "none")
            tbr    = f.get("tbr") or 0

            if not fmt_id or not h:
                continue
            if not vcodec or vcodec in ("none", ""):
                continue

            snapped = snap_to_standard(h)
            if snapped is None:
                continue

            key = f"{snapped}p"
            # Aynı çözünürlük için en yüksek bitrate'li formatı sakla
            if key not in res_map or tbr > res_map[key][1]:
                res_map[key] = (fmt_id, tbr)

        sorted_res = sorted(res_map.keys(), key=lambda x: int(x[:-1]))
        self.resolution_list = sorted_res
        self.format_options  = {k: v[0] for k, v in res_map.items()}
        self._update_quality_combo()

    # ── Format Seçimi ─────────────────────────────────────────────────────────

    def _toggle_format(self):
        self._format = "MP4" if self._format == "MP3" else "MP3"
        self.btn_format.setText(f"{self._format} ▾")
        self._update_quality_combo()

    def _update_quality_combo(self):
        """Format'a göre combo içeriğini güncelle: MP3→bitrate, MP4→çözünürlük."""
        self.cmb_resolution.clear()
        if self._format == "MP3":
            self.cmb_resolution.addItems(["128 kbps", "192 kbps", "320 kbps"])
            self.cmb_resolution.setCurrentIndex(2)  # 320 varsayılan
            self.cmb_resolution.setEnabled(True)
        else:
            self.cmb_resolution.addItems(self.resolution_list)
            if self.resolution_list:
                self.cmb_resolution.setCurrentIndex(len(self.resolution_list) - 1)
            self.cmb_resolution.setEnabled(bool(self.resolution_list))

    # ── Buton Aksiyonları ─────────────────────────────────────────────────────

    def _on_action(self):
        if self.download_state == "idle":
            self._start()
        elif self.download_state == "downloading":
            self._pause()
        elif self.download_state == "paused":
            self._resume()
        elif self.download_state in ("completed", "error"):
            self._reset()

    def _start(self):
        # Her indirme başında ayarları tazele (klasör değişmiş olabilir)
        self.settings = self.settings_manager.load()
        # download_folder dışarıdan atandıysa (Hepsini İndir) sormadan devam
        if not self.download_folder:
            # Format bazlı klasör kontrolü
            if self._format == "MP3" and self.settings.get("music_folder"):
                self.download_folder = self.settings["music_folder"]
            elif self._format == "MP4" and self.settings.get("video_folder"):
                self.download_folder = self.settings["video_folder"]
            else:
                last = self.settings.get("last_download_folder", "")
                desktop = str(Path.home() / "Desktop")
                if not os.path.exists(desktop):
                    desktop = str(Path.home() / "Masaüstü")
                if not os.path.exists(desktop):
                    desktop = str(Path.home())
                default_dir = last if last and os.path.exists(last) else desktop
                folder = QFileDialog.getExistingDirectory(
                    self, "İndirme Klasörü Seç", default_dir
                )
                if not folder:
                    return
                self.download_folder = folder
                self.settings["last_download_folder"] = folder
                self.settings_manager.save(self.settings)

        selected = self.cmb_resolution.currentText()
        # Hız limiti ayardan al
        speed_limit = None
        if self.settings.get("speed_limit_enabled", False):
            mbps = self.settings.get("speed_limit_mbps", 5)
            speed_limit = int(mbps * 1024 * 1024)

        options = {
            "output_dir":    self.download_folder,
            "format":        self._format.lower(),
            "format_id":     self.format_options.get(selected) if self._format == "MP4" else None,
            "audio_quality": selected.replace(" kbps", "") if self._format == "MP3" else None,
            "title":         self.full_title,
            "channel":       self.video_info.get("channel", "") or self.video_info.get("uploader", ""),
            "speed_limit":   speed_limit,
        }

        self._set_state("downloading")
        self.download_manager.download_video(
            self.download_id, self.url, options,
            self._on_progress, self._on_completed
        )

    def _pause(self):
        self.download_manager.pause_download(self.download_id)
        self._set_state("paused")

    def _resume(self):
        self.download_manager.resume_download(self.download_id)
        self._set_state("downloading")

    def _reset(self):
        """Hata sonrası veya tamamlanma sonrası sıfırla."""
        self.download_id = str(uuid.uuid4())
        self.progress_bar.setValue(0)
        self.lbl_pct.setText("")
        self.lbl_speed.setText("")
        self.lbl_error.setVisible(False)
        self._set_state("idle")

    def mouseDoubleClickEvent(self, event):
        """Çift tıklama: idle/error → indir, downloading → duraklat, paused → devam et."""
        from PyQt6.QtCore import Qt as _Qt
        if event.button() == _Qt.MouseButton.LeftButton:
            self._on_action()
        super().mouseDoubleClickEvent(event)

    def _show_context_menu(self, pos):
        """Sağ tık menüsü — tema-aware, crash-safe."""
        from ytdownloader.ui.qt.theme import theme_manager
        is_dark = theme_manager.current == "dark"
        bg       = "#1a1d27" if is_dark else "#ffffff"
        border   = "#2e3348" if is_dark else "#d0d5e0"
        item_clr = "#e8eaf0" if is_dark else "#111827"
        sel_bg   = "#252a3d" if is_dark else "#f0f2f8"
        sel_clr  = "#ffffff" if is_dark else "#111827"
        dis_clr  = "#4a5068" if is_dark else "#adb5bd"

        # Parent olarak None — kart silinse bile menü çökmez
        menu = QMenu(None)
        menu.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        menu.setStyleSheet(f"""
            QMenu {{
                background: {bg};
                border: 1px solid {border};
                border-radius: 10px;
                padding: 6px 4px;
                font-size: 13px;
            }}
            QMenu::item {{
                padding: 7px 18px 7px 12px;
                color: {item_clr};
                border-radius: 6px;
                margin: 1px 4px;
            }}
            QMenu::item:selected {{
                background: {sel_bg};
                color: {sel_clr};
            }}
            QMenu::item:disabled {{ color: {dis_clr}; }}
            QMenu::separator {{
                height: 1px;
                background: {border};
                margin: 5px 10px;
            }}
        """)

        # Kart referanslarını snapshot olarak al — menü açıkken kart değişse de sorun olmaz
        state      = self.download_state
        url        = self.url
        title      = self.full_title
        final_file = getattr(self, "_final_file", "")
        download_id = self.download_id

        # ── Grup 1: İndirme eylemi ─────────────────────────────────────
        if state == "idle":
            a = menu.addAction("İndir")
            a.triggered.connect(self._on_action)
        elif state == "downloading":
            a = menu.addAction("Duraklat")
            a.triggered.connect(self._on_action)
        elif state == "paused":
            a = menu.addAction("Devam Et")
            a.triggered.connect(self._on_action)
        elif state in ("completed", "error"):
            a = menu.addAction("Yeniden İndir")
            a.triggered.connect(self._on_action)

        if state == "completed" and final_file:
            a = menu.addAction("Klasörde Göster")
            a.triggered.connect(self._open_file)

        if state in ("idle", "error", "paused"):
            a = menu.addAction("İndirme Konumunu Seç")
            a.triggered.connect(self._choose_folder)

        menu.addSeparator()

        # ── Grup 2: Kopyala ────────────────────────────────────────────
        a = menu.addAction("URL'yi Kopyala")
        a.triggered.connect(lambda: QApplication.clipboard().setText(url))

        a = menu.addAction("Başlığı Kopyala")
        a.triggered.connect(lambda: QApplication.clipboard().setText(title))

        if state == "completed" and final_file:
            a = menu.addAction("Dosya Yolunu Kopyala")
            a.triggered.connect(self._copy_path)

        menu.addSeparator()

        # ── Grup 3: Kaldır — kırmızı renk için QWidgetAction ──────────
        from PyQt6.QtWidgets import QWidgetAction
        remove_label = QLabel("Listeden Kaldır")
        remove_label.setContentsMargins(12, 7, 18, 7)
        remove_label.setStyleSheet(f"""
            QLabel {{
                color: #e05a5a;
                font-size: 13px;
                border-radius: 6px;
                background: transparent;
            }}
            QLabel:hover {{ background: {sel_bg}; }}
        """)
        remove_label.setMinimumWidth(200)
        wa = QWidgetAction(menu)
        wa.setDefaultWidget(remove_label)
        wa.triggered.connect(lambda: QTimer.singleShot(50, self._on_remove))
        remove_label.mousePressEvent = lambda e: (wa.trigger(), menu.close())
        menu.addAction(wa)

        menu.popup(self.mapToGlobal(pos))

    def _open_file(self):
        """Tamamlanan dosyayı dosya yöneticisinde göster."""
        import subprocess, sys
        path = self._final_file
        if not path or not os.path.exists(path):
            # Dosya yolu yoksa klasörü aç
            folder = self.download_folder or str(Path.home() / "Desktop")
            path = folder
        if sys.platform == "win32":
            if os.path.isfile(path):
                subprocess.Popen(f'explorer /select,"{path}"')
            else:
                subprocess.run(["explorer", path])
        elif sys.platform == "darwin":
            subprocess.run(["open", "-R", path] if os.path.isfile(path) else ["open", path])
        else:
            folder = os.path.dirname(path) if os.path.isfile(path) else path
            subprocess.run(["xdg-open", folder])

    def _copy_path(self):
        """Tamamlanan dosyanın yolunu panoya kopyalar."""
        path = self._final_file
        if path and os.path.exists(path):
            from PyQt6.QtWidgets import QApplication
            QApplication.clipboard().setText(path)
            self.notification_center.show("📋 Kopyalandı", os.path.basename(path), "info")

    def _choose_folder(self):
        last = self.settings.get("last_download_folder", "")
        folder = QFileDialog.getExistingDirectory(
            self, "İndirme Klasörü Seç",
            last if last and os.path.exists(last) else str(Path.home())
        )
        if folder:
            self.download_folder = folder
            self.settings["last_download_folder"] = folder
            self.settings_manager.save(self.settings)

    def _on_remove(self):
        if self.download_state == "downloading":
            self.download_manager.cancel_download(self.download_id)
        self.remove_requested.emit(self.download_id)

    # ── Progress Callback'leri ────────────────────────────────────────────────

    def _on_progress(self, info: dict):
        """Worker thread'den gelir — sinyal ile ana thread'e ilet."""
        self._progress_signal.emit(info)

    def _apply_progress(self, info: dict):
        """Ana thread'de çalışır."""
        status = info.get("status", "")
        if status == "downloading":
            pct   = info.get("percent", 0)
            speed = info.get("speed", 0)
            eta   = info.get("eta", 0)

            self.progress_bar.setValue(int(pct))
            self.lbl_pct.setText(f"%{pct:.0f}")

            # %100'e ulaşınca hemen bildirim — FFmpeg'i bekleme
            if pct >= 100 and not getattr(self, "_toast_sent", False):
                self._toast_sent = True
                self.notification_center.show(
                    "✅ İndirme Tamamlandı",
                    self.full_title,
                    "success"
                )
                # Sistem sesini çal
                try:
                    import sys, ctypes
                    if sys.platform == "win32":
                        ctypes.windll.winmm.PlaySoundW("SystemAsterisk", None, 0x00010001)
                except Exception:
                    pass

            if speed:
                spd_str = self._fmt_size(speed) + "/s"
                dur = getattr(self, "_video_duration", 0)
                if dur and dur > 0 and eta and eta > 0:
                    elapsed = dur - eta
                    elapsed = max(0, elapsed)
                    time_str = f" · {format_duration(int(elapsed))}/{format_duration(int(dur))}"
                elif eta and eta > 0:
                    time_str = f" · {format_duration(int(eta))} kaldı"
                else:
                    time_str = ""
                self.lbl_speed.setText(spd_str + time_str)
                self.speed_graph.setVisible(True)
                self.speed_graph.add_point(speed)

    def _on_completed(self, success: bool, result):
        """Worker thread'den gelir — sinyal ile ana thread'e ilet."""
        self._completed_signal.emit(success, result)

    def _apply_completed(self, success: bool, result):
        """Ana thread'de çalışır."""
        self._toast_sent = False  # sonraki indirme için sıfırla
        if success:
            self.progress_bar.setValue(100)
            self.lbl_pct.setText("%100")
            self.lbl_speed.setText("")
            self.lbl_error.setVisible(False)
            self.speed_graph.freeze(color="#28a745")
            if isinstance(result, dict):
                self._final_file = result.get("file_path", "")
            self._set_state("completed")
            # Klasör otomatik açma
            if self.settings.get("open_folder_on_complete", False):
                if isinstance(result, dict):
                    fp = result.get("file_path", "")
                    if fp and os.path.exists(fp):
                        import subprocess, sys
                        if sys.platform == "win32":
                            subprocess.Popen(f'explorer /select,"{fp}"')
                        elif sys.platform == "darwin":
                            subprocess.Popen(["open", "-R", fp])
                        else:
                            subprocess.Popen(["xdg-open", str(Path(fp).parent)])
        else:
            self._set_state("error")
            full_err = str(result)
            # Kısa özet lbl_speed'de, tam mesaj tooltip'te
            short_err = full_err[:120]
            self.lbl_speed.setText("")
            self.lbl_error.setText(short_err)
            self.lbl_error.setToolTip(full_err)
            self.lbl_error.setVisible(True)
            self.notification_center.show(
                "❌ İndirme Hatası",
                self.full_title,
                "error"
            )

    # ── Durum Yönetimi ────────────────────────────────────────────────────────

    def enterEvent(self, event):
        """Mouse karta girince butonları göster."""
        self._btn_bar.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Mouse karttan çıkınca — sadece completed state'inde gizle."""
        if self.download_state == "completed":
            self._btn_bar.setVisible(False)
        super().leaveEvent(event)

    def set_drag_highlight(self, active: bool):
        """Sürükleme sırasında mavi vurgu göster/gizle."""
        self.setProperty("dragging", active)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def _icon_color(self) -> str:
        """Temaya göre ikon rengi döner."""
        try:
            from ytdownloader.ui.qt.theme import theme_manager
            return "#9da3b4" if theme_manager.current == "dark" else "#1a1a2e"
        except Exception:
            return "#9da3b4"

    def _set_state(self, state: str):
        self.download_state = state
        color = self.STATE_COLORS.get(state, "#c0392b")  # noqa — renk badge için kullanılıyor

        badge = self.STATE_BADGES.get(state, "")
        self.lbl_badge.setObjectName(f"badge_{state}")
        self.lbl_badge.setText(badge)
        self.lbl_badge.style().unpolish(self.lbl_badge)
        self.lbl_badge.style().polish(self.lbl_badge)

        # Progress bar rengi
        state_map = {
            "downloading": "",
            "completed":   "success",
            "error":       "error",
            "paused":      "warning",
        }
        self.progress_bar.setProperty("state", state_map.get(state, ""))
        self.progress_bar.style().unpolish(self.progress_bar)
        self.progress_bar.style().polish(self.progress_bar)
        action_icons = {
            "idle":        "download",
            "downloading": "pause",
            "paused":      "play",
            "completed":   "retry",
            "error":       "retry",
        }
        icon_name = action_icons.get(state, "download")
        set_icon(self.btn_action, icon_name, "#ffffff", 17)

        # Tamamlandığında buton barını gizle (hover'da açılır), diğer durumlarda her zaman göster
        is_done = state == "completed"
        self._btn_bar.setVisible(not is_done)
        self.btn_open_file.setVisible(is_done)
        self.btn_copy_path.setVisible(is_done)
        self.btn_folder.setVisible(not is_done)

        if is_done:
            # Küçük soluk butonlar — kart dağılmasın
            self.btn_action.setObjectName("btn_action_done")
            self.btn_action.setFixedSize(32, 32)
            self.btn_open_file.setFixedSize(32, 32)
            self.btn_copy_path.setFixedSize(32, 32)
            set_icon(self.btn_action, "retry", "#6b7280", 14)
            set_icon(self.btn_open_file, "folder", "#6b7280", 14)
            set_icon(self.btn_copy_path, "paste", "#6b7280", 14)
        else:
            self.btn_action.setObjectName("btn_action")
            self.btn_action.setFixedSize(38, 38)
            self.btn_action.setStyleSheet(
                "QPushButton { background-color: #c0392b; border: none; border-radius: 8px; }"
                "QPushButton:hover { background-color: #a93226; }"
            )
            set_icon(self.btn_action, icon_name, "#ffffff", 17)

        # Style yenile
        self.btn_action.style().unpolish(self.btn_action)
        self.btn_action.style().polish(self.btn_action)

        # Tema-aware ikon rengi
        set_icon(self.btn_folder, "folder", self._icon_color(), 17)

    # ── Yardımcılar ───────────────────────────────────────────────────────────

    @staticmethod
    def _fmt_size(b: float) -> str:
        if b < 1024:
            return f"{b:.0f} B"
        elif b < 1024 ** 2:
            return f"{b/1024:.1f} KB"
        elif b < 1024 ** 3:
            return f"{b/1024**2:.1f} MB"
        return f"{b/1024**3:.1f} GB"
