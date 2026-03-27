# -*- coding: utf-8 -*-
"""DownloadManager — indirme motoru yöneticisi."""

import os
import threading
from pathlib import Path

from yt_dlp import YoutubeDL

from ytdownloader.config.constants import DEFAULT_HTTP_HEADERS
from ytdownloader.models.download_item import DownloadItem
from ytdownloader.infrastructure.state_manager import StateManager
from ytdownloader.infrastructure.event_bus import EventBus, Events
from ytdownloader.core.download_engine import DownloadEngine, _is_ssl_error
from ytdownloader.infrastructure.logger import get_logger

log = get_logger("download_manager")


class DownloadManager:

    def __init__(self, settings_service, base_path, auth_service=None):
        self.settings_service = settings_service
        self.base_path = Path(base_path)
        self._auth_service = auth_service

        # Faz 1: yeni altyapı
        self._event_bus    = EventBus()
        self._state_manager = StateManager(self._event_bus)
        max_concurrent = settings_service.load().get("max_concurrent", 0)
        max_workers = max_concurrent if max_concurrent > 0 else 4   # 0 = varsayılan (4)
        self._engine = DownloadEngine(
            state_manager = self._state_manager,
            event_bus     = self._event_bus,
            base_path     = self.base_path,
            max_workers   = max_workers,
            auth_service  = auth_service,
        )

        # Sıralı indirme kuyruğu
        self._sequential_mode  = settings_service.load().get("sequential_mode", False)
        self._seq_queue: list  = []   # (download_id, url, options, prog_cb, done_cb)
        self._seq_active: bool = False
        self._seq_lock         = threading.Lock()

        self.downloads: dict   = {}
        # self.downloads üzerindeki read/write/pop işlemlerini worker thread'lerden
        # korur. Sadece dict erişimlerini kapsar; uzun işlemler lock dışında kalır.
        self._downloads_lock   = threading.Lock()

        self._common_ydl_opts = {
            "quiet":             True,
            "no_warnings":       True,
            "noplaylist":        True,
            "geo_bypass":        True,
            "nocache":           True,
            "extractor_retries": 3,
            "http_headers":      DEFAULT_HTTP_HEADERS,
        }
        self._init_ffmpeg()

    def _init_ffmpeg(self):
        """FFmpeg konumunu tespit edip ydl_opts'a ekler."""
        import sys as _sys
        ffmpeg_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
        appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
        candidates = []
        # PyInstaller EXE
        if hasattr(_sys, "_MEIPASS"):
            candidates.append(Path(_sys._MEIPASS) / "ytdownloader" / "assets" / "ffmpeg")
        candidates += [
            Path(appdata) / "MyYouTubeDownloader" / "ffmpeg",
            self.base_path / "bin",
            self.base_path / "ytdownloader" / "assets" / "ffmpeg",
            self.base_path / "assets" / "ffmpeg",
        ]
        for ffmpeg_dir in candidates:
            if (ffmpeg_dir / ffmpeg_name).exists():
                self._common_ydl_opts["ffmpeg_location"] = str(ffmpeg_dir)
                log.info(f"FFmpeg konumu: {ffmpeg_dir}")
                return
        log.warning("FFmpeg bulunamadı — lokal klasörlerde yok")

    def refresh_ffmpeg(self) -> None:
        """FFmpeg konumunu yeniden tespit eder. Kurulum sonrası çağrılır."""
        self._init_ffmpeg()

    # ── Public API ──────────────────────────────────────────────────────────

    def fetch_video_info(self, url: str, callback) -> None:
        """Video meta bilgisini arka planda çeker."""
        def _fetch():
            try:
                log.info(f"Video bilgisi alınıyor: {url}")
                opts = {**self._common_ydl_opts, "socket_timeout": 15}
                try:
                    with YoutubeDL(opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                except Exception as e:
                    # SSL hatasında bir kez fallback dene; diğer hataları ilet
                    if _is_ssl_error(str(e)):
                        log.warning(f"Fetch SSL hatası, nocheckcertificate ile yeniden deneniyor: {e}")
                        opts["nocheckcertificate"] = True
                        with YoutubeDL(opts) as ydl:
                            info = ydl.extract_info(url, download=False)
                    else:
                        raise
                if "entries" in info:
                    info = info["entries"][0]
                log.info(f"Video bilgisi alındı: {info.get('title', '?')}")
                callback(True, info)
            except Exception as e:
                log.error(f"Video bilgisi alınamadı: {e}")
                callback(False, str(e))

        threading.Thread(target=_fetch, daemon=True).start()

    def set_sequential_mode(self, enabled: bool):
        """Sıralı modu açar/kapatır."""
        self._sequential_mode = enabled

    def reorder_queue(self, ordered_ids: list):
        """Sıralı kuyruktaki bekleyen öğeleri yeniden sıralar."""
        with self._seq_lock:
            # Sadece kuyrukta bekleyenleri yeniden sırala (aktif olan değişmez)
            waiting = [item for item in self._seq_queue]
            reordered = sorted(
                waiting,
                key=lambda x: ordered_ids.index(x[0]) if x[0] in ordered_ids else 999
            )
            self._seq_queue = reordered

    def _seq_next(self):
        """
        Kuyruktaki bir sonraki indirmeyi başlatır.

        Başarısız başlatma (False veya exception) durumunda:
          - İlgili item atlanır, kuyruk bir sonraki item ile devam eder.
          - _seq_active yönetimi while döngüsüyle güvence altına alınmıştır;
            recursion olmadığı için peş peşe başarısız itemlar stack taşması yaratmaz.
        """
        while True:
            with self._seq_lock:
                if not self._seq_queue:
                    self._seq_active = False
                    return
                item = self._seq_queue.pop(0)
                # _seq_active True kalıyor — başlatma girişimi yapılacak.

            download_id, url, options, prog_cb, done_cb = item

            # _dcb default argümanıyla bağlanır; loop closure'ında yanlış
            # done_cb yakalanma riskini önler.
            def _wrapped_done(result, _dcb=done_cb):
                _dcb(result)
                self._seq_next()

            try:
                started = self._start_download(
                    download_id, url, options, prog_cb, _wrapped_done
                )
            except Exception as e:
                log.error(
                    f"[{download_id}] Sequential start beklenmeyen hata: {e}",
                    exc_info=True,
                )
                started = False

            if started:
                # Başarıyla başlatıldı. Tamamlandığında _wrapped_done → _seq_next.
                return

            # Başarısız — bu item atlanıyor, döngü bir sonrakine geçiyor.
            log.warning(
                f"[{download_id}] Sequential start başarısız (zaten var / hata), "
                f"sonraki item'a geçiliyor"
            )

    def download_video(self, download_id: str, url: str, options: dict,
                       progress_callback, complete_callback) -> bool:
        """İndirmeyi başlatır — sıralı modda kuyruğa, normal modda direkt başlar."""
        if download_id in self.downloads:
            return False

        if self._sequential_mode:
            with self._seq_lock:
                self._seq_queue.append(
                    (download_id, url, options, progress_callback, complete_callback)
                )
                # Lock içinde hem kontrol hem işaretle — lock dışı TOCTOU yarışını önler.
                # İki thread aynı anda buraya giremez; yalnızca biri should_start=True alır.
                should_start = not self._seq_active
                if should_start:
                    self._seq_active = True
            if should_start:
                self._seq_next()
            return True

        return self._start_download(download_id, url, options, progress_callback, complete_callback)

    def _start_download(self, download_id: str, url: str, options: dict,
                        progress_callback, complete_callback) -> bool:
        """
        Gerçek indirme başlatıcı.

        Thread güvenliği:
          - self.downloads erişimleri _downloads_lock ile korunur.
          - Başlatma sırasında (register/engine.start) exception atılırsa
            EventBus abonelikleri temizlenir ve downloads kaydı silinir;
            sızıntı olmaz.
        """
        with self._downloads_lock:
            if download_id in self.downloads:
                return False

        # DownloadItem oluştur
        item = DownloadItem(
            id            = download_id,
            url           = url,
            output_dir    = options.get("output_dir", str(Path.home())),
            format        = options.get("format", "mp4"),
            format_id     = options.get("format_id"),
            audio_quality = options.get("audio_quality"),
            speed_limit   = options.get("speed_limit"),
            title         = options.get("title", ""),
            channel       = options.get("channel", ""),
        )

        # ── Callback tanımları ──────────────────────────────────────────────

        def _unsub_all():
            """Tüm abonelikleri tek seferde temizler."""
            self._event_bus.unsubscribe(Events.DOWNLOAD_PROGRESS,  on_progress)
            self._event_bus.unsubscribe(Events.DOWNLOAD_COMPLETED, on_completed)
            self._event_bus.unsubscribe(Events.DOWNLOAD_CANCELLED, on_cancelled)
            self._event_bus.unsubscribe(Events.DOWNLOAD_ERROR,     on_error)

        def on_progress(data: dict):
            if data.get("id") == download_id:
                progress_callback({
                    "status":           "downloading",
                    "percent":          data.get("progress", 0),
                    "speed":            data.get("speed", 0),
                    "eta":              data.get("eta", 0),
                    "downloaded_bytes": data.get("downloaded_bytes", 0),
                    "total_bytes":      data.get("total_bytes", 0),
                })

        def on_completed(data: dict):
            if data.get("id") == download_id:
                _unsub_all()
                with self._downloads_lock:
                    self.downloads.pop(download_id, None)
                final_file = data.get("final_file", "")
                import os as _os
                size_bytes = _os.path.getsize(final_file) if final_file and _os.path.exists(final_file) else 0
                self.settings_service.save_history_entry({
                    "title":      data.get("title", ""),
                    "channel":    data.get("channel", ""),
                    "url":        url,
                    "file":       final_file,
                    "format":     item.format,
                    "size_bytes": size_bytes,
                })
                complete_callback(True, {"status": "completed", "file_path": final_file})

        def on_cancelled(data: dict):
            if data.get("id") == download_id:
                _unsub_all()
                with self._downloads_lock:
                    self.downloads.pop(download_id, None)
                complete_callback(False, "İndirme iptal edildi")

        def on_error(data: dict):
            if data.get("id") == download_id:
                _unsub_all()
                with self._downloads_lock:
                    self.downloads.pop(download_id, None)
                complete_callback(False, data.get("error_message", "Bilinmeyen hata"))

        # ── Abonelik + başlatma ─────────────────────────────────────────────

        self._event_bus.subscribe(Events.DOWNLOAD_PROGRESS,  on_progress)
        self._event_bus.subscribe(Events.DOWNLOAD_COMPLETED, on_completed)
        self._event_bus.subscribe(Events.DOWNLOAD_CANCELLED, on_cancelled)
        self._event_bus.subscribe(Events.DOWNLOAD_ERROR,     on_error)

        try:
            # State machine'e kaydet ve motoru başlat.
            # Bu blok exception atarsa abonelikler ve downloads kaydı temizlenir.
            self._state_manager.register(item)
            with self._downloads_lock:
                self.downloads[download_id] = item
            log.info(f"[{download_id}] Kuyruğa eklendi: {url}")
            self._engine.start(item)
        except Exception:
            _unsub_all()
            with self._downloads_lock:
                self.downloads.pop(download_id, None)
            raise

        return True

    def pause_download(self, download_id: str) -> bool:
        log.info(f"[{download_id}] Pause isteği")
        return bool(self._engine.pause(download_id))

    def resume_download(self, download_id: str) -> bool:
        log.info(f"[{download_id}] Resume isteği")
        return bool(self._engine.resume(download_id))

    def cancel_download(self, download_id: str) -> bool:
        log.info(f"[{download_id}] Cancel isteği")
        return bool(self._engine.cancel(download_id))


