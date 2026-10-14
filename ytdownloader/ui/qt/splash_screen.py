# -*- coding: utf-8 -*-
"""SplashScreen — program açılışında gösterilen animasyonlu karşılama ekranı."""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QApplication
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty, QObject
from PyQt6.QtGui import (QPainter, QColor, QPolygonF, QPixmap, QPen,
                          QLinearGradient, QFont, QFontMetrics)
from PyQt6.QtCore import QPointF, QRectF
from ytdownloader.config.constants import APP_VERSION


class _AnimatedValue(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0.0

    def get_value(self): return self._value
    def set_value(self, v): self._value = v
    value = pyqtProperty(float, get_value, set_value)


class SplashScreen(QWidget):
    """
    Program açılışında gösterilen splash ekranı.
    - YouTube logosu (animasyonlu puls)
    - Program adı ve versiyonu
    - Adım adım yükleme mesajları
    - Smooth progress bar
    """

    STEPS = [
        "Başlatılıyor...",
        "Ayarlar yükleniyor...",
        "Tema uygulanıyor...",
        "İndirme motoru hazırlanıyor...",
        "FFmpeg kontrol ediliyor...",
        "Arayüz oluşturuluyor...",
        "Hazır!",
    ]

    def __init__(self):
        super().__init__()
        self._progress  = 0
        self._pulse     = 0.0
        self._step_idx  = 0

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SplashScreen
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(420, 340)
        self._center_on_screen()
        self._build_ui()
        self._start_pulse()

    # ── UI ───────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Ana kart
        self._card = QWidget()
        self._card.setObjectName("splash_card")
        self._card.setStyleSheet("""
            #splash_card {
                background: #12141f;
                border-radius: 18px;
                border: 1px solid #2e3348;
            }
        """)
        card_lay = QVBoxLayout(self._card)
        card_lay.setContentsMargins(40, 44, 40, 36)
        card_lay.setSpacing(0)

        # Logo
        self._logo_lbl = QLabel()
        self._logo_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._logo_lbl.setFixedHeight(88)
        card_lay.addWidget(self._logo_lbl)
        card_lay.addSpacing(20)

        # Başlık
        lbl_title = QLabel("YouTube İndirici")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        lbl_title.setStyleSheet(
            "font-size: 26px; font-weight: 700; color: #e8eaf0; letter-spacing: -0.5px;"
        )
        card_lay.addWidget(lbl_title)
        card_lay.addSpacing(6)

        # Versiyon
        lbl_ver = QLabel(f"v{APP_VERSION}")
        lbl_ver.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        lbl_ver.setStyleSheet("font-size: 13px; color: #4a9eff; font-weight: 600;")
        card_lay.addWidget(lbl_ver)
        card_lay.addSpacing(32)

        # Progress bar
        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(5)
        self._bar.setStyleSheet("""
            QProgressBar {
                background: #1e2030;
                border-radius: 3px;
                border: none;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4a9eff, stop:1 #6ec6ff);
                border-radius: 3px;
            }
        """)
        card_lay.addWidget(self._bar)
        card_lay.addSpacing(12)

        # Adım mesajı
        self._lbl_step = QLabel(self.STEPS[0])
        self._lbl_step.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._lbl_step.setStyleSheet("font-size: 12px; color: #6b7280;")
        card_lay.addWidget(self._lbl_step)

        card_lay.addStretch()

        # Alt not
        lbl_copy = QLabel("Tüm hakları saklıdır")
        lbl_copy.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        lbl_copy.setStyleSheet("font-size: 10px; color: #3d4460;")
        card_lay.addWidget(lbl_copy)

        root.addWidget(self._card)
        self._draw_logo(1.0)

    def _draw_logo(self, scale: float = 1.0):
        size = int(80 * scale)
        px = QPixmap(88, 88)
        px.fill(Qt.GlobalColor.transparent)
        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        offset = (88 - size) // 2

        # Glow efekti
        glow = QColor("#ff0000")
        glow.setAlpha(int(30 * scale))
        p.setBrush(glow)
        p.setPen(Qt.PenStyle.NoPen)
        glow_size = size + 12
        glow_off  = (88 - glow_size) // 2
        p.drawRoundedRect(glow_off, glow_off, glow_size, glow_size,
                          glow_size * 0.2, glow_size * 0.2)

        # Kırmızı kutu
        p.setBrush(QColor("#ff0000"))
        r = size * 0.18
        p.drawRoundedRect(offset, offset, size, size, r, r)

        # Beyaz üçgen
        tri = QPolygonF([
            QPointF(offset + size * 0.36, offset + size * 0.25),
            QPointF(offset + size * 0.36, offset + size * 0.75),
            QPointF(offset + size * 0.78, offset + size * 0.50),
        ])
        p.setBrush(QColor("#ffffff"))
        p.drawPolygon(tri)
        p.end()
        self._logo_lbl.setPixmap(px)

    # ── Animasyon ────────────────────────────────────────────────────────────

    def _start_pulse(self):
        """Logo hafifçe büyüyüp küçülen pulse animasyonu."""
        self._pulse_dir = 1
        self._pulse_val = 1.0
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._do_pulse)
        self._pulse_timer.start(40)

    def _do_pulse(self):
        self._pulse_val += self._pulse_dir * 0.008
        if self._pulse_val >= 1.06:
            self._pulse_dir = -1
        elif self._pulse_val <= 0.94:
            self._pulse_dir = 1
        self._draw_logo(self._pulse_val)

    def advance(self, step_idx: int):
        """Dışarıdan çağrılır — yükleme adımını günceller."""
        step_idx = min(step_idx, len(self.STEPS) - 1)
        pct = int((step_idx / (len(self.STEPS) - 1)) * 100)
        self._bar.setValue(pct)
        self._lbl_step.setText(self.STEPS[step_idx])
        QApplication.processEvents()

    def set_status(self, pct: int, message: str):
        """FFmpeg kurulumu gibi özel ilerleme mesajı göster."""
        self._bar.setValue(pct)
        self._lbl_step.setText(message)
        QApplication.processEvents()

    def finish(self, main_window):
        """Ana pencereyi göster, splash'ı kapat."""
        self._pulse_timer.stop()
        self._bar.setValue(100)
        self._lbl_step.setText("Hazır!")
        QApplication.processEvents()
        QTimer.singleShot(400, lambda: self._do_finish(main_window))

    def _do_finish(self, main_window):
        # Ana pencere "simge durumunda başlat" ile gizli kalabilir; splash
        # kapanınca görünür pencere kalmadığı için Qt uygulamayı kapatmasın.
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        if hasattr(main_window, "show_initial"):
            main_window.show_initial()
        else:
            main_window.show()
        self.close()

    # ── Yardımcı ─────────────────────────────────────────────────────────────

    def _center_on_screen(self):
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width()  - self.width())  // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def mousePressEvent(self, event):
        """Splash'a tıklamak pencereyi taşımayı sağlar."""
        self._drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if hasattr(self, '_drag_pos'):
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.move(self.pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()
