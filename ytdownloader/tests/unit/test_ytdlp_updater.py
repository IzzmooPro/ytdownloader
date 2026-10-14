# -*- coding: utf-8 -*-
"""ytdlp_updater birim testleri — ağ ve gerçek yt-dlp paketi kullanılmaz."""

import hashlib
import io
import json
import sys
import zipfile

import pytest

from ytdownloader.config.constants import APP_VERSION
from ytdownloader.utils import ytdlp_updater as up


def _make_zipapp(version: str, valid: bool = True) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("__main__.py", "")
        if valid:
            zf.writestr("yt_dlp/__init__.py", "")
            zf.writestr("yt_dlp/version.py", f"__version__ = '{version}'\n")
    return buf.getvalue()


def _fake_http(zip_bytes: bytes, sha: str | None = None):
    digest = sha or hashlib.sha256(zip_bytes).hexdigest()
    calls = []

    def http_get(url, timeout=30):
        calls.append(url)
        if url == up.SUMS_URL:
            return f"deadbeef  yt-dlp.exe\n{digest}  yt-dlp\n".encode()
        if url == up.ZIPAPP_URL:
            return zip_bytes
        raise AssertionError(url)

    http_get.calls = calls
    return http_get


@pytest.fixture
def current(monkeypatch):
    monkeypatch.setattr(up, "current_version", lambda: "2024.01.01")


class TestParseVersion:
    def test_date_versions_compare(self):
        assert up.parse_version("2025.09.26") > up.parse_version("2025.9.5")
        assert up.parse_version("2024.12.31") < up.parse_version("2025.01.01")


class TestReadZipVersion:
    def test_reads_version_without_executing(self, tmp_path):
        p = tmp_path / "z.zip"
        p.write_bytes(_make_zipapp("2025.10.01"))
        assert up.read_zip_version(p) == "2025.10.01"

    def test_invalid_package_returns_none(self, tmp_path):
        p = tmp_path / "z.zip"
        p.write_bytes(_make_zipapp("x", valid=False))
        assert up.read_zip_version(p) is None

    def test_not_a_zip_returns_none(self, tmp_path):
        p = tmp_path / "z.zip"
        p.write_bytes(b"not a zip")
        assert up.read_zip_version(p) is None


class TestCheckAndInstall:
    def test_installs_newer_version(self, tmp_path, current):
        res = up.check_and_install(tmp_path, http_get=_fake_http(_make_zipapp("2025.10.01")))
        assert res["status"] == "installed"
        assert res["version"] == "2025.10.01"
        assert (tmp_path / "yt-dlp.zip").exists()
        meta = json.loads((tmp_path / "meta.json").read_text())
        assert meta["app_version"] == APP_VERSION
        assert meta["version"] == "2025.10.01"

    def test_rejects_hash_mismatch(self, tmp_path, current):
        res = up.check_and_install(
            tmp_path, http_get=_fake_http(_make_zipapp("2025.10.01"), sha="0" * 64)
        )
        assert res["status"] == "error"
        assert "SHA-256" in res["error"]
        assert not (tmp_path / "yt-dlp.zip").exists()

    def test_older_or_same_version_not_installed(self, tmp_path, current):
        res = up.check_and_install(tmp_path, http_get=_fake_http(_make_zipapp("2024.01.01")))
        assert res["status"] == "up_to_date"
        assert not (tmp_path / "yt-dlp.zip").exists()
        assert not list(tmp_path.glob("*.tmp"))

    def test_same_checksum_skips_download(self, tmp_path, current):
        data = _make_zipapp("2024.01.01")
        up.check_and_install(tmp_path, http_get=_fake_http(data))
        http = _fake_http(data)
        res = up.check_and_install(tmp_path, http_get=http)
        assert res["status"] == "up_to_date"
        assert http.calls == [up.SUMS_URL]

    def test_network_error_reported(self, tmp_path, current):
        def boom(url, timeout=30):
            raise OSError("ağ yok")
        res = up.check_and_install(tmp_path, http_get=boom)
        assert res["status"] == "error"
        assert not up.should_auto_check(tmp_path)  # hata sonrası da bir gün bekler


class TestActivateOverride:
    def _install(self, tmp_path, app_version=APP_VERSION, data=None):
        (tmp_path / "yt-dlp.zip").write_bytes(data or _make_zipapp("2099.01.01"))
        (tmp_path / "meta.json").write_text(json.dumps({"app_version": app_version}))

    def test_no_override(self, tmp_path):
        assert up.activate_override(tmp_path) is None

    def test_removed_when_app_version_changes(self, tmp_path):
        self._install(tmp_path, app_version="0.0.1")
        assert up.activate_override(tmp_path) is None
        assert not (tmp_path / "yt-dlp.zip").exists()

    def test_invalid_zip_removed(self, tmp_path):
        self._install(tmp_path, data=b"bozuk")
        assert up.activate_override(tmp_path) is None
        assert not (tmp_path / "yt-dlp.zip").exists()

    def test_not_activated_when_yt_dlp_already_loaded(self, tmp_path):
        # Testlerde yt_dlp zaten import edilmiş olduğundan override devreye giremez;
        # fonksiyon bunu fark edip None dönmeli ve sys.path'i kirletmemeli.
        import yt_dlp  # noqa: F401
        self._install(tmp_path)
        before = list(sys.path)
        try:
            assert up.activate_override(tmp_path) is None
        finally:
            sys.path[:] = before
