# -*- coding: utf-8 -*-
"""
Uygulama içi güncelleme — kurulum dosyasını indir, doğrula, kur.

Akış:
  1. GitHub release bilgisinden kurulum (.exe) dosyası seçilir.
  2. %TEMP% altına indirilir; boyut ve (GitHub verdiyse) SHA-256 doğrulanır.
  3. Kullanıcı "Kur ve Yeniden Başlat" derse kurulum hemen yönetici olarak
     başlatılır (UAC onayı program öndeyken görünür), /WAITPID ile bu sürecin
     bitmesini bekler; uygulama normal kapanış akışıyla kapanır.
  4. Kurulum sessiz modda biter, [Run] (Check: WizardSilent) programı yeniden açar.

Qt'ye bağımlı değildir — UI tarafı ui/qt/update_dialog.py'dedir.
"""

import hashlib
import os
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

def build_installer_params(installer: Path, wait_pid: int) -> str:
    """
    /WAITPID: kurulum bu süreç kapanana kadar bekler (Youtube Setup.iss).
    Süreç kapanmazsa (kullanıcı vazgeçti) kurulum hiçbir şey yapmadan çıkar.
    """
    log_file = installer.with_suffix(".log")
    return " ".join([*INSTALLER_ARGS, f"/WAITPID={int(wait_pid)}", f'/LOG="{log_file}"'])


def start_installer(installer: Path, wait_pid: int | None = None) -> bool:
    """
    Kurulumu başlatır; kurulum yönetici iznini (UAC) kendisi ister. Program
    pencereleri hâlâ öndeyken çağrılmalı: Windows, arka plandaki bir süreçten
    istenen UAC onayını öne getirmez, görev çubuğunda yanıp sönen simge bırakır.
    "runas" kullanılmaz — kurulum baştan yönetici başlarsa [Run]
    runasoriginaluser etkisiz kalır ve program yönetici olarak açılır.

    Returns: kurulum başladıysa True.
    """
    if not installer.exists():
        log.error(f"Kurulum dosyası bulunamadı: {installer}")
        return False
    params = build_installer_params(installer, wait_pid or os.getpid())
    # Kurulum (ve onun yeniden açtığı program) ortam değişkenlerimizi devralır;
    # PyInstaller onefile bunları görünce kapanırken silinen eski _MEI
    # klasöründe python313.dll arar → "Failed to load Python DLL".
    os.environ["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    import ctypes
    rc = ctypes.windll.shell32.ShellExecuteW(None, "open", str(installer), params, None, 1)
    if rc <= 32:
        log.warning(f"Kurulum başlatılamadı (ShellExecute={rc})")
        return False
    log.info(f"Kurulum başlatıldı, program kapanınca devam edecek: {installer}")
    return True
