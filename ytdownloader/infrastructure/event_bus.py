# -*- coding: utf-8 -*-
"""
EventBus — thread-safe pub/sub mesajlaşma sistemi.

Modüller birbirini doğrudan import etmek yerine event yayar/dinler.
Bu sayede modüller birbirinden bağımsız kalır (loose coupling).

UI thread güvenliği:
    Callback'ler publish() çağrıldığında senkron çalışır. Worker thread'den
    UI'ya köprü kurulması UI katmanının sorumluluğundadır (PyQt6 sinyal mekanizması).

Kullanım:
    bus = EventBus()
    bus.subscribe("download:progress", on_progress)
    bus.publish("download:progress", {"id": "abc", "pct": 45.2})
"""

import threading
import logging
from typing import Callable
from dataclasses import dataclass

log = logging.getLogger("ytdownloader.event_bus")


@dataclass
class _Subscription:
    callback: Callable


class EventBus:

    def __init__(self):
        self._lock = threading.RLock()
        # { event_name: [_Subscription, ...] }
        self._subscribers: dict[str, list[_Subscription]] = {}

    # ── Public API ────────────────────────────────────────────────────────────

    def subscribe(self, event: str, callback: Callable) -> None:
        """
        Bir olayı dinlemeye başlar.

        Args:
            event:    Olay adı, örn. "download:progress"
            callback: Olay gerçekleşince çağrılacak fonksiyon.
                      UI güncellemesi gerekiyorsa callback içinde PyQt6
                      sinyal mekanizması (pyqtSignal.emit) kullanılmalıdır.
        """
        with self._lock:
            if event not in self._subscribers:
                self._subscribers[event] = []
            self._subscribers[event].append(_Subscription(callback))
            log.debug(f"Abonelik: '{event}' ← {callback.__qualname__}")

    def unsubscribe(self, event: str, callback: Callable) -> None:
        """Belirtilen callback'i olay dinleyicilerinden çıkarır."""
        with self._lock:
            subs = self._subscribers.get(event, [])
            self._subscribers[event] = [s for s in subs if s.callback is not callback]

    def publish(self, event: str, data=None) -> None:
        """
        Olayı yayınlar. Tüm subscriber'lar bildirilir.
        Lock dışında çağrılır — callback içinde publish yapılsa bile deadlock olmaz.
        """
        with self._lock:
            subs = list(self._subscribers.get(event, []))

        if not subs:
            return

        for sub in subs:
            try:
                self._dispatch(sub, event, data)
            except Exception as e:
                log.error(f"EventBus callback hatası [{event}]: {e}", exc_info=True)

    def clear(self, event: str | None = None) -> None:
        """
        Tüm abonelikleri temizler.
        event verilirse sadece o olayın abonelikleri temizlenir.
        """
        with self._lock:
            if event:
                self._subscribers.pop(event, None)
            else:
                self._subscribers.clear()

    # ── Internal ──────────────────────────────────────────────────────────────

    @staticmethod
    def _dispatch(sub: _Subscription, event: str, data) -> None:
        sub.callback(data)



# ── Standart event isimleri ───────────────────────────────────────────────────
class Events:
    """Event isimlerini string literal yerine sabit olarak tanımlar."""

    # Download lifecycle
    DOWNLOAD_QUEUED     = "download:queued"
    DOWNLOAD_STARTED    = "download:started"
    DOWNLOAD_PROGRESS   = "download:progress"
    DOWNLOAD_PAUSED     = "download:paused"
    DOWNLOAD_RESUMED    = "download:resumed"
    DOWNLOAD_COMPLETED  = "download:completed"
    DOWNLOAD_CANCELLED  = "download:cancelled"
    DOWNLOAD_ERROR      = "download:error"
    DOWNLOAD_RETRYING   = "download:retrying"

    # State change (genel)
    STATE_CHANGED       = "state:changed"

    # Fetch
    FETCH_STARTED       = "fetch:started"
    FETCH_COMPLETED     = "fetch:completed"
    FETCH_ERROR         = "fetch:error"

    # Settings
    SETTINGS_CHANGED    = "settings:changed"
    THEME_CHANGED       = "settings:theme_changed"
    LANGUAGE_CHANGED    = "settings:language_changed"
