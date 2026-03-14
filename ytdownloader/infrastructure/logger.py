# -*- coding: utf-8 -*-
"""
AppLogger — merkezi loglama sistemi.
Hem konsola (renkli) hem dosyaya (rotating) yazar.
"""

import logging
import logging.handlers
import sys
from pathlib import Path


def setup_logger(log_dir: Path, level: int = logging.DEBUG) -> logging.Logger:
    """
    Uygulamanın tek logger'ını kurar ve döner.
    İki handler:
      - Konsol : DEBUG+ (renkli, CMD'de görünür)
      - Dosya  : DEBUG+ (rotating, max 5MB x 3)
    """
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("ytdownloader")
    if logger.handlers:          # tekrar çağrılırsa duplicate handler ekleme
        return logger

    logger.setLevel(level)

    # ── Konsol handler ────────────────────────────────────────────────────
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG)
    console.setFormatter(_ColorFormatter())
    logger.addHandler(console)

    # ── Dosya handler ─────────────────────────────────────────────────────
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=5 * 1024 * 1024,   # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "") -> logging.Logger:
    """
    Alt modüller için logger döner.
    Kullanım: log = get_logger(__name__)
    """
    base = "ytdownloader"
    return logging.getLogger(f"{base}.{name}" if name else base)


# ── Renkli konsol formatter ───────────────────────────────────────────────────

class _ColorFormatter(logging.Formatter):
    """Windows CMD ve Unix terminalinde renkli log çıktısı."""

    GREY   = "\033[90m"
    CYAN   = "\033[96m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    BOLD_RED = "\033[1;91m"
    RESET  = "\033[0m"

    FORMATS = {
        logging.DEBUG:    GREY    + "[DEBUG]   " + RESET + " %(message)s",
        logging.INFO:     CYAN    + "[INFO]    " + RESET + " %(message)s",
        logging.WARNING:  YELLOW  + "[UYARI]   " + RESET + " %(message)s",
        logging.ERROR:    RED     + "[HATA]    " + RESET + " %(message)s",
        logging.CRITICAL: BOLD_RED+ "[KRİTİK]  " + RESET + " %(message)s",
    }

    def __init__(self):
        super().__init__()
        # Windows'ta ANSI renk desteğini etkinleştir
        if sys.platform == "win32":
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                kernel32.SetConsoleMode(
                    kernel32.GetStdHandle(-11),
                    7  # ENABLE_PROCESSED_OUTPUT | ENABLE_WRAP_AT_EOL_OUTPUT | ENABLE_VIRTUAL_TERMINAL_PROCESSING
                )
            except Exception:
                pass

    def format(self, record: logging.LogRecord) -> str:
        fmt = self.FORMATS.get(record.levelno, self.FORMATS[logging.DEBUG])
        formatter = logging.Formatter(
            "%(asctime)s " + fmt,
            datefmt="%H:%M:%S",
        )
        return formatter.format(record)
