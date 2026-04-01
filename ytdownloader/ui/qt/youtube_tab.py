# -*- coding: utf-8 -*-
"""YouTubeTab — Gömülü YouTube tarayıcısı sekmesi."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QSizePolicy, QLineEdit,
)
from pathlib import Path
import os
from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from ytdownloader.ui.qt.icon_helper import set_icon

# WebEngine opsiyonel — kurulu değilse fallback göster
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import (
        QWebEnginePage, QWebEngineSettings, QWebEngineProfile, QWebEngineScript,
        QWebEngineUrlRequestInterceptor, QWebEngineUrlRequestInfo,
    )
    WEBENGINE_AVAILABLE = True
except ImportError:
    WEBENGINE_AVAILABLE = False


# ── Reklam engelleyici ────────────────────────────────────────────────────────

_AD_DOMAINS = [
    "googlesyndication.com",
    "doubleclick.net",
    "googleadservices.com",
    "adservice.google.com",
    "pagead2.googlesyndication.com",
    "tpc.googlesyndication.com",
    "adsense.google.com",
    "imasdk.googleapis.com",
]

_AD_URL_PATTERNS = [
    "/pagead/",
]

# ── CSS: YouTube reklam elementlerini gizle ──────────────────────────────────
# DocumentReady'de inject edilir — sürdürülebilir minimum katman.
_ADBLOCK_CSS_JS = """
(function() {
    if (document.getElementById('__ytab_css')) return;
    var s = document.createElement('style');
    s.id = '__ytab_css';
    s.textContent = [
        /* ── VİDEO REKLAMI: player'ın TÜM içeriğini gizle ──────────────────── */
        '#movie_player.ad-showing{background:#0f0f0f!important}',
        '#movie_player.ad-showing>*{visibility:hidden!important}',
        '#movie_player.ad-interrupting{background:#0f0f0f!important}',
        '#movie_player.ad-interrupting>*{visibility:hidden!important}',
        /* ── COMPANION / BANNER ──────────────────────────────────────────────── */
        'ytd-action-companion-ad-renderer{display:none!important}',
        'ytd-companion-slot-renderer{display:none!important}',
        'ytd-banner-promo-renderer{display:none!important}',
        '.video-ads.ytp-ad-module{display:none!important}',
        '.ytp-ce-covering-overlay{display:none!important}',
        '.ytp-ad-progress-list{display:none!important}',
        /* ── ANASAYFA / FEED REKLAMLARI ─────────────────────────────────────── */
        '#masthead-ad{display:none!important}',
        'ytd-ad-slot-renderer{display:none!important}',
        'ytd-in-feed-ad-layout-renderer{display:none!important}',
        'ytd-display-ad-renderer{display:none!important}',
        'ytd-promoted-sparkles-web-renderer{display:none!important}',
        'ytd-promoted-video-renderer{display:none!important}',
        'ytd-rich-item-renderer:has(>*>ytd-ad-slot-renderer){display:none!important}',
        /* ── İZLEME SAYFASI SIDEBAR ─────────────────────────────────────────── */
        '#player-ads{display:none!important}',
        '#related ytd-ad-slot-renderer{display:none!important}',
        'ytd-engagement-panel-section-list-renderer[target-id="engagement-panel-ads"]{display:none!important}',
        /* ── YOUTUBE PREMIUM BASKISI ─────────────────────────────────────────── */
        'yt-mealbar-promo-renderer{display:none!important}',
        /* ── ARAMA SAYFASI ───────────────────────────────────────────────────── */
        'ytd-search-pyv-renderer{display:none!important}',
        'ytd-promoted-sparkles-text-search-renderer{display:none!important}',
    ].join('');
    (document.head || document.documentElement).appendChild(s);
})();
"""


class _AdBlockInterceptor(QWebEngineUrlRequestInterceptor):
    """Bilinen reklam sunucularına giden istekleri engeller."""

    def interceptRequest(self, info: QWebEngineUrlRequestInfo):
        url  = info.requestUrl().toString()
        host = info.requestUrl().host()
        for domain in _AD_DOMAINS:
            if domain in host:
                info.block(True)
                return
        for pattern in _AD_URL_PATTERNS:
            if pattern in url:
                info.block(True)
                return


# Güncel tarayıcı User-Agent'ları
_USER_AGENTS = {
    "edge":    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    "chrome":  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "firefox": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "opera":   "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 OPR/117.0.0.0",
    "brave":   "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "vivaldi": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
}
_DEFAULT_UA = _USER_AGENTS["edge"]  # fallback
_YT_PROFILE = None  # Global kalıcı profil


def _detect_default_browser() -> str:
    """Windows'ta varsayılan tarayıcıyı tespit et. Tarayıcı key döner."""
    import os, winreg
    if os.name != "nt":
        return "edge"
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice"
        )
        prog_id, _ = winreg.QueryValueEx(key, "ProgId")
        winreg.CloseKey(key)
        prog_id = prog_id.lower()
        if "edge" in prog_id:      return "edge"
        if "chrome" in prog_id:    return "chrome"
        if "firefox" in prog_id:   return "firefox"
        if "opera" in prog_id:     return "opera"
        if "brave" in prog_id:     return "brave"
        if "vivaldi" in prog_id:   return "vivaldi"
    except Exception:
        pass
    return "edge"


