"""
downloader.py — Downloads Instagram videos and metadata using yt-dlp.

Supports:
  - A single Instagram URL (profile page, reel, or post)
  - A list of individual reel/post URLs

For each video, produces:
  - <id>.mp4 (or .webm) — the video file
  - <id>.info.json — full metadata (title, description, uploader, etc.)
  - <id>.description — caption/description text
"""

import json
import subprocess
import time
from pathlib import Path
from typing import Optional

VIDEO_EXTENSIONS = ["mp4", "webm", "mkv", "mov"]


def _build_yt_dlp_cmd(
    url: str,
    output_dir: Path,
    cookies_browser: Optional[str],
    limit: Optional[int],
) -> list[str]:
    cmd = [
        "yt-dlp",
        "--write-info-json",
        "--write-description",
        "--no-warnings",
        "-o", str(output_dir / "%(id)s.%(ext)s"),
    ]
    if cookies_browser:
        cmd += ["--cookies-from-browser", cookies_browser]
    if limit:
        cmd += ["--playlist-items", f"1:{limit}"]
    cmd.append(url)
    return cmd


def _collect_videos(output_dir: Path) -> list[dict]:
    """Scan output_dir for downloaded videos and parse their metadata."""
    videos = []
    for info_file in sorted(output_dir.glob("*.info.json")):
        try:
            with open(info_file) as f:
                info = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        video_id = info.get("id", info_file.stem.replace(".info", ""))

        # Find the actual video file
        video_path = None
        for ext in VIDEO_EXTENSIONS:
            candidate = output_dir / f"{video_id}.{ext}"
            if candidate.exists():
                video_path = candidate
                break

        if not video_path:
            continue

        # Prefer description from sidecar file, fall back to info.json field
        desc_file = output_dir / f"{video_id}.description"
        if desc_file.exists():
            description = desc_file.read_text(encoding="utf-8").strip()
        else:
            description = (info.get("description") or "").strip()

        videos.append({
            "id": video_id,
            "path": video_path,
            "description": description,
            "title": info.get("title", ""),
            "uploader": info.get("uploader", ""),
            "url": info.get("webpage_url", ""),
        })

    return videos


def download_from_url(
    url: str,
    output_dir: Path,
    cookies_browser: Optional[str] = None,
    limit: Optional[int] = None,
) -> list[dict]:
    """
    Download all videos from a single Instagram URL.

    Works for profiles (downloads all reels), individual reels, and posts.
    Pass limit=N to cap the number of videos downloaded from a profile.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = _build_yt_dlp_cmd(url, output_dir, cookies_browser, limit)

    print(f"Downloading from: {url}")
    result = subprocess.run(cmd, text=True)
    if result.returncode != 0:
        print(f"  yt-dlp exited with code {result.returncode} — some videos may have failed.")

    return _collect_videos(output_dir)


def download_from_url_list(
    urls: list[str],
    output_dir: Path,
    cookies_browser: Optional[str] = None,
    delay: float = 2.0,
) -> list[dict]:
    """
    Download videos from an explicit list of Instagram URLs, one at a time.

    Waits `delay` seconds between downloads to reduce rate-limiting risk.
    Already-downloaded videos (detected by existing .info.json) are skipped.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    for i, url in enumerate(urls):
        url = url.strip()
        if not url or url.startswith("#"):
            continue

        if i > 0:
            time.sleep(delay)

        cmd = _build_yt_dlp_cmd(url, output_dir, cookies_browser, limit=None)
        # Remove --no-playlist so a single reel URL is treated as one item
        cmd = ["yt-dlp", "--write-info-json", "--write-description",
               "--no-warnings", "--no-playlist",
               "-o", str(output_dir / "%(id)s.%(ext)s")]
        if cookies_browser:
            cmd += ["--cookies-from-browser", cookies_browser]
        cmd.append(url)

        print(f"[{i+1}/{len(urls)}] Downloading: {url}")
        result = subprocess.run(cmd, text=True)
        if result.returncode != 0:
            print(f"  Warning: yt-dlp exited {result.returncode} for {url}")

    return _collect_videos(output_dir)
