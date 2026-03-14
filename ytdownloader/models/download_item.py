# -*- coding: utf-8 -*-
"""
DownloadItem — tek bir indirme işleminin veri modeli.

dataclass(frozen=False) kullanıldı çünkü state güncellenmesi gerekiyor.
Thread'ler arası geçişte kopyası alınır (asdict ile).
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ytdownloader.models.download_state import DownloadState


@dataclass
class DownloadItem:
    """Tek bir indirme işlemini temsil eder."""

    # Kimlik
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    url: str = ""

    # Video bilgisi (fetch sonrası dolar)
    title: str = ""
    channel: str = ""
    duration: Optional[int] = None        # saniye
    thumbnail_url: str = ""
    video_id: str = ""

    # İndirme seçenekleri
    output_dir: str = ""
    format: str = "mp4"                   # "mp4" | "mp3"
    format_id: Optional[str] = None       # yt-dlp format kodu
    audio_quality: Optional[str] = None   # MP3 bitrate: "128", "192", "320"
    speed_limit: Optional[int] = None     # bytes/s, None = sınırsız

    # Durum
    state: DownloadState = DownloadState.PENDING

    # İlerleme
    progress: float = 0.0                 # 0.0 - 100.0
    speed: float = 0.0                    # bytes/saniye
    eta: Optional[int] = None             # saniye
    downloaded_bytes: int = 0
    total_bytes: int = 0

    # Dosya
    partial_file: str = ""
    final_file: str = ""

    # Zamanlama
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Hata
    error_message: str = ""
    retry_count: int = 0

    def to_dict(self) -> dict:
        """Thread'ler arası güvenli kopyalama için dict döner."""
        return {
            "id":              self.id,
            "url":             self.url,
            "title":           self.title,
            "channel":         self.channel,
            "duration":        self.duration,
            "state":           self.state.name,
            "progress":        self.progress,
            "speed":           self.speed,
            "eta":             self.eta,
            "downloaded_bytes": self.downloaded_bytes,
            "total_bytes":     self.total_bytes,
            "final_file":      self.final_file,
            "error_message":   self.error_message,
            "retry_count":     self.retry_count,
            "audio_quality":   self.audio_quality,
        }
