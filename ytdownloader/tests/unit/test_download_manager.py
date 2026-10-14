# -*- coding: utf-8 -*-
"""
DownloadManager testleri:
  - Sequential queue fail-safe (_seq_next)
  - EventBus subscription cleanup (_start_download exception)
  - downloads dict lock (duplicate ID, thread safety temeli)
"""

import threading
from unittest.mock import MagicMock, patch

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# Fixture
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def dm():
    """
    DownloadManager örneği — DownloadEngine, StateManager, EventBus mock'lanmış.
    Gerçek threading veya ağ çağrısı yapmaz.
    """
    with patch("ytdownloader.core.download_manager.DownloadEngine"), \
         patch("ytdownloader.core.download_manager.StateManager"), \
         patch("ytdownloader.core.download_manager.EventBus"):
        from ytdownloader.core.download_manager import DownloadManager
        svc = MagicMock()
        svc.load.return_value = {"max_concurrent": 2, "sequential_mode": True}
        mgr = DownloadManager(svc, ".")
        mgr._sequential_mode = True
        return mgr


# ─────────────────────────────────────────────────────────────────────────────
# Sequential queue fail-safe
# ─────────────────────────────────────────────────────────────────────────────

class TestSeqNextFailSafe:

    def test_all_fail_releases_seq_active(self, dm):
        """Tüm itemlar başarısız → _seq_active False olmalı (kilitlenme yok)."""
        dm._start_download = MagicMock(return_value=False)
        dm._seq_queue = [
            ("id1", "url1", {}, MagicMock(), MagicMock()),
            ("id2", "url2", {}, MagicMock(), MagicMock()),
        ]
        dm._seq_active = True
        dm._seq_next()
        assert dm._seq_active is False

    def test_all_fail_empties_queue(self, dm):
        """Tüm itemlar başarısız → kuyruk tamamen boşalmalı."""
        dm._start_download = MagicMock(return_value=False)
        dm._seq_queue = [
            ("id1", "url1", {}, MagicMock(), MagicMock()),
            ("id2", "url2", {}, MagicMock(), MagicMock()),
            ("id3", "url3", {}, MagicMock(), MagicMock()),
        ]
        dm._seq_active = True
        dm._seq_next()
        assert dm._seq_queue == []

    def test_exception_in_start_does_not_lock(self, dm):
        """_start_download exception atarsa kuyruk kilitlenmemeli."""
        dm._start_download = MagicMock(side_effect=RuntimeError("beklenmeyen"))
        dm._seq_queue = [("id1", "url1", {}, MagicMock(), MagicMock())]
        dm._seq_active = True
        dm._seq_next()
        assert dm._seq_active is False
        assert dm._seq_queue == []

    def test_empty_queue_releases_seq_active(self, dm):
        """Baştan boş kuyrukta _seq_next() → _seq_active False."""
        dm._seq_queue = []
        dm._seq_active = True
        dm._seq_next()
        assert dm._seq_active is False

    def test_successful_start_keeps_active(self, dm):
        """İlk item başarıyla başlatılınca _seq_active True kalmalı."""
        wrapped_holder = []

        def capture_start(did, url, opts, pcb, dcb):
            wrapped_holder.append(dcb)
            return True

        dm._start_download = capture_start
        dm._seq_queue = [
            ("A", "urlA", {}, MagicMock(), MagicMock()),
            ("B", "urlB", {}, MagicMock(), MagicMock()),
        ]
        dm._seq_active = True
        dm._seq_next()

        # A başlatıldı, B hâlâ kuyrukta, _seq_active True
        assert dm._seq_active is True
        assert len(dm._seq_queue) == 1
        assert dm._seq_queue[0][0] == "B"

    def test_done_callback_triggers_next_item(self, dm):
        """
        A tamamlandığında _wrapped_done → _seq_next → B denenir.
        B de başarısız olursa kuyruk temiz kapanmalı.
        """
        wrapped_holder = []

        def start_a_succeed_b_fail(did, url, opts, pcb, dcb):
            if did == "A":
                wrapped_holder.append(dcb)
                return True
            return False   # B başarısız

        dm._start_download = start_a_succeed_b_fail
        dm._seq_queue = [
            ("A", "urlA", {}, MagicMock(), MagicMock()),
            ("B", "urlB", {}, MagicMock(), MagicMock()),
        ]
        dm._seq_active = True
        dm._seq_next()

        assert dm._seq_active is True    # A çalışıyor
        wrapped_holder[0]({"status": "completed"})  # A bitti
        assert dm._seq_active is False   # B başarısız → kuyruk bitti

    def test_done_callback_captures_correct_done_cb(self, dm):
        """
        Closure'daki _dcb=done_cb default argümanı doğru done_cb'yi yakalamalı.
        A tamamlanınca yalnızca A'nın done_cb'si çağrılmalı; B'ninki değil.
        """
        calls = []
        done_a = lambda r: calls.append(("A", r))
        done_b = lambda r: calls.append(("B", r))
        wrapped_holder = []

        def start_a(did, url, opts, pcb, dcb):
            if did == "A":
                wrapped_holder.append(dcb)
                return True
            return False

        dm._start_download = start_a
        dm._seq_queue = [
            ("A", "urlA", {}, MagicMock(), done_a),
            ("B", "urlB", {}, MagicMock(), done_b),
        ]
        dm._seq_active = True
        dm._seq_next()

        result = {"status": "completed"}
        wrapped_holder[0](result)

        assert calls == [("A", result)]   # sadece A'nın done_cb'si çağrıldı


