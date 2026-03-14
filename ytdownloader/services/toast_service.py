# -*- coding: utf-8 -*-
"""
ToastService — Windows bildirimlerini kalıcı bir PowerShell process üzerinden
anlık gönderir. Her bildirim için yeni process başlatmaz = gecikme yok.
"""

import sys
import threading
import subprocess
import os


class _ToastService:
    """
    Tek bir PowerShell process başlatır, stdin'e JSON komut gönderir.
    Process bir kere başlar, uygulama kapanana kadar canlı kalır.
    """

    APP_ID = "YTDownloader.YouTubeIndirici.1.0"

    # PowerShell loop scripti — stdin'den satır okur, her satır bir bildirim
    _PS_LOOP = r"""
$app = 'YTDownloader.YouTubeIndirici.1.0'
[void][Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime]
[void][Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType=WindowsRuntime]
$notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($app)
while ($true) {
    $line = [Console]::ReadLine()
    if ($null -eq $line) { break }
    $line = $line.Trim()
    if ($line -eq '') { continue }
    try {
        $parts = $line -split '\|', 2
        $title = $parts[0]
        $body  = if ($parts.Length -gt 1) { $parts[1] } else { '' }
        $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
        $escaped_title = [System.Security.SecurityElement]::Escape($title)
        $escaped_body  = [System.Security.SecurityElement]::Escape($body)
        $xml.LoadXml("<toast><visual><binding template='ToastGeneric'><text>$escaped_title</text><text>$escaped_body</text></binding></visual></toast>")
        $toast = New-Object Windows.UI.Notifications.ToastNotification $xml
        $notifier.Show($toast)
    } catch { }
}
"""

    def __init__(self):
        self._proc = None
        self._lock = threading.Lock()
        self._started = False

    def _ensure_started(self):
        if self._started:
            return
        with self._lock:
            if self._started:
                return
            try:
                self._proc = subprocess.Popen(
                    ["powershell", "-NonInteractive", "-NoProfile",
                     "-WindowStyle", "Hidden", "-Command", self._PS_LOOP],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=0x08000000,  # CREATE_NO_WINDOW
                    text=True,
                    encoding="utf-8",
                    bufsize=1,  # line-buffered
                )
                self._started = True
            except Exception:
                self._started = False

    def notify(self, title: str, message: str = "") -> None:
        """Bildirimi anlık gönder — non-blocking."""
        if sys.platform != "win32":
            return

        # Sistem sesini hemen çal (non-blocking)
        try:
            import ctypes
            ctypes.windll.winmm.PlaySoundW("SystemAsterisk", None, 0x00010001)
        except Exception:
            pass

        # Toast'ı arka planda gönder
        threading.Thread(
            target=self._send,
            args=(title, message),
            daemon=True
        ).start()

    def _send(self, title: str, message: str):
        try:
            self._ensure_started()
            if not self._started or self._proc is None:
                return

            # | karakterini temizle (ayırıcı olarak kullanıyoruz)
            safe_title   = title.replace("|", "-").replace("\n", " ")[:80]
            safe_message = message.replace("|", "-").replace("\n", " ")[:120]

            line = f"{safe_title}|{safe_message}\n"
            with self._lock:
                if self._proc.poll() is not None:
                    # Process ölmüş, yeniden başlat
                    self._started = False
                    self._ensure_started()
                self._proc.stdin.write(line)
                self._proc.stdin.flush()
        except Exception:
            # Process öldüyse bir sonraki çağrıda yeniden başlatılır
            self._started = False

    def shutdown(self):
        """Uygulama kapanırken PowerShell process'ini temizle."""
        try:
            if self._proc and self._proc.poll() is None:
                self._proc.stdin.close()
                self._proc.terminate()
        except Exception:
            pass


# Singleton
_service = _ToastService()


def notify(title: str, message: str = "") -> None:
    """Global bildirim fonksiyonu — her yerden çağrılabilir."""
    _service.notify(title, message)


def shutdown():
    """Uygulama kapanışında çağır."""
    _service.shutdown()
