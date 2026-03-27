# YouTube Downloader

A Windows desktop application for downloading YouTube videos as MP4 and MP3, featuring a clean Turkish-language interface.

---

## Features

- Download video (MP4) and audio (MP3) from YouTube URLs
- Up to 8 simultaneous parallel downloads
- MP3 ID3 tag and cover art (thumbnail) embedding
- Dark / Light theme
- Windows toast notifications
- Automatic FFmpeg installation (requires internet connection)
- Drag & drop queue reordering
- Download speed graph and speed limiter
- Playlist support (select individual videos)
- Download history
- System tray integration

---

## Installation (End User)

1. Run `YouTube İndirici Setup.exe`
2. FFmpeg will be downloaded and installed automatically on first launch
3. That's it — no Python or additional dependencies required

---

## Developer Setup

**Requirements:**
- Python 3.11 – 3.13
- PyQt6, yt-dlp, mutagen, requests, certifi

**Install dependencies:**
```bash
pip install pyqt6 yt-dlp mutagen requests certifi
```

**Run:**
```bash
python main.py
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| UI | PyQt6 |
| Downloading | yt-dlp |
| Audio processing | FFmpeg, mutagen |
| Packaging | PyInstaller |
| Platform | Windows 10 / 11 |

---

## Project Structure

```
ytdownloader/
├── core/           # Download engine and thread management
├── infrastructure/ # Settings, logging, event bus
├── models/         # Data models
├── services/       # Notification, update, audio services
├── ui/qt/          # All UI components
└── assets/         # Icons and FFmpeg
```

---

## License

Proprietary software. Unauthorized distribution or use is prohibited.
