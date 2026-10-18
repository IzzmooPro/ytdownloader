# YouTube Downloader

A Windows desktop application focused on downloading YouTube videos and audio as MP4 / MP3, with a clean Turkish-language interface and a helper YouTube browser tab.

---

## Features

- Download video (MP4) and audio (MP3) from YouTube URLs
- Up to 5 simultaneous parallel downloads (default: 4)
- MP3 ID3 tag and cover art (thumbnail) embedding
- Dark / Light theme
- Windows toast notifications
- Automatic FFmpeg installation with SHA-256 verification (requires internet connection)
- In-app updates: new versions are downloaded, verified and installed with one click; the app restarts itself
- Automatic yt-dlp (download engine) updates in the background, checked daily; active after restart
- Drag & drop queue reordering
- Download speed graph and speed limiter
- Playlist support (select individual videos)
- Download history
- System tray integration
- Playlist / Mix selection support with searchable picking dialog

---

## Installation (End User)

1. Run `YouTube İndirici Setup.exe`
2. FFmpeg will be downloaded and installed automatically on first launch
3. That's it — no Python or additional dependencies required

---

## Developer Setup

**Requirements:**
- Python 3.11 – 3.13
- PyQt6, yt-dlp, certifi, mutagen

**Install dependencies:**
```bash
pip install pyqt6 yt-dlp certifi mutagen
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
├── core/           # Download engine and queue management
├── infrastructure/ # Settings, logging, event bus
├── models/         # Data models
├── services/       # Notification, update, audio services
├── ui/qt/          # Desktop UI components
└── assets/         # Icons
```

---

## License

Proprietary software. Unauthorized distribution or use is prohibited.