# ─────────────────────────────────────────────────────────────────────────────
# Subscription cleanup
# ─────────────────────────────────────────────────────────────────────────────

class TestSubscriptionCleanup:

    def _setup_dm_for_start(self, dm, register_side_effect=None):
        """_start_download için gerekli mock'ları kurar."""
        dm._event_bus = MagicMock()
        dm._state_manager = MagicMock()
        if register_side_effect:
            dm._state_manager.register.side_effect = register_side_effect
        dm._engine = MagicMock()

    def test_exception_triggers_unsub_for_all_four_events(self, dm):
        """register() exception atarsa 4 subscribe + 4 unsubscribe çağrılmalı."""
        self._setup_dm_for_start(dm, register_side_effect=ValueError("test"))
        with pytest.raises(ValueError):
            dm._start_download("id_x", "http://x", {}, MagicMock(), MagicMock())
        assert dm._event_bus.subscribe.call_count == 4
        assert dm._event_bus.unsubscribe.call_count == 4

    def test_exception_leaves_downloads_clean(self, dm):
        """register() exception atarsa downloads dict'i temiz kalmalı."""
        self._setup_dm_for_start(dm, register_side_effect=ValueError("test"))
        with pytest.raises(ValueError):
            dm._start_download("id_y", "http://y", {}, MagicMock(), MagicMock())
        assert "id_y" not in dm.downloads

    def test_engine_start_exception_also_cleans(self, dm):
        """engine.start() exception atarsa da abonelikler ve downloads temizlenmeli."""
        self._setup_dm_for_start(dm)
        dm._engine.start.side_effect = RuntimeError("engine crash")
        with pytest.raises(RuntimeError):
            dm._start_download("id_z", "http://z", {}, MagicMock(), MagicMock())
        assert dm._event_bus.unsubscribe.call_count == 4
        assert "id_z" not in dm.downloads

    def test_successful_start_does_not_unsub(self, dm):
        """Başarılı başlatmada unsubscribe çağrılmamalı."""
        self._setup_dm_for_start(dm)
        dm._start_download("id_ok", "http://ok", {}, MagicMock(), MagicMock())
        assert dm._event_bus.unsubscribe.call_count == 0
        assert dm._event_bus.subscribe.call_count == 4


# ─────────────────────────────────────────────────────────────────────────────
# downloads dict lock
# ─────────────────────────────────────────────────────────────────────────────

class TestDownloadsLock:

    def test_lock_attribute_exists(self, dm):
        assert hasattr(dm, "_downloads_lock")
        assert isinstance(dm._downloads_lock, type(threading.Lock()))

    def test_duplicate_id_rejected_early(self, dm):
        """Aynı download_id ile _start_download → subscribe bile çağrılmamalı."""
        dm._event_bus = MagicMock()
        dm._state_manager = MagicMock()
        dm._engine = MagicMock()
        # Önce downloads'a ekle
        with dm._downloads_lock:
            dm.downloads["dup"] = object()

        result = dm._start_download("dup", "http://dup", {}, MagicMock(), MagicMock())
        assert result is False
        dm._event_bus.subscribe.assert_not_called()

    def test_refresh_ffmpeg_public(self, dm):
        """refresh_ffmpeg() public API mevcut ve çağrılabilir olmalı."""
        assert callable(getattr(dm, "refresh_ffmpeg", None))
        # İçeride _init_ffmpeg'i çağırır; mock ortamında sessizce geçer
        dm.refresh_ffmpeg()

    def test_refresh_ffmpeg_also_refreshes_engine(self, dm):
        """FFmpeg sonradan kurulunca motor da yeni konumu öğrenmeli."""
        dm._engine = MagicMock()
        dm.refresh_ffmpeg()
        dm._engine.refresh_ffmpeg.assert_called_once()
