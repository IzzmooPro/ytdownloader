# -*- coding: utf-8 -*-
"""ffmpeg_installer checksum çözümleme testleri (ağ kullanılmaz)."""


def test_remove_leftovers_keeps_required_exes(tmp_path):
    from ytdownloader.utils.ffmpeg_installer import remove_leftovers
    for name in ("ffmpeg.exe", "ffprobe.exe", "ffplay.exe", "_ffmpeg_tmp_0.zip", "_ffmpeg_tmp_2.zip"):
        (tmp_path / name).write_bytes(b"x" * 10)
    assert remove_leftovers(tmp_path) == 30
    assert sorted(p.name for p in tmp_path.iterdir()) == ["ffmpeg.exe", "ffprobe.exe"]
    assert remove_leftovers(tmp_path) == 0

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
