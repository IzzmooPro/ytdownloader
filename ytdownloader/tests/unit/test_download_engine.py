# -*- coding: utf-8 -*-
"""
DownloadEngine — _organize() ve final path doğrulaması testleri.
Gerçek dosya sistemi kullanılır (tmp_path); yt-dlp/ağ çağrısı yok.
"""

import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# Fixture
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def engine():
    """
    DownloadEngine örneği — __init__ atlanarak minimal state kurulur.
    Thread pool, StateManager, EventBus yok; sadece _organize / _run_ydl testi.
    """
    from ytdownloader.core.download_engine import DownloadEngine
    e = DownloadEngine.__new__(DownloadEngine)
    e._sm  = MagicMock()
    e._bus = MagicMock()
    return e


@pytest.fixture
def item():
    from ytdownloader.models.download_item import DownloadItem
    return DownloadItem(id="test_id", url="http://example.com")


# ─────────────────────────────────────────────────────────────────────────────
# _organize() — path çözümleme
# ─────────────────────────────────────────────────────────────────────────────

class TestOrganize:

    def test_exact_path_exists(self, engine, item, tmp_path):
        """Dosya tam adıyla varsa aynı path dönmeli."""
        f = tmp_path / "video.mp4"
        f.touch()
        result = engine._organize({}, str(f), item)
        assert result == str(f)

    def test_alt_extension_webm(self, engine, item, tmp_path):
        """mp4 yok ama webm var → webm path dönmeli."""
        base = tmp_path / "video.mp4"     # bu dosya YOK
        webm = tmp_path / "video.webm"
        webm.touch()
        result = engine._organize({}, str(base), item)
        assert result == str(webm)

    def test_alt_extension_mp3(self, engine, item, tmp_path):
        """mp4 yok ama mp3 var → mp3 path dönmeli."""
        base = tmp_path / "audio.mp4"
        mp3  = tmp_path / "audio.mp3"
        mp3.touch()
        result = engine._organize({}, str(base), item)
        assert result == str(mp3)

    def test_alt_extension_m4a(self, engine, item, tmp_path):
        base = tmp_path / "audio.mp4"
        m4a  = tmp_path / "audio.m4a"
        m4a.touch()
        result = engine._organize({}, str(base), item)
        assert result == str(m4a)

    def test_alt_extension_mkv(self, engine, item, tmp_path):
        base = tmp_path / "video.mp4"
        mkv  = tmp_path / "video.mkv"
        mkv.touch()
        result = engine._organize({}, str(base), item)
        assert result == str(mkv)

    def test_no_file_found_returns_none(self, engine, item, tmp_path):
        """Hiçbir uzantıyla dosya bulunamazsa None dönmeli."""
        base = tmp_path / "ghost.mp4"   # hiçbir uzantı yok
        result = engine._organize({}, str(base), item)
        assert result is None

    def test_none_not_original_path(self, engine, item, tmp_path):
        """None dönerken orijinal (var olmayan) path dönülmemeli."""
        base = tmp_path / "missing.mp4"
        result = engine._organize({}, str(base), item)
        assert result != str(base)


# ─────────────────────────────────────────────────────────────────────────────
# _run_ydl() — None path hata akışına düşürmeli
# ─────────────────────────────────────────────────────────────────────────────

class TestRunYdlPathValidation:

    def test_none_from_organize_produces_error_status(self, engine, item, tmp_path):
        """
        _organize() None döndüğünde _run_ydl {"status": "error"} üretmeli.
        Dosya yokken "completed" denmemeli.
        """
        item.format = "mp4"
        engine._base_path = tmp_path
        engine._auth = None
        engine._ffmpeg_location = None
        cancel_ev = threading.Event()

        with patch.object(engine, "_organize", return_value=None), \
             patch("ytdownloader.core.download_engine.is_ffmpeg_available",
                   return_value=False), \
             patch("ytdownloader.core.download_engine.YoutubeDL") as mock_ydl_cls:

            ydl = MagicMock()
            ydl.__enter__ = MagicMock(return_value=ydl)
            ydl.__exit__ = MagicMock(return_value=False)
            ydl.extract_info.return_value = {"title": "t", "ext": "mp4"}
            ydl.prepare_filename.return_value = str(tmp_path / "t.mp4")
            ydl.download.return_value = None
            mock_ydl_cls.return_value = ydl

            opts = {
                "quiet":          True,
                "outtmpl":        str(tmp_path / "%(title)s.%(ext)s"),
                "progress_hooks": [],
            }
            result = engine._run_ydl(item, opts, cancel_ev)

        assert result["status"] == "error"
        assert "bulunamadı" in result.get("error", "")

    def test_valid_path_from_organize_produces_completed(self, engine, item, tmp_path):
        """
        _organize() geçerli path döndüğünde completed status gelmeli.
        """
        real_file = tmp_path / "t.mp4"
        real_file.touch()
        item.format = "mp4"
        engine._base_path = tmp_path
        engine._auth = None
        engine._ffmpeg_location = None
        cancel_ev = threading.Event()

        with patch.object(engine, "_organize", return_value=str(real_file)), \
             patch("ytdownloader.core.download_engine.is_ffmpeg_available",
                   return_value=False), \
             patch("ytdownloader.core.download_engine.YoutubeDL") as mock_ydl_cls:

            ydl = MagicMock()
            ydl.__enter__ = MagicMock(return_value=ydl)
            ydl.__exit__ = MagicMock(return_value=False)
            ydl.extract_info.return_value = {"title": "t", "ext": "mp4"}
            ydl.prepare_filename.return_value = str(real_file)
            ydl.download.return_value = None
            mock_ydl_cls.return_value = ydl

            opts = {
                "quiet":          True,
                "outtmpl":        str(tmp_path / "%(title)s.%(ext)s"),
                "progress_hooks": [],
            }
            result = engine._run_ydl(item, opts, cancel_ev)

        assert result["status"] == "completed"
        assert result["file_path"] == str(real_file)


