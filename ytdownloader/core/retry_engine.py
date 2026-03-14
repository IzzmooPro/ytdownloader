# -*- coding: utf-8 -*-
"""
RetryEngine — ağ hatalarında otomatik yeniden deneme.

Strateji: Exponential backoff + jitter
  1. deneme: 2 saniye bekle
  2. deneme: 4 saniye
  3. deneme: 8 saniye
  4. deneme: 16 saniye
  5. deneme: 32 saniye (max)
  + her beklemeye rastgele ±1s jitter eklenir (aynı anda başlayan
    çok sayıda indirmenin YouTube'u eş zamanlı vurmasını önler)

Hata sınıflandırması:
  - Yeniden denenebilir: ağ timeout, rate limit, geçici sunucu hatası
  - Denenemeyen: video mevcut değil, özel video, telif hakkı
"""

import re
import time
import random
import threading
from dataclasses import dataclass, field
from typing import Callable

from ytdownloader.infrastructure.logger import get_logger

log = get_logger("retry_engine")


# ── Yeniden denenemeyen hata kalıpları ───────────────────────────────────────
_NON_RETRYABLE_PATTERNS = [
    r"video unavailable",
    r"this video is private",
    r"this video has been removed",
    r"copyright",
    r"age.restricted",
    r"sign in to confirm your age",
    r"this video is not available",
    r"no video formats found",
    r"urlopen error",           # DNS hatası — retry işe yaramaz
]

_NON_RETRYABLE_RE = re.compile(
    "|".join(_NON_RETRYABLE_PATTERNS), re.IGNORECASE
)


@dataclass
class RetryConfig:
    max_attempts:  int   = 5
    base_delay:    float = 2.0    # saniye
    max_delay:     float = 32.0   # saniye
    jitter:        float = 1.0    # ±saniye


@dataclass
class RetryState:
    attempt:       int   = 0
    total_wait:    float = 0.0
    last_error:    str   = ""
    gave_up:       bool  = False


class RetryEngine:

    def __init__(self, config: RetryConfig | None = None):
        self._config = config or RetryConfig()

    def is_retryable(self, error: str | Exception) -> bool:
        """Hatanın yeniden denenip denenemeayeceğini döner."""
        msg = str(error).lower()
        return not bool(_NON_RETRYABLE_RE.search(msg))

    def next_delay(self, attempt: int) -> float:
        """
        Kaçıncı denemede ne kadar bekleneceğini hesaplar.
        attempt=1 → ilk retry (2s + jitter)
        """
        cfg = self._config
        delay = min(cfg.base_delay * (2 ** (attempt - 1)), cfg.max_delay)
        jitter = random.uniform(-cfg.jitter, cfg.jitter)
        return max(0.5, delay + jitter)

    def run(self,
            fn: Callable[[], dict],
            download_id: str,
            cancel_event: threading.Event,
            on_retry: Callable[[int, float, str], None] | None = None) -> dict:
        """
        fn'i en fazla max_attempts kez çalıştırır.

        Args:
            fn:           İndirme işlemini yapan fonksiyon. {"status": ...} döner.
            download_id:  Log için ID.
            cancel_event: Set edilirse retry döngüsü kırılır.
            on_retry:     Her retry öncesi çağrılır: (attempt, wait_secs, error_msg)

        Returns:
            fn'in son döndürdüğü sonuç dict'i.
        """
        cfg    = self._config
        state  = RetryState()
        result = {"status": "error", "error": "Bilinmeyen hata"}

        for attempt in range(1, cfg.max_attempts + 1):
            if cancel_event.is_set():
                return {"status": "cancelled"}

            state.attempt = attempt
            log.debug(f"[{download_id}] Deneme {attempt}/{cfg.max_attempts}")

            result = fn()

            # Başarılı veya iptal
            if result.get("status") in ("completed", "cancelled"):
                return result

            error = result.get("error", "")
            state.last_error = error

            # Son deneme veya yeniden denenemez hata
            if attempt == cfg.max_attempts:
                log.error(f"[{download_id}] Tüm denemeler tükendi: {error}")
                state.gave_up = True
                break

            if not self.is_retryable(error):
                log.warning(f"[{download_id}] Yeniden denenemez hata: {error}")
                break

            # Bekle
            wait = self.next_delay(attempt)
            state.total_wait += wait
            log.warning(
                f"[{download_id}] Hata (deneme {attempt}): {error} "
                f"— {wait:.1f}s sonra tekrar denenecek"
            )

            if on_retry:
                on_retry(attempt, wait, error)

            # İptal edilebilir bekleme (1 saniyelik dilimler)
            waited = 0.0
            while waited < wait:
                if cancel_event.is_set():
                    return {"status": "cancelled"}
                sleep_chunk = min(1.0, wait - waited)
                time.sleep(sleep_chunk)
                waited += sleep_chunk

        return result
