# -*- coding: utf-8 -*-
"""
Dosya sistemi yardımcıları.
Path traversal koruması, dosya adı temizleme, çakışma yönetimi.
"""

import re
import os
import uuid
from pathlib import Path

# Windows ve Linux/macOS'ta geçersiz karakter seti
_ILLEGAL_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_MAX_FILENAME_LEN = 200   # Windows MAX_PATH güvenliği için


def sanitize_filename(name: str) -> str:
    """
    Dosya adındaki geçersiz karakterleri temizler.
    Boş sonuç durumunda 'video' döner.
    """
    if not name:
        return "video"
    name = _ILLEGAL_CHARS.sub("_", name)
    name = re.sub(r"_+", "_", name).strip("_. ")
    return name[:_MAX_FILENAME_LEN] or "video"


def resolve_conflict(path: Path) -> Path:
    """
    Dosya zaten varsa eşsiz bir isim üretir.
    title.mp4 → title (1).mp4 → title (2).mp4 → ... → title_<uuid>.mp4
    """
    if not path.exists():
        return path

    stem, suffix = path.stem, path.suffix
    for i in range(1, 1000):
        candidate = path.with_name(f"{stem} ({i}){suffix}")
        if not candidate.exists():
            return candidate

    # Son çare: UUID suffix
    return path.with_name(f"{stem}_{uuid.uuid4().hex[:8]}{suffix}")


def organize_path(base: Path, video_info: dict, criteria: str) -> Path:
    """
    Belirlenen kritere göre alt klasör oluşturur ve yolunu döner.

    criteria:
        'none'     → base döner, alt klasör oluşturulmaz
        'channel'  → base/KanalAdı/
        'date'     → base/2024/01/
        'category' → base/Kategori/
    """
    if criteria == "channel":
        channel = video_info.get("channel") or video_info.get("uploader") or "Unknown"
        sub = sanitize_filename(channel)

    elif criteria == "date":
        upload_date = video_info.get("upload_date", "")
        if len(upload_date) >= 6:
            sub = os.path.join(upload_date[:4], upload_date[4:6])
        else:
            sub = "Unknown"

    elif criteria == "category":
        categories = video_info.get("categories") or ["Misc"]
        sub = sanitize_filename(categories[0])

    else:
        return base

    out = base / sub
    out.mkdir(parents=True, exist_ok=True)
    return out


def safe_resolve(path_str: str) -> Path:
    """
    Kullanıcıdan gelen yolu güvenli biçimde çözümler.
    Sembolik link ve .. traversal'larını normalize eder.
    """
    return Path(path_str).resolve()


def is_ffmpeg_available(base_path=None) -> bool:
    """FFmpeg'in program klasöründe mevcut olup olmadığını kontrol eder.
    Sistem PATH'e BAKMAZ — sadece program içi klasörler kontrol edilir."""
    import os, sys
    from pathlib import Path
    ffmpeg_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"

    # APPDATA altındaki kalıcı kurulum dizini (EXE modunda buraya yüklenir)
    appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
    candidates = [Path(appdata) / "MyYouTubeDownloader" / "ffmpeg"]

    if base_path:
        candidates += [
            Path(base_path) / "bin",
            Path(base_path) / "ytdownloader" / "assets" / "ffmpeg",
            Path(base_path) / "assets" / "ffmpeg",
        ]

    # Gömülü PyInstaller kopyası varsa son çare olarak bak.
    if hasattr(sys, "_MEIPASS"):
        candidates.append(Path(sys._MEIPASS) / "ytdownloader" / "assets" / "ffmpeg")

    for d in candidates:
        if (d / ffmpeg_name).exists():
            return True
    return False
