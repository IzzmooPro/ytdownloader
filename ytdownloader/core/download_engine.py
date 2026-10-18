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

import gc
import os
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Optional

from yt_dlp import YoutubeDL

from ytdownloader.config.constants import DEFAULT_HTTP_HEADERS
from ytdownloader.models.download_item import DownloadItem
from ytdownloader.models.download_state import DownloadState, StateError
from ytdownloader.infrastructure.state_manager import StateManager
from ytdownloader.infrastructure.event_bus import EventBus
from ytdownloader.infrastructure.logger import get_logger
from ytdownloader.utils.file_utils import is_ffmpeg_available, find_ffmpeg_dir
from ytdownloader.core.retry_engine import RetryEngine, RetryConfig

log = get_logger("download_engine")


# İptalde kilitli kalan yarım dosyalar için yeniden deneme (toplam ~3 sn)
_PARTIAL_DELETE_ATTEMPTS = 7
_PARTIAL_DELETE_DELAY_S  = 0.5


def _progress_percent(d: dict) -> float:
    """
    yt-dlp progress hook verisinden yüzde hesaplar.

    Parçalı (HLS/DASH, "frag 168/344") indirmelerde toplam boyut tahmini ilk
    anda ~1 KB gelir ve yüzde %100 görünür; kartın ilerleme çubuğu geri
    gitmediği için %100'de takılı kalıyordu. Parça sayısı varsa ona göre
    hesaplanır. İndirme sürerken %100 gösterilmez — %100 yalnızca bitince.
    """
    frag_count = d.get("fragment_count")
    frag_index = d.get("fragment_index")
    if frag_count and frag_index is not None:
        pct = frag_index / frag_count * 100
    else:
        total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
        pct = (d.get("downloaded_bytes") or 0) / total * 100 if total else 0.0
    return max(0.0, min(pct, 99.9))


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

        # FFmpeg konumu — kurulum sonrası refresh_ffmpeg() ile güncellenir
        self._ffmpeg_location: str | None = find_ffmpeg_dir(self._base_path)

    def refresh_ffmpeg(self) -> None:
        """FFmpeg konumunu yeniden tespit eder.
        Açılışta FFmpeg henüz kurulmamış olabilir; kurulum bitince çağrılır."""
        self._ffmpeg_location = find_ffmpeg_dir(self._base_path)

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
        # FSM: PENDING → QUEUED. ACTIVE geçişi worker başladığında yapılır —
        # executor kuyruğunda bekleyenler QUEUED kalır, UI yanıltıcı "indiriliyor" göstermez.
        self._sm.transition(item.id, DownloadState.QUEUED)
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

        # FFmpeg dönüştürme/birleştirme sırasında progress hook çağrılmaz;
        # duraklatma isteği hiçbir zaman karşılanmaz ve kart takılı kalırdı.
        item = self._sm.get_item(download_id)
        if item is not None and item.post_processing:
            log.info(f"[{download_id}] pause reddedildi: dönüştürme sürüyor")
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

        # .part dosyaları worker yt-dlp'den çıktıktan sonra _handle_result'ta
        # silinir — burada silmek açık dosyayla yarışır (Windows'ta başarısız olur).

        try:
            self._sm.transition(download_id, DownloadState.CANCELLED)
        except (StateError, KeyError) as e:
            # KeyError: indirme bu arada tamamlanıp kayıttan silinmiş olabilir
            log.warning(f"[{download_id}] cancel geçiş hatası: {e}")

        log.info(f"[{download_id}] İptal edildi")
        return True

    def cleanup(self, download_id: str) -> None:
        """İndirme tamamlandıktan sonra event'leri temizler."""
        with self._lock:
            self._pause_events.pop(download_id, None)
            self._cancel_events.pop(download_id, None)

    def shutdown(self) -> None:
        """
        Tüm worker thread'leri durdurur.

        Duraklatılmış indirmeler pause_ev.wait()'te bloklu bekler; ThreadPoolExecutor
        thread'leri daemon olmadığı için önce cancel+pause event'leri set edilerek
        uyandırılmalı — aksi halde uygulama çıkışta sonsuza kadar takılır.
        """
        self._shutting_down = True
        with self._lock:
            for ev in self._cancel_events.values():
                ev.set()
            for ev in self._pause_events.values():
                ev.set()
        self._executor.shutdown(wait=False, cancel_futures=True)

    # ── Worker (arka plan thread) ─────────────────────────────────────────────

    def _worker(self, item: DownloadItem,
                pause_ev: threading.Event,
                cancel_ev: threading.Event) -> None:
        """Her indirme için ayrı thread'de çalışır."""
        try:
            # QUEUED → ACTIVE: worker gerçekten başladı.
            # Kuyruktayken pause istendiyse durum PAUSING'dir — dokunma,
            # progress hook ilk çağrıda bloklanıp PAUSED'a geçirecek.
            if self._sm.get_state(item.id) == DownloadState.QUEUED:
                try:
                    self._sm.transition(item.id, DownloadState.ACTIVE)
                except StateError:
                    pass
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
            # Worker bitti — kayıt artık gerekmiyor; StateManager'da birikmesin.
            self._sm.unregister(item.id)

    def _perform_download(self, item: DownloadItem,
                          pause_ev: threading.Event,
                          cancel_ev: threading.Event) -> dict:

        if cancel_ev.is_set():
            return {"status": "cancelled"}

        item.post_processing = False
        opts = self._build_ydl_opts(item, pause_ev, cancel_ev)
        if opts is None:
            return {"status": "error", "error": "FFmpeg gerekli ama bulunamadı"}

        return self._run_ydl(item, opts, cancel_ev)

    def _run_ydl(self, item: DownloadItem, opts: dict,
                 cancel_ev: threading.Event) -> dict:
        """Tek bir yt-dlp oturumu çalıştırır. _perform_download tarafından çağrılır."""
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
                if final_path is None:
                    return {
                        "status": "error",
                        "error":  f"İndirme tamamlandı ama çıktı dosyası bulunamadı: {filename}",
                    }
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

        # Duraklatma isteği indirme bittikten sonra geldiyse (ör. dönüştürme
        # başlamadan hemen önce) durum PAUSING/PAUSED kalır; COMPLETED geçişi
        # buradan geçersiz olduğu için kart sonsuza kadar takılırdı.
        if status == "completed" and self._sm.get_state(item.id) in (
                DownloadState.PAUSING, DownloadState.PAUSED):
            try:
                self._sm.transition(item.id, DownloadState.ACTIVE)
            except StateError:
                pass

        if status == "completed":
            self._sm.set_final_file(item.id, result.get("file_path", ""))
            try:
                self._sm.transition(item.id, DownloadState.COMPLETED)
            except StateError:
                pass
            log.info(f"[{item.id}] ✓ Tamamlandı: {result.get('file_path')}")

        elif status == "cancelled":
            # Kapanışta iptal edilenlerin parçaları korunur (kuyruk geri
            # yüklenince kaldığı yerden devam eder); kullanıcı iptalinde silinir.
            if not getattr(self, "_shutting_down", False):
                self._remove_partials(item)
            try:
                self._sm.transition(item.id, DownloadState.CANCELLED)
            except StateError:
                pass

        else:
            error = result.get("error", "Bilinmeyen hata")
            self._sm.set_error(item.id, error)

    def _remove_partials(self, item: DownloadItem) -> None:
        """
        İptal edilen indirmenin yarım dosyalarını siler.
        MP4'te yt-dlp görüntü ve sesi ayrı parçalara yazar
        ("Başlık [id].f137.mp4.part", "Başlık [id].f140.m4a.part");
        planlanan dosya adının kökü ile başlayan tüm .part/.ytdl dosyaları temizlenir.
        """
        if not item.partial_file:
            return
        planned = Path(item.partial_file.removesuffix(".part"))
        prefix  = planned.stem + "."
        try:
            candidates = list(planned.parent.iterdir())
        except OSError:
            return
        targets = [
            f for f in candidates
            if f.name.startswith(prefix)
            and (f.name.endswith(".part") or f.name.endswith(".ytdl") or ".part-Frag" in f.name)
        ]
        # Parçalı (frag) indirmelerde yt-dlp iptal sonrası ana .part dosyasını
        # hemen kapatmaz; dosya nesnesi çöp toplanana kadar açık kalır ve
        # Windows silmeye izin vermez (WinError 32). gc + kısa bekleme ile
        # birkaç kez yeniden denenir — worker thread'deyiz, UI etkilenmez.
        for attempt in range(_PARTIAL_DELETE_ATTEMPTS):
            remaining = []
            for f in targets:
                try:
                    f.unlink()
                    log.debug(f"[{item.id}] Yarım dosya silindi: {f.name}")
                except FileNotFoundError:
                    pass
                except OSError as e:
                    remaining.append((f, e))
            if not remaining:
                return
            targets = [f for f, _ in remaining]
            if attempt < _PARTIAL_DELETE_ATTEMPTS - 1:
                gc.collect()
                time.sleep(_PARTIAL_DELETE_DELAY_S)
        for f, e in remaining:
            log.warning(f"[{item.id}] Yarım dosya silinemedi ({f.name}): {e}")

    def _make_postprocessor_hook(self, item: DownloadItem) -> Callable:
        """FFmpeg aşaması başlayınca işaretler — bu aşamada pause reddedilir."""
        def hook(d: dict) -> None:
            if d.get("status") == "started":
                item.post_processing = True
        return hook

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
                pct   = _progress_percent(d)
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
                        item._last_log_pct = (int(pct) // 25) * 25  # type: ignore[attr-defined]

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
            "geo_bypass":            True,
            "nocache":               True,
            "extractor_retries":     3,
            "http_headers":          DEFAULT_HTTP_HEADERS,
            "continuedl":            True,   # kaldığı yerden devam
            "progress_hooks":        [self._make_progress_hook(item.id, pause_ev, cancel_ev)],
            "postprocessor_hooks":   [self._make_postprocessor_hook(item)],
            # [%(id)s] eki: aynı başlıklı farklı videoların birbirinin .part
            # dosyasına devam etmesini / üzerine yazmasını önler.
            "outtmpl":               str(Path(item.output_dir) / "%(title)s [%(id)s].%(ext)s"),
            "windowsfilenames":      True,   # Windows'ta yasak karakterleri güvenli temizle
            # Format testi (_check_formats) geçici dosyayı paths["temp"] yoksa
            # çalışma dizinine yazar — kurulu programda Program Files → Errno 13
            "paths":                 {"temp": tempfile.gettempdir()},
            # YouTube https formatları tek bağlantıyla iner; "dashy" onları
            # parçalara böler, parçalar paralel iner (ölçüm: ~12 → ~15 MB/s).
            "extractor_args":        {"youtube": {"formats": ["dashy"]}},
            "concurrent_fragment_downloads": 8,
        }

        # Cookie auth (tarayıcıdan veya cookie dosyasından)
        if self._auth:
            opts.update(self._auth.get_ydl_cookie_opts())

        # FFmpeg konumu — init'te bulunamadıysa (ör. sonradan kurulduysa) tekrar ara
        if ffmpeg_ok and not self._ffmpeg_location:
            self.refresh_ffmpeg()
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



    def _organize(self, info: dict, filename: str, item: DownloadItem) -> str | None:
        """
        Tamamlanan dosyanın gerçek yolunu döner, uzantı değişimini handle eder.
        Dosya hiçbir bilinen uzantıyla bulunamazsa None döner — çağıran hata akışına düşürür.
        """
        if os.path.exists(filename):
            return filename
        for ext in ("mp4", "webm", "mkv", "mp3", "m4a", "opus", "aac", "ogg", "flac"):
            candidate = Path(filename).with_suffix(f".{ext}")
            if candidate.exists():
                return str(candidate)
        log.warning(f"[{item.id}] Çıktı dosyası bulunamadı: {filename}")
        return None
