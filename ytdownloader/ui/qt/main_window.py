# -*- coding: utf-8 -*-
"""MainWindow — PyQt6 ana uygulama penceresi. Tam i18n entegrasyonu."""

import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QRadioButton, QButtonGroup,
    QScrollArea, QFrame, QApplication, QStatusBar, QFileDialog,
    QMessageBox, QTabWidget,
)
from PyQt6.QtCore import Qt, QTimer, QSize, QPoint, QMimeData
from PyQt6.QtGui import QAction, QDrag, QPixmap, QPainter, QColor, QPalette

from ytdownloader.ui.qt.video_card import VideoCard
from ytdownloader.ui.qt.notification import NotificationCenter
from ytdownloader.ui.qt.theme import theme_manager
from ytdownloader.ui.qt.icon_helper import set_icon, make_icon
from ytdownloader.ui.qt.dialogs import SettingsDialog, AboutDialog
from ytdownloader.ui.qt.playlist_dialog import PlaylistDialog
from ytdownloader.services.update_service import UpdateService
from ytdownloader.services.ytdlp_update_service import YtdlpUpdateService
from ytdownloader.ui.qt.tray_icon import TrayIcon
from ytdownloader.services.i18n_service import get_i18n
from ytdownloader.infrastructure.logger import get_logger
from ytdownloader.utils.url_utils import validate_youtube_url
from ytdownloader.config.constants import APP_VERSION

log = get_logger("main_window")




