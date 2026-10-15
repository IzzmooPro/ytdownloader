# -*- coding: utf-8 -*-
"""
Uygulama içi güncelleme — kurulum dosyasını indir, doğrula, kur.

Akış:
  1. GitHub release bilgisinden kurulum (.exe) dosyası seçilir.
  2. %TEMP% altına indirilir; boyut ve (GitHub verdiyse) SHA-256 doğrulanır.
  3. Kullanıcı "Kur ve Yeniden Başlat" derse yol kaydedilir, uygulama normal
     kapanış akışıyla kapanır (kuyruk diske yazılır, worker'lar durur).
  4. main.py çıkışta launch_pending_installer() çağırır: küçük bir PowerShell
     süreci bu işlemin bitmesini bekler, sonra kurulumu sessiz modda başlatır.
     Kurulum betiği ([Run], Check: WizardSilent) bitince programı yeniden açar.

Qt'ye bağımlı değildir — UI tarafı ui/qt/update_dialog.py'dedir.
"""

import hashlib
import os
import subprocess
import tempfile
import threading
import urllib.request
from pathlib import Path
from typing import Callable

from ytdownloader.infrastructure.logger import get_logger

log = get_logger("app_updater")

# Inno Setup sessiz kurulum parametreleri — ilerleme penceresi görünür,
# soru sorulmaz, yeniden başlatma istenmez.
INSTALLER_ARGS = ["/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART"]

_CHUNK = 256 * 1024

# Kullanıcı "Kur ve Yeniden Başlat" dediğinde doldurulur; main.py çıkışta okur.
_pending_installer: Path | None = None


class UpdateCancelled(Exception):
    """İndirme kullanıcı tarafından iptal edildi."""


def pick_installer_asset(release_info: dict) -> dict | None:
    """Release içinden Windows kurulum dosyasını seçer (adında 'setup' geçen .exe)."""
    for asset in release_info.get("assets") or []:
        name = (asset.get("name") or "").lower()
        if name.endswith(".exe") and "setup" in name and asset.get("browser_download_url"):
            return asset
    return None


def _expected_sha256(asset: dict) -> str | None:
    """GitHub, asset bilgisinde 'digest': 'sha256:<hex>' verir (varsa)."""
    digest = asset.get("digest") or ""
    if digest.lower().startswith("sha256:"):
        value = digest.split(":", 1)[1].strip().lower()
        if len(value) == 64:
            return value
    return None


def installer_path(version: str, base_dir: Path | None = None) -> Path:
    base = base_dir or Path(tempfile.gettempdir()) / "YTDownloader_update"
    return base / f"YTDownloader-Setup-{version}.exe"


def _is_valid(path: Path, asset: dict) -> bool:
    """Dosya beklenen boyutta ve (biliniyorsa) özette mi?"""
    try:
        if path.stat().st_size != int(asset.get("size") or -1):
            return False
    except OSError:
        return False
    expected = _expected_sha256(asset)
    if expected:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for block in iter(lambda: f.read(_CHUNK), b""):
                h.update(block)
        return h.hexdigest() == expected
    return True


def _open_url(url: str, timeout: int = 30):
    req = urllib.request.Request(url, headers={"User-Agent": "ytdownloader"})
    return urllib.request.urlopen(req, timeout=timeout)


def download_installer(asset: dict, version: str,
                       progress: Callable[[int, int], None] | None = None,
                       cancel: threading.Event | None = None,
                       base_dir: Path | None = None,
                       opener=_open_url) -> Path:
    """
    Kurulum dosyasını indirir ve doğrular. Daha önce indirilmiş geçerli bir
    kopya varsa yeniden indirmez.

    Raises:
        UpdateCancelled — cancel set edildiyse
        ValueError      — boyut / SHA-256 uyuşmazlığı
        OSError         — ağ / disk hatası
    """
    dest = installer_path(version, base_dir)
    dest.parent.mkdir(parents=True, exist_ok=True)
    total = int(asset.get("size") or 0)

    if dest.exists() and _is_valid(dest, asset):
        log.info(f"Kurulum dosyası zaten indirilmiş: {dest}")
        if progress:
            progress(total, total)
        return dest

    tmp = dest.with_suffix(".exe.part")
    expected = _expected_sha256(asset)
    h = hashlib.sha256()
    done = 0
    try:
        with opener(asset["browser_download_url"]) as resp, tmp.open("wb") as f:
            while True:
                if cancel is not None and cancel.is_set():
                    raise UpdateCancelled()
                block = resp.read(_CHUNK)
                if not block:
                    break
                f.write(block)
                h.update(block)
                done += len(block)
                if progress:
                    progress(done, total)

        if total and done != total:
            raise ValueError(f"Eksik indirme: {done} / {total} bayt")
        if expected and h.hexdigest() != expected:
            raise ValueError("SHA-256 doğrulaması başarısız")
        os.replace(tmp, dest)
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise

    log.info(f"Kurulum dosyası indirildi ve doğrulandı: {dest}")
    return dest


# ── Kurulum ──────────────────────────────────────────────────────────────────

def set_pending_installer(path: Path | None) -> None:
    global _pending_installer
    _pending_installer = path


def get_pending_installer() -> Path | None:
    return _pending_installer


def _ps_quote(s: str) -> str:
    """PowerShell tek tırnaklı dize — içindeki ' iki kez yazılır."""
    return "'" + s.replace("'", "''") + "'"


def build_install_command(installer: Path, wait_pid: int) -> list[str]:
    """
    Bu süreç kapanana kadar bekleyip kurulumu başlatan PowerShell komutu.
    Program Files'a kurulduğu için kurulum UAC onayı ister; yeniden açılış
    kurulum betiğinde runasoriginaluser ile normal kullanıcı yetkisiyle yapılır.
    """
    args = ",".join(_ps_quote(a) for a in INSTALLER_ARGS)
    script = (
        f"Wait-Process -Id {int(wait_pid)} -Timeout 120 -ErrorAction SilentlyContinue; "
        f"Start-Process -FilePath {_ps_quote(str(installer))} -ArgumentList {args}"
    )
    return [
        "powershell.exe", "-NoProfile", "-NonInteractive",
        "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden",
        "-Command", script,
    ]


def launch_pending_installer() -> bool:
    """
    main.py çıkışta çağırır. Bekleyen kurulum varsa ayrık bir süreçle başlatır.
    Returns: başlatıldıysa True.
    """
    installer = _pending_installer
    if installer is None:
        return False
    if not installer.exists():
        log.error(f"Kurulum dosyası bulunamadı: {installer}")
        return False
    cmd = build_install_command(installer, os.getpid())
    flags = 0
    if os.name == "nt":
        flags = (subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
                 | subprocess.CREATE_NO_WINDOW)
    try:
        subprocess.Popen(cmd, creationflags=flags, close_fds=True,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    except OSError as e:
        log.error(f"Kurulum başlatılamadı: {e}")
        return False
    log.info(f"Kurulum başlatılıyor (program kapandıktan sonra): {installer}")
    return True
