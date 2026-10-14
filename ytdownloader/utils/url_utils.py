# -*- coding: utf-8 -*-
"""
YouTube URL doğrulama ve işleme yardımcıları.
Hiçbir uygulama modülüne bağımlı değil — saf fonksiyonlar.
Shorts URL desteği dahil.
"""

import re
import urllib.parse
from ytdownloader.config.constants import VALID_YT_DOMAINS


def extract_video_id(url: str) -> str | None:
    """URL'den video ID'sini çıkarır. Shorts dahil. Bulunamazsa None döner."""
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        return None

    if parsed.netloc in ("www.youtube.com", "youtube.com", "music.youtube.com", "m.youtube.com"):
        # /shorts/ID, /live/ID, /embed/ID formatları
        parts = parsed.path.split("/")
        for marker in ("shorts", "live", "embed"):
            if marker in parts:
                idx = parts.index(marker)
                if idx + 1 < len(parts) and parts[idx + 1]:
                    return parts[idx + 1]
        # Normal watch?v=VIDEO_ID
        params = urllib.parse.parse_qs(parsed.query)
        return params.get("v", [None])[0]

    if parsed.netloc in ("youtu.be", "www.youtu.be"):
        return parsed.path.lstrip("/") or None

    if parsed.netloc in ("www.youtube-nocookie.com", "youtube-nocookie.com"):
        parts = parsed.path.split("/")
        if "embed" in parts and len(parts) > 2:
            return parts[-1] or None

    return None


def is_playlist_url(url: str) -> bool:
    """
    Video içermeyen saf playlist linki mi? (youtube.com/playlist?list=...)
    Bu linkler kart yerine playlist seçim penceresine yönlendirilir.
    """
    try:
        parsed = urllib.parse.urlparse(url.strip())
    except Exception:
        return False
    if parsed.netloc not in VALID_YT_DOMAINS:
        return False
    params = urllib.parse.parse_qs(parsed.query)
    return bool(params.get("list")) and not params.get("v") and extract_video_id(url) is None


def is_shorts_url(url: str) -> bool:
    """URL bir YouTube Shorts URL'si mi?"""
    try:
        parsed = urllib.parse.urlparse(url)
        return "shorts" in parsed.path.split("/")
    except Exception:
        return False


def shorten_youtube_url(url: str) -> str:
    """Video URL'sini kısa youtu.be formatına çevirir."""
    video_id = extract_video_id(url)
    if video_id:
        return f"https://youtu.be/{video_id}"
    return url


def validate_youtube_url(url: str) -> tuple[bool, str]:
    """
    URL'i doğrular. Shorts URL'leri de geçerli kabul edilir.
    Returns:
        (True, "")           → geçerli
        (False, "hata_msg")  → geçersiz
    """
    if not isinstance(url, str):
        return False, "URL string olmalı"

    url = url.strip()

    if not url:
        return False, "URL boş olamaz"

    if len(url) > 2048:
        return False, "URL çok uzun"

    if not re.match(r"^https?://", url):
        return False, "URL https:// veya http:// ile başlamalı"

    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        return False, "Geçersiz URL formatı"

    if parsed.netloc not in VALID_YT_DOMAINS:
        return False, f"Desteklenmeyen domain: {parsed.netloc}"

    if extract_video_id(url) is None:
        return False, "Video ID bulunamadı"

    return True, ""


def get_thumbnail_urls(video_id: str) -> list[str]:
    """Kaliteden yükseğe doğru thumbnail URL listesi döner."""
    if not video_id:
        return []
    base = f"https://img.youtube.com/vi/{video_id}"
    return [
        f"{base}/maxresdefault.jpg",
        f"{base}/sddefault.jpg",
        f"{base}/hqdefault.jpg",
        f"{base}/mqdefault.jpg",
        f"{base}/default.jpg",
    ]


def format_duration(seconds: int | None) -> str:
    """Saniyeyi okunabilir süre formatına çevirir."""
    if not seconds:
        return ""
    if seconds < 60:
        # Dilden bağımsız gösterim — "19 sn" yerine "0:19"
        return f"0:{seconds:02d}"
    if seconds < 3600:
        m, s = divmod(seconds, 60)
        return f"{m}:{s:02d}"
    h, r = divmod(seconds, 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}"


def parse_resolution(format_note: str | None) -> int | None:
    """'1080p' gibi bir string'den çözünürlük sayısını çıkarır."""
    if not format_note:
        return None
    match = re.search(r"(\d+)p", format_note)
    return int(match.group(1)) if match else None
