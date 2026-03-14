# -*- coding: utf-8 -*-
"""
Theme — PyQt6 için light/dark QSS stylesheet sistemi.
CSS benzeri sözdizimi, değişken tabanlı renk sistemi.
"""

from dataclasses import dataclass


@dataclass
class ColorPalette:
    # Arkaplan katmanları
    bg_base:       str   # En dış arkaplan
    bg_surface:    str   # Kart arkaplanı
    bg_elevated:   str   # Dialog, popup arkaplanı
    bg_hover:      str   # Hover durumu

    # Kenarlık
    border:        str
    border_focus:  str

    # Metin
    text_primary:  str
    text_secondary: str
    text_muted:    str

    # Accent renkler
    accent:        str   # Mavi — ana işlem
    accent_hover:  str
    success:       str   # Yeşil
    warning:       str   # Turuncu
    error:         str   # Kırmızı
    info:          str   # Açık mavi

    # Progress bar
    progress_bg:   str
    progress_fill: str

    # Scrollbar
    scroll_bg:     str
    scroll_handle: str


LIGHT = ColorPalette(
    bg_base       = "#f0f2f5",
    bg_surface    = "#ffffff",
    bg_elevated   = "#e8ecf4",
    bg_hover      = "#dce2ef",
    border        = "#b8bfc8",
    border_focus  = "#c0392b",
    text_primary  = "#1a1a2e",
    text_secondary = "#495057",
    text_muted    = "#868e96",
    accent        = "#c0392b",
    accent_hover  = "#a93226",
    success       = "#28a745",
    warning       = "#fd7e14",
    error         = "#dc3545",
    info          = "#17a2b8",
    progress_bg   = "#e9ecef",
    progress_fill = "#c0392b",
    scroll_bg     = "#f0f2f5",
    scroll_handle = "#adb5bd",
)

DARK = ColorPalette(
    bg_base       = "#0f1117",
    bg_surface    = "#1a1d27",
    bg_elevated   = "#22263a",
    bg_hover      = "#2a2f45",
    border        = "#2e3348",
    border_focus  = "#c0392b",
    text_primary  = "#e8eaf0",
    text_secondary = "#9da3b4",
    text_muted    = "#6b7280",
    accent        = "#c0392b",
    accent_hover  = "#a93226",
    success       = "#2ecc71",
    warning       = "#f39c12",
    error         = "#e74c3c",
    info          = "#3498db",
    progress_bg   = "#2e3348",
    progress_fill = "#c0392b",
    scroll_bg     = "#1a1d27",
    scroll_handle = "#3d4460",
)


