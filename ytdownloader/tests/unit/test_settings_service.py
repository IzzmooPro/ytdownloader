# -*- coding: utf-8 -*-
"""
SettingsService — atomic write davranışı testleri.
Gerçek dosya sistemi kullanılır (tmp_path), ağ/Qt bağımlılığı yok.
"""

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def svc(tmp_path, monkeypatch):
    """
    SettingsService örneği — ayarlar tmp_path altına yazılır.
    APPDATA override ile gerçek kullanıcı dizinine dokunulmaz.
    """
    monkeypatch.setenv("APPDATA", str(tmp_path))
    from ytdownloader.infrastructure.settings_service import SettingsService
    return SettingsService(tmp_path)


class TestAtomicSave:
    def test_save_creates_file(self, svc):
        assert svc.save({"theme": "dark"}) is True
        assert svc.settings_file.exists()

    def test_save_content_correct(self, svc):
        data = {"theme": "dark", "language": "tr", "version": "1.0.0"}
        svc.save(data)
        loaded = json.loads(svc.settings_file.read_text(encoding="utf-8"))
        assert loaded == data

    def test_tmp_file_absent_after_success(self, svc):
        """Başarılı save sonrası .json.tmp dosyası kalmamalı."""
        svc.save({"theme": "light"})
        tmp = svc.settings_file.with_suffix(".json.tmp")
        assert not tmp.exists()

    def test_original_preserved_when_replace_fails(self, svc):
        """
        os.replace başarısız olursa orijinal settings.json bozulmamalı.
        Atomic write'ın asıl güvencesi budur.
        """
        original = {"theme": "dark", "protected": True}
        svc.save(original)

        with patch("os.replace", side_effect=OSError("simulated disk full")):
            result = svc.save({"theme": "light", "new": "data"})

        assert result is False
        # Hedef dosya orijinal içeriği korumalı
        survived = json.loads(svc.settings_file.read_text(encoding="utf-8"))
        assert survived == original

    def test_tmp_cleaned_after_failed_replace(self, svc):
        """Başarısız save sonrası .json.tmp diskte kalmamalı."""
        with patch("os.replace", side_effect=OSError("disk full")):
            svc.save({"x": 1})

        tmp = svc.settings_file.with_suffix(".json.tmp")
        assert not tmp.exists()

    def test_returns_false_on_failure(self, svc):
        with patch("os.replace", side_effect=OSError("disk full")):
            assert svc.save({"x": 1}) is False


class TestRoundTrip:
    def test_all_value_types_preserved(self, svc):
        data = {
            "int_val":  42,
            "str_val":  "merhaba",
            "bool_val": True,
            "none_val": None,
            "list_val": [1, 2, 3],
            "dict_val": {"nested": "yes"},
        }
        svc.save(data)
        loaded = svc.load()
        for key, expected in data.items():
            assert loaded[key] == expected, f"{key} round-trip başarısız"

    def test_repeated_saves_overwrite(self, svc):
        svc.save({"v": 1})
        svc.save({"v": 2})
        assert svc.load()["v"] == 2

    def test_load_returns_defaults_when_file_missing(self, svc):
        assert not svc.settings_file.exists()
        result = svc.load()
        assert isinstance(result, dict)
        assert len(result) > 0  # DEFAULT_SETTINGS dolu

    def test_load_returns_defaults_on_corrupted_file(self, svc):
        svc.settings_file.write_text("bu gecersiz json {{{", encoding="utf-8")
        result = svc.load()
        assert isinstance(result, dict)  # crash değil, default döner