class _ThemedTabWidget(QTabWidget):
    """QTabWidget subclass — tabBar boş alanını tema rengiyle boyar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bar_bg = "#1a1d27"  # instance değişkeni — class var değil

    def set_bar_bg(self, color: str):
        self._bar_bg = color
        self.tabBar().update()
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        bar = self.tabBar()
        if bar.count() == 0:
            return
        tab_end_x = 0
        for i in range(bar.count()):
            r = bar.tabRect(i)
            tab_end_x = max(tab_end_x, r.right())
        # Corner widget varsa onun soluna kadar boya
        corner = self.cornerWidget()
        corner_x = self.width() - (corner.width() if corner else 0)
        empty_x  = bar.x() + tab_end_x + 1
        empty_w  = corner_x - empty_x
        if empty_w > 0:
            p = QPainter(self)
            p.fillRect(empty_x, bar.y(), empty_w, bar.height(), QColor(self._bar_bg))
            p.end()

    def showEvent(self, event):
        super().showEvent(event)
        self.update()  # İlk görünümde doğru renkle yeniden çiz


class MainWindow(QMainWindow):

    def __init__(self, download_manager, settings_manager):
        super().__init__()
        self.download_manager  = download_manager
        self.settings_manager  = settings_manager
        self.settings          = settings_manager.load()
        self.cards: list[VideoCard] = []
        self.notification_center = NotificationCenter(self)

        # i18n — ayarlardaki dili uygula
        lang = self.settings.get("language", "tr")
        self._i18n = get_i18n(lang)
        self._update_service = UpdateService()
        # İndirme motoru (yt-dlp) — menü yok, arka planda günde bir sessiz kontrol
        self._ytdlp_updater = YtdlpUpdateService(self)
        self._ytdlp_updater.finished.connect(self._on_ytdlp_update_finished)

        self._build_ui()
        self._build_menu()
        self._apply_theme()
        self._start_status_timer()
        self.setAcceptDrops(True)   # tarayıcıdan URL sürükle-bırak
        if self.settings.get("minimize_to_tray", True):
            self._setup_tray()
        self.setMinimumSize(900, 600)
        self.resize(1000, 700)
        self._set_window_icon()
        # Sıralı modu başlangıçta uygula
        self.download_manager.set_sequential_mode(
            self.settings.get("sequential_mode", False)
        )
        self.setWindowTitle(f"YouTube İndirici v{APP_VERSION}")

        # Açılışta otomatik güncelleme kontrolü — 3 saniye sonra, arka planda.
        # show_no_update=False: yeni sürüm yoksa sessiz kalır.
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(3000, lambda: self._update_service.check(self, show_no_update=False))
        QTimer.singleShot(5000, lambda: self._ytdlp_updater.check(manual=False))

        # İndirme sürerken sistemin uykuya dalmasını engelleme durumu
        self._keep_awake_active = False

        # İkinci instance başlatılırsa main.py bu işaret dosyasını bırakır;
        # status timer görünce pencereyi öne getirir (bkz. _check_show_request)
        self._show_flag = self.settings_manager.settings_dir / "show_window.flag"

        # Önceki oturumdan kalan tamamlanmamış indirmeler varsa geri yüklemeyi öner
        QTimer.singleShot(600, self._offer_queue_restore)

    def _offer_queue_restore(self):
        """Önceki oturumdan kalan kuyruk varsa kullanıcıya sorup geri yükler."""
        entries = self.settings_manager.load_pending_queue()
        if not entries:
            return
        t = self._t
        restore = self._confirm_dialog(
            t("kuyruk_geri_baslik"),
            t("kuyruk_geri_govde", n=len(entries)),
            btn_ok=t("evet_yukle"), btn_cancel=t("hayir"),
        )
        # Dosya her durumda temizlenir — bir sonraki kapanışta güncel liste yazılır
        self.settings_manager.clear_pending_queue()
        if not restore:
            return
        for e in entries:
            url = e.get("url", "")
            if not url or self._find_card(url):
                continue
            card = self._add_card(
                url,
                preset_format=e.get("format"),
                preset_quality=e.get("quality"),
            )
            if card and e.get("folder"):
                card.download_folder = e["folder"]

    def _check_show_request(self):
        """
        İkinci instance açılmaya çalışıldıysa bıraktığı işaret dosyasını görüp
        pencereyi öne getirir. Status timer'dan saniyede bir çağrılır.
        (nativeEvent/RegisterWindowMessage yerine dosya işareti: PyQt6'da
        nativeEvent override'ı pencere oluşturulurken native çökmeye yol açtı.)
        """
        flag = getattr(self, "_show_flag", None)
        if not flag:
            return
        try:
            if flag.exists():
                flag.unlink()
                self.show()
                self.showNormal()
                self.raise_()
                self.activateWindow()
        except Exception:
            pass

    def _set_keep_awake(self, active: bool):
        """Aktif indirme varken Windows'un uykuya geçmesini engeller."""
        # getattr: __init__ sırasında status timer'dan erken çağrılabilir
        if os.name != "nt" or active == getattr(self, "_keep_awake_active", False):
            return
        try:
            import ctypes
            ES_CONTINUOUS      = 0x80000000
            ES_SYSTEM_REQUIRED = 0x00000001
            flags = ES_CONTINUOUS | (ES_SYSTEM_REQUIRED if active else 0)
            # c_uint32 şart: 0x80000000 işaretli 32-bit int'e sığmaz (OverflowError)
            ret = ctypes.windll.kernel32.SetThreadExecutionState(ctypes.c_uint32(flags))
            if ret:
                self._keep_awake_active = active
                log.debug(f"Uyku engelleme: {'açık' if active else 'kapalı'}")
        except Exception:
            pass

    def show_initial(self):
        """
        Açılışta pencereyi gösterir. "Simge durumunda başlat" açıksa:
        tepsi varsa tepside gizli başlar, yoksa görev çubuğunda simge durumunda.
        """
        if not self.settings.get("start_minimized", False):
            self.show()
            return
        tray = getattr(self, "_tray", None)
        if tray and tray.isVisible():
            log.info("Simge durumunda başlatıldı (tepside)")
            return
        self.showMinimized()

    def _setup_tray(self):
        """Sistem tepsisi ikonunu kur."""
        from PyQt6.QtWidgets import QSystemTrayIcon
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self._tray = TrayIcon(self)
        self._tray.show()

    def _set_window_icon(self):
        """Hakkında penceresindeki logoyu pencere ikonu olarak ata."""
        from PyQt6.QtGui import QPixmap, QPainter, QColor, QPolygonF, QIcon
        from PyQt6.QtCore import QPointF, Qt
        size = 64
        px = QPixmap(size, size)
        px.fill(Qt.GlobalColor.transparent)
        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor("#c0392b"))
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
        self.setWindowIcon(QIcon(px))

    def _t(self, key: str, **kw) -> str:
        return self._i18n.t(key, **kw)

    # ── UI Kurulumu ──────────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Sekme sistemi ────────────────────────────────────────────────────
        self._tabs = _ThemedTabWidget()
        self._tabs.setDocumentMode(False)
        root.addWidget(self._tabs, stretch=1)

        # ── Sekme 1: İndirme Yöneticisi ─────────────────────────────────────
        manager_widget = QWidget()
        manager_lay = QVBoxLayout(manager_widget)
        manager_lay.setContentsMargins(0, 0, 0, 0)
        manager_lay.setSpacing(0)

        # Toolbar
        toolbar = QFrame()
        toolbar.setObjectName("topbar")
        toolbar.setFixedHeight(60)
        tb = QHBoxLayout(toolbar)
        tb.setContentsMargins(16, 8, 16, 8)
        tb.setSpacing(10)

        self.btn_paste = QPushButton()
        self.btn_paste.setObjectName("btn_paste")
        self.btn_paste.setFixedHeight(38)
        self.btn_paste.clicked.connect(self.paste_url)
        tb.addWidget(self.btn_paste)

        self.btn_download_all = QPushButton()
        self.btn_download_all.setObjectName("btn_download_all")
        self.btn_download_all.setFixedHeight(38)
        self.btn_download_all.setEnabled(False)
        self.btn_download_all.clicked.connect(self.download_all)
        tb.addWidget(self.btn_download_all)

        self.btn_clear = QPushButton()
        self.btn_clear.setObjectName("btn_clear")
        self.btn_clear.setFixedHeight(38)
        self.btn_clear.setEnabled(False)
        self.btn_clear.clicked.connect(self.clear_list)
        tb.addWidget(self.btn_clear)

        tb.addStretch()

        self.filter_lbl = QLabel()
        self.filter_lbl.setObjectName("card_meta")
        tb.addWidget(self.filter_lbl)

        self._filter_group = QButtonGroup(self)
        self._filter_buttons = {}
        for fid in ["all", "active", "done"]:
            rb = QRadioButton()
            rb.setProperty("filter_id", fid)
            if fid == "all":
                rb.setChecked(True)
            self._filter_group.addButton(rb)
            self._filter_buttons[fid] = rb
            tb.addWidget(rb)
        self._filter_group.buttonClicked.connect(self._apply_filter)

        manager_lay.addWidget(toolbar)

        # Kart listesi
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(8, 8, 8, 8)
        self.cards_layout.setSpacing(0)
        self.cards_layout.addStretch()
        self.scroll_area.setWidget(self.cards_container)
        manager_lay.addWidget(self.scroll_area, stretch=1)

        # ── Boş ekran — güzel empty state ────────────────────────────────
        self._empty_widget = QWidget()
        self._empty_widget.setObjectName("empty_state")
        ev = QVBoxLayout(self._empty_widget)
        ev.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ev.setSpacing(16)
        ev.setContentsMargins(40, 0, 40, 60)

        # SVG ikon — tema rengiyle
        from ytdownloader.ui.qt.icon_helper import make_pixmap
        _ico_lbl = QLabel()
        _ico_lbl.setObjectName("empty_icon")
        _ico_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _ico_px = make_pixmap("download", "#c0392b", 64)
        _ico_lbl.setPixmap(_ico_px)
        _ico_lbl.setStyleSheet("background:transparent; margin-bottom:4px;")
        ev.addWidget(_ico_lbl)

        # Başlık — metinler _retranslate_ui_only'de atanır (i18n)
        self._empty_title = QLabel()
        self._empty_title.setObjectName("empty_title")
        self._empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_title.setStyleSheet(
            "font-size:22px; font-weight:700; color:#c0392b; background:transparent;"
        )
        ev.addWidget(self._empty_title)

        # Alt açıklama
        self._empty_sub = QLabel()
        self._empty_sub.setObjectName("empty_sub")
        self._empty_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_sub.setWordWrap(True)
        ev.addWidget(self._empty_sub)

        ev.addSpacing(4)

        # Kısayol ipuçları
        # (seçicisiz "background: transparent" verme — çocuk çiplerin
        #  arka planını da ezer; QWidget zaten global QSS'te şeffaf)
        _hints = QWidget()
        hl = QHBoxLayout(_hints)
        hl.setSpacing(8)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_chips = []
        for _ in range(3):
            chip = QLabel()
            chip.setObjectName("empty_hint")
            self._empty_chips.append(chip)
            hl.addWidget(chip)
        ev.addWidget(_hints)

        self._empty_widget.setParent(self.cards_container)
        self._empty_widget.setMinimumHeight(420)
        self.cards_layout.insertWidget(0, self._empty_widget)
        self.lbl_empty = self._empty_widget  # eski kod uyumu için alias

        # ── Tema butonu — sekmelerin sağ köşesinde bağımsız ────────────────
        # Corner widget — tema butonu için wrapper (arka plan tab bar ile uyumlu)
        _corner = QWidget()
        self._corner_widget = _corner  # tema güncellemesi için sakla
        _corner_lay = QHBoxLayout(_corner)
        _corner_lay.setContentsMargins(0, 0, 4, 0)
        _corner_lay.setSpacing(0)
        self.btn_theme = QPushButton()
        self.btn_theme.setFixedSize(38, 38)
        self.btn_theme.setToolTip("Tema Değiştir")
        self.btn_theme.clicked.connect(self._toggle_theme)
        _corner_lay.addWidget(self.btn_theme)
        self._tabs.setCornerWidget(_corner, Qt.Corner.TopRightCorner)
        # Tema burada uygulanır — corner artık hazır
        self._apply_theme_icon()

        # ── Sekme 0: İndirme Yöneticisi (ana sekme) ──────────────────────────
        self._tabs.addTab(manager_widget, self._t("tab_indirme_yoneticisi"))

        # Status bar
        self._status_bar = QStatusBar()
        self._status_bar.setObjectName("statusbar")
        self._status_bar.setSizeGripEnabled(False)
        self.setStatusBar(self._status_bar)
        self._lbl_status = QLabel()
        self._status_bar.addPermanentWidget(self._lbl_status, 1)



    def _build_menu(self):
        mb = self.menuBar()

        self._m_file  = mb.addMenu("")
        self._m_tools = mb.addMenu("")

        # Mouse hover ile menü açma
        mb.installEventFilter(self)

        self._a_paste = QAction(self); self._a_paste.setShortcut("Ctrl+V")
        self._a_paste.triggered.connect(self.paste_url)
        self._m_file.addAction(self._a_paste)

        self._a_dl_all = QAction(self); self._a_dl_all.setShortcut("Ctrl+D")
        self._a_dl_all.triggered.connect(self.download_all)
        self._m_file.addAction(self._a_dl_all)

        self._m_file.addSeparator()

        self._a_open_list = QAction(self); self._a_open_list.setShortcut("Ctrl+O")
        self._a_open_list.triggered.connect(self.open_list)
        self._m_file.addAction(self._a_open_list)

        self._a_save_list = QAction(self); self._a_save_list.setShortcut("Ctrl+S")
        self._a_save_list.triggered.connect(self.save_list)
        self._m_file.addAction(self._a_save_list)

        self._m_file.addSeparator()

        self._a_quit = QAction(self); self._a_quit.setShortcut("Ctrl+Q")
        self._a_quit.triggered.connect(self.close)
        self._m_file.addAction(self._a_quit)

        # Araçlar
        self._a_settings = QAction(self)
        self._a_settings.triggered.connect(self._open_settings)
        self._m_tools.addAction(self._a_settings)

        self._m_tools.addSeparator()

        self._a_history = QAction(self)
        self._a_history.triggered.connect(self._open_history)
        self._m_tools.addAction(self._a_history)

        self._a_kullanim = QAction(self)
        self._a_kullanim.triggered.connect(self._open_kullanim)
        self._m_tools.addAction(self._a_kullanim)

        self._a_about = QAction(self)
        self._a_about.triggered.connect(self._open_about)
        self._m_tools.addAction(self._a_about)

        self._retranslate_menu()
        self._retranslate_ui_only()

    def _retranslate_ui_only(self):
        t = self._t
        is_dark = theme_manager.current == "dark"
        icon_color = "#e8eaf0" if is_dark else "#1a1a2e"
        set_icon(self.btn_paste,        "paste",        icon_color, 15)
        set_icon(self.btn_download_all, "download_all", icon_color, 15)
        set_icon(self.btn_clear,        "trash",        icon_color, 15)
        self.btn_paste.setText(f"  {t('yapistir')}")
        self.btn_download_all.setText(f"  {t('hepsini_indir')}")
        self.btn_clear.setText(f"  {t('listeyi_temizle')}")
        self.btn_paste.setToolTip(t("tt_pano"))
        self.btn_download_all.setToolTip(t("tt_hepsini"))
        self.btn_clear.setToolTip(t("tt_temizle"))
        self.filter_lbl.setText(t("goster"))
        self._filter_buttons["all"].setText(t("tumu"))
        self._filter_buttons["active"].setText(t("indiriliyor"))
        self._filter_buttons["done"].setText(t("tamamlandi"))
        # Sekme + boş ekran metinleri
        if hasattr(self, "_tabs") and self._tabs.count() > 0:
            self._tabs.setTabText(0, t("tab_indirme_yoneticisi"))
        if hasattr(self, "_empty_title"):
            self._empty_title.setText(t("bos_baslik"))
            self._empty_sub.setText(t("bos_alt"))
            hints = [f"Ctrl+V  {t('yapistir')}",
                     f"Ctrl+D  {t('hepsini_indir')}",
                     t("playlist_destegi")]
            for chip, text in zip(self._empty_chips, hints):
                chip.setText(text)
        self._update_status()

    def retranslate(self):
        """Tüm UI metinlerini aktif dile çevir."""
        self.setWindowTitle(f"YouTube İndirici v{APP_VERSION}")

        # Toolbar butonları — _apply_theme_icon ikon+metin rengini halleder
        self._apply_theme_icon()

        # Toolbar/filtre/sekme/boş ekran metinleri
        self._retranslate_ui_only()

        # Menü
        self._retranslate_menu()

        # Tepsi menüsü
        tray = getattr(self, "_tray", None)
        if tray and hasattr(tray, "retranslate"):
            tray.retranslate()

    def _apply_tab_style(self, bg, active_bg, hover_bg,
                          passive_color, active_color, hover_color,
                          border, accent):
        """Sekme stilini segmented-control görünümüyle uygular."""

        self._tabs.setStyleSheet(f"""
            QTabWidget {{
                background: {bg};
            }}
            QTabWidget::pane {{
                background: {bg};
                border: 1px solid {border};
                border-top: 1px solid {border};
            }}
            QTabBar {{
                background: {bg};
                border: none;
                qproperty-drawBase: 0;
            }}
            QTabBar::tab {{
                background: transparent;
                color: {passive_color};
                padding: 9px 26px;
                font-size: 13px;
                font-weight: 500;
                border: none;
                border-bottom: 2px solid transparent;
                margin: 5px 2px 0px 2px;
                min-width: 120px;
            }}
            QTabBar::tab:selected {{
                background: {active_bg};
                color: {active_color};
                border-bottom: 2px solid {accent};
                font-weight: 600;
            }}
            QTabBar::tab:hover:!selected {{
                background: {hover_bg};
                color: {hover_color};
            }}
            QTabBar::scroller {{ width: 0px; }}
        """)

        self._tabs.tabBar().setStyleSheet(f"background: {bg}; border: none;")

        # tabBar() ve QTabWidget ana arka planını CSS dışında da zorla
        self._tabs.setAutoFillBackground(True)
        from PyQt6.QtGui import QPalette
        for w in [self._tabs, self._tabs.tabBar()]:
            pal = w.palette()
            pal.setColor(QPalette.ColorRole.Window, QColor(bg))
            pal.setColor(QPalette.ColorRole.Base,   QColor(bg))
            w.setAutoFillBackground(True)
            w.setPalette(pal)

        # _ThemedTabWidget'a rengi bildir — boş alanı boyar
        if hasattr(self._tabs, 'set_bar_bg'):
            self._tabs.set_bar_bg(bg)

        if hasattr(self, '_corner_widget'):
            self._corner_widget.setStyleSheet(
                f"background: {bg}; border: none; border-bottom: 1px solid {accent};"
            )
            from PyQt6.QtGui import QPalette
            pal2 = self._corner_widget.palette()
            pal2.setColor(QPalette.ColorRole.Window, QColor(bg))
            self._corner_widget.setAutoFillBackground(True)
            self._corner_widget.setPalette(pal2)

    def _confirm_dialog(self, title: str, message: str,
                        btn_ok: str = "Evet", btn_cancel: str = "İptal",
                        danger: bool = False) -> bool:
        """Temaya uyumlu onay diyalogu. True = onaylandı."""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel
        from ytdownloader.ui.qt.theme import theme_manager

        is_dark = theme_manager.current == "dark"
        bg       = "#1a1d27" if is_dark else "#ffffff"
        card_bg  = "#12141f" if is_dark else "#f8f9fa"
        border   = "#2e3348" if is_dark else "#c4c9d8"
        txt      = "#e8eaf0" if is_dark else "#000000"
        sub_txt  = "#9da3b4" if is_dark else "#111111"

        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.setFixedWidth(420)
        dlg.setWindowFlags(
            dlg.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )
        dlg.setStyleSheet(f"""
            QDialog {{ background: {bg}; border-radius: 10px; }}
            QLabel  {{ color: {txt}; }}
        """)

        root = QVBoxLayout(dlg)
        root.setContentsMargins(28, 24, 28, 20)
        root.setSpacing(16)

        # Başlık
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"font-size:16px;font-weight:700;color:{txt};")
        root.addWidget(lbl_title)

        # Mesaj
        lbl_msg = QLabel(message)
        lbl_msg.setWordWrap(True)
        lbl_msg.setStyleSheet(f"font-size:13px;color:{sub_txt};line-height:1.5;")
        root.addWidget(lbl_msg)

        root.addSpacing(4)

        # Butonlar
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        from PyQt6.QtWidgets import QPushButton, QSizePolicy
        b_cancel = QPushButton(btn_cancel)
        b_cancel.setMinimumHeight(36)
        b_cancel.setMinimumWidth(90)
        b_cancel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        b_cancel.setStyleSheet(f"""
            QPushButton {{ background: transparent; border: 1px solid {border};
                border-radius: 7px; color: {sub_txt}; font-size: 13px; padding: 0 16px; }}
            QPushButton:hover {{ background: {border}; color: {txt}; }}
        """)
        b_cancel.clicked.connect(dlg.reject)
        btn_row.addWidget(b_cancel)

        ok_color = "#e05a5a" if danger else "#c0392b"
        ok_hover = "#c94444" if danger else "#a93226"
        b_ok = QPushButton(btn_ok)
        b_ok.setMinimumHeight(36)
        b_ok.setMinimumWidth(90)
        b_ok.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        b_ok.setStyleSheet(f"""
            QPushButton {{ background: {ok_color}; border: none;
                border-radius: 7px; color: #ffffff; font-size: 13px;
                font-weight: 600; padding: 0 16px; }}
            QPushButton:hover {{ background: {ok_hover}; }}
        """)
        b_ok.clicked.connect(dlg.accept)
        btn_row.addWidget(b_ok)

        root.addLayout(btn_row)
        return dlg.exec() == QDialog.DialogCode.Accepted

    def _retranslate_menu(self):
        t = self._t
        self._m_file.setTitle(t("dosya"))
        self._m_tools.setTitle(t("araclar"))
        self._a_paste.setText(t("yapistir"))
        self._a_dl_all.setText(t("hepsini_indir"))
        self._a_open_list.setText(t("listeyi_ac"))
        self._a_save_list.setText(t("listeyi_kaydet"))
        self._a_quit.setText(t("cikis"))
        self._a_settings.setText(t("ayarlar"))
        self._a_history.setText(t("gecmis"))
        self._a_kullanim.setText(t("kullanim"))
        self._a_about.setText(t("hakkinda"))

    # ── Tema ─────────────────────────────────────────────────────────────────

    def _apply_theme_icon(self):
        is_dark = theme_manager.current == "dark"
        icon_name = "sun" if is_dark else "moon"
        icon_color = "#e8eaf0" if is_dark else "#333344"
        self.btn_theme.setIcon(make_icon(icon_name, icon_color, 16))
        self.btn_theme.setIconSize(QSize(16, 16))

        # Toolbar buton ikonlarını da güncelle
        tb_icon_color = "#e8eaf0" if is_dark else "#1a1a2e"
        set_icon(self.btn_paste,        "paste",        tb_icon_color, 15)
        set_icon(self.btn_download_all, "download_all", tb_icon_color, 15)
        set_icon(self.btn_clear,        "trash",        tb_icon_color, 15)
        # setText ile metni geri ekle (set_icon metin bırakmaz)
        t = self._i18n.t
        self.btn_paste.setText(f"  {t('yapistir')}")
        self.btn_download_all.setText(f"  {t('hepsini_indir')}")
        self.btn_clear.setText(f"  {t('listeyi_temizle')}")

        # Tema butonunun kendi stili
        btn_bg  = "#2e3348" if is_dark else "#d8dce8"
        btn_hov = "#3d4460" if is_dark else "#c4c9d8"
        self.btn_theme.setStyleSheet(f"""
            QPushButton {{
                background: {btn_bg}; border: none;
                border-radius: 8px; margin: 4px;
            }}
            QPushButton:hover {{ background: {btn_hov}; }}
        """)

        # Sekme bar renkleri — segmented-control
        tab_bg          = "#1a1d27"  if is_dark else "#e8eaf0"
        tab_active_bg   = "#22263a"  if is_dark else "#daddf0"
        tab_hover_bg    = "#1e2235"  if is_dark else "#e0e3ee"
        tab_passive_clr = "#6b7280"  if is_dark else "#8892a4"
        tab_active_clr  = "#e8eaf0"  if is_dark else "#111827"
        tab_hover_clr   = "#9da3b4"  if is_dark else "#444455"
        tab_border      = "#2e3348"  if is_dark else "#c8cdd8"
        accent          = "#c0392b"

        self._apply_tab_style(tab_bg, tab_active_bg, tab_hover_bg,
                               tab_passive_clr, tab_active_clr, tab_hover_clr,
                               tab_border, accent)

    def _apply_theme(self):
        QApplication.instance().setStyleSheet(theme_manager.stylesheet())
        self._apply_theme_icon()
        # Kartlardaki dropdown ve buton stillerini yenile
        for card in getattr(self, "cards", []):
            if hasattr(card, "_apply_resolution_style"):
                card._apply_resolution_style()
            if hasattr(card, "_apply_btn_styles"):
                card._apply_btn_styles()

    def _toggle_theme(self):
        theme_manager.toggle()
        self._apply_theme()
        # Yalnızca bu anahtarı yaz — elimizdeki kopya eski olabilir,
        # tamamını kaydetmek araya giren ayar değişikliklerini geri alır.
        self.settings["theme"] = theme_manager.current
        self.settings_manager.update("theme", theme_manager.current)

    # ── URL İşlemleri ────────────────────────────────────────────────────────

    def _find_card(self, url: str):
        """
        URL'ye karşılık gelen kartı döner. Aynı video farklı URL biçimleriyle
        (youtu.be/X vs watch?v=X) eklenmesin diye video ID üzerinden karşılaştırır.
        """
        from ytdownloader.utils.url_utils import extract_video_id
        vid = extract_video_id(url)
        for c in self.cards:
            if c.url == url:
                return c
            if vid and extract_video_id(c.url) == vid:
                return c
        return None

    def paste_url(self):
        text = QApplication.clipboard().text().strip()
        if not text:
            return
        self._add_urls_from_text(text)

    def _add_urls_from_text(self, text: str):
        """Metindeki geçerli YouTube URL'lerini karta çevirir (yapıştır + sürükle-bırak)."""
        from ytdownloader.utils.url_utils import is_playlist_url
        urls = [u.strip() for u in text.splitlines() if u.strip()]

        # Saf playlist linki (youtube.com/playlist?list=...) kart olamaz —
        # seçim penceresini aç. Tek seferde yalnızca bir pencere açılır.
        playlist = next((u for u in urls if is_playlist_url(u)), None)
        if playlist:
            urls = [u for u in urls if not is_playlist_url(u)]
            self._handle_playlist(playlist)
            if not urls:
                return

        added = 0
        existing = None
        for url in urls:
            valid, _ = validate_youtube_url(url)
            if not valid:
                continue
            found = self._find_card(url)
            if found:
                existing = existing or found
                continue
            self._add_card(url)
            added += 1
        if added == 0 and existing:
            # Geçerli link ama zaten listede — "geçersiz URL" demek yanıltıcıydı
            self._scroll_to_card(existing)
            self.notification_center.show(
                self._t("zaten_listede_baslik"),
                self._t("zaten_listede_govde"), "info"
            )
        elif added == 0:
            self.notification_center.show(
                self._t("gecersiz_url"), self._t("pano_url_yok"), "warning"
            )
        else:
            self.notification_center.show(
                self._t("liste_yuklendi"), self._t("url_eklendi", n=added), "success"
            )

    # ── Sürükle-Bırak (URL) ─────────────────────────────────────────────────
    # Tarayıcıdan adres çubuğu/bağlantı sürüklenince kart olarak ekle.

    def dragEnterEvent(self, event):
        md = event.mimeData()
        if md.hasUrls() or md.hasText():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event):
        md = event.mimeData()
        parts = []
        if md.hasUrls():
            parts.extend(u.toString() for u in md.urls())
        if md.hasText():
            parts.append(md.text())
        text = "\n".join(p for p in parts if p).strip()
        if text:
            self._add_urls_from_text(text)
            event.acceptProposedAction()

    def _is_playlist_url(self, url: str) -> bool:
        import urllib.parse
        p = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(p.query)
        return "list" in params and "v" not in params

    def _handle_playlist(self, url: str):
        dlg = PlaylistDialog(self, url, self.download_manager)
        if dlg.exec() and dlg.selected_urls:
            for u in dlg.selected_urls:
                if not self._find_card(u):
                    self._add_card(u,
                                   preset_format=dlg.selected_format,
                                   preset_quality=dlg.selected_quality)
            self.notification_center.show(
                self._t("liste_yuklendi"),
                self._t("url_eklendi", n=len(dlg.selected_urls)),
                "success"
            )

    def _add_card(self, url: str, preset_format: str = None, preset_quality: str = None):
        # Duplicate guard — çağıran tarafta da kontrol edilmeli ama burada kesin son hat.
        existing = self._find_card(url)
        if existing:
            self._scroll_to_card(existing)
            return existing

        card = VideoCard(
            url=url,
            download_manager=self.download_manager,
            notification_center=self.notification_center,
            settings_manager=self.settings_manager,
            parent=self.cards_container,
        )
        if preset_format:
            card._preset_format  = preset_format
            card._preset_quality = preset_quality
        card.remove_requested.connect(self._remove_card)
        card.playlist_open_requested.connect(self._handle_playlist)
        # Sürükle-bırak
        card.mousePressEvent   = lambda e, c=card: self._drag_start(e, c)
        card.mouseMoveEvent    = lambda e, c=card: self._drag_move(e, c)
        card.mouseReleaseEvent = lambda e, c=card: self._drag_end(e, c)
        # cards.append ÖNCE — insertWidget Qt event processing tetikleyebilir;
        # duplicate check bu noktadan sonra karta görür.
        self.cards.append(card)
        self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)
        self.lbl_empty.setVisible(False)
        self._update_controls()
        log.info(f"Kart eklendi: {url[:50]}")
        return card

    def _scroll_to_card(self, card) -> None:
        """Mevcut kartı görünür hale getirir ve kısa bir flash ile vurgular."""
        self.scroll_area.ensureWidgetVisible(card)
        # Kırmızı border flash — 600ms sonra sıfırlanır
        orig = card.styleSheet()
        card.setStyleSheet(orig + "\nQFrame#VideoCard { border: 2px solid #c0392b; }")
        QTimer.singleShot(600, lambda: card.setStyleSheet(orig))

    # ── Sürükle-Bırak ────────────────────────────────────────────────────────

    _drag_card      = None
    _drag_start_pos = None
    _drag_indicator = None
    _drag_ghost     = None
    _drag_scroll_timer = None   # sürükleme sırasında otomatik scroll

    def _drag_start(self, event, card):
        from ytdownloader.ui.qt.video_card import VideoCard as _VC
        _VC.mousePressEvent(card, event)
        if event.button() == Qt.MouseButton.LeftButton:
            # Güvenlik: tüm kartların drag state'ini sıfırla
            for c in self.cards:
                if getattr(c, "_dragging", False):
                    c._dragging = False
                    c.set_drag_highlight(False)
            self._drag_card      = card
            self._drag_start_pos = event.globalPosition().toPoint()

    def _drag_move(self, event, card):
        from ytdownloader.ui.qt.video_card import VideoCard as _VC
        _VC.mouseMoveEvent(card, event)
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if self._drag_card is not card:
            return
        global_pos = event.globalPosition().toPoint()
        delta = (global_pos - self._drag_start_pos).manhattanLength()
        if delta < 8:
            return

        # İlk hareket — kartı vurgula ve ghost oluştur (sadece bir kez)
        if not getattr(card, "_dragging", False):
            card._dragging = True
            card.set_drag_highlight(True)
            self._create_ghost(card)
            return  # ilk karede ghost oluşturduk, pozisyonu bir sonraki harekette ayarla

        # Ghost'u mouse ile birlikte taşı
        if self._drag_ghost:
            gh = self._drag_ghost
            gh.move(
                global_pos.x() - gh.width() // 2,
                global_pos.y() - 24
            )
            if not gh.isVisible():
                gh.show()
            gh.raise_()

        # Hedef kartı bul ve drop çizgisini güncelle
        target = self._card_at_global(global_pos)
        self._show_drop_indicator(target)

        # Otomatik scroll — mouse scroll alanının kenarına yaklaşınca
        self._auto_scroll(global_pos)

    def _drag_end(self, event, card):
        from ytdownloader.ui.qt.video_card import VideoCard as _VC
        _VC.mouseReleaseEvent(card, event)
        self._hide_drop_indicator()
        self._destroy_ghost()

        # Tüm kartları temizle — mouse dışarı çıkma durumuna karşı
        for c in self.cards:
            if getattr(c, "_dragging", False):
                c._dragging = False
                c.set_drag_highlight(False)

        if self._drag_card is None or self._drag_card is not card:
            self._drag_card = None
            return

        target = self._card_at_global(event.globalPosition().toPoint())
        if target and target is not self._drag_card:
            self._reorder_card(self._drag_card, target)
        self._drag_card = None

    def _create_ghost(self, card):
        """Kartın yarı saydam küçük önizlemesinden ghost penceresi oluştur."""
        self._destroy_ghost()

        # Kartın pixmap'ini al ve %50 küçült
        px = card.grab()
        scaled = px.scaled(
            int(px.width() * 0.55),
            int(px.height() * 0.55),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        # Yarı saydam ghost widget
        ghost = QWidget(None)
        ghost.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.WindowTransparentForInput
        )
        ghost.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        ghost.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        ghost.resize(scaled.size())

        # %65 opaklık
        result = QPixmap(scaled.size())
        result.fill(QColor(0, 0, 0, 0))
        painter = QPainter(result)
        painter.setOpacity(0.65)
        painter.drawPixmap(0, 0, scaled)
        # Mavi çerçeve
        from PyQt6.QtCore import Qt as _Qt
        painter.setOpacity(1.0)
        from PyQt6.QtGui import QPen
        pen = QPen(QColor("#3b82f6"))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(QColor(0, 0, 0, 0))
        painter.drawRoundedRect(result.rect().adjusted(1,1,-1,-1), 10, 10)
        painter.end()

        from PyQt6.QtWidgets import QLabel
        lbl = QLabel(ghost)
        lbl.setPixmap(result)
        lbl.resize(result.size())
        ghost.setStyleSheet("background: transparent; border: none;")

        self._drag_ghost = ghost

    def _auto_scroll(self, global_pos: QPoint):
        """Sürükleme sırasında scroll alanının üst/alt kenarında otomatik kaydır."""
        sa = self.scroll_area
        local = sa.mapFromGlobal(global_pos)
        h = sa.height()
        zone = 60   # kenardan bu kadar px içinde scroll başlar
        speed = 12  # her adımda kaç px kaydır

        vbar = sa.verticalScrollBar()
        if local.y() < zone and vbar.value() > 0:
            vbar.setValue(max(0, vbar.value() - speed))
        elif local.y() > h - zone and vbar.value() < vbar.maximum():
            vbar.setValue(min(vbar.maximum(), vbar.value() + speed))

    def _destroy_ghost(self):
        if self._drag_ghost:
            self._drag_ghost.hide()
            self._drag_ghost.deleteLater()
            self._drag_ghost = None

    def _card_at_global(self, global_pos: QPoint):
        """Global pozisyondaki kartı döndürür."""
        for c in self.cards:
            local = c.mapFromGlobal(global_pos)
            if c.rect().contains(local):
                return c
        return None

    def _show_drop_indicator(self, target_card):
        """Hedef kartın üstünde kırmızı çizgi göster."""
        if self._drag_indicator is None:
            self._drag_indicator = QWidget(self.cards_container)
            self._drag_indicator.setFixedHeight(3)
            self._drag_indicator.setStyleSheet(
                "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                "stop:0 transparent, stop:0.1 #3b82f6, stop:0.9 #3b82f6, stop:1 transparent);"
            )
        if target_card:
            pos = target_card.mapTo(self.cards_container, QPoint(0, 0))
            self._drag_indicator.setGeometry(
                pos.x(), pos.y() - 1,
                target_card.width(), 3
            )
            self._drag_indicator.raise_()
            self._drag_indicator.show()
        else:
            self._drag_indicator.hide()

    def _hide_drop_indicator(self):
        if self._drag_indicator:
            self._drag_indicator.hide()

    def _reorder_card(self, card, target):
        """Kartı hedefin önüne taşır — layout ve self.cards listesini günceller."""
        if card not in self.cards or target not in self.cards:
            return
        old_idx = self.cards.index(card)
        new_idx = self.cards.index(target)

        # Layout'tan çıkar ve yeni pozisyona ekle
        self.cards_layout.removeWidget(card)
        self.cards.pop(old_idx)
        # Stretch ve empty_widget offset'i hesapla
        insert_at = new_idx if new_idx < old_idx else new_idx
        self.cards.insert(insert_at, card)
        # Layout'ta empty_widget index 0, kartlar 1'den başlar
        self.cards_layout.insertWidget(insert_at + 1, card)

        # Sıralı modda kuyruğu güncelle
        if self._seq_mode_active():
            self.download_manager.reorder_queue(
                [c.download_id for c in self.cards]
            )
        log.debug(f"Kart taşındı: {old_idx} → {insert_at}")

    def _seq_mode_active(self) -> bool:
        return self.settings.get("sequential_mode", False)

    def _remove_card(self, download_id: str):
        for card in self.cards[:]:
            if card.download_id == download_id:
                self.cards.remove(card)
                card.setParent(None)
                card.deleteLater()
                break
        self.lbl_empty.setVisible(len(self.cards) == 0)
        self._update_controls()

    # ── Toplu İşlemler ───────────────────────────────────────────────────────

    def download_all(self):
        idle_cards = [c for c in self.cards if c.download_state == "idle"]
        if not idle_cards:
            return
        default_dir = self._desktop_path()
        last = self.settings.get("last_download_folder", "")
        if last and os.path.exists(last):
            default_dir = last
        folder = QFileDialog.getExistingDirectory(
            self, self._t("indirme_klasoru_sec"), default_dir
        )
        if not folder:
            return
        self.settings["last_download_folder"] = folder
        self.settings_manager.update("last_download_folder", folder)
        # Tüm idle kartlara klasörü ata — tekrar sorulmayacak
        for card in idle_cards:
            card.download_folder = folder
            card._start()
        self.notification_center.show(
            self._t("toplu_indirme"),
            self._t("video_baslatildi", n=len(idle_cards)),
            "info"
        )

    def clear_list(self):
        if not self.cards:
            return
        t = self._t
        active_n = sum(1 for c in self.cards
                       if c.download_state in ("downloading", "queued", "paused"))
        if active_n:
            msg = t("temizle_soru_aktif", a=active_n, n=len(self.cards))
        else:
            msg = t("temizle_soru", n=len(self.cards))
        if not self._confirm_dialog(t("listeyi_temizle"), msg,
                                    btn_ok=t("evet_temizle"), btn_cancel=t("vazgec"),
                                    danger=active_n > 0):
            return
        for card in self.cards[:]:
            if card.download_state in ("downloading", "queued", "paused"):
                self.download_manager.cancel_download(card.download_id)
            card.setParent(None)
            card.deleteLater()
        self.cards.clear()
        self.lbl_empty.setVisible(True)
        self._update_controls()

    def open_list(self):
        path, _ = QFileDialog.getOpenFileName(
            self, self._t("listeyi_ac"), self._desktop_path(),
            "Metin Dosyaları (*.txt);;Tüm Dosyalar (*)"
        )
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                lines = [l.strip() for l in f if l.strip()]
        except Exception as e:
            self.notification_center.show(self._t("hata"), str(e), "error")
            return
        added = 0
        for url in lines:
            valid, _ = validate_youtube_url(url)
            if not valid or self._find_card(url):
                continue
            self._add_card(url)
            added += 1
        if added > 0:
            self.notification_center.show(
                self._t("liste_yuklendi"), self._t("url_eklendi", n=added), "success"
            )
        else:
            self.notification_center.show(
                self._t("hata"), self._t("gecerli_url_yok"), "warning"
            )

    def save_list(self):
        if not self.cards:
            self.notification_center.show(
                self._t("hata"), self._t("listede_video_yok"), "warning"
            )
            return
        default = os.path.join(self._desktop_path(), "url_listesi.txt")
        path, _ = QFileDialog.getSaveFileName(
            self, self._t("listeyi_kaydet"), default, "Metin Dosyaları (*.txt)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                for card in self.cards:
                    f.write(card.url + "\n")
            self.notification_center.show(
                self._t("liste_kaydedildi"),
                self._t("url_kaydedildi", n=len(self.cards)),
                "success"
            )
        except Exception as e:
            self.notification_center.show(self._t("hata"), str(e), "error")

    # ── Ayarlar / Hakkında ───────────────────────────────────────────────────

    def _open_settings(self):
        auth = getattr(self.download_manager, '_auth_service', None)
        dlg = SettingsDialog(self, self.settings_manager, auth_service=auth)
        if dlg.exec():
            self.settings = self.settings_manager.load()
            # Sıralı modu hemen uygula
            self.download_manager.set_sequential_mode(
                self.settings.get("sequential_mode", False)
            )
            # Dili güncelle ve anında uygula
            new_lang = self.settings.get("language", "tr")
            self._i18n = get_i18n(new_lang)
            self.retranslate()

    def _show_auth_dialog(self):
        """Tarayıcı cookie / oturum yönetimi dialog'u."""
        from ytdownloader.ui.qt.auth_dialog import AuthDialog
        auth = getattr(self.download_manager, '_auth_service', None)
        dlg = AuthDialog(self, auth)
        dlg.exec()

    def _bulk_format(self, fmt: str):
        """Listedeki idle kartların tümünü aynı formata çevirir."""
        changed = 0
        for card in self.cards:
            if card.download_state == "idle" and card._format != fmt:
                card._format = fmt
                card.btn_format.setText(f"{fmt} ▾")
                card._update_quality_combo()
                changed += 1
        if changed:
            self.notification_center.show(
                f"🔄 Format Değiştirildi",
                f"{changed} kart {fmt} olarak ayarlandı",
                "info"
            )

    def _on_ytdlp_update_finished(self, result: dict, manual: bool):
        """Yeni indirme motoru indirildiyse bilgi ver; diğer durumlarda sessiz kal."""
        if result.get("status") == "installed":
            self.notification_center.show(
                self._t("motor_guncellendi_baslik"),
                self._t("motor_guncellendi_govde"),
                "success",
            )

    def _open_history(self):
        from ytdownloader.ui.qt.history_dialog import HistoryDialog

        def _re_download(url: str):
            if not url:
                return
            existing = self._find_card(url)
            self._tabs.setCurrentIndex(0)
            if existing:
                self._scroll_to_card(existing)
            else:
                self._add_card(url)

        HistoryDialog(self, self.settings_manager, re_download_cb=_re_download).exec()

    def _open_about(self):
        AboutDialog(self, self._i18n).exec()

    def _open_kullanim(self):
        """Kullanım kılavuzu diyalogu — kısayollar ve bilgiler."""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QScrollArea, QWidget
        is_dark = theme_manager.current == "dark"
        bg     = "#1a1d27" if is_dark else "#f0f2f7"
        card   = "#12141f" if is_dark else "#ffffff"
        border = "#2e3348" if is_dark else "#d0d5e0"
        txt    = "#e8eaf0" if is_dark else "#111827"
        sub    = "#9da3b4" if is_dark else "#6b7280"
        acc    = "#c0392b"

        dlg = QDialog(self)
        dlg.setWindowTitle(self._t("kullanim"))
        dlg.setFixedWidth(480)
        dlg.setMinimumHeight(500)
        dlg.setWindowFlags(dlg.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        dlg.setStyleSheet(f"QDialog {{ background: {bg}; }} QLabel {{ color: {txt}; }}")

        root = QVBoxLayout(dlg)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Başlık
        header = QWidget()
        header.setStyleSheet(f"background: {acc};")
        h_lay = QVBoxLayout(header)
        h_lay.setContentsMargins(24, 16, 24, 16)
        lbl_h = QLabel("📖  " + self._t("kullanim"))
        lbl_h.setStyleSheet("font-size:18px;font-weight:700;color:#ffffff;")
        h_lay.addWidget(lbl_h)
        root.addWidget(header)

        # İçerik
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"QScrollArea {{ background: {bg}; border: none; }}")

        content = QWidget()
        content.setStyleSheet(f"background: {bg};")
        c_lay = QVBoxLayout(content)
        c_lay.setContentsMargins(24, 16, 24, 16)
        c_lay.setSpacing(8)

        sections = [
            ("🔑  Klavye Kısayolları", [
                ("Ctrl + V", "URL yapıştır ve ekle"),
                ("Ctrl + D", "Tümünü indir"),
                ("Ctrl + O", "URL listesi aç"),
                ("Ctrl + S", "URL listesini kaydet"),
                ("Ctrl + Q", "Uygulamadan çık"),
            ]),
            ("⬇  İndirme İşlemleri", [
                ("URL Yapıştır", "Panodaki YouTube URL'sini ekler"),
                ("Hepsini İndir", "Listedeki tüm videoları indirir"),
                ("Listeyi Temizle", "Tüm kartları kaldırır"),
                ("Çift Tıklama", "Kart üzerinde: İndirmeyi başlat / Duraklat / Devam et"),
                ("Sağ Tık", "Kart üzerinde: İndir, Sil, Konum Seç"),
                ("Shorts", "YouTube Shorts videoları da indirilebilir"),
            ]),
            ("⚙  Ayarlar", [
                ("Dil", "7 dil desteklenir: TR, EN, ES, FR, DE, JA, PT"),
                ("Tema", "Koyu ve Açık tema"),
                ("Format", "MP4 (video) veya MP3 (ses) seçin"),
                ("Ses Bildirimi", "İndirme tamamlandığında ses çalar"),
            ]),
        ]

        for section_title, items in sections:
            # Bölüm başlığı
            lbl_sec = QLabel(section_title)
            lbl_sec.setStyleSheet(f"font-size:13px;font-weight:700;color:{acc};margin-top:8px;")
            c_lay.addWidget(lbl_sec)

            # Çizgi
            line = QFrame()
            line.setFrameShape(QFrame.Shape.HLine)
            line.setStyleSheet(f"background:{border};max-height:1px;")
            c_lay.addWidget(line)

            for key, val in items:
                row = QWidget()
                row.setStyleSheet(f"background:{card};border-radius:6px;")
                r_lay = QHBoxLayout(row)
                r_lay.setContentsMargins(12, 6, 12, 6)
                r_lay.setSpacing(12)
                lbl_key = QLabel(key)
                lbl_key.setFixedWidth(160)
                lbl_key.setStyleSheet(f"font-size:12px;font-weight:600;color:{txt};background:transparent;")
                lbl_val = QLabel(val)
                lbl_val.setStyleSheet(f"font-size:12px;color:{sub};background:transparent;")
                lbl_val.setWordWrap(True)
                r_lay.addWidget(lbl_key)
                r_lay.addWidget(lbl_val, 1)
                c_lay.addWidget(row)

        c_lay.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        # Kapat butonu
        btn_close = QPushButton("  Kapat")
        btn_close.setFixedHeight(38)
        btn_close.setStyleSheet(f"""
            QPushButton {{ background: {acc}; border: none; border-radius: 0;
                color: #fff; font-size: 13px; font-weight: 600; }}
            QPushButton:hover {{ background: #a93226; }}
        """)
        btn_close.clicked.connect(dlg.accept)
        root.addWidget(btn_close)

        dlg.exec()

    # ── Filtre ───────────────────────────────────────────────────────────────

    def _apply_filter(self, btn):
        fid = btn.property("filter_id")
        for card in self.cards:
            if fid == "all":
                card.setVisible(True)
            elif fid == "active":
                card.setVisible(card.download_state in ("downloading", "queued", "paused"))
            elif fid == "done":
                card.setVisible(card.download_state == "completed")

    # ── Yardımcılar ──────────────────────────────────────────────────────────

    def _update_controls(self):
        has = len(self.cards) > 0
        self.btn_download_all.setEnabled(has)
        self.btn_clear.setEnabled(has)

    def _start_status_timer(self):
        t = QTimer(self)
        t.timeout.connect(self._update_status)
        t.start(1000)
        self._prev_active = 0   # toplu bildirim için önceki aktif sayısı
        self._notified_batch = False

    def _update_status(self):
        total     = len(self.cards)
        active    = sum(1 for c in self.cards if c.download_state in ("downloading", "queued"))
        completed = sum(1 for c in self.cards if c.download_state == "completed")
        errors    = sum(1 for c in self.cards if c.download_state == "error")
        tray = getattr(self, "_tray", None)
        if tray:
            tray.update_tooltip(active, completed)

        # İndirme sürerken PC uykuya dalmasın
        self._set_keep_awake(active > 0)

        # İkinci instance "beni öne getir" istediyse uygula
        self._check_show_request()

        # ── Toplu tamamlanma bildirimi ─────────────────────────────────
        prev_active = getattr(self, "_prev_active", 0)
        if prev_active > 0 and active == 0 and completed > 0 and not getattr(self, "_notified_batch", False):
            # Tüm indirmeler bitti
            total_bytes = sum(
                os.path.getsize(c._final_file)
                for c in self.cards
                if c.download_state == "completed" and c._final_file and os.path.exists(c._final_file)
            )
            if total_bytes >= 1024 * 1024 * 1024:
                size_str = f"{total_bytes/1024/1024/1024:.1f} GB"
            elif total_bytes >= 1024 * 1024:
                size_str = f"{total_bytes/1024/1024:.1f} MB"
            else:
                size_str = f"{total_bytes/1024:.0f} KB"

            err_str = f", {self._t('n_hata', n=errors)}" if errors > 0 else ""
            self.notification_center.show(
                self._t("indirmeler_tamamlandi"),
                f"{self._t('n_video_indirildi', n=completed)} · {size_str}{err_str}",
                "success"
            )
            self._notified_batch = True

        if active > 0:
            self._notified_batch = False  # yeni indirmeler başladıysa sıfırla

        self._prev_active = active

        # Tamamlanan dosyaların toplam boyutu
        total_bytes = 0
        for c in self.cards:
            if c.download_state == "completed" and c._final_file:
                try:
                    import os as _os
                    total_bytes += _os.path.getsize(c._final_file)
                except Exception:
                    pass

        size_str = ""
        if total_bytes > 0:
            _dl = self._t("indirildi_ek")
            if total_bytes >= 1024 * 1024 * 1024:
                size_str = f"  |  {total_bytes/1024/1024/1024:.1f} GB {_dl}"
            elif total_bytes >= 1024 * 1024:
                size_str = f"  |  {total_bytes/1024/1024:.1f} MB {_dl}"
            else:
                size_str = f"  |  {total_bytes/1024:.0f} KB {_dl}"

        self._lbl_status.setText(
            f"{self._t('toplam')}: {total} {self._t('video')}  |  "
            f"{self._t('indiriliyor')}: {active}  |  "
            f"{self._t('tamamlandi')}: {completed}"
            f"{size_str}"
        )

    def _desktop_path(self) -> str:
        for candidate in [Path.home() / "Desktop", Path.home() / "Masaüstü"]:
            if candidate.exists():
                return str(candidate)
        return str(Path.home())

    def quit_for_update(self) -> bool:
        """
        Güncelleme kurulumu için uygulamayı kapatır. Normal kapanış akışı
        çalışır (kuyruk diske yazılır); "çıkmak istiyor musunuz" sorusu
        sorulmaz ama aktif indirme varsa onay yine istenir.
        Returns: pencere kapandıysa True (kullanıcı vazgeçtiyse False).
        """
        self._force_quit = True
        self._updating   = True
        try:
            self.show()
            self.raise_()
            return self.close()
        finally:
            self._updating = False

    def quit_from_tray(self):
        """
        Tepsi menüsündeki Çıkış buradan gelir. Pencereyi gösterip normal
        closeEvent akışını (aktif indirme onayı dahil) çalıştırır —
        tepsiye gizleme dalı _force_quit ile atlanır.
        """
        self._force_quit = True
        self.show()
        self.raise_()
        self.activateWindow()
        self.close()

    def closeEvent(self, event):
        """Aktif indirme varsa kullanıcıya sor; tepsi aktifse gizle."""
        active = [c for c in self.cards
                  if c.download_state in ("downloading", "queued", "paused")]

        force_quit = getattr(self, "_force_quit", False)
        self._force_quit = False    # tek seferlik — iptal edilirse normal akışa dön

        t = self._t

        # Tepsi aktifse gizle (tepsiden Çıkış hariç)
        tray = getattr(self, "_tray", None)
        if tray and tray.isVisible() and not force_quit:
            if active:
                self.hide()
                tray.notify(t("arka_planda"),
                            t("arka_planda_govde", n=len(active)))
                event.ignore()
                return
            else:
                self._persist_queue_on_exit()
                event.accept()
                return

        if not active:
            # confirm_exit ayarı (güncelleme kurulumu için kapanırken sorma)
            if self.settings.get("confirm_exit", True) and not getattr(self, "_updating", False):
                if self._confirm_dialog(t("cikis"), t("cikis_soru"),
                                        btn_ok=t("evet_cik"), btn_cancel=t("hayir_cikma")):
                    self._persist_queue_on_exit()
                    event.accept()
                else:
                    event.ignore()
                return
            self._persist_queue_on_exit()
            event.accept()
            return

        names = []
        for c in active:
            title = getattr(c, "full_title", "") or c.url[:50]
            names.append("- " + title)
        names_text = "\n".join(names[:5])
        if len(active) > 5:
            names_text += "\n" + t("ve_n_daha", n=len(active) - 5)

        body = t("cikis_aktif", n=len(active)) + f"\n\n{names_text}"

        if self._confirm_dialog(t("cikis"), body,
                                btn_ok=t("evet_cik"), btn_cancel=t("hayir_cikma"),
                                danger=True):
            # Kuyruk diske yazılır; indirmeler İPTAL EDİLMEZ — .part dosyaları
            # kalır ki geri yüklemede kaldığı yerden devam edilebilsin.
            # Worker'ları main.py çıkışta download_manager.shutdown() durdurur.
            self._persist_queue_on_exit()
            event.accept()
        else:
            event.ignore()

    def _persist_queue_on_exit(self):
        """Tamamlanmamış kartları diske yazar — açılışta geri yükleme önerilir."""
        entries = []
        for c in self.cards:
            if c.download_state == "completed":
                continue
            entries.append({
                "url":     c.url,
                "format":  getattr(c, "_format", None),
                "quality": c.cmb_resolution.currentText() if c.cmb_resolution.count() else None,
                "folder":  c.download_folder or "",
            })
        self.settings_manager.save_pending_queue(entries)


    def eventFilter(self, obj, event):
        """Menü barında hover ile menü açma."""
        from PyQt6.QtCore import QEvent
        mb = self.menuBar()
        if obj is mb and event.type() in (QEvent.Type.MouseMove, QEvent.Type.HoverMove):
            action = mb.actionAt(event.pos())
            if action and action.menu():
                menu = action.menu()
                active = next(
                    (m for m in [self._m_file, self._m_tools] if m.isVisible()),
                    None
                )
                if active and active is not menu:
                    active.close()
                    mb.setActiveAction(action)
                    menu.popup(mb.mapToGlobal(mb.actionGeometry(action).bottomLeft()))
                elif not active:
                    mb.setActiveAction(action)
                    menu.popup(mb.mapToGlobal(mb.actionGeometry(action).bottomLeft()))
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        super().keyPressEvent(event)

    def moveEvent(self, event):
        super().moveEvent(event)
        self.notification_center._reposition()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.notification_center._reposition()
