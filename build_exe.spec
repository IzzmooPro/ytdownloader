# -*- mode: python ; coding: utf-8 -*-
# YouTube İndirici — PyInstaller build spec
# Kullanım: python -m PyInstaller build_exe.spec --noconfirm

import sys
import os
from pathlib import Path

block_cipher = None
app_name = "YouTube Indirici"

# Proje kökü (bu spec dosyasının bulunduğu yer)
ROOT = Path(SPECPATH)

datas = [
    # SVG ikonlar
    (str(ROOT / "ytdownloader" / "assets" / "icons" / "svg"), "ytdownloader/assets/icons/svg"),
]

# FFmpeg binary'leri — exe içine göm
ffmpeg_dir = ROOT / "ytdownloader" / "assets" / "ffmpeg"
ffmpeg_binaries = []
for exe_name in ["ffmpeg.exe", "ffprobe.exe", "ffplay.exe"]:
    exe_path = ffmpeg_dir / exe_name
    if exe_path.exists():
        ffmpeg_binaries.append((str(exe_path), "ytdownloader/assets/ffmpeg"))
    else:
        print(f"UYARI: {exe_name} bulunamadı — EXE'ye dahil edilmedi!")

# Python DLL — hedef PC'de Python kurulu olmasa bile çalışsın
python_binaries = []
python_dir = Path(sys.exec_prefix)

# python3xx.dll — ana runtime DLL
for dll_pattern in ["python3*.dll", "python*.dll"]:
    import glob
    for dll_path in glob.glob(str(python_dir / dll_pattern)):
        dll_name = Path(dll_path).name
        python_binaries.append((dll_path, "."))
        print(f"Python DLL eklendi: {dll_name}")

# MSVC runtime DLL'leri (vcruntime, msvcp vb.)
sys32 = Path(os.environ.get("SystemRoot", "C:\\Windows")) / "System32"
for vcrt in ["vcruntime140.dll", "vcruntime140_1.dll", "msvcp140.dll", "concrt140.dll"]:
    vcrt_path = sys32 / vcrt
    if vcrt_path.exists():
        python_binaries.append((str(vcrt_path), "."))
        print(f"MSVC DLL eklendi: {vcrt}")

hiddenimports = [
    # yt-dlp
    "yt_dlp",
    "yt_dlp.extractor",
    "yt_dlp.extractor.youtube",
    "yt_dlp.postprocessor",
    "yt_dlp.postprocessor.ffmpeg",
    "yt_dlp.cookies",
    "yt_dlp.networking",
    "yt_dlp.networking.common",
    # PyQt6 WebEngine
    "PyQt6.QtWebEngineWidgets",
    "PyQt6.QtWebEngineCore",
    "PyQt6.QtWebChannel",
    "PyQt6.QtWebEngineQuick",
    # Network
    "certifi",
    "urllib3",
    "charset_normalizer",
    "requests",
    # Media
    "mutagen",
    "mutagen.mp3",
    "mutagen.mp4",
    # Other
    "winsound",
    "json",
    "threading",
    "concurrent.futures",
]

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT), str(ROOT / "ytdownloader")],
    binaries=ffmpeg_binaries + python_binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "numpy",
        "pandas",
        "PIL",
        "scipy",
        "IPython",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,             # UPX DLL'leri bozabilir — kapalı
    console=True,          # Hata ayıklama için geçici olarak True
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='ytdownloader/assets/icons/app.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=app_name,
)
