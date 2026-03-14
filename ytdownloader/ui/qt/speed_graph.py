# -*- coding: utf-8 -*-
"""SpeedGraph — indirme hızını gösteren mini sparkline widget."""

from collections import deque
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QPen, QColor, QPainterPath, QLinearGradient


class SpeedGraph(QWidget):
    """
    Son N hız ölçümünü çizgi grafik olarak gösterir.
    İndirme tamamlanınca animasyonu dondurur.
    """

    MAX_POINTS = 40

    def __init__(self, parent=None, color: str = "#4a9eff"):
        super().__init__(parent)
        self._color    = QColor(color)
        self._data: deque[float] = deque(maxlen=self.MAX_POINTS)
        self._frozen   = False
        self.setFixedSize(200, 24)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setVisible(False)

    # ── Public API ────────────────────────────────────────────────────────────

    def add_point(self, speed_bps: float):
        if self._frozen:
            return
        mb = speed_bps / (1024 * 1024)
        self._data.append(max(0.0, mb))
        self.setVisible(True)
        self.update()

    def freeze(self, color: str | None = None):
        """İndirme bitince grafiği dondur, renk opsiyonel."""
        self._frozen = True
        if color:
            self._color = QColor(color)
        self.update()

    def reset(self):
        self._data.clear()
        self._frozen = False
        self.setVisible(False)
        self.update()

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        if len(self._data) < 2:
            return

        w, h   = self.width(), self.height()
        points = list(self._data)
        n      = len(points)
        mx     = max(points) or 1.0

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Koordinatları hesapla
        coords: list[QPointF] = []
        for i, v in enumerate(points):
            x = i / (n - 1) * w
            y = h - (v / mx) * (h - 4) - 2
            coords.append(QPointF(x, y))

        # Dolgu (gradient)
        path = QPainterPath()
        path.moveTo(QPointF(0, h))
        for pt in coords:
            path.lineTo(pt)
        path.lineTo(QPointF(w, h))
        path.closeSubpath()

        grad = QLinearGradient(0, 0, 0, h)
        fill = QColor(self._color)
        fill.setAlpha(55)
        grad.setColorAt(0, fill)
        fill2 = QColor(self._color)
        fill2.setAlpha(0)
        grad.setColorAt(1, fill2)
        painter.fillPath(path, grad)

        # Çizgi
        line_path = QPainterPath()
        line_path.moveTo(coords[0])
        for pt in coords[1:]:
            line_path.lineTo(pt)

        pen = QPen(self._color, 1.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPath(line_path)

        painter.end()
