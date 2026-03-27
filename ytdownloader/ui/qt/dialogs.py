# -*- coding: utf-8 -*-
"""SettingsDialog ve AboutDialog — tam i18n entegrasyonlu."""

import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QFrame, QTabWidget, QWidget, QLineEdit,
    QCheckBox, QFileDialog, QSpinBox,
)
from PyQt6.QtCore import Qt, QPointF, QSize
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPolygonF
from ytdownloader.services.i18n_service import get_i18n, I18nService


def _divider(color="#2e3348"):
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet(f"background:{color};max-height:1px;margin:4px 0;")
    return f


class SettingsDialog(QDialog):
    _BROWSER_MAP = {
        "Otomatik (Sistem Varsayılanı)": "auto",
        "Microsoft Edge":  "edge",
        "Google Chrome":   "chrome",
        "Mozilla Firefox": "firefox",
        "Opera":           "opera",
        "Brave":           "brave",
        "Vivaldi":         "vivaldi",
    }

    LANGUAGES = {
        "Türkçe": "tr", "English": "en", "Español": "es",
        "Français": "fr", "Deutsch": "de", "日本語": "ja", "Português": "pt",
    }

    def __init__(self, parent, settings_manager, auth_service=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.settings = settings_manager.load()
        self.auth_service = auth_service
        self._i18n = get_i18n(self.settings.get("language", "tr"))
        # Tema renkleri
        from ytdownloader.ui.qt.theme import theme_manager
        _dark = theme_manager.current == "dark"
        self._dark = _dark
        self._c = {
            "bg":       "#1a1d27" if _dark else "#f0f2f7",
            "surface":  "#2e3348" if _dark else "#e8eaf0",
            "border":   "#2e3348" if _dark else "#d0d5e0",
            "border2":  "#3d4460" if _dark else "#c4c9d8",
            "txt":      "#e8eaf0" if _dark else "#111827",
            "sub":      "#9da3b4" if _dark else "#6b7280",
            "hover":    "#3d4460" if _dark else "#d8dce8",
            "acc":      "#c0392b",
            "field_bg": "#1e2235" if _dark else "#ffffff",
            "acc_hov":  "#a93226",
            "input_bg": "#1a1d27" if _dark else "#ffffff",
            "icon":     "#e8eaf0" if _dark else "#1a1a2e",
        }
        self.setMinimumSize(600, 500)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        self.setStyleSheet(f"QDialog {{ background: {self._c['bg']}; }} QLabel {{ background: transparent; }}")
        self._build_ui()
        self._load_values()

    def _t(self, key): return self._i18n.t(key)

    def _sec_lbl(self, key):
        lbl = QLabel(self._t(key))
        lbl.setStyleSheet("font-weight:700;font-size:10px;color:#9da3b4;"
                          "letter-spacing:1.2px;margin-top:8px;")
        return lbl

    def _row(self, key, widget):
        row = QHBoxLayout(); row.setSpacing(12)
        lbl = QLabel(self._t(key))
        lbl.setFixedWidth(190)
        lbl.setStyleSheet("font-size:13px;color:#e8eaf0;")
        row.addWidget(lbl); row.addWidget(widget); row.addStretch()
        return row

    def _build_ui(self):
        self.setWindowTitle(self._t("ayarlar_title"))
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 16)
        root.setSpacing(0)

        self.tabs = QTabWidget()
        c = self._c
        tab_hover = "#c0392b" if self._dark else "#c0392b"
        self.tabs.setStyleSheet(f"""
            QTabWidget {{ background: {c['bg']}; }}
            QTabWidget::pane {{ border: none; background: {c['bg']}; }}
            QTabBar {{ background: {c['bg']}; }}
            QTabBar::tab {{
                padding: 10px 22px; font-size: 13px; color: {c['sub']};
                border: none; border-bottom: 2px solid transparent;
                background: transparent; font-weight: 500;
            }}
            QTabBar::tab:selected {{ color: {c['acc']}; border-bottom: 2px solid {c['acc']}; font-weight: 700; }}
            QTabBar::tab:hover:!selected {{ color: {c['txt']}; }}
        """)
        self.tabs.addTab(self._tab_general(), self._t("genel"))
        self.tabs.addTab(self._tab_download(), self._t("indirme"))
        root.addWidget(self.tabs)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(20, 8, 20, 0)
        btn_row.addStretch()

        self.btn_cancel = QPushButton(self._t("iptal"))
        self.btn_cancel.setFixedSize(100, 36)
        self.btn_cancel.setStyleSheet(f"""
            QPushButton {{ background: transparent; border: 1px solid {c['border']};
                border-radius: 7px; color: {c['sub']}; font-size: 13px; }}
            QPushButton:hover {{ background: {c['hover']}; color: {c['txt']}; border-color: {c['border2']}; }}
        """)
        self.btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_cancel)
        btn_row.addSpacing(8)

        self.btn_save = QPushButton(self._t("kaydet"))
        self.btn_save.setFixedSize(100, 36)
        self.btn_save.setStyleSheet(f"""
            QPushButton {{ background: {c['acc']}; border: none;
                border-radius: 7px; color: #ffffff; font-size: 13px; font-weight: 600; }}
            QPushButton:hover {{ background: {c['acc_hov']}; }}
        """)
        self.btn_save.clicked.connect(self._save)
        btn_row.addWidget(self.btn_save)
        root.addLayout(btn_row)

    def _tab_general(self):
        c = self._c
        w = QWidget()
        w.setStyleSheet(f"background: {c['bg']};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 16, 24, 8)
        lay.setSpacing(10)

        chk_style = f"""
            QCheckBox {{ font-size:13px; color:{c['txt']}; spacing:8px; background:transparent; }}
            QCheckBox::indicator {{ width:16px; height:16px; border-radius:4px;
                border:2px solid {c['border2']}; background:{c['field_bg']}; }}
            QCheckBox::indicator:checked {{ background:{c['acc']}; border-color:{c['acc']}; }}
        """

        def _sec(text):
            lbl = QLabel(text)
            lbl.setStyleSheet(f"font-weight:700;font-size:10px;color:{c['sub']};letter-spacing:1.2px;margin-top:8px;background:transparent;")
            return lbl

        def _note(text):
            lbl = QLabel(text)
            lbl.setStyleSheet(f"font-size:11px;color:{c['sub']};margin-left:4px;background:transparent;")
            return lbl

        def _lbl(text):
            lbl = QLabel(text)
            lbl.setStyleSheet(f"font-size:13px;color:{c['txt']};background:transparent;")
            lbl.setFixedWidth(190)
            return lbl

        combo_style = f"""
            QComboBox {{ background:{c['field_bg']}; border:1px solid {c['border']};
                border-radius:6px; padding:5px 10px; color:{c['txt']}; font-size:13px; min-width:160px; }}
            QComboBox:hover {{ border-color:{c['acc']}; }}
            QComboBox::drop-down {{ border:none; width:20px; }}
            QComboBox QAbstractItemView {{ background:{c['field_bg']}; border:1px solid {c['border']};
                color:{c['txt']}; selection-background-color:{c['acc']}; selection-color:#fff;
                outline:none; padding:2px; }}
            QComboBox QAbstractItemView::item {{ padding:6px 10px; background:{c['field_bg']}; color:{c['txt']}; }}
            QComboBox QAbstractItemView::item:selected {{ background:{c['acc']}; color:#fff; }}
        """

        # Dil
        lay.addWidget(_sec("DİL"))
        lay.addWidget(_divider(c['border']))
        self.cmb_lang = QComboBox()
        self.cmb_lang.setFixedWidth(190)
        self.cmb_lang.addItems(list(self.LANGUAGES.keys()))
        self.cmb_lang.setStyleSheet(combo_style)
        r = QHBoxLayout(); r.addWidget(_lbl(self._t("uygulama_dili"))); r.addWidget(self.cmb_lang); r.addStretch()
        lay.addLayout(r)
        lay.addWidget(_note(self._t("dil_not")))

        # Tema
        lay.addWidget(_sec("TEMA"))
        lay.addWidget(_divider(c['border']))
        self.cmb_theme = QComboBox()
        self.cmb_theme.setFixedWidth(190)
        self.cmb_theme.addItems([self._t("koyu"), self._t("acik")])
        self.cmb_theme.setStyleSheet(combo_style)
        r = QHBoxLayout(); r.addWidget(_lbl(self._t("renk_temasi"))); r.addWidget(self.cmb_theme); r.addStretch()
        lay.addLayout(r)

        # Tarayıcı
        lay.addWidget(_sec("TARAYICI"))
        lay.addWidget(_divider(c['border']))
        self.cmb_browser = QComboBox()
        self.cmb_browser.setFixedWidth(220)
        self.cmb_browser.addItems(["Otomatik (Sistem Varsayılanı)", "Microsoft Edge",
            "Google Chrome", "Mozilla Firefox", "Opera", "Brave", "Vivaldi"])
        self.cmb_browser.setStyleSheet(combo_style)
        r = QHBoxLayout(); r.addWidget(_lbl("YouTube Tarayıcısı")); r.addWidget(self.cmb_browser); r.addStretch()
        lay.addLayout(r)
        lay.addWidget(_note("YouTube sekmesi bu tarayıcıyı taklit eder."))

        # Bildirimler
        lay.addWidget(_sec("BİLDİRİMLER"))
        lay.addWidget(_divider(c['border']))
        self.chk_notif = QCheckBox(self._t("bildirim_tamamlandi"))
        self.chk_notif.setStyleSheet(chk_style)
        lay.addWidget(self.chk_notif)
        self.chk_notif_error = QCheckBox(self._t("bildirim_hata"))
        self.chk_notif_error.setStyleSheet(chk_style)
        lay.addWidget(self.chk_notif_error)
        self.chk_sound = QCheckBox("İndirme tamamlanınca ses çal")
        self.chk_sound.setStyleSheet(chk_style)
        lay.addWidget(self.chk_sound)

        # Diğer
        lay.addWidget(_sec("DİĞER"))
        lay.addWidget(_divider(c['border']))
        self.chk_open_folder = QCheckBox("İndirme bitince klasörü otomatik aç")
        self.chk_open_folder.setStyleSheet(chk_style)
        lay.addWidget(self.chk_open_folder)
        self.chk_start_minimized = QCheckBox("Sistem tepsisinde başlat")
        self.chk_start_minimized.setStyleSheet(chk_style)
        lay.addWidget(self.chk_start_minimized)
        self.chk_confirm_exit = QCheckBox("Çıkışta onay iste")
        self.chk_confirm_exit.setStyleSheet(chk_style)
        lay.addWidget(self.chk_confirm_exit)

        lay.addStretch()
        return w

    def _tab_download(self):
        c = self._c
        w = QWidget()
        w.setStyleSheet(f"background: {c['bg']};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 16, 24, 8)
        lay.setSpacing(10)

        txt_style = f"""
            QLineEdit {{ background:{c['field_bg']}; border:1px solid {c['border']};
                border-radius:6px; padding:5px 10px; color:{c['txt']}; font-size:12px; }}
            QLineEdit:read-only {{ color:{c['sub']}; }}
        """
        btn_acc = f"""
            QPushButton {{ background:{c['acc']}; border:none; border-radius:6px;
                color:#fff; font-size:12px; font-weight:600; }}
            QPushButton:hover {{ background:{c['acc_hov']}; }}
        """
        btn_neu = f"""
            QPushButton {{ background:{c['surface']}; border:1px solid {c['border2']};
                border-radius:6px; color:{c['txt']}; font-size:12px; font-weight:500; }}
            QPushButton:hover {{ background:{c['hover']}; border-color:{c['acc']}; }}
        """
        combo_style = f"""
            QComboBox {{ background:{c['field_bg']}; border:1px solid {c['border']};
                border-radius:6px; padding:5px 10px; color:{c['txt']}; font-size:13px; min-width:160px; }}
            QComboBox:hover {{ border-color:{c['acc']}; }}
            QComboBox::drop-down {{ border:none; width:20px; }}
            QComboBox QAbstractItemView {{ background:{c['field_bg']}; border:1px solid {c['border']};
                color:{c['txt']}; selection-background-color:{c['acc']}; selection-color:#fff;
                outline:none; padding:2px; }}
            QComboBox QAbstractItemView::item {{ padding:6px 10px; background:{c['field_bg']}; color:{c['txt']}; }}
            QComboBox QAbstractItemView::item:selected {{ background:{c['acc']}; color:#fff; }}
        """
        chk_style = f"""
            QCheckBox {{ font-size:13px; color:{c['txt']}; spacing:8px; background:transparent; }}
            QCheckBox::indicator {{ width:16px; height:16px; border-radius:4px;
                border:2px solid {c['border2']}; background:{c['field_bg']}; }}
            QCheckBox::indicator:checked {{ background:{c['acc']}; border-color:{c['acc']}; }}
        """
        def _sec(text):
            lbl = QLabel(text)
            lbl.setStyleSheet(f"font-weight:700;font-size:10px;color:{c['sub']};letter-spacing:1.2px;margin-top:8px;background:transparent;")
            return lbl
        def _note(text):
            lbl = QLabel(text)
            lbl.setStyleSheet(f"font-size:11px;color:{c['sub']};margin-left:4px;background:transparent;")
            return lbl
        def _lbl(text, w=190):
            lbl = QLabel(text)
            lbl.setStyleSheet(f"font-size:13px;color:{c['txt']};background:transparent;")
            lbl.setFixedWidth(w)
            return lbl

        # İndirme Konumu
        lay.addWidget(_sec("İNDİRME KONUMU"))
        lay.addWidget(_divider(c['border']))
        folder_row = QHBoxLayout(); folder_row.setSpacing(8)
        folder_row.addWidget(_lbl(self._t("varsayilan_klasor")))
        self.txt_folder = QLineEdit()
        self.txt_folder.setPlaceholderText(self._t("klasor_secilmedi"))
        self.txt_folder.setReadOnly(True)
        self.txt_folder.setStyleSheet(txt_style)
        folder_row.addWidget(self.txt_folder, stretch=1)
        btn_browse = QPushButton(self._t("sec")); btn_browse.setFixedSize(72, 32); btn_browse.setStyleSheet(btn_acc)
        btn_browse.clicked.connect(self._choose_folder); folder_row.addWidget(btn_browse)
        btn_clr = QPushButton("Temizle"); btn_clr.setFixedSize(100, 32); btn_clr.setStyleSheet(btn_neu)
        btn_clr.clicked.connect(lambda: self.txt_folder.clear()); folder_row.addWidget(btn_clr)
        lay.addLayout(folder_row)

        # Format Bazlı Klasörler
        lay.addWidget(_sec("FORMAT BAZLI KLASÖRLER"))
        lay.addWidget(_divider(c['border']))
        for fmt_key, fmt_label in [("music_folder", "MP3 Klasörü"), ("video_folder", "MP4 Klasörü")]:
            row = QHBoxLayout(); row.setSpacing(8)
            row.addWidget(_lbl(fmt_label))
            txt = QLineEdit(); txt.setPlaceholderText("Boşsa her indirmede sorulur")
            txt.setReadOnly(True); txt.setStyleSheet(txt_style)
            setattr(self, f"txt_{fmt_key}", txt); row.addWidget(txt, stretch=1)
            btn_b = QPushButton("Seç"); btn_b.setFixedSize(56, 32); btn_b.setStyleSheet(btn_acc)
            btn_b.clicked.connect(lambda checked, t=txt, k=fmt_key: self._choose_fmt_folder(t, k))
            row.addWidget(btn_b)
            btn_x = QPushButton("Temizle"); btn_x.setFixedSize(90, 32); btn_x.setStyleSheet(btn_neu)
            btn_x.clicked.connect(lambda checked, t=txt: t.clear()); row.addWidget(btn_x)
            lay.addLayout(row)

        # Format & Kalite
        lay.addWidget(_divider(c['border']))
        self.cmb_format = QComboBox(); self.cmb_format.setFixedWidth(180)
        self.cmb_format.addItems(["MP3", "MP4"]); self.cmb_format.setStyleSheet(combo_style)
        self.cmb_format.currentTextChanged.connect(self._on_format_changed)
        r = QHBoxLayout(); r.addWidget(_lbl("Format")); r.addWidget(self.cmb_format); r.addStretch()
        lay.addLayout(r)

        self.cmb_quality = QComboBox(); self.cmb_quality.setFixedWidth(180)
        self.cmb_quality.setStyleSheet(combo_style)
        r = QHBoxLayout(); r.addWidget(_lbl("Varsayılan Kalite")); r.addWidget(self.cmb_quality); r.addStretch()
        lay.addLayout(r)

        # Performans
        lay.addWidget(_sec("PERFORMANS"))
        lay.addWidget(_divider(c['border']))

        spin_widget = QWidget(); spin_widget.setStyleSheet("background:transparent;")
        spin_lay = QHBoxLayout(spin_widget); spin_lay.setContentsMargins(0,0,0,0); spin_lay.setSpacing(0)
        from ytdownloader.ui.qt.icon_helper import make_icon
        btn_minus = QPushButton(); btn_minus.setFixedSize(30, 32)
        btn_minus.setIcon(make_icon("minus", c["icon"], 14)); btn_minus.setIconSize(QSize(14, 14))
        btn_minus.setStyleSheet(f"QPushButton{{background:{c['surface']};border:1px solid {c['border2']};border-radius:6px 0 0 6px;}}QPushButton:hover{{background:{c['hover']};}}")
        self._spin_val = QLabel("0"); self._spin_val.setFixedSize(42, 32)
        self._spin_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._spin_val.setStyleSheet(f"QLabel{{background:{c['field_bg']};border-top:1px solid {c['border2']};border-bottom:1px solid {c['border2']};color:{c['txt']};font-size:13px;}}")
        btn_plus = QPushButton(); btn_plus.setFixedSize(30, 32)
        btn_plus.setIcon(make_icon("plus", c["icon"], 14)); btn_plus.setIconSize(QSize(14, 14))
        btn_plus.setStyleSheet(f"QPushButton{{background:{c['surface']};border:1px solid {c['border2']};border-radius:0 6px 6px 0;}}QPushButton:hover{{background:{c['hover']};}}")
        def _dec():
            v = int(self._spin_val.text())
            if v > 0: self._spin_val.setText(str(v-1))
        def _inc():
            v = int(self._spin_val.text())
            if v < 5: self._spin_val.setText(str(v+1))
        btn_minus.clicked.connect(_dec); btn_plus.clicked.connect(_inc)
        spin_lay.addWidget(btn_minus); spin_lay.addWidget(self._spin_val); spin_lay.addWidget(btn_plus)
        r = QHBoxLayout(); r.addWidget(_lbl(self._t("eszamanli_indirme"))); r.addWidget(spin_widget); r.addStretch()
        lay.addLayout(r)
        lay.addWidget(_note(self._t("eszamanli_not")))

        # Sıralı indirme
        self.chk_sequential = QCheckBox("Sıralı indirme (birer birer indir)")
        self.chk_sequential.setStyleSheet(chk_style)
        lay.addWidget(self.chk_sequential)
        lay.addWidget(_note("Aktifken kartları sürükleyerek sırayı belirleyebilirsiniz"))

        # Hız Limiti
        lay.addWidget(_sec("HIZ LİMİTİ"))
        lay.addWidget(_divider(c['border']))
        self.chk_speed_limit = QCheckBox("İndirme hızını sınırla")
        self.chk_speed_limit.setStyleSheet(chk_style)
        lay.addWidget(self.chk_speed_limit)

        spd_row = QHBoxLayout(); spd_row.setSpacing(8)
        spd_row.addWidget(_lbl("Maksimum hız:", 120))
        self.spin_speed = QSpinBox(); self.spin_speed.setRange(1, 100)
        self.spin_speed.setValue(5); self.spin_speed.setSuffix(" MB/s")
        self.spin_speed.setFixedWidth(110); self.spin_speed.setFixedHeight(32)
        self.spin_speed.setStyleSheet(f"""
            QSpinBox {{ background:{c['field_bg']}; border:1px solid {c['border2']};
                border-radius:6px; color:{c['txt']}; font-size:12px; padding:4px 8px; }}
            QSpinBox::up-button, QSpinBox::down-button {{ width:18px; background:{c['surface']}; }}
        """)
        spd_row.addWidget(self.spin_speed); spd_row.addStretch()
        lay.addLayout(spd_row)
        self.chk_speed_limit.stateChanged.connect(lambda s: self.spin_speed.setEnabled(bool(s)))
        self.spin_speed.setEnabled(False)

        lay.addStretch()
        return w

    def _on_format_changed(self, fmt):
        self.cmb_quality.clear()
        if fmt == "MP3":
            self.cmb_quality.addItems(["128 kbps", "192 kbps", "320 kbps"])
        else:
            self.cmb_quality.addItems(["720p", "1080p", "1440p", "2160p"])

    def _plain_lbl(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"font-size:12px;font-weight:700;color:{self._c['sub']};letter-spacing:0.5px;")
        return lbl

    def _choose_fmt_folder(self, txt_widget, setting_key: str):
        desktop = str(Path.home() / "Desktop")
        if not os.path.exists(desktop):
            desktop = str(Path.home() / "Masaüstü")
        current = txt_widget.text() or desktop
        folder = QFileDialog.getExistingDirectory(self, "Klasör Seç", current)
        if folder:
            txt_widget.setText(folder)

    def _choose_folder(self):
        desktop = str(Path.home() / "Desktop")
        if not os.path.exists(desktop):
            desktop = str(Path.home() / "Masaüstü")
        current = self.txt_folder.text() or desktop
        folder = QFileDialog.getExistingDirectory(
            self, self._t("indirme_klasoru_sec"), current
        )
        if folder:
            self.txt_folder.setText(folder)

    def _load_values(self):
        s = self.settings
        lang = s.get("language", "tr")
        for display, code in self.LANGUAGES.items():
            if code == lang:
                self.cmb_lang.setCurrentText(display)
                break
        # Tema
        is_light = s.get("theme", "dark") == "light"
        self.cmb_theme.setCurrentIndex(1 if is_light else 0)
        self.chk_notif.setChecked(s.get("notify_complete", True))
        self.chk_notif_error.setChecked(s.get("notify_error", True))
        self.chk_sound.setChecked(s.get("sound_enabled", True))
        self.chk_open_folder.setChecked(s.get("open_folder_on_complete", False))
        self.chk_start_minimized.setChecked(s.get("start_minimized", False))
        self.chk_confirm_exit.setChecked(s.get("confirm_exit", True))
        folder = s.get("last_download_folder", "")
        if folder and os.path.exists(folder):
            self.txt_folder.setText(folder)
        fmt = s.get("default_format", "MP3").upper()
        self.cmb_format.setCurrentText(fmt)
        self._on_format_changed(fmt)
        quality = s.get("default_quality", "320 kbps" if fmt == "MP3" else "1080p")
        idx = self.cmb_quality.findText(quality)
        if idx >= 0:
            self.cmb_quality.setCurrentIndex(idx)
        self._spin_val.setText(str(s.get("max_concurrent", 0)))
        self.chk_sequential.setChecked(s.get("sequential_mode", False))
        self.chk_speed_limit.setChecked(s.get("speed_limit_enabled", False))
        self.spin_speed.setValue(s.get("speed_limit_mbps", 5))
        self.spin_speed.setEnabled(s.get("speed_limit_enabled", False))
        # Format bazlı klasörler
        for key in ("music_folder", "video_folder"):
            val = s.get(key, "")
            txt = getattr(self, f"txt_{key}", None)
            if txt and val and os.path.exists(val):
                txt.setText(val)

    def _tab_session(self):
        """YouTube oturum (cookie) sekmesi."""
        from ytdownloader.services.auth_service import AuthService
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(10)

        # Başlık
        lbl_title = QLabel("YouTube Oturumu (Cookie)")
        lbl_title.setStyleSheet(f"font-size:14px;font-weight:700;color:{self._c['txt']};")
        lay.addWidget(lbl_title)

        lbl_desc = QLabel(
            "Tarayıcınızdaki YouTube oturumunu aktararak üye içerikleri indirebilirsiniz.\n"
            "İşlem sırasında tarayıcı kısa süreliğine kapatılıp tekrar açılacaktır."
        )
        lbl_desc.setStyleSheet(f"font-size:12px;color:{self._c['sub']};")
        lbl_desc.setWordWrap(True)
        lay.addWidget(lbl_desc)

        # Ayırıcı
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background:{self._c['border']};max-height:1px;")
        lay.addWidget(sep)

        # Tarayıcı butonları
        auth = self.auth_service
        browsers = auth.get_available_browsers() if auth else []

        if browsers:
            lbl_pick = QLabel("Tarayıcınızı seçin:")
            lbl_pick.setStyleSheet(f"font-size:12px;color:{self._c['sub']};margin-top:4px;")
            lay.addWidget(lbl_pick)

            self._session_btns = []
            for name in browsers:
                btn = QPushButton(f"  {name}'den Al")
                btn.setFixedHeight(38)
                btn.setStyleSheet(f"""
                    QPushButton {{ background: {self._c['field_bg']}; border: 1px solid {self._c['border']};
                        border-radius: 8px; color: {self._c['txt']}; font-size: 13px;
                        text-align: left; padding-left: 14px; }}
                    QPushButton:hover {{ border-color: #4a9eff; background: {self._c['hover']}; }}
                    QPushButton:disabled {{ color: {self._c['sub']}; }}
                """)
                btn.clicked.connect(lambda checked, n=name: self._on_session_import(n))
                lay.addWidget(btn)
                self._session_btns.append(btn)
        else:
            lbl_no = QLabel("⚠  Sistemde desteklenen tarayıcı bulunamadı.\nEdge, Chrome veya Firefox kurulu olmalı.")
            lbl_no.setStyleSheet("font-size:12px;color:#f0a500;")
            lay.addWidget(lbl_no)

        # Durum
        self._lbl_session_status = QLabel("")
        self._lbl_session_status.setWordWrap(True)
        self._lbl_session_status.setStyleSheet(f"font-size:12px;color:{self._c['sub']};min-height:18px;")
        lay.addWidget(self._lbl_session_status)

        # Aktif oturum varsa kapat butonu
        if auth and auth._cookie_browser:
            self._lbl_session_status.setText(f"✓  Aktif oturum: {auth._cookie_browser}")
            self._lbl_session_status.setStyleSheet("font-size:12px;color:#28a745;font-weight:600;")
            btn_clear = QPushButton("Oturumu Kapat")
            btn_clear.setFixedHeight(36)
            btn_clear.setStyleSheet("""
                QPushButton { background: transparent; border: 1px solid #e05a5a;
                    border-radius: 7px; color: #e05a5a; font-size: 12px; padding: 0 12px; }
                QPushButton:hover { background: rgba(224,90,90,0.1); }
            """)
            btn_clear.clicked.connect(self._on_session_clear)
            lay.addWidget(btn_clear)

        lay.addStretch()
        return w

    def _on_session_import(self, browser_name: str):
        from PyQt6.QtCore import QThread, pyqtSignal as Signal

        class _T(QThread):
            done = Signal(bool, str)
            def __init__(self, auth, name):
                super().__init__()
                self._auth = auth; self._name = name
            def run(self):
                self._auth.set_cookie_browser(self._name)
                ok, msg = self._auth.test_cookie_browser()
                self.done.emit(ok, msg)

        if not self.auth_service:
            return

        # Butonları devre dışı
        for b in getattr(self, "_session_btns", []):
            b.setEnabled(False)
        self._lbl_session_status.setText(f"⏳  {browser_name} oturumu aktarılıyor...")
        self._lbl_session_status.setStyleSheet("font-size:12px;color:#f0a500;")

        self._session_thread = _T(self.auth_service, browser_name)
        self._session_thread.done.connect(self._on_session_done)
        self._session_thread.start()

    def _on_session_done(self, ok: bool, msg: str):
        import re
        msg = re.sub(r'\x1b\[[0-9;]*m', '', msg).strip()
        for b in getattr(self, "_session_btns", []):
            b.setEnabled(True)
        if ok:
            self._lbl_session_status.setText("✓  Oturum başarıyla aktarıldı!")
            self._lbl_session_status.setStyleSheet("font-size:12px;color:#28a745;font-weight:600;")
        else:
            self._lbl_session_status.setText(f"✗  {msg}")
            self._lbl_session_status.setStyleSheet("font-size:12px;color:#e05a5a;")

    def _on_session_clear(self):
        if self.auth_service:
            self.auth_service.set_cookie_browser(None)
            self.auth_service.set_logged_in(False)
        self._lbl_session_status.setText("Oturum kapatıldı.")
        self._lbl_session_status.setStyleSheet(f"font-size:12px;color:{self._c['sub']};")

    def _save(self):
        s = self.settings
        s["language"]         = self.LANGUAGES.get(self.cmb_lang.currentText(), "tr")
        s["theme"]            = "light" if self.cmb_theme.currentIndex() == 1 else "dark"
        s["notify_complete"]       = self.chk_notif.isChecked()
        s["notify_error"]          = self.chk_notif_error.isChecked()
        s["sound_enabled"]           = self.chk_sound.isChecked()
        s["open_folder_on_complete"] = self.chk_open_folder.isChecked()
        s["start_minimized"]         = self.chk_start_minimized.isChecked()
        s["confirm_exit"]            = self.chk_confirm_exit.isChecked()
        s["default_format"]   = self.cmb_format.currentText()
        s["default_quality"]  = self.cmb_quality.currentText()
        s["max_concurrent"]      = int(self._spin_val.text())
        s["sequential_mode"]     = self.chk_sequential.isChecked()
        s["speed_limit_enabled"] = self.chk_speed_limit.isChecked()
        s["speed_limit_mbps"]    = self.spin_speed.value()
        folder = self.txt_folder.text()
        if folder and os.path.exists(folder):
            s["last_download_folder"] = folder
        elif not folder:
            s.pop("last_download_folder", None)
        # Format bazlı klasörler
        for key in ("music_folder", "video_folder"):
            txt = getattr(self, f"txt_{key}", None)
            if txt:
                val = txt.text()
                if val and os.path.exists(val):
                    s[key] = val
                elif not val:
                    s.pop(key, None)
        self.settings_manager.save(s)
        # Temayı hemen uygula
        from ytdownloader.ui.qt.theme import theme_manager
        from PyQt6.QtWidgets import QApplication
        theme_manager.set_theme(s["theme"])
        QApplication.instance().setStyleSheet(theme_manager.stylesheet())
        self.accept()


class AboutDialog(QDialog):
    def __init__(self, parent, i18n: I18nService | None = None):
        super().__init__(parent)
        self._i18n = i18n or get_i18n()
        from ytdownloader.ui.qt.theme import theme_manager
        self._is_dark = theme_manager.current == "dark"
        self.setFixedSize(420, 460)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        self._build_ui()

    def _t(self, key): return self._i18n.t(key)

    def _build_ui(self):
        is_dark = self._is_dark
        bg       = "#1a1d27" if is_dark else "#f0f2f7"
        card_bg  = "#12141f" if is_dark else "#ffffff"
        border   = "#2e3348" if is_dark else "#d0d5e0"
        txt      = "#e8eaf0" if is_dark else "#0a0a0a"
        sub      = "#9da3b4" if is_dark else "#555a6e"
        acc      = "#c0392b"
        desc_clr = "#c0c5d0" if is_dark else "#444455"
        sep_clr  = "#2e3348" if is_dark else "#d0d5e0"

        self.setWindowTitle(self._t("hakkinda_title"))
        self.setStyleSheet(f"QDialog {{ background: {bg}; }} QLabel {{ color: {txt}; }}")

        root = QVBoxLayout(self)
        root.setContentsMargins(36, 28, 36, 24)
        root.setSpacing(0)

        logo = QLabel()
        logo.setFixedSize(72, 72)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setPixmap(self._make_logo(72))
        root.addWidget(logo, alignment=Qt.AlignmentFlag.AlignHCenter)
        root.addSpacing(14)

        lbl_name = QLabel("YouTube İndirici")
        lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_name.setStyleSheet(f"font-size:22px;font-weight:700;color:{txt};")
        root.addWidget(lbl_name)

        from ytdownloader.config.constants import APP_VERSION
        lbl_ver = QLabel(f"v{APP_VERSION}")
        lbl_ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_ver.setStyleSheet("font-size:13px;color:#c0392b;font-weight:600;")
        root.addWidget(lbl_ver)

        root.addSpacing(18)
        f = QFrame(); f.setFrameShape(QFrame.Shape.HLine)
        f.setStyleSheet(f"background:{sep_clr};max-height:1px;")
        root.addWidget(f)
        root.addSpacing(14)

        desc = QLabel(self._t("hakkinda_desc"))
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet(f"font-size:12px;color:{desc_clr};line-height:1.8;")
        desc.setWordWrap(True)
        root.addWidget(desc)

        root.addSpacing(14)

        # Geliştirici bilgileri
        info_frame = QFrame()
        info_frame.setStyleSheet(f"""
            QFrame {{ background: {card_bg}; border-radius: 8px; border: 1px solid {border}; }}
            QLabel {{ background: transparent; border: none; }}
        """)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(16, 12, 16, 12)
        info_layout.setSpacing(6)

        def _info_row(icon, text, url=None):
            row = QHBoxLayout()
            icon_lbl = QLabel(icon)
            icon_lbl.setFixedWidth(20)
            icon_lbl.setStyleSheet(f"font-size:13px; background:transparent; border:none;")
            row.addWidget(icon_lbl)
            if url:
                lbl = QLabel(f'<a href="{url}" style="color:#c0392b;text-decoration:none;">{text}</a>')
                lbl.setOpenExternalLinks(True)
            else:
                lbl = QLabel(text)
                lbl.setStyleSheet(f"font-size:12px;color:{sub}; background:transparent; border:none;")
            row.addWidget(lbl)
            row.addStretch()
            info_layout.addLayout(row)

        _info_row("👤", "IzzmooPro")
        _info_row("🐙", "github.com/IzzmooPro", "https://github.com/IzzmooPro")
        _info_row("📧", "IzzmooPro@gmail.com", "mailto:IzzmooPro@gmail.com")

        root.addWidget(info_frame)
        root.addSpacing(12)

        # Güncellemeleri Denetle butonu
        btn_update = QPushButton("🔄  Güncellemeleri Denetle")
        btn_update.setFixedSize(220, 36)
        btn_update.setStyleSheet(f"""
            QPushButton {{ background: transparent; border: 1px solid {border};
                border-radius: 8px; color: {sub}; font-size: 12px; font-weight: 500; }}
            QPushButton:hover {{ background: {"#2e3348" if is_dark else "#e0e4ef"};
                color: {txt}; border-color: {acc}; }}
        """)
        btn_update.clicked.connect(self._check_updates)
        root.addWidget(btn_update, alignment=Qt.AlignmentFlag.AlignHCenter)

        root.addSpacing(8)

        btn = QPushButton(self._t("kapat"))
        btn.setFixedSize(110, 36)
        btn.setStyleSheet(f"""
            QPushButton {{ background: {acc}; border: none; border-radius: 8px;
                color: #fff; font-size: 13px; font-weight: 600; }}
            QPushButton:hover {{ background: #a93226; }}
        """)
        btn.clicked.connect(self.accept)
        root.addWidget(btn, alignment=Qt.AlignmentFlag.AlignHCenter)

    def _check_updates(self) -> None:
        """Güncelleme kontrolünü UpdateService üzerinden yapar."""
        from ytdownloader.services.update_service import UpdateService
        # Instance'ı attribute olarak sakla — thread bitmeden GC'ye gitmesin.
        self._update_svc = UpdateService(self)
        self._update_svc.check(parent_widget=self, show_no_update=True)

    @staticmethod
    def _make_logo(size):
        px = QPixmap(size, size)
        px.fill(Qt.GlobalColor.transparent)
        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor("#ff0000"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, size, size, size * 0.18, size * 0.18)
        tri = QPolygonF([
            QPointF(size * 0.36, size * 0.25),
            QPointF(size * 0.36, size * 0.75),
            QPointF(size * 0.78, size * 0.50),
        ])
        p.setBrush(QColor("#ffffff"))
        p.drawPolygon(tri)
        p.end()
        return px
