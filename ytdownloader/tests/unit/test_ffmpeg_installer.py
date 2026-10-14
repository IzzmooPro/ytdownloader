# -*- coding: utf-8 -*-
"""ffmpeg_installer checksum çözümleme testleri (ağ kullanılmaz)."""

import pytest

from ytdownloader.utils import ffmpeg_installer as fi


def test_every_source_has_a_checksum_strategy(monkeypatch):
    monkeypatch.setattr(
        fi, "_fetch_text",
        lambda url, timeout=15: (
            "a" * 64 + "  ffmpeg-master-latest-win64-gpl.zip\n" if "checksums" in url
            else "b" * 64 + "\n"
        ),
    )
    for url in fi.FFMPEG_URLS:
        assert len(fi._expected_sha256(url)) == 64


def test_btbn_missing_entry_raises(monkeypatch):
    monkeypatch.setattr(fi, "_fetch_text", lambda url, timeout=15: "x  other.zip\n")
    btbn = next(u for u in fi.FFMPEG_URLS if "BtbN" in u)
    with pytest.raises(ValueError):
        fi._expected_sha256(btbn)


def test_unknown_source_raises():
    with pytest.raises(ValueError):
        fi._expected_sha256("https://example.com/ffmpeg.zip")