def build_stylesheet(p: ColorPalette) -> str:
    """ColorPalette'ten tam QSS stylesheet üretir."""
    return f"""
/* ── Genel ─────────────────────────────────────────────────────────── */
QMainWindow, QDialog {{
    background-color: {p.bg_base};
    color: {p.text_primary};
}}

QWidget {{
    font-family: "Segoe UI", "SF Pro Display", "Ubuntu", sans-serif;
    font-size: 13px;
    color: {p.text_primary};
    background-color: transparent;
}}

/* ── Scrollbar ──────────────────────────────────────────────────────── */
QScrollArea {{
    border: none;
    background-color: {p.bg_base};
}}

QScrollBar:vertical {{
    background: {p.scroll_bg};
    width: 8px;
    border-radius: 4px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {p.scroll_handle};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {p.accent};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

/* ── Toolbar / Top bar ──────────────────────────────────────────────── */
#topbar {{
    background-color: {p.bg_surface};
    border-bottom: 1px solid {p.border};
    padding: 8px 16px;
}}

/* ── Butonlar ───────────────────────────────────────────────────────── */
QPushButton {{
    background-color: {p.bg_elevated};
    color: {p.text_primary};
    border: none;
    border-radius: 7px;
    padding: 7px 16px;
    font-weight: 600;
    font-size: 13px;
    letter-spacing: 0.2px;
}}
QPushButton:hover {{
    background-color: {p.bg_hover};
}}
QPushButton:pressed {{
    background-color: {p.border};
}}
QPushButton:disabled {{
    background-color: {p.border};
    color: {p.text_muted};
}}

QPushButton#btn_paste {{
    background-color: {p.bg_elevated};
    color: {p.text_primary};
    border: 1px solid {p.border};
}}
QPushButton#btn_paste:hover {{
    background-color: {p.bg_hover};
    border-color: {p.accent};
    color: {p.accent};
}}
QPushButton#btn_download_all {{
    background-color: {p.bg_elevated};
    color: {p.text_primary};
    border: 1px solid {p.border};
}}
QPushButton#btn_download_all:hover {{
    background-color: {p.bg_hover};
    border-color: {p.accent};
    color: {p.accent};
}}
QPushButton#btn_clear {{
    background-color: {p.bg_elevated};
    color: {p.text_primary};
    border: 1px solid {p.border};
}}
QPushButton#btn_clear:hover {{
    background-color: {p.bg_hover};
    border-color: {p.error};
    color: {p.error};
}}
QPushButton#btn_icon {{
    background-color: {p.bg_elevated};
    border: 1.5px solid {p.border};
    border-radius: 8px;
    padding: 3px 8px;
    color: {p.text_secondary};
    font-size: 12px;
    font-family: "Segoe UI Symbol", "Segoe MDL2 Assets", "Arial Unicode MS", sans-serif;
}}
QPushButton#btn_icon:hover {{
    background-color: {p.bg_hover};
    border-color: {p.accent};
    color: {p.accent};
}}
QPushButton#btn_action {{
    background-color: {p.accent};
    border: none;
    border-radius: 8px;
    padding: 3px 8px;
}}
QPushButton#btn_action:hover {{
    background-color: {p.accent_hover};
}}
QPushButton#btn_action:disabled {{
    background-color: {p.border};
    color: {p.text_muted};
}}
/* Tamamlandı sonrası küçük soluk retry butonu */
QPushButton#btn_action_done {{
    background-color: transparent;
    border: 1px solid {p.border};
    border-radius: 7px;
}}
QPushButton#btn_action_done:hover {{
    background-color: {p.bg_hover};
    border-color: {p.accent};
}}
QPushButton#btn_remove {{
    background-color: transparent;
    border: none;
    color: {p.text_muted};
    font-size: 16px;
    padding: 2px 6px;
    border-radius: 4px;
}}
QPushButton#btn_remove:hover {{
    background-color: #fee2e2;
    color: {p.error};
}}

/* ── Video Kartı ────────────────────────────────────────────────────── */
#VideoCard {{
    background-color: {p.bg_surface};
    border: 2px solid {p.border};
    border-radius: 12px;
    margin: 4px 8px;
}}
#VideoCard:hover {{
    border: 2px solid {p.accent};
}}
#VideoCard[dragging="true"] {{
    border: 2px solid #3b82f6;
    background-color: rgba(59, 130, 246, 0.08);
    border-radius: 12px;
}}

#card_title {{
    font-size: 14px;
    font-weight: 700;
    color: {p.text_primary};
}}
#card_meta {{
    font-size: 11px;
    color: {p.text_muted};
}}
#card_channel {{
    font-size: 12px;
    color: {p.text_secondary};
    font-weight: 500;
}}

/* ── Progress Bar ───────────────────────────────────────────────────── */
QProgressBar {{
    background-color: {p.progress_bg};
    border: none;
    border-radius: 5px;
    height: 10px;
    text-align: center;
}}
QProgressBar::chunk {{
    border-radius: 5px;
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 {p.accent},
        stop:1 {p.accent_hover}
    );
}}
QProgressBar[state="success"]::chunk {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 {p.success},
        stop:1 #20c04a
    );
}}
QProgressBar[state="error"]::chunk {{
    background: {p.error};
}}
QProgressBar[state="warning"]::chunk {{
    background: {p.warning};
}}

/* ── Combobox ───────────────────────────────────────────────────────── */
QComboBox {{
    background-color: {p.bg_surface};
    border: 1px solid {p.border};
    border-radius: 6px;
    padding: 5px 10px;
    color: {p.text_primary};
    font-size: 12px;
    min-width: 80px;
}}
QComboBox:hover {{
    border-color: {p.accent};
}}
QComboBox:focus {{
    border-color: {p.border_focus};
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {p.text_muted};
    width: 0;
    height: 0;
    margin-right: 6px;
}}
QComboBox QAbstractItemView {{
    background-color: {p.bg_elevated};
    border: 1px solid {p.border};
    border-radius: 0px;
    selection-background-color: {p.accent};
    selection-color: white;
    padding: 0px;
    margin: 0px;
    outline: none;
    color: {p.text_primary};
}}
QComboBox QAbstractItemView::item {{
    background-color: {p.bg_elevated};
    color: {p.text_primary};
    padding: 6px 12px;
    min-height: 24px;
    border: none;
}}
QComboBox QAbstractItemView::item:hover {{
    background-color: {p.bg_hover};
    color: {p.text_primary};
}}
QComboBox QAbstractItemView::item:selected {{
    background-color: {p.accent};
    color: white;
}}
QComboBox QAbstractScrollArea {{
    background-color: {p.bg_elevated};
    border: none;
    padding: 0px;
    margin: 0px;
}}
QComboBox QScrollBar:vertical {{
    width: 0px;
}}

/* ── Label ──────────────────────────────────────────────────────────── */
QLabel {{
    color: {p.text_primary};
    background-color: transparent;
}}

/* ── Status Badge ───────────────────────────────────────────────────── */
#badge_downloading  {{ color: {p.accent};   font-weight: 700; font-size: 11px; }}
#badge_completed    {{ color: {p.success};  font-weight: 700; font-size: 11px; }}
#badge_paused       {{ color: {p.warning};  font-weight: 700; font-size: 11px; }}
#badge_error        {{ color: {p.error};    font-weight: 700; font-size: 11px; }}
#badge_retrying     {{ color: {p.warning};  font-weight: 700; font-size: 11px; }}
#badge_queued       {{ color: {p.text_muted}; font-size: 11px; }}

/* ── Status Bar ─────────────────────────────────────────────────────── */
#statusbar {{
    background-color: {p.bg_surface};
    border-top: 1px solid {p.border};
    padding: 6px 16px;
    font-size: 12px;
    color: {p.text_secondary};
}}

/* ── Radio Buttons ──────────────────────────────────────────────────── */
QRadioButton {{
    color: {p.text_secondary};
    font-size: 12px;
    spacing: 6px;
}}
QRadioButton::indicator {{
    width: 14px;
    height: 14px;
    border-radius: 7px;
    border: 2px solid {p.border};
    background: {p.bg_surface};
}}
QRadioButton::indicator:checked {{
    border-color: {p.accent};
    background-color: {p.accent};
}}

/* ── Menu Bar ───────────────────────────────────────────────────────── */
QMenuBar {{
    background-color: {p.bg_surface};
    color: {p.text_primary};
    border-bottom: 1px solid {p.border};
    padding: 2px;
}}
QMenuBar::item {{
    padding: 4px 10px;
    border-radius: 4px;
}}
QMenuBar::item:selected {{
    background-color: {p.bg_hover};
}}
QMenu {{
    background-color: {p.bg_elevated};
    border: 1px solid {p.border};
    border-radius: 8px;
    padding: 4px;
}}
QMenu::item {{
    padding: 7px 20px;
    border-radius: 4px;
    color: {p.text_primary};
}}
QMenu::item:selected {{
    background-color: {p.accent};
    color: white;
}}
QMenu::separator {{
    height: 1px;
    background-color: {p.border};
    margin: 4px 8px;
}}

/* ── Bildirim popup ─────────────────────────────────────────────────── */
#NotificationPopup {{
    background-color: {p.bg_elevated};
    border: 1px solid {p.border};
    border-radius: 10px;
}}

/* ── Boş ekran (empty state) ────────────────────────────────────────── */
#empty_state {{
    background: transparent;
}}
QLabel#empty_sub {{
    font-size: 15px;
    color: {p.text_secondary};
    background: transparent;
}}
QLabel#empty_hint {{
    font-size: 12px;
    color: {p.text_primary};
    background: {p.bg_hover};
    padding: 5px 14px;
    border-radius: 14px;
    border: 1px solid {p.border};
}}
"""


class ThemeManager:
    """Uygulama genelinde tema yönetimi."""

    def __init__(self):
        self._current = "light"
        self._palettes = {"light": LIGHT, "dark": DARK}

    @property
    def current(self) -> str:
        return self._current

    @property
    def palette(self) -> ColorPalette:
        return self._palettes[self._current]

    def stylesheet(self) -> str:
        return build_stylesheet(self.palette)

    def toggle(self) -> str:
        self._current = "dark" if self._current == "light" else "light"
        return self._current

    def set_theme(self, name: str) -> None:
        if name in self._palettes:
            self._current = name


# Singleton
theme_manager = ThemeManager()