# ─────────────────────────────────────────────────────────────────────────────
# FFmpeg konumu — açılıştan sonra kurulan FFmpeg motor tarafından görülmeli
# ─────────────────────────────────────────────────────────────────────────────

class TestFfmpegRefresh:

    def test_location_picked_up_after_late_install(self, engine, item, tmp_path, monkeypatch):
        monkeypatch.setenv("APPDATA", str(tmp_path))
        engine._base_path = tmp_path
        engine._auth = None
        engine._ffmpeg_location = None   # açılışta FFmpeg yoktu

        # FFmpeg sonradan kuruldu
        import os
        ffdir = tmp_path / "MyYouTubeDownloader" / "ffmpeg"
        ffdir.mkdir(parents=True)
        (ffdir / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")).touch()

        item.format = "mp3"
        opts = engine._build_ydl_opts(item, threading.Event(), threading.Event())
        assert opts is not None
        assert opts["ffmpeg_location"] == str(ffdir)

    def test_refresh_ffmpeg_updates_location(self, engine, tmp_path, monkeypatch):
        import os
        monkeypatch.setenv("APPDATA", str(tmp_path))
        engine._base_path = tmp_path
        engine._ffmpeg_location = None
        ffdir = tmp_path / "MyYouTubeDownloader" / "ffmpeg"
        ffdir.mkdir(parents=True)
        (ffdir / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")).touch()
        engine.refresh_ffmpeg()
        assert engine._ffmpeg_location == str(ffdir)


# ─────────────────────────────────────────────────────────────────────────────
# Duraklatma — FFmpeg aşaması ve geç gelen pause isteği
# ─────────────────────────────────────────────────────────────────────────────

class TestPauseDuringPostProcessing:

    @pytest.fixture
    def real(self):
        from ytdownloader.infrastructure.event_bus import EventBus, Events
        from ytdownloader.infrastructure.state_manager import StateManager
        from ytdownloader.core.download_engine import DownloadEngine
        from ytdownloader.models.download_item import DownloadItem
        from ytdownloader.models.download_state import DownloadState
        bus = EventBus()
        sm = StateManager(bus)
        completed = []
        bus.subscribe(Events.DOWNLOAD_COMPLETED, completed.append)
        eng = DownloadEngine(sm, bus, Path("."), max_workers=1)
        it = DownloadItem(id="p1", url="u")
        sm.register(it)
        ev = threading.Event()
        ev.set()
        eng._pause_events["p1"] = ev
        sm.transition("p1", DownloadState.QUEUED)
        sm.transition("p1", DownloadState.ACTIVE)
        yield eng, sm, it, completed
        eng.shutdown()

    def test_pause_rejected_while_post_processing(self, real):
        from ytdownloader.models.download_state import DownloadState
        eng, sm, it, _ = real
        eng._make_postprocessor_hook(it)({"status": "started"})
        assert eng.pause("p1") is False
        assert sm.get_state("p1") == DownloadState.ACTIVE

    def test_late_pause_does_not_block_completion(self, real):
        from ytdownloader.models.download_state import DownloadState
        eng, sm, it, completed = real
        assert eng.pause("p1") is True                      # PAUSING
        eng._handle_result(it, {"status": "completed", "file_path": "x.mp3"})
        assert sm.get_state("p1") == DownloadState.COMPLETED
        assert completed, "DOWNLOAD_COMPLETED yayınlanmalı — kart takılı kalmamalı"


# ─────────────────────────────────────────────────────────────────────────────
# İptalde yarım dosya temizliği
# ─────────────────────────────────────────────────────────────────────────────

class TestRemovePartials:

    def _setup(self, engine, item, tmp_path):
        planned = tmp_path / "Şarkı [abc123].mp4"
        item.partial_file = str(planned) + ".part"
        for n in ("Şarkı [abc123].f137.mp4.part", "Şarkı [abc123].f140.m4a.part",
                  "Şarkı [abc123].f137.mp4.ytdl", "Şarkı [abc123].mp4.part-Frag3"):
            (tmp_path / n).write_text("x")
        keep = ["Şarkı [abc123].mp3",              # başka formatta tamamlanmış dosya
                "Şarkı [zzz999].f137.mp4.part",    # başka videonun parçası
                "Başka.mp4"]
        for n in keep:
            (tmp_path / n).write_text("x")
        return keep

    def test_user_cancel_removes_all_partials(self, engine, item, tmp_path):
        keep = self._setup(engine, item, tmp_path)
        engine._handle_result(item, {"status": "cancelled"})
        assert sorted(p.name for p in tmp_path.iterdir()) == sorted(keep)

    def test_shutdown_keeps_partials_for_resume(self, engine, item, tmp_path):
        self._setup(engine, item, tmp_path)
        engine._shutting_down = True
        engine._handle_result(item, {"status": "cancelled"})
        assert (tmp_path / "Şarkı [abc123].f137.mp4.part").exists()
