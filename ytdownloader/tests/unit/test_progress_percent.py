# -*- coding: utf-8 -*-
"""Progress yüzdesi — parçalı (HLS/DASH) indirmelerde %100'de takılmamalı."""

from ytdownloader.core.download_engine import _progress_percent


def test_fragmented_uses_fragment_count():
    # yt-dlp ilk anda "100% of ~1.00KiB (frag 0/344)" der
    d = {"downloaded_bytes": 1024, "total_bytes_estimate": 1024,
         "fragment_index": 0, "fragment_count": 344}
    assert _progress_percent(d) == 0.0
    d.update(fragment_index=168)
    assert round(_progress_percent(d)) == 49


def test_regular_download_uses_bytes():
    assert _progress_percent({"downloaded_bytes": 50, "total_bytes": 200}) == 25.0


def test_never_100_while_downloading():
    assert _progress_percent({"downloaded_bytes": 200, "total_bytes": 200}) < 100
    assert _progress_percent({"fragment_index": 344, "fragment_count": 344}) < 100


def test_unknown_total_is_zero():
    assert _progress_percent({"downloaded_bytes": 10}) == 0.0
