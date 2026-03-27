# -*- coding: utf-8 -*-
"""
FFmpeg otomatik indirici — paralel yarış sistemi.

Tüm kaynaklar aynı anda başlar, ilk tamamlanan kazanır.
Diğerleri otomatik iptal edilir.
"""

import os
import threading
import zipfile
import urllib.request
from pathlib import Path

FFMPEG_URLS = [
    # GitHub BtbN — genellikle hızlı
    "https://github.com/BtbN/ffmpeg-builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
    # gyan.dev — Avrupa mirror
    "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
    # GyanD GitHub essentials (~30MB — en küçük)
    "https://github.com/GyanD/codexffmpeg/releases/download/7.1/ffmpeg-7.1-essentials_build.zip",
]

APPROX_SIZE_BYTES = 75 * 1024 * 1024  # fallback


def _get_install_dir(base_path: Path) -> Path:
    """
    FFmpeg kurulum dizini.
    Program Files gibi kısıtlı dizinlerde izin hatası almamak için
    her zaman APPDATA altına yükler — orası her kullanıcı için yazılabilir.
    """
    appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
    return Path(appdata) / "MyYouTubeDownloader" / "ffmpeg"


def is_installed_locally(base_path) -> bool:
    bp = Path(base_path)
    ffmpeg_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    for d in [
        bp / "bin",
        bp / "ytdownloader" / "assets" / "ffmpeg",
        bp / "assets" / "ffmpeg",
    ]:
        if (d / ffmpeg_name).exists():
            return True
    return False


def download_and_install(base_path, progress_callback=None, done_callback=None):
    """
    Tüm kaynakları paralel başlatır.
    İlk başarılı olan diğerlerini iptal eder.
    """
    base_path   = Path(base_path)
    install_dir = _get_install_dir(base_path)
    install_dir.mkdir(parents=True, exist_ok=True)

    winner_lock  = threading.Lock()
    winner_found = threading.Event()
    active_count = [len(FFMPEG_URLS)]
    last_errors  = {}

    def _cleanup(path):
        try:
            if Path(path).exists():
                Path(path).unlink()
        except Exception:
            pass

    def _short_name(url):
        if "BtbN" in url:   return "GitHub BtbN"
        if "gyan.dev" in url: return "gyan.dev"
        if "GyanD" in url:  return "GitHub GyanD"
        return "mirror"

    # Hangi thread progress güncelleyebilir — sadece en hızlı bağlanan
    lead_thread_id = [None]
    lead_lock      = threading.Lock()

    def _race_worker(url, idx):
        tmp_zip = install_dir / f"_ffmpeg_tmp_{idx}.zip"
        try:
            if winner_found.is_set():
                return

            req  = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            })
            resp = urllib.request.urlopen(req, timeout=30)

            if winner_found.is_set():
                resp.close()
                return

            # İlk bağlanan thread lead olur — sadece o progress gösterir
            with lead_lock:
                if lead_thread_id[0] is None:
                    lead_thread_id[0] = idx
            is_lead = (lead_thread_id[0] == idx)

            total      = int(resp.headers.get("Content-Length", 0)) or APPROX_SIZE_BYTES
            downloaded = 0
            chunk      = 1024 * 1024  # 1 MB

            with open(tmp_zip, "wb") as f:
                while True:
                    if winner_found.is_set():
                        resp.close()
                        _cleanup(tmp_zip)
                        return
                    data = resp.read(chunk)
                    if not data:
                        break
                    f.write(data)
                    downloaded += len(data)
                    if is_lead and progress_callback and not winner_found.is_set():
                        pct      = min(78, 5 + int(downloaded * 73 / total))
                        mb_dl    = downloaded / 1024 / 1024
                        mb_total = total / 1024 / 1024
                        progress_callback(
                            pct,
                            f"İndiriliyor...  {mb_dl:.1f} / {mb_total:.0f} MB"
                        )
            resp.close()

            # Kazananı belirle
            with winner_lock:
                if winner_found.is_set():
                    _cleanup(tmp_zip)
                    return
                winner_found.set()

            # Çıkart
            if progress_callback:
                progress_callback(82, "Çıkartılıyor...")

            exe_names = {"ffmpeg.exe", "ffprobe.exe", "ffplay.exe"}
            found = set()
            with zipfile.ZipFile(tmp_zip, "r") as zf:
                for member in zf.namelist():
                    fname = Path(member).name
                    if fname in exe_names:
                        dest = install_dir / fname
                        dest.write_bytes(zf.read(member))
                        found.add(fname)
                        if progress_callback:
                            progress_callback(
                                85 + len(found) * 4,
                                f"{fname} kuruldu ({len(found)}/3)"
                            )
            _cleanup(tmp_zip)

            if (install_dir / "ffmpeg.exe").exists():
                if progress_callback:
                    progress_callback(100, "✓ FFmpeg kuruldu!")
                if done_callback:
                    done_callback(True, str(install_dir))
            else:
                if done_callback:
                    done_callback(False, "ffmpeg.exe zip içinde bulunamadı")

        except Exception as e:
            last_errors[idx] = str(e)
            _cleanup(tmp_zip)
            with winner_lock:
                active_count[0] -= 1
                remaining = active_count[0]
            if remaining == 0 and not winner_found.is_set():
                summary = " | ".join(
                    f"K{i+1}: {m[:35]}" for i, m in last_errors.items()
                )
                if done_callback:
                    done_callback(False, f"Tüm kaynaklar başarısız: {summary}")

    def _main():
        if progress_callback:
            progress_callback(2, "Bağlanıyor...")
        for i, url in enumerate(FFMPEG_URLS):
            threading.Thread(target=_race_worker, args=(url, i), daemon=True).start()

    threading.Thread(target=_main, daemon=True).start()
