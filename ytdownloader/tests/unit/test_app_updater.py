# -*- coding: utf-8 -*-
"""Uygulama içi güncelleme — ağ kullanılmaz."""

import hashlib
import io
import threading

import pytest

from ytdownloader.utils import app_updater as au

DATA = b"MZ" + b"x" * 700_000          # sahte kurulum dosyası (birkaç parça)


def _asset(data=DATA, digest=True, **kw):
    a = {
        "name": "YouTube.Indirici.Setup.v1.2.2.exe",
        "size": len(data),
        "browser_download_url": "https://example.invalid/setup.exe",
    }
    if digest:
        a["digest"] = "sha256:" + hashlib.sha256(data).hexdigest()
    a.update(kw)
    return a


def _opener(data=DATA):
    calls = []

    def open_(url, timeout=30):
        calls.append(url)
        return io.BytesIO(data)
    open_.calls = calls
    return open_


class TestPickAsset:
    def test_picks_setup_exe(self):
        rel = {"assets": [
            {"name": "notes.txt", "browser_download_url": "u1"},
            {"name": "YouTube.Indirici.Setup.v1.2.2.exe", "browser_download_url": "u2"},
        ]}
        assert au.pick_installer_asset(rel)["browser_download_url"] == "u2"

    def test_none_when_missing(self):
        assert au.pick_installer_asset({"assets": [{"name": "src.zip"}]}) is None
        assert au.pick_installer_asset({}) is None


class TestDownload:
    def test_downloads_and_verifies(self, tmp_path):
        progress = []
        path = au.download_installer(_asset(), "1.2.2", progress=lambda d, t: progress.append(d),
                                     base_dir=tmp_path, opener=_opener())
        assert path.read_bytes() == DATA
        assert progress[-1] == len(DATA)
        assert not list(tmp_path.glob("*.part"))

    def test_sha_mismatch_rejected(self, tmp_path):
        bad = _asset(digest=False)
        bad["digest"] = "sha256:" + "0" * 64
        with pytest.raises(ValueError, match="SHA-256"):
            au.download_installer(bad, "1.2.2", base_dir=tmp_path, opener=_opener())
        assert not list(tmp_path.glob("*.exe*"))

    def test_truncated_download_rejected(self, tmp_path):
        asset = _asset(digest=False)
        with pytest.raises(ValueError, match="Eksik"):
            au.download_installer(asset, "1.2.2", base_dir=tmp_path, opener=_opener(DATA[:1000]))
        assert not list(tmp_path.glob("*.exe"))

    def test_works_without_digest(self, tmp_path):
        path = au.download_installer(_asset(digest=False), "1.2.2",
                                     base_dir=tmp_path, opener=_opener())
        assert path.exists()

    def test_reuses_valid_existing_file(self, tmp_path):
        au.download_installer(_asset(), "1.2.2", base_dir=tmp_path, opener=_opener())
        op = _opener()
        au.download_installer(_asset(), "1.2.2", base_dir=tmp_path, opener=op)
        assert op.calls == []

    def test_cancel(self, tmp_path):
        ev = threading.Event()
        ev.set()
        with pytest.raises(au.UpdateCancelled):
            au.download_installer(_asset(), "1.2.2", cancel=ev, base_dir=tmp_path, opener=_opener())
        assert not list(tmp_path.glob("*.exe*"))


class TestInstallParams:
    def test_silent_waits_for_pid_and_logs(self, tmp_path):
        params = au.build_installer_params(tmp_path / "Setup.exe", 4242)
        assert "/SILENT" in params and "/WAITPID=4242" in params
        assert f'/LOG="{tmp_path / "Setup.log"}"' in params

    def test_missing_installer_not_started(self, tmp_path):
        assert au.start_installer(tmp_path / "yok.exe", 1) is False
