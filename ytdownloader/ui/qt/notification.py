# -*- coding: utf-8 -*-
"""
NotificationToast — sağ alt köşede beliren, fade-out ile kaybolan bildirim.
NotificationCenter — bildirim geçmişi ve yönetimi.
"""

from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QFrame
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt6.QtGui import QFont


class NotificationToast(QWidget):
    """Tek bir toast bildirimi."""

    closed = pyqtSignal()

    LEVEL_STYLES = {
        "success": ("#d1fae5", "#065f46", "#34d399"),
        "error":   ("#fee2e2", "#991b1b", "#f87171"),
        "warning": ("#fff7ed", "#92400e", "#fb923c"),
        "info":    ("#eff6ff", "#1e40af", "#60a5fa"),
    }
    LEVEL_ICONS = {
        "success": "✅",
        "error":   "❌",
        "warning": "⚠️",
        "info":    "ℹ️",
    }

    def __init__(self, title: str, message: str, level: str = "info", parent=None):
        super().__init__(None,
                         Qt.WindowType.FramelessWindowHint |
                         Qt.WindowType.WindowStaysOnTopHint |
                         Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        bg, text_color, accent = self.LEVEL_STYLES.get(level, self.LEVEL_STYLES["info"])
        icon = self.LEVEL_ICONS.get(level, "ℹ️")

        # Ana frame
        frame = QFrame(self)
        frame.setObjectName("NotificationPopup")
        frame.setStyleSheet(f"""
            QFrame#NotificationPopup {{
                background-color: {bg};
                border: 1px solid {accent};
                border-left: 4px solid {accent};
                border-radius: 10px;
            }}
        """)
        frame.setFixedWidth(340)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        # Başlık satırı
        header = QHBoxLayout()
        lbl_icon = QLabel(icon)
        lbl_icon.setStyleSheet("font-size: 15px; background: transparent;")
        header.addWidget(lbl_icon)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(
            f"font-weight: 700; font-size: 13px; color: {text_color}; background: transparent;"
        )
        header.addWidget(lbl_title, stretch=1)

        btn_close = QPushButton("✕")
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none;
                color: {text_color}; font-size: 12px; padding: 0 2px;
            }}
            QPushButton:hover {{ color: #000; }}
        """)
        btn_close.setFixedSize(20, 20)
        btn_close.clicked.connect(self._close_now)
        header.addWidget(btn_close)

        layout.addLayout(header)

        if message:
            lbl_msg = QLabel(message)
            lbl_msg.setWordWrap(True)
            lbl_msg.setStyleSheet(
                f"font-size: 12px; color: {text_color}; background: transparent; opacity: 0.85;"
            )
            lbl_msg.setMaximumWidth(300)
            layout.addWidget(lbl_msg)

        # Outer layout (şeffaf arka plan için)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(frame)

        self.adjustSize()

        # Fade animasyonu
        self._opacity_anim = QPropertyAnimation(self, b"windowOpacity")
        self._opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # 3.5 sn sonra fade-out başlat
        QTimer.singleShot(3500, self._start_fade_out)

    def _start_fade_out(self):
        self._opacity_anim.setDuration(600)
        self._opacity_anim.setStartValue(1.0)
        self._opacity_anim.setEndValue(0.0)
        self._opacity_anim.finished.connect(self._close_now)
        self._opacity_anim.start()

    def _close_now(self):
        self.closed.emit()
        self.close()
        self.deleteLater()

    def mousePressEvent(self, event):
        self._close_now()


class NotificationCenter:
    """
    Bildirim yöneticisi.
    Toast'ları sağ alt köşede üst üste yığar.
    """

    def __init__(self, parent_window):
        self._parent = parent_window
        self._toasts: list[NotificationToast] = []
        self._history: list[dict] = []
        self._unread = 0

    def show(self, title: str, message: str, level: str = "info"):
        """Yeni bir toast bildirimi göster."""
        from datetime import datetime
        self._history.append({
            "title": title, "message": message,
            "level": level, "time": datetime.now(), "read": False
        })
        self._unread += 1

        toast = NotificationToast(title, message, level, None)
        toast.closed.connect(lambda t=toast: self._on_toast_closed(t))
        self._toasts.append(toast)
        # Önce göster, sonra boyut kesinleşince konumlandır
        toast.show()
        toast.adjustSize()
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(10, self._reposition)

    # backward compat — eski Tkinter API
    def add_notification(self, title: str, message: str, level: str = "info",
                         show_popup: bool = True):
        if show_popup:
            self.show(title, message, level)

    def _on_toast_closed(self, toast: NotificationToast):
        if toast in self._toasts:
            self._toasts.remove(toast)
        self._reposition()

    def _reposition(self):
        """Aktif toast'ları ana pencerenin sağ alt köşesine yığ."""
        if not self._parent or not self._parent.isVisible():
            return

        win   = self._parent.frameGeometry()
        tw    = 350   # toast genişliği
        margin = 10
        x = win.right() - tw - margin
        y = win.bottom() - margin

        for toast in reversed(self._toasts):
            if not toast.isVisible():
                continue
            toast.adjustSize()
            y -= toast.height() + 6
            toast.move(x, y)
            toast.raise_()

    def get_unread_count(self) -> int:
        return self._unread

    def mark_all_read(self):
        self._unread = 0
        for item in self._history:
            item["read"] = True