class YouTubeTab(QWidget):
    """
    YouTube.com'u gösteren gömülü tarayıcı sekmesi.
    Video sayfasında üstte 'Bu Videoyu İndir' butonu çıkar.
    """

    # Video URL'si algılandığında bu sinyal yayınlanır
    video_detected = pyqtSignal(str)   # url

    YOUTUBE_HOME = "https://www.youtube.com"

    def __init__(self, settings_service=None, parent=None):
        super().__init__(parent)
        self._current_url = ""
        self._profile = None
        self._settings = settings_service
        # Ayarlardan tarayıcı seç, "auto" ise sistem varsayılanını tespit et
        if settings_service:
            br = settings_service.get("webview_browser", "auto")
            self._browser_key = br if br != "auto" else _detect_default_browser()
        else:
            self._browser_key = _detect_default_browser()
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        if not WEBENGINE_AVAILABLE:
            self._build_fallback(root)
            return

        # ── Adres çubuğu ─────────────────────────────────────────────────────
        bar = QFrame()
        self._bar = bar
        bar.setObjectName("youtube_bar")
        bar.setFixedHeight(48)
        bar.setStyleSheet("""
            #youtube_bar {
                background: #1a1d27;
                border-bottom: 1px solid #2e3348;
            }
        """)
        bar_lay = QHBoxLayout(bar)
        bar_lay.setContentsMargins(12, 6, 12, 6)
        bar_lay.setSpacing(8)

        # Geri / İleri / Yenile — set_icon ile SVG (yapıştır/indir butonlarıyla aynı sistem)
        _nav_css = """
            QPushButton { background: #2e3348; border: none; border-radius: 8px; }
            QPushButton:hover { background: #3d4460; }
        """
        self._btn_back = QPushButton()
        self._btn_back.setFixedSize(32, 32)
        self._btn_back.setToolTip("Geri")
        self._btn_back.setStyleSheet(_nav_css)
        self._btn_back.setEnabled(False)
        set_icon(self._btn_back, "arrow_left", "#e8eaf0", 16)
        self._btn_back.clicked.connect(lambda: self._view.back())
        bar_lay.addWidget(self._btn_back)

        self._btn_forward = QPushButton()
        self._btn_forward.setFixedSize(32, 32)
        self._btn_forward.setToolTip("İleri")
        self._btn_forward.setStyleSheet(_nav_css)
        self._btn_forward.setEnabled(False)
        set_icon(self._btn_forward, "arrow_right", "#e8eaf0", 16)
        self._btn_forward.clicked.connect(lambda: self._view.forward())
        bar_lay.addWidget(self._btn_forward)

        self._btn_reload = QPushButton()
        self._btn_reload.setFixedSize(32, 32)
        self._btn_reload.setToolTip("Yenile")
        self._btn_reload.setStyleSheet(_nav_css)
        set_icon(self._btn_reload, "refresh", "#e8eaf0", 16)
        self._btn_reload.clicked.connect(lambda: self._view.reload())
        bar_lay.addWidget(self._btn_reload)

        # Arama / URL çubuğu
        self._lbl_url = QLineEdit()
        self._lbl_url.setPlaceholderText("Ara veya URL yapıştır...")
        self._lbl_url.setStyleSheet(
            "QLineEdit { background: #12141f; border: 1px solid #2e3348;"
            " border-radius: 8px; padding: 0 12px; color: #e8eaf0; font-size: 12px; }"
            " QLineEdit:focus { border: 1px solid #c0392b; background: #0e1018; }"
        )
        self._lbl_url.setFixedHeight(32)
        self._lbl_url.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._lbl_url.returnPressed.connect(self._on_search_or_navigate)
        bar_lay.addWidget(self._lbl_url)

        # "Tarayıcıda Aç" — mevcut URL'yi sistem tarayıcısında açar
        self._btn_open_browser = QPushButton("  Tarayıcıda Aç")
        self._btn_open_browser.setFixedHeight(32)
        self._btn_open_browser.setToolTip(
            "Bu sayfayı sistem tarayıcınızda aç.\n"
            "Oturum, indirme kalitesi ve reklam deneyimi\n"
            "için sistem tarayıcınızı kullanmanız önerilir."
        )
        self._btn_open_browser.setStyleSheet("""
            QPushButton {
                background: #2e3348; border: 1px solid #3d4460;
                border-radius: 8px; color: #9da3b4;
                font-size: 12px; padding: 0 12px 0 8px;
            }
            QPushButton:hover { background: #3d4460; color: #e8eaf0; border-color: #5a6080; }
        """)
        set_icon(self._btn_open_browser, "external_link", "#9da3b4", 14)
        self._btn_open_browser.clicked.connect(self._on_open_in_browser)
        bar_lay.addWidget(self._btn_open_browser)

        # "İndirme Yöneticisine Ekle" butonu — sadece video sayfasında görünür
        self._btn_download = QPushButton("⬇  İndirme Yöneticisine Ekle")
        self._btn_download.setFixedHeight(32)
        self._btn_download.setVisible(False)
        self._btn_download.setToolTip("İndirme listesine ekle")
        self._btn_download.setStyleSheet("""
            QPushButton {
                background: #c0392b; border: none; border-radius: 8px;
                color: #ffffff; font-size: 12px; font-weight: 700;
                padding: 0 14px; letter-spacing: 0.3px;
            }
            QPushButton:hover { background: #a93226; }
            QPushButton:pressed { background: #aa0000; }
        """)
        self._btn_download.clicked.connect(self._on_download_clicked)
        bar_lay.addWidget(self._btn_download)

        root.addWidget(bar)

        # ── WebEngine görünümü ────────────────────────────────────────────────
        # Kalıcı profil — oturum uygulama kapanınca silinmez
        if WEBENGINE_AVAILABLE:
            try:
                # APPDATA her ortamda çalışır (bat, exe, direkt python)
                appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
                profile_path = str(Path(appdata) / "MyYouTubeDownloader" / "browser_profile")
                Path(profile_path).mkdir(parents=True, exist_ok=True)
                # Global profil — uygulama boyunca tek instance, kapanınca silinmez
                global _YT_PROFILE
                if _YT_PROFILE is None:
                    _YT_PROFILE = QWebEngineProfile("yt_session")
                    _YT_PROFILE.setPersistentStoragePath(profile_path)
                    _YT_PROFILE.setCachePath(profile_path + "_cache")
                    _YT_PROFILE.setPersistentCookiesPolicy(
                        QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
                    )
                    ua = _USER_AGENTS.get(self._browser_key, _DEFAULT_UA)
                    _YT_PROFILE.setHttpUserAgent(ua)
                    # Gerçekte kullanılan dizinleri logla — kalıcılık sorunlarını ayıklamak için
                    import logging as _logging
                    _log = _logging.getLogger("youtube_tab")
                    _log.info(f"[WebEngine] Profil storage: {_YT_PROFILE.persistentStoragePath()}")
                    _log.info(f"[WebEngine] Cache: {_YT_PROFILE.cachePath()}")
                    _log.info(f"[WebEngine] Off-the-record: {_YT_PROFILE.isOffTheRecord()}")

                    # Reklam engelleyici — ağ katmanı
                    _YT_PROFILE._interceptor = _AdBlockInterceptor()
                    _YT_PROFILE.setUrlRequestInterceptor(_YT_PROFILE._interceptor)

                self._profile = _YT_PROFILE
                self._view = _QuietWebEngineView(profile=self._profile)

                # CSS — reklam elementlerini gizler (DocumentReady)
                # QWebEnginePage.scripts().insert() kullanılıyor (profile level
                # bu Qt/PyQt6 sürümünde çalışmıyor).
                css_script = QWebEngineScript()
                css_script.setName("adblock_css")
                css_script.setSourceCode(_ADBLOCK_CSS_JS)
                css_script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentReady)
                css_script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
                css_script.setRunsOnSubFrames(False)
                self._view.page().scripts().insert(css_script)

            except Exception as e:
                self._view = _QuietWebEngineView()
        else:
            self._view = _QuietWebEngineView()

        # Ayarlar — JavaScript, medya, vs.
        settings = self._view.settings()
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)

        self._view.urlChanged.connect(self._on_url_changed)
        self._view.loadFinished.connect(self._on_load_finished)

        # Sağ tık menüsü için callback bağla
        self._view._on_send_to_manager = lambda url: self.video_detected.emit(url)

        # Başlangıçta mevcut temayı uygula
        from ytdownloader.ui.qt.theme import theme_manager
        self.apply_theme(theme_manager.current)

        root.addWidget(self._view)

        # YouTube'u yükle
        self._view.load(QUrl(self.YOUTUBE_HOME))

    def _build_fallback(self, root):
        """WebEngine kurulu değilse kurulum talimatı göster."""
        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(16)

        lbl_icon = QLabel("🌐")
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        lbl_icon.setStyleSheet("font-size: 48px;")
        lay.addWidget(lbl_icon)

        lbl_title = QLabel("YouTube Tarayıcısı Kullanılamıyor")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        lbl_title.setStyleSheet(
            "font-size: 18px; font-weight: 700; color: #e8eaf0;"
        )
        lay.addWidget(lbl_title)

        lbl_desc = QLabel(
            "Bu özellik için PyQt6-WebEngine paketi gerekli.\n"
            "Aşağıdaki komutu çalıştırarak kurabilirsiniz:"
        )
        lbl_desc.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        lbl_desc.setStyleSheet("font-size: 13px; color: #9da3b4;")
        lay.addWidget(lbl_desc)

        lbl_cmd = QLabel("pip install PyQt6-WebEngine")
        lbl_cmd.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        lbl_cmd.setStyleSheet("""
            background: #1a1d27; border: 1px solid #2e3348;
            border-radius: 8px; padding: 12px 24px;
            color: #c0392b; font-size: 14px; font-family: monospace;
        """)
        lbl_cmd.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        lay.addWidget(lbl_cmd)

        root.addWidget(container)

    # ── URL İzleme ────────────────────────────────────────────────────────────

    def _on_url_changed(self, url: QUrl):
        url_str = url.toString()
        self._current_url = url_str
        if not self._lbl_url.hasFocus():
            self._lbl_url.setText(url_str)

        # Video sayfası mı? watch?v= veya /shorts/ içeriyorsa evet
        is_video = (
            ("youtube.com/watch" in url_str and "v=" in url_str)
            or "youtube.com/shorts/" in url_str
        )
        self._btn_download.setVisible(is_video)

    def _on_load_finished(self, ok: bool):
        """Sayfa yüklenince geri/ileri butonlarını güncelle."""
        if hasattr(self, "_btn_back"):
            self._btn_back.setEnabled(self._view.history().canGoBack())
            self._btn_forward.setEnabled(self._view.history().canGoForward())

        if not ok or not hasattr(self, "_view"):
            return

        url = self._view.url().toString()

        # Google giriş sayfasındaysa passkey popup'ını kapat, oturum sorgusu yapma
        if "accounts.google.com" in url:
            self._view.page().runJavaScript("""
                (function() {
                    var selectors = [
                        'button[data-action="dismiss"]',
                        'button[jsname="LgbsSe"]',
                        '[data-challengetype="56"] button',
                        'div[role="dialog"] button:last-child',
                    ];
                    for (var s of selectors) {
                        var btn = document.querySelector(s);
                        if (btn && (btn.textContent.includes('ptal') || btn.textContent.includes('ancel') || btn.textContent.includes('kip'))) {
                            btn.click();
                            return 'closed';
                        }
                    }
                    var overlays = document.querySelectorAll('[role="dialog"]');
                    for (var o of overlays) {
                        var btns = o.querySelectorAll('button');
                        for (var b of btns) {
                            if (b.textContent.trim() === 'İptal' || b.textContent.trim() === 'Cancel') {
                                b.click();
                                return 'overlay-closed';
                            }
                        }
                    }
                    return 'not-found';
                })()
            """, lambda result: None)
            return  # Google sayfalarında oturum sorgusu yapma



    def _on_search_or_navigate(self):
        """Enter'a basılınca: URL ise git, değilse YouTube'da ara."""
        text = self._lbl_url.text().strip()
        if not text:
            return
        if text.startswith("http://") or text.startswith("https://") or text.startswith("www."):
            # Direkt URL — git
            if not text.startswith("http"):
                text = "https://" + text
            from PyQt6.QtCore import QUrl
            self._view.load(QUrl(text))
        else:
            # Arama sorgusu — YouTube'da ara
            import urllib.parse
            query = urllib.parse.quote_plus(text)
            from PyQt6.QtCore import QUrl
            self._view.load(QUrl(f"https://www.youtube.com/results?search_query={query}"))
        self._lbl_url.clearFocus()


    def _on_open_in_browser(self):
        """Mevcut URL'yi işletim sisteminin varsayılan tarayıcısında açar."""
        url = self._current_url or self.YOUTUBE_HOME
        import webbrowser
        webbrowser.open(url)

    def _on_download_clicked(self):
        """İndir butonuna basılınca video URL'sini sinyal olarak yayınla."""
        if self._current_url:
            self.video_detected.emit(self._current_url)

    def apply_theme(self, theme: str):
        """Tema değişince adres çubuğunu güncelle (dark/light)."""
        if not WEBENGINE_AVAILABLE:
            return

        is_dark  = theme == "dark"
        bg       = "#1a1d27" if is_dark else "#f0f2f7"
        border   = "#2e3348" if is_dark else "#d0d5e0"
        text     = "#9da3b4" if is_dark else "#444b5e"
        bar_bg   = "#1a1d27" if is_dark else "#e8eaf0"
        btn_bg   = "#2e3348" if is_dark else "#d8dce8"
        btn_hov  = "#3d4460" if is_dark else "#c4c9d8"
        icon_clr = "#e8eaf0" if is_dark else "#222233"

        if hasattr(self, '_bar'):
            self._bar.setStyleSheet(f"""
                #youtube_bar {{
                    background: {bar_bg};
                    border-bottom: 1px solid {border};
                }}
            """)

        if hasattr(self, "_lbl_url"):
            self._lbl_url.setStyleSheet(
                f"QLineEdit {{ background: {bg}; border: 1px solid {border};"
                f" border-radius: 8px; padding: 0 12px; color: {text}; font-size: 12px; }}"
                f" QLineEdit:focus {{ border: 1px solid #c0392b; }}"
            )

        nav_css = f"QPushButton{{background:{btn_bg};border:none;border-radius:8px;}}QPushButton:hover{{background:{btn_hov};}}"
        if hasattr(self, '_btn_open_browser'):
            brd = '#3d4460' if is_dark else '#c4c9d8'
            clr = '#9da3b4' if is_dark else '#6b7280'
            hov_clr = '#e8eaf0' if is_dark else '#111827'
            self._btn_open_browser.setStyleSheet(f"""
                QPushButton {{
                    background: {btn_bg}; border: 1px solid {brd};
                    border-radius: 8px; color: {clr};
                    font-size: 12px; padding: 0 12px 0 8px;
                }}
                QPushButton:hover {{ background: {btn_hov}; color: {hov_clr}; border-color: {'#5a6080' if is_dark else '#a0a8be'}; }}
            """)
            set_icon(self._btn_open_browser, "external_link", icon_clr, 14)
        for btn, svg in [(self._btn_back,"arrow_left"),(self._btn_forward,"arrow_right"),(self._btn_reload,"refresh")]:
            btn.setStyleSheet(nav_css)
            set_icon(btn, svg, icon_clr, 16)


