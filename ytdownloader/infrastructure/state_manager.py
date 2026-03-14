# -*- coding: utf-8 -*-
"""
StateManager — tüm indirmelerin durumunu thread-safe yönetir.

Kurallar:
  1. Durum değişikliği sadece transition() ile yapılır
  2. Geçersiz geçiş → StateError (sessizce geçmez)
  3. Lock minimum süre tutulur — callback'ler lock dışında çağrılır
  4. EventBus'a publish lock dışında yapılır (deadlock önlemi)
"""

import threading
from datetime import datetime
from typing import Optional

from ytdownloader.models.download_state import (
    DownloadState, VALID_TRANSITIONS, TERMINAL_STATES, StateError
)
from ytdownloader.models.download_item import DownloadItem
from ytdownloader.infrastructure.event_bus import EventBus, Events
from ytdownloader.infrastructure.logger import get_logger

log = get_logger("state_manager")


class StateManager:

    def __init__(self, event_bus: EventBus):
        self._bus = event_bus
        self._lock = threading.RLock()          # RLock: callback zincirinde recursive güvenli
        self._items: dict[str, DownloadItem] = {}

    # ── Kayıt ─────────────────────────────────────────────────────────────────

    def register(self, item: DownloadItem) -> None:
        """Yeni bir indirmeyi kayıt altına alır."""
        with self._lock:
            if item.id in self._items:
                raise ValueError(f"ID zaten kayıtlı: {item.id}")
            self._items[item.id] = item
            log.debug(f"[{item.id}] Kayıt edildi: {item.url}")

        self._bus.publish(Events.STATE_CHANGED, {
            "id":        item.id,
            "old_state": None,
            "new_state": item.state.name,
            "item":      item.to_dict(),
        })

    def unregister(self, download_id: str) -> None:
        """Tamamlanmış/iptal edilmiş indirmeyi kayıttan siler."""
        with self._lock:
            self._items.pop(download_id, None)
        log.debug(f"[{download_id}] Kayıttan silindi")

    # ── Durum Geçişi ──────────────────────────────────────────────────────────

    def transition(self, download_id: str, new_state: DownloadState) -> None:
        """
        Belirtilen indirmeyi yeni duruma geçirir.
        Geçersiz geçiş → StateError fırlatır.
        """
        # Kritik bölge: sadece state değişikliğini yap
        with self._lock:
            item = self._items.get(download_id)
            if item is None:
                raise KeyError(f"Bilinmeyen download_id: {download_id}")

            old_state = item.state

            if old_state == new_state:
                return  # zaten bu durumda, sessizce geç

            if new_state not in VALID_TRANSITIONS.get(old_state, frozenset()):
                raise StateError(
                    f"[{download_id}] Geçersiz geçiş: "
                    f"{old_state.name} → {new_state.name}"
                )

            item.state = new_state

            # Zamanlama güncelle
            if new_state == DownloadState.ACTIVE and item.started_at is None:
                item.started_at = datetime.now()
            elif new_state in TERMINAL_STATES:
                item.completed_at = datetime.now()

            snapshot = item.to_dict()   # lock içinde kopyala, dışında yayınla

        # Lock dışında yayınla — callback içinde başka transition olsa bile deadlock yok
        log.debug(f"[{download_id}] {old_state.name} → {new_state.name}")
        self._bus.publish(Events.STATE_CHANGED, {
            "id":        download_id,
            "old_state": old_state.name,
            "new_state": new_state.name,
            "item":      snapshot,
        })

        # Özel event'ler
        event_map = {
            DownloadState.ACTIVE:     Events.DOWNLOAD_STARTED,
            DownloadState.PAUSED:     Events.DOWNLOAD_PAUSED,
            DownloadState.COMPLETED:  Events.DOWNLOAD_COMPLETED,
            DownloadState.CANCELLED:  Events.DOWNLOAD_CANCELLED,
            DownloadState.ERROR:      Events.DOWNLOAD_ERROR,
            DownloadState.RETRYING:   Events.DOWNLOAD_RETRYING,
        }
        if new_state in event_map:
            self._bus.publish(event_map[new_state], snapshot)

    # ── Sorgulama ─────────────────────────────────────────────────────────────

    def get_state(self, download_id: str) -> Optional[DownloadState]:
        with self._lock:
            item = self._items.get(download_id)
            return item.state if item else None

    def get_item(self, download_id: str) -> Optional[DownloadItem]:
        with self._lock:
            return self._items.get(download_id)

    def get_all(self) -> list[DownloadItem]:
        with self._lock:
            return list(self._items.values())

    def get_active_count(self) -> int:
        with self._lock:
            return sum(1 for i in self._items.values()
                       if i.state == DownloadState.ACTIVE)

    def update_progress(self, download_id: str, progress: float,
                        speed: float = 0, eta: Optional[int] = None,
                        downloaded_bytes: int = 0, total_bytes: int = 0) -> None:
        """İlerleme bilgisini günceller. State geçişi yapmaz."""
        with self._lock:
            item = self._items.get(download_id)
            if item is None:
                return
            item.progress        = progress
            item.speed           = speed
            item.eta             = eta
            item.downloaded_bytes = downloaded_bytes
            item.total_bytes     = total_bytes
            snapshot = item.to_dict()

        self._bus.publish(Events.DOWNLOAD_PROGRESS, snapshot)

    def set_error(self, download_id: str, message: str) -> None:
        """Hata mesajını kaydeder ve ERROR durumuna geçirir."""
        with self._lock:
            item = self._items.get(download_id)
            if item:
                item.error_message = message

        try:
            self.transition(download_id, DownloadState.ERROR)
        except StateError as e:
            log.warning(f"set_error geçiş hatası: {e}")

    def set_final_file(self, download_id: str, path: str) -> None:
        with self._lock:
            item = self._items.get(download_id)
            if item:
                item.final_file = path
