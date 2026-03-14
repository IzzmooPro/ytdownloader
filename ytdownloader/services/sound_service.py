# -*- coding: utf-8 -*-
"""
SoundService — İndirme tamamlanınca ses bildirimi.
Windows: winsound (built-in)
macOS  : afplay (built-in)
Linux  : paplay / aplay (built-in)
"""

import sys
import threading
from ytdownloader.infrastructure.logger import get_logger

log = get_logger("sound_service")


def play_complete():
    """İndirme tamamlandı sesi — arka planda çalar, programı bloklamaz."""
    threading.Thread(target=_play, daemon=True).start()


def play_error():
    """Hata sesi."""
    threading.Thread(target=_play_error, daemon=True).start()


def _play():
    try:
        if sys.platform == "win32":
            import winsound
            # Windows built-in "Asterisk" sistem sesi
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        elif sys.platform == "darwin":
            import subprocess
            subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"],
                           capture_output=True)
        else:
            # Linux — paplay veya aplay
            import subprocess
            for cmd in [
                ["paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga"],
                ["aplay", "/usr/share/sounds/freedesktop/stereo/complete.oga"],
            ]:
                try:
                    subprocess.run(cmd, capture_output=True, timeout=3)
                    break
                except FileNotFoundError:
                    continue
    except Exception as e:
        log.debug(f"Ses çalınamadı: {e}")


def _play_error():
    try:
        if sys.platform == "win32":
            import winsound
            winsound.MessageBeep(winsound.MB_ICONHAND)
        elif sys.platform == "darwin":
            import subprocess
            subprocess.run(["afplay", "/System/Library/Sounds/Basso.aiff"],
                           capture_output=True)
        else:
            import subprocess
            for cmd in [
                ["paplay", "/usr/share/sounds/freedesktop/stereo/dialog-error.oga"],
                ["aplay", "/usr/share/sounds/freedesktop/stereo/dialog-error.oga"],
            ]:
                try:
                    subprocess.run(cmd, capture_output=True, timeout=3)
                    break
                except FileNotFoundError:
                    continue
    except Exception as e:
        log.debug(f"Hata sesi çalınamadı: {e}")
