# -*- coding: utf-8 -*-
"""
url_utils modülü için birim testler.
pytest ile çalıştır: pytest ytdownloader/tests/unit/test_url_utils.py -v
"""

import pytest
from ytdownloader.utils.url_utils import (
    extract_video_id,
    validate_youtube_url,
    shorten_youtube_url,
    format_duration,
    get_thumbnail_urls,
)


class TestExtractVideoId:
    def test_standard_url(self):
        assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_short_url(self):
        assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_embed_url(self):
        assert extract_video_id("https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_music_url(self):
        assert extract_video_id("https://music.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_invalid_url(self):
        assert extract_video_id("https://google.com") is None

    def test_empty_string(self):
        assert extract_video_id("") is None

    def test_url_with_extra_params(self):
        assert extract_video_id(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s&list=PL123"
        ) == "dQw4w9WgXcQ"


class TestValidateYoutubeUrl:
    def test_valid_url(self):
        valid, msg = validate_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert valid is True
        assert msg == ""

    def test_short_url(self):
        valid, _ = validate_youtube_url("https://youtu.be/dQw4w9WgXcQ")
        assert valid is True

    def test_non_youtube_domain(self):
        valid, msg = validate_youtube_url("https://vimeo.com/123456")
        assert valid is False
        assert "domain" in msg.lower()

    def test_no_video_id(self):
        valid, msg = validate_youtube_url("https://www.youtube.com/")
        assert valid is False

    def test_http_scheme(self):
        # http de geçerli
        valid, _ = validate_youtube_url("http://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert valid is True

    def test_no_scheme(self):
        valid, msg = validate_youtube_url("www.youtube.com/watch?v=abc")
        assert valid is False

    def test_too_long(self):
        valid, msg = validate_youtube_url("https://youtu.be/" + "a" * 2048)
        assert valid is False

    def test_non_string_input(self):
        valid, msg = validate_youtube_url(None)  # type: ignore
        assert valid is False


class TestFormatDuration:
    def test_seconds_only(self):
        # Dilden bağımsız gösterim: "45 sn" değil "0:45"
        assert format_duration(45) == "0:45"

    def test_minutes_and_seconds(self):
        assert format_duration(125) == "2:05"

    def test_hours(self):
        assert format_duration(3661) == "1:01:01"

    def test_zero(self):
        assert format_duration(0) == ""

    def test_none(self):
        assert format_duration(None) == ""


class TestGetThumbnailUrls:
    def test_returns_list(self):
        urls = get_thumbnail_urls("dQw4w9WgXcQ")
        assert isinstance(urls, list)
        assert len(urls) == 5

    def test_all_contain_video_id(self):
        vid_id = "dQw4w9WgXcQ"
        for url in get_thumbnail_urls(vid_id):
            assert vid_id in url

    def test_empty_id(self):
        assert get_thumbnail_urls("") == []

    def test_none_id(self):
        assert get_thumbnail_urls(None) == []  # type: ignore
