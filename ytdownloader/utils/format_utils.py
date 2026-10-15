# -*- coding: utf-8 -*-
"""yt-dlp format listesinden çözünürlük → format_id seçimi (Qt'ye bağımlı değil)."""


def pick_video_formats(formats: list) -> dict[str, str]:
    """
    Her standart çözünürlük için indirilecek görüntü formatını seçer.
    Returns: {"1080p": "137", ...}
    """
    # Standart çözünürlükler — YouTube'un garip değerlerini en yakına yuvarla
    STANDARD = [144, 240, 360, 480, 720, 1080, 1440, 2160, 4320]

    def snap_to_standard(h):
        """Yüksekliği en yakın standart değere yuvarla (±20% tolerans)."""
        if not h:
            return None
        closest = min(STANDARD, key=lambda s: abs(s - h))
        # Tolerans: standart değerin %25'i kadar sapma kabul et
        if abs(closest - h) <= closest * 0.25:
            return closest
        return None

    res_map = {}   # "1080p" -> (format_id, sıralama anahtarı)
    for f in formats:
        h    = f.get("height") or 0
        fmt_id = f.get("format_id", "")
        vcodec = f.get("vcodec", "none")
        tbr    = f.get("tbr") or 0

        if not fmt_id or not h:
            continue
        if not vcodec or vcodec in ("none", ""):
            continue

        snapped = snap_to_standard(h)
        if snapped is None:
            continue

        key = f"{snapped}p"
        # Tercih sırası: H.264 (avc1) > yalnız-görüntü akışı > bitrate.
        # VP9/AV1 "MP4" dosyaları bazı TV/telefon/oynatıcılarda açılmaz;
        # YouTube 1080p ve altında H.264 sunar, 1440p/4K'da sunmaz —
        # orada otomatik olarak en iyi VP9/AV1 seçilir, çözünürlük kaybolmaz.
        # Sesli birleşik akışlar (ör. 18) +bestaudio ile çift ses izi üretir.
        rank = (
            str(vcodec).startswith("avc1"),
            f.get("acodec") in (None, "none"),
            tbr,
        )
        if key not in res_map or rank > res_map[key][1]:
            res_map[key] = (fmt_id, rank)


    return {k: v[0] for k, v in res_map.items()}
