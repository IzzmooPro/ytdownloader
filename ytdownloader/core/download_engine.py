# -*- coding: utf-8 -*-
"""
DownloadEngine — gerçek pause/resume destekli indirme motoru.

Faz 1'deki kritik fark:
  - Eski: pause = cancel + restart (veri kaybı, baştan indirir)
  - Yeni: pause = progress_hook'ta threading.Event.wait() ile thread bloklanır
           .part dosyası diskte kalır, resume = kaldığı yerden devam

Thread güvenliği:
  - Her indirme için ayrı _pause_event ve _cancel_event
  - progress_hook worker thread'de çalışır — UI'ya dokunmaz
  - StateManager üzerinden tüm durum değişiklikleri yapılır
  - EventBus üzerinden UI haberdar edilir
"""

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Optional

from yt_dlp import YoutubeDL

from ytdownloader.config.constants import DEFAULT_HTTP_HEADERS
from ytdownloader.models.download_item import DownloadItem
from ytdownloader.models.download_state import DownloadState, StateError
from ytdownloader.infrastructure.state_manager import StateManager
from ytdownloader.infrastructure.event_bus import EventBus, Events
from ytdownloader.infrastructure.logger import get_logger
from ytdownloader.utils.file_utils import is_ffmpeg_available
from ytdownloader.core.retry_engine import RetryEngine, RetryConfig

log = get_logger("download_engine")


class _DownloadCancelledError(Exception):
    """Progress hook'tan indirmeyi durdurmak için kullanılır."""
    pass


