# -*- coding: utf-8 -*-
"""
file_utils modülü için birim testler.
"""

import pytest
from pathlib import Path
import tempfile
import os

from ytdownloader.utils.file_utils import sanitize_filename, resolve_conflict, organize_path


class TestSanitizeFilename:
    def test_normal_name(self):
        assert sanitize_filename("hello world") == "hello world"

    def test_illegal_chars_replaced(self):
        result = sanitize_filename('video: "test" <ok>')
        assert ":" not in result
        assert '"' not in result
        assert "<" not in result
        assert ">" not in result

    def test_empty_returns_video(self):
        assert sanitize_filename("") == "video"

    def test_only_illegal_chars(self):
        assert sanitize_filename("???***") == "video"

    def test_long_name_truncated(self):
        long_name = "a" * 300
        result = sanitize_filename(long_name)
        assert len(result) <= 200

    def test_strips_leading_trailing_dots(self):
        result = sanitize_filename("...test...")
        assert not result.startswith(".")
        assert not result.endswith(".")


class TestResolveConflict:
    def test_no_conflict(self, tmp_path):
        p = tmp_path / "video.mp4"
        assert resolve_conflict(p) == p

    def test_single_conflict(self, tmp_path):
        p = tmp_path / "video.mp4"
        p.touch()
        result = resolve_conflict(p)
        assert result == tmp_path / "video (1).mp4"

    def test_multiple_conflicts(self, tmp_path):
        base = tmp_path / "video.mp4"
        base.touch()
        (tmp_path / "video (1).mp4").touch()
        (tmp_path / "video (2).mp4").touch()
        result = resolve_conflict(base)
        assert result == tmp_path / "video (3).mp4"


class TestOrganizePath:
    def test_none_criteria_returns_base(self, tmp_path):
        result = organize_path(tmp_path, {}, "none")
        assert result == tmp_path

    def test_channel_creates_subfolder(self, tmp_path):
        info = {"channel": "Test Channel"}
        result = organize_path(tmp_path, info, "channel")
        assert result == tmp_path / "Test Channel"
        assert result.exists()

    def test_date_criteria(self, tmp_path):
        info = {"upload_date": "20240115"}
        result = organize_path(tmp_path, info, "date")
        assert result == tmp_path / "2024" / "01"
        assert result.exists()

    def test_category_criteria(self, tmp_path):
        info = {"categories": ["Music"]}
        result = organize_path(tmp_path, info, "category")
        assert result == tmp_path / "Music"
        assert result.exists()

    def test_channel_sanitizes_name(self, tmp_path):
        info = {"channel": "Test: <Channel>"}
        result = organize_path(tmp_path, info, "channel")
        assert ":" not in result.name
        assert "<" not in result.name
