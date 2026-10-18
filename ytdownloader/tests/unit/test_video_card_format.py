# -*- coding: utf-8 -*-
"""Kartın format seçimi: varsayılan hemen görünür, kullanıcı seçimi ezilmez."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QtWidgets = pytest.importorskip("PyQt6.QtWidgets")

from ytdownloader.ui.qt.video_card import VideoCard  # noqa: E402

INFO = {"title": "t", "channel": "c", "duration": 60,
        "formats": [{"format_id": "137", "vcodec": "avc1", "ext": "mp4", "height": 1080}]}


class _Settings:
    def __init__(self, fmt):
        self.data = {"default_format": fmt, "default_quality": "320 kbps"}

    def load(self):
        return dict(self.data)


class _DM:
    def fetch_video_info(self, url, callback):
        pass


@pytest.fixture(scope="module")
def app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _card(fmt):
    return VideoCard("https://www.youtube.com/watch?v=abc", _DM(), None, _Settings(fmt))


@pytest.mark.parametrize("fmt", ["MP3", "MP4"])
def test_default_format_shown_immediately(app, fmt):
    card = _card(fmt)
    assert card._format == fmt
    assert card.btn_format.text().startswith(fmt)


def test_user_choice_survives_info_arrival(app):
    card = _card("MP3")
    card._toggle_format()                      # bilgi yüklenirken MP4 seçildi
    card._on_info_received(True, INFO, "")
    assert card._format == "MP4"
    assert card.btn_format.text().startswith("MP4")


def test_default_applied_when_user_did_not_choose(app):
    card = _card("MP4")
    card._on_info_received(True, INFO, "")
    assert card._format == "MP4"
