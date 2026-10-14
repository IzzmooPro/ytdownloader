# -*- coding: utf-8 -*-
"""
yt-dlp çalışma zamanı güncelleyici.

EXE içine gömülü yt-dlp zamanla eskir ve YouTube değişiklikleri indirmeleri
bozar. Bu modül, yt-dlp'nin resmi GitHub sürümündeki zip paketini (`yt-dlp`
dosyası — içinde `yt_dlp/` paketi bulunan bir zipapp) APPDATA altına indirir
ve program açılışında `sys.path`'in başına ekler. Böylece programı yeniden
yayınlamadan yt-dlp güncellenebilir.

Güvenlik:
  - İndirilen dosya, aynı sürümün SHA2-256SUMS listesiyle doğrulanır.
  - Bozuk / açılamayan paket otomatik devre dışı bırakılır, gömülü sürüme dönülür.
  - Program sürümü değişince (yeni EXE) eski override silinir; yeni EXE kendi
    güncel yt-dlp'si ile gelir.

Qt'ye bağımlı değildir — UI tarafı services/ytdlp_update_service.py'dedir.
"""

import hashlib
import json
import os
import re
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

from ytdownloader.config.constants import APP_VERSION
from ytdownloader.infrastructure.logger import get_logger

log = get_logger("ytdlp_updater")

_RELEASE_BASE = "https://github.com/yt-dlp/yt-dlp/releases/latest/download"
SUMS_URL      = f"{_RELEASE_BASE}/SHA2-256SUMS"
ZIPAPP_URL    = f"{_RELEASE_BASE}/yt-dlp"
ZIPAPP_NAME   = "yt-dlp"

AUTO_CHECK_INTERVAL_S = 24 * 60 * 60   # otomatik kontrol en fazla günde bir

_VERSION_RE = re.compile(r"""__version__\s*=\s*['"]([^'"]+)['"]""")


def get_override_dir() -> Path:
    appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
    return Path(appdata) / "MyYouTubeDownloader" / "ytdlp"


def _zip_path(base: Path | None = None) -> Path:
    return (base or get_override_dir()) / "yt-dlp.zip"


def _meta_path(base: Path | None = None) -> Path:
    return (base or get_override_dir()) / "meta.json"