class _QuietPage(QWebEnginePage):
    """Console mesajlarını susturan sayfa."""
    def __init__(self, profile_or_parent=None, parent=None):
        if profile_or_parent is None:
            super().__init__()
        elif hasattr(profile_or_parent, 'persistentStoragePath'):
            # QWebEngineProfile
            super().__init__(profile_or_parent, parent)
        else:
            super().__init__(profile_or_parent)

    def javaScriptConsoleMessage(self, level, message, line, source):
        pass  # YouTube JS console çıktısını bastır


class _QuietWebEngineView(QWebEngineView):
    def __init__(self, profile=None, parent=None):
        if profile is not None:
            page = _QuietPage(profile, None)
            super().__init__(parent)
            self.setPage(page)
        else:
            super().__init__(parent)
        self._on_send_to_manager = None  # Callback: fn(url)

    def createWindow(self, type_):
        """Yeni sekme/popup isteklerini aynı view'da aç."""
        return self

    def contextMenuEvent(self, event):
        """Sağ tık menüsü — sadece İndirme Yöneticisine Gönder."""
        from PyQt6.QtWidgets import QMenu
        url = self.url().toString()
        is_video = (
            ("youtube.com/watch" in url and "v=" in url)
            or "youtube.com/shorts/" in url
        )
        if not is_video or not self._on_send_to_manager:
            return  # Video sayfasında değilse hiç menü çıkmasın

        label = "İndirme Yöneticisine Ekle"

        menu = QMenu(self)
        act = menu.addAction(f"⬇  {label}")
        act.triggered.connect(lambda: self._on_send_to_manager(url))
        menu.exec(event.globalPos())
