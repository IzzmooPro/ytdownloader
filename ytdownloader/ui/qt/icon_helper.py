# -*- coding: utf-8 -*-
"""
IconHelper — SVG dosyalarını QIcon/QPixmap'e çevirir.
stroke="currentColor" olan SVG'lere renk enjekte eder.
"""

import re
from pathlib import Path
from PyQt6.QtGui import QIcon, QPixmap, QPainter
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtCore import QByteArray

_ICONS_DIR = Path(__file__).parent.parent.parent / "assets" / "icons" / "svg"


def _svg_with_color(name: str, color: str) -> bytes:
    """SVG dosyasını okur, stroke rengini enjekte eder."""
    path = _ICONS_DIR / f"{name}.svg"
    svg = path.read_text(encoding="utf-8")
    # currentColor → gerçek renk
    svg = svg.replace("currentColor", color)
    return svg.encode("utf-8")


def make_icon(name: str, color: str = "#ffffff", size: int = 18) -> QIcon:
    """SVG dosyasından renkli QIcon üretir."""
    svg_bytes = _svg_with_color(name, color)
    renderer = QSvgRenderer(QByteArray(svg_bytes))
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    painter = QPainter(px)
    renderer.render(painter)
    painter.end()
    return QIcon(px)


def make_pixmap(name: str, color: str = "#ffffff", size: int = 18) -> QPixmap:
    """SVG dosyasından renkli QPixmap üretir."""
    svg_bytes = _svg_with_color(name, color)
    renderer = QSvgRenderer(QByteArray(svg_bytes))
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    painter = QPainter(px)
    renderer.render(painter)
    painter.end()
    return px


def set_icon(btn, name: str, color: str = "#e8eaf0", size: int = 16):
    """Butona SVG ikon ata, metni temizle."""
    icon = make_icon(name, color, size)
    btn.setIcon(icon)
    btn.setIconSize(QSize(size, size))
    btn.setText("")