def _load_meta(base: Path | None = None) -> dict:
    try:
        return json.loads(_meta_path(base).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_meta(meta: dict, base: Path | None = None) -> None:
    path = _meta_path(base)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _remove_override(base: Path | None = None) -> None:
    for p in (_zip_path(base), _meta_path(base)):
        try:
            p.unlink()
        except FileNotFoundError:
            pass
        except Exception as e:
            log.warning(f"yt-dlp override silinemedi ({p}): {e}")


def parse_version(v: str) -> tuple:
    """'2025.09.26' → (2025, 9, 26). Ayrıştırılamayan parçalar 0 sayılır."""
    out = []
    for part in re.split(r"[.\-]", v.strip()):
        try:
            out.append(int(part))
        except ValueError:
            out.append(0)
    return tuple(out)


def read_zip_version(zip_file: Path) -> str | None:
    """Zipapp içindeki yt_dlp/version.py'den sürümü okur (kod çalıştırmadan)."""
    try:
        with zipfile.ZipFile(zip_file) as zf:
            names = set(zf.namelist())
            if "yt_dlp/__init__.py" not in names or "yt_dlp/version.py" not in names:
                return None
            m = _VERSION_RE.search(zf.read("yt_dlp/version.py").decode("utf-8", "replace"))
            return m.group(1) if m else None
    except Exception:
        return None


# ── Açılış: override'ı etkinleştir ───────────────────────────────────────────

def activate_override(base: Path | None = None) -> str | None:
    """
    İndirilmiş yt-dlp varsa sys.path'e ekler ve import eder.
    yt_dlp başka bir yerde import edilmeden ÖNCE çağrılmalıdır.

    Returns: etkinleşen sürüm ya da None (gömülü sürüm kullanılıyor).
    """
    zip_file = _zip_path(base)
    if not zip_file.exists():
        return None

    meta = _load_meta(base)
    if meta.get("app_version") != APP_VERSION:
        log.info("Program sürümü değişmiş — eski yt-dlp güncellemesi kaldırılıyor")
        _remove_override(base)
        return None

    version = read_zip_version(zip_file)
    if not version:
        log.warning("yt-dlp güncellemesi geçersiz — kaldırılıyor")
        _remove_override(base)
        return None

    zip_str = str(zip_file)
    sys.path.insert(0, zip_str)
    try:
        import yt_dlp  # noqa: F401
        loaded_from = getattr(yt_dlp, "__file__", "") or ""
        if not loaded_from.startswith(zip_str):
            log.warning(f"yt-dlp güncellemesi devreye girmedi, gömülü sürüm yüklendi: {loaded_from}")
            return None
    except Exception as e:
        log.error(f"Güncellenmiş yt-dlp yüklenemedi, gömülü sürüme dönülüyor: {e}")
        sys.path.remove(zip_str)
        for name in [m for m in sys.modules if m == "yt_dlp" or m.startswith("yt_dlp.")]:
            del sys.modules[name]
        _remove_override(base)
        return None

    log.info(f"yt-dlp {version} (güncellenmiş) kullanılıyor")
    return version


# ── Güncelleme kontrolü ve kurulum ───────────────────────────────────────────

def _http_get(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "ytdownloader"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _expected_sha256(sums_text: str) -> str:
    for line in sums_text.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].lstrip("*") == ZIPAPP_NAME:
            return parts[0].lower()
    raise ValueError("SHA2-256SUMS içinde yt-dlp bulunamadı")


def current_version() -> str:
    try:
        from yt_dlp.version import __version__
        return __version__
    except Exception:
        return "0"


def should_auto_check(base: Path | None = None) -> bool:
    last = _load_meta(base).get("last_check", 0)
    return (time.time() - last) >= AUTO_CHECK_INTERVAL_S


def check_and_install(base: Path | None = None, http_get=_http_get) -> dict:
    """
    En son yt-dlp'yi kontrol eder; daha yeniyse indirip doğrular ve kurar.

    Returns:
        {"status": "up_to_date" | "installed" | "error",
         "version": str, "current": str, "error": str}
    """
    base_dir = base or get_override_dir()
    current  = current_version()
    meta     = _load_meta(base_dir)
    meta["last_check"] = time.time()

    try:
        expected = _expected_sha256(http_get(SUMS_URL, timeout=15).decode("utf-8", "replace"))

        # Aynı paket zaten kurulu/denetlenmiş → indirmeye gerek yok
        if meta.get("checked_sha256") == expected:
            _save_meta(meta, base_dir)
            pending = meta.get("version") if _zip_path(base_dir).exists() else None
            if pending and parse_version(pending) > parse_version(current):
                return {"status": "installed", "version": pending, "current": current}
            return {"status": "up_to_date", "version": current, "current": current}

        data = http_get(ZIPAPP_URL, timeout=120)
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError("SHA-256 doğrulaması başarısız")

        base_dir.mkdir(parents=True, exist_ok=True)
        tmp = base_dir / "yt-dlp.zip.tmp"
        tmp.write_bytes(data)
        latest = read_zip_version(tmp)
        if not latest:
            tmp.unlink(missing_ok=True)
            raise ValueError("İndirilen yt-dlp paketi geçersiz")

        meta["checked_sha256"] = expected
        if parse_version(latest) <= parse_version(current):
            tmp.unlink(missing_ok=True)
            _save_meta(meta, base_dir)
            return {"status": "up_to_date", "version": current, "current": current}

        os.replace(tmp, _zip_path(base_dir))
        meta.update({"version": latest, "sha256": expected, "app_version": APP_VERSION})
        _save_meta(meta, base_dir)
        log.info(f"yt-dlp {latest} indirildi (şu an: {current}) — yeniden başlatınca etkin")
        return {"status": "installed", "version": latest, "current": current}

    except Exception as e:
        log.warning(f"yt-dlp güncelleme kontrolü başarısız: {e}")
        try:
            _save_meta(meta, base_dir)
        except Exception:
            pass
        return {"status": "error", "error": str(e), "current": current}
