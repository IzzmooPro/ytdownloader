# -*- coding: utf-8 -*-
"""TrayIcon — Sistem tepsisi ikonu ve menüsü."""

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPolygonF
from PyQt6.QtCore import Qt, QPointF
from ytdownloader.config.constants import APP_VERSION


def _make_tray_icon(size: int = 64) -> QIcon:
    """Kırmızı YouTube play ikonu oluşturur."""
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
    return QIcon(px)


class TrayIcon(QSystemTrayIcon):
    """Uygulama sistem tepsisi ikonu."""

    def __init__(self, main_window):
        super().__init__(_make_tray_icon(), main_window)
        self._win = main_window
        self.setToolTip(f"YouTube İndirici v{APP_VERSION}")
        self._build_menu()
        self.activated.connect(self._on_activated)

    def _build_menu(self):
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background: #1a1d27; border: 1px solid #2e3348;
                border-radius: 8px; padding: 4px;
            }
            QMenu::item {
                padding: 8px 20px; color: #e8eaf0;
                font-size: 13px; border-radius: 5px;
            }
            QMenu::item:selected { background: #2e3348; }
            QMenu::separator { height: 1px; background: #2e3348; margin: 4px 8px; }
        """)

        self._a_show = menu.addAction("Göster / Gizle")
        self._a_show.triggered.connect(self._toggle_window)

        menu.addSeparator()

        self._a_paste = menu.addAction("URL Yapıştır")
        self._a_paste.triggered.connect(self._paste_from_tray)

        menu.addSeparator()

        self._a_quit = menu.addAction("Çıkış")
        self._a_quit.triggered.connect(self._quit)

        self.setContextMenu(menu)

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._toggle_window()

    def _toggle_window(self):
        if self._win.isVisible():
            self._win.hide()
            self._a_show.setText("Göster")
        else:
            self._win.show()
            self._win.raise_()
            self._win.activateWindow()
            self._a_show.setText("Gizle")

    def _quit(self):
        """
        Kontrollü çıkış: pencereden kapatmayla aynı onay akışı çalışsın.
        QApplication.quit doğrudan çağrılırsa closeEvent atlanır — aktif
        indirme varken sormadan kapanırdı.
        """
        if hasattr(self._win, "quit_from_tray"):
            self._win.quit_from_tray()
        else:
            QApplication.quit()

    def _paste_from_tray(self):
        self._win.show()
        self._win.raise_()
        self._win.activateWindow()
        self._win.paste_url()

    def notify(self, title: str, message: str):
        """Sistem bildirimi göster."""
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.showMessage(title, message,
                             QSystemTrayIcon.MessageIcon.Information, 3000)

    def update_tooltip(self, active: int, completed: int):
        self.setToolTip(
            f"YouTube İndirici v{APP_VERSION}\n"
            f"İndiriliyor: {active}  |  Tamamlandı: {completed}"
        )