class DownloadEngine:

    def __init__(self,
                 state_manager: StateManager,
                 event_bus: EventBus,
                 base_path: Path,
                 max_workers: int = 3,
                 auth_service=None):

        self._sm          = state_manager
        self._bus         = event_bus
        self._base_path   = base_path
        self._auth        = auth_service
        self._executor    = ThreadPoolExecutor(max_workers=max_workers,
                                               thread_name_prefix="dl_worker")

        # Her download_id için kontrol event'leri
        # _pause_events[id].set()   → devam et
        # _pause_events[id].clear() → blokla (pause)
        self._pause_events:  dict[str, threading.Event] = {}
        self._cancel_events: dict[str, threading.Event] = {}
        self._lock = threading.Lock()
        self._retry_engine = RetryEngine(RetryConfig(
            max_attempts = 5,
            base_delay   = 2.0,
            max_delay    = 32.0,
            jitter       = 1.0,
        ))

        # FFmpeg konumunu bir kez belirle — _build_ydl_opts tekrar aramaz
        self._ffmpeg_location: str | None = self._detect_ffmpeg()

    def _detect_ffmpeg(self) -> str | None:
        """FFmpeg klasörünü bir kez tespit eder. Sonuç önbelleğe alınır."""
        import sys as _sys
        ffmpeg_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
        candidates = []
        if hasattr(_sys, "_MEIPASS"):
            candidates.append(Path(_sys._MEIPASS) / "ytdownloader" / "assets" / "ffmpeg")
        candidates += [
            self._base_path / "bin",
            self._base_path / "ytdownloader" / "assets" / "ffmpeg",
            self._base_path / "assets" / "ffmpeg",
        ]
        for d in candidates:
            if (d / ffmpeg_name).exists():
                return str(d)
        return None

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self, item: DownloadItem) -> None:
        """İndirmeyi başlatır (kuyruğa alır)."""
        with self._lock:
            pause_ev  = threading.Event()
            pause_ev.set()                      # başlangıçta "devam et"
            cancel_ev = threading.Event()
            self._pause_events[item.id]  = pause_ev
            self._cancel_events[item.id] = cancel_ev

        log.info(f"[{item.id}] İndirme başlatıldı: {item.url}")
        # FSM: PENDING → QUEUED → ACTIVE
        self._sm.transition(item.id, DownloadState.QUEUED)
        self._sm.transition(item.id, DownloadState.ACTIVE)
        self._executor.submit(self._worker, item, pause_ev, cancel_ev)

    def pause(self, download_id: str) -> bool:
        """
        İndirmeyi gerçekten durdurur.
        .part dosyası diskte kalır — resume kaldığı yerden devam eder.
        """
        with self._lock:
            pause_ev = self._pause_events.get(download_id)

        if pause_ev is None:
            log.warning(f"[{download_id}] pause: aktif indirme bulunamadı")
            return False

        try:
            self._sm.transition(download_id, DownloadState.PAUSING)
        except StateError as e:
            log.warning(f"[{download_id}] pause geçiş hatası: {e}")
            return False

        pause_ev.clear()    # progress_hook burada bloklanacak
        log.info(f"[{download_id}] Durduruldu (pause)")
        return True

    def resume(self, download_id: str) -> bool:
        """Duraklatılmış indirmeyi kaldığı yerden devam ettirir."""
        state = self._sm.get_state(download_id)
        if state not in (DownloadState.PAUSED, DownloadState.PAUSING):
            log.warning(f"[{download_id}] resume: durum {state}, devam edilemiyor")
            return False

        with self._lock:
            pause_ev = self._pause_events.get(download_id)

        if pause_ev is None:
            log.warning(f"[{download_id}] resume: pause_event bulunamadı")
            return False

        try:
            self._sm.transition(download_id, DownloadState.ACTIVE)
        except StateError as e:
            log.warning(f"[{download_id}] resume geçiş hatası: {e}")
            return False

        pause_ev.set()      # progress_hook'u serbest bırak
        log.info(f"[{download_id}] Devam ettiriliyor (resume)")
        return True

    def cancel(self, download_id: str) -> bool:
        """İndirmeyi iptal eder ve .part dosyasını siler."""
        with self._lock:
            cancel_ev = self._cancel_events.get(download_id)
            pause_ev  = self._pause_events.get(download_id)

        if cancel_ev:
            cancel_ev.set()         # worker döngüsünü kırar

        if pause_ev:
            pause_ev.set()          # eğer pause'daysa önce blokajı kaldır

        # .part dosyasını sil
        item = self._sm.get_item(download_id)
        if item and item.partial_file and os.path.exists(item.partial_file):
            try:
                os.remove(item.partial_file)
                log.debug(f"[{download_id}] .part dosyası silindi")
            except Exception as e:
                log.warning(f"[{download_id}] .part silinemedi: {e}")

        try:
            self._sm.transition(download_id, DownloadState.CANCELLED)
        except StateError as e:
            log.warning(f"[{download_id}] cancel geçiş hatası: {e}")

        log.info(f"[{download_id}] İptal edildi")
        return True

    def cleanup(self, download_id: str) -> None:
        """İndirme tamamlandıktan sonra event'leri temizler."""
        with self._lock:
            self._pause_events.pop(download_id, None)
            self._cancel_events.pop(download_id, None)

    def shutdown(self) -> None:
        """Tüm worker thread'leri durdurur."""
        self._executor.shutdown(wait=False, cancel_futures=True)

    # ── Worker (arka plan thread) ─────────────────────────────────────────────

    def _worker(self, item: DownloadItem,
                pause_ev: threading.Event,
                cancel_ev: threading.Event) -> None:
        """Her indirme için ayrı thread'de çalışır."""
        try:
            def on_retry(attempt_no: int, wait: float, error: str):
                # Retry öncesi: ACTIVE → RETRYING
                log.warning(f"[{item.id}] Retry {attempt_no}: {wait:.1f}s bekleniyor")
                try:
                    self._sm.transition(item.id, DownloadState.RETRYING)
                except Exception:
                    pass

            def attempt_with_reactivate():
                # Her retry başında RETRYING → ACTIVE
                state = self._sm.get_state(item.id)
                if state == DownloadState.RETRYING:
                    try:
                        self._sm.transition(item.id, DownloadState.ACTIVE)
                    except Exception:
                        pass
                return self._perform_download(item, pause_ev, cancel_ev)

            result = self._retry_engine.run(
                fn           = attempt_with_reactivate,
                download_id  = item.id,
                cancel_event = cancel_ev,
                on_retry     = on_retry,
            )

            # Retry sonrası ACTIVE'e dön (RETRYING → ACTIVE)
            if result.get("status") not in ("completed", "cancelled"):
                pass  # set_error zaten ERROR'a geçirir

            self._handle_result(item, result)
        except Exception as e:
            log.error(f"[{item.id}] Worker beklenmeyen hata: {e}", exc_info=True)
            self._sm.set_error(item.id, str(e))
        finally:
            self.cleanup(item.id)

    def _perform_download(self, item: DownloadItem,
                          pause_ev: threading.Event,
                          cancel_ev: threading.Event) -> dict:

        if cancel_ev.is_set():
            return {"status": "cancelled"}

        opts = self._build_ydl_opts(item, pause_ev, cancel_ev)
        if opts is None:
            return {"status": "error", "error": "FFmpeg gerekli ama bulunamadı"}

        try:
            with YoutubeDL(opts) as ydl:
                log.debug(f"[{item.id}] yt-dlp başlatıldı")
                info = ydl.extract_info(item.url, download=False)
                filename = ydl.prepare_filename(info)

                # .part yolunu state'e kaydet
                item.partial_file = filename + ".part"

                ydl.download([item.url])

                # Birleştirme varsa MERGING durumuna geç
                if item.format == "mp4" and is_ffmpeg_available(self._base_path):
                    try:
                        self._sm.transition(item.id, DownloadState.MERGING)
                    except StateError:
                        pass    # zaten completed olabilir

                final_path = self._organize(info, filename, item)
                return {"status": "completed", "file_path": final_path, "info": info}

        except _DownloadCancelledError:
            return {"status": "cancelled"}
        except Exception as e:
            if cancel_ev.is_set():
                return {"status": "cancelled"}
            log.error(f"[{item.id}] İndirme hatası: {e}")
            return {"status": "error", "error": str(e)}

    def _handle_result(self, item: DownloadItem, result: dict) -> None:
        status = result.get("status")

        if status == "completed":
            self._sm.set_final_file(item.id, result.get("file_path", ""))
            try:
                self._sm.transition(item.id, DownloadState.COMPLETED)
            except StateError:
                pass
            log.info(f"[{item.id}] ✓ Tamamlandı: {result.get('file_path')}")

        elif status == "cancelled":
            try:
                self._sm.transition(item.id, DownloadState.CANCELLED)
            except StateError:
                pass

        else:
            error = result.get("error", "Bilinmeyen hata")
            self._sm.set_error(item.id, error)

    # ── Progress Hook ─────────────────────────────────────────────────────────

    def _make_progress_hook(self, download_id: str,
                            pause_ev: threading.Event,
                            cancel_ev: threading.Event) -> Callable:
        """
        Closure olarak progress hook döner.
        Bu hook yt-dlp'nin worker thread'inde çağrılır.

        PAUSE MEKANİZMASI:
          pause_ev.clear() → hook burada bloklanır, thread uyur
          pause_ev.set()   → hook devam eder, indirme kaldığı yerden sürer
          .part dosyası diskte olduğu için veri kaybı olmaz
        """
        def hook(d: dict) -> None:
            # ── Cancel kontrolü ──────────────────────────────────────────
            if cancel_ev.is_set():
                raise _DownloadCancelledError()

            # ── Pause kontrolü (gerçek pause) ────────────────────────────
            if not pause_ev.is_set():
                log.debug(f"[{download_id}] Thread duraklatıldı")
                # PAUSING → PAUSED geçişi
                try:
                    self._sm.transition(download_id, DownloadState.PAUSED)
                except StateError:
                    pass

                # Burası bloklanır — pause_ev.set() çağrılana kadar uyur
                pause_ev.wait()

                # Uyandıktan sonra cancel kontrolü
                if cancel_ev.is_set():
                    raise _DownloadCancelledError()

                log.debug(f"[{download_id}] Thread devam etti")

            # ── Progress güncelleme ───────────────────────────────────────
            if d.get("status") == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
                pct   = d.get("downloaded_bytes", 0) / total * 100 if total else 0
                speed = d.get("speed", 0) or 0
                eta   = d.get("eta")

                self._sm.update_progress(
                    download_id,
                    progress         = pct,
                    speed            = speed,
                    eta              = eta,
                    downloaded_bytes = d.get("downloaded_bytes", 0),
                    total_bytes      = total,
                )

                # Konsol logu (her %25'te bir)
                item = self._sm.get_item(download_id)
                if item:
                    last_log = getattr(item, "_last_log_pct", -1)
                    if pct >= last_log + 25:
                        speed_str = f"{speed/1024/1024:.1f} MB/s" if speed else "?"
                        log.info(f"[{download_id}] %{pct:.0f} — {speed_str}")
                        item._last_log_pct = (int(pct) // 25) * 25

            elif d.get("status") == "finished":
                self._sm.update_progress(download_id, progress=100)
                log.debug(f"[{download_id}] İndirme bitti, işleniyor...")

        return hook

    # ── YDL Options ───────────────────────────────────────────────────────────

    def _build_ydl_opts(self, item: DownloadItem,
                        pause_ev: threading.Event,
                        cancel_ev: threading.Event) -> Optional[dict]:
        ffmpeg_ok = is_ffmpeg_available(self._base_path)

        opts: dict = {
            "quiet":                 True,
            "no_warnings":           True,
            "noplaylist":            True,
            "nocheckcertificate":    True,
            "geo_bypass":            True,
            "nocache":               True,
            "extractor_retries":     3,
            "http_headers":          DEFAULT_HTTP_HEADERS,
            "continuedl":            True,   # kaldığı yerden devam
            "progress_hooks":        [self._make_progress_hook(item.id, pause_ev, cancel_ev)],
            "outtmpl":               str(Path(item.output_dir) / "%(title)s.%(ext)s"),
        }

        # Cookie auth (tarayıcıdan veya cookie dosyasından)
        if self._auth:
            opts.update(self._auth.get_ydl_cookie_opts())

        # FFmpeg konumu — init'te bir kez tespit edildi
        if self._ffmpeg_location:
            opts["ffmpeg_location"] = self._ffmpeg_location

        # Hız limiti
        if item.speed_limit:
            opts["ratelimit"] = item.speed_limit

        if item.format == "mp3":
            if not ffmpeg_ok:
                return None
            # audio_quality: "128", "192", "320" — options'tan gelir
            quality = str(getattr(item, "audio_quality", None) or "192")
            opts.update({
                "format": "bestaudio/best",
                "writethumbnail": True,         # thumbnail indir (kapak resmi için)
                "postprocessors": [
                    {
                        "key":              "FFmpegExtractAudio",
                        "preferredcodec":   "mp3",
                        "preferredquality": quality,
                    },
                    {
                        "key": "FFmpegMetadata",   # ID3 tag: başlık, sanatçı, albüm
                        "add_metadata": True,
                    },
                    {
                        "key": "EmbedThumbnail",   # Kapak resmi gömme
                    },
                ],
            })
        else:
            if ffmpeg_ok and item.format_id:
                opts["format"] = f"{item.format_id}+bestaudio[ext=m4a]/best[ext=mp4]/best"
                opts["merge_output_format"] = "mp4"
            else:
                opts["format"] = "best[ext=mp4]/best"

        return opts

    # ── Yardımcılar ───────────────────────────────────────────────────────────



    def _organize(self, info: dict, filename: str, item: DownloadItem) -> str:
        """Tamamlanan dosyanın gerçek yolunu döner, uzantı değişimini handle eder."""
        if not os.path.exists(filename):
            for ext in ("mp4", "webm", "mkv", "mp3", "m4a"):
                candidate = Path(filename).with_suffix(f".{ext}")
                if candidate.exists():
                    filename = str(candidate)
                    break
        return filename
