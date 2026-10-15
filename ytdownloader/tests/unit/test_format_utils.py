# -*- coding: utf-8 -*-
"""Çözünürlük başına format seçimi — uyumluluk (H.264) önceliği."""

from ytdownloader.utils.format_utils import pick_video_formats


def _f(fid, h, vcodec, acodec="none", tbr=0):
    return {"format_id": fid, "height": h, "vcodec": vcodec, "acodec": acodec, "tbr": tbr}


FORMATS = [
    _f("18",  360,  "avc1.42001E", "mp4a.40.2", 500),   # sesli birleşik
    _f("134", 360,  "avc1.4d401e", tbr=300),
    _f("243", 360,  "vp9", tbr=400),
    _f("137", 1080, "avc1.640028", tbr=4000),
    _f("248", 1080, "vp9", tbr=4500),
    _f("399", 1080, "av01.0.08M.08", tbr=4200),
    _f("271", 1440, "vp9", tbr=9000),
    _f("400", 1440, "av01.0.12M.08", tbr=8000),
    _f("140", None, "none", "mp4a.40.2", 128),           # yalnız ses
]


def test_prefers_h264_when_available():
    picked = pick_video_formats(FORMATS)
    assert picked["1080p"] == "137"     # VP9/AV1 daha yüksek bitrate olsa da H.264


def test_prefers_video_only_over_muxed():
    assert pick_video_formats(FORMATS)["360p"] == "134"


def test_keeps_high_resolutions_without_h264():
    assert pick_video_formats(FORMATS)["1440p"] == "271"   # H.264 yok → en iyi kalan


def test_audio_only_ignored():
    assert set(pick_video_formats(FORMATS)) == {"360p", "1080p", "1440p"}
