"""
notes_exporter.py — Exports video summaries to Bear Notes or Apple Notes.

Bear: uses the bear:// URL scheme (Bear must be installed and running).
Apple Notes: uses osascript/AppleScript (plain text only, no Markdown).

Two export modes:
  combined  — one note containing all video summaries (best for batches)
  individual — one note per video
"""

import subprocess
import urllib.parse
from datetime import datetime
from typing import List


# ---------------------------------------------------------------------------
# Bear
# ---------------------------------------------------------------------------

def _bear_create(title: str, body: str, tags: str) -> None:
    """Open a Bear create URL to create a new note."""
    params = urllib.parse.urlencode(
        {"title": title, "text": body, "tags": tags, "open_note": "no"},
        quote_via=urllib.parse.quote,
    )
    subprocess.run(["open", f"bear://x-callback-url/create?{params}"], check=True)


def _format_bear_video_block(video: dict, index: int, total: int) -> str:
    """Format a single video as a Markdown section for a Bear note."""
    uploader = video.get("uploader") or "unknown"
    url = video.get("url") or ""
    description = (video.get("description") or "").strip()
    summary = (video.get("summary") or "*(no summary)*").strip()
    transcript = (video.get("transcript") or "").strip()

    lines = [f"## {index}/{total} — @{uploader}"]
    if url:
        lines.append(f"[View on Instagram]({url})\n")
    lines.append(f"**Summary**\n{summary}")
    if description:
        lines.append(f"\n**Caption**\n{description}")
    if transcript:
        lines.append(f"\n**Transcript**\n{transcript}")
    return "\n\n".join(lines)


def export_to_bear_combined(videos: List[dict], tags: str = "instagram,video-summary") -> None:
    """Create a single Bear note containing summaries of all videos."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    title = f"Instagram Summaries — {now}"

    sections = [
        _format_bear_video_block(v, i + 1, len(videos))
        for i, v in enumerate(videos)
    ]
    body = f"# {title}\n\n" + "\n\n---\n\n".join(sections)

    print(f"\nCreating combined Bear note: "{title}"")
    _bear_create(title, body, tags)
    print("Done — check Bear.")


def export_to_bear_individual(videos: List[dict], tags: str = "instagram,video-summary") -> None:
    """Create one Bear note per video."""
    for i, video in enumerate(videos):
        uploader = video.get("uploader") or "unknown"
        video_id = video.get("id", f"video-{i+1}")
        title = f"@{uploader} — {video_id}"
        body = _format_bear_video_block(video, 1, 1)

        print(f"  Creating Bear note: "{title}"")
        _bear_create(title, body, tags)

    print(f"\nCreated {len(videos)} Bear note(s).")


# ---------------------------------------------------------------------------
# Apple Notes
# ---------------------------------------------------------------------------

def _apple_notes_create(title: str, body: str) -> None:
    """Create a note in Apple Notes via AppleScript (plain text)."""
    # Escape double quotes and backslashes for AppleScript
    safe_title = title.replace("\\", "\\\\").replace('"', '\\"')
    safe_body = body.replace("\\", "\\\\").replace('"', '\\"')

    script = f'''
    tell application "Notes"
        tell account "iCloud"
            make new note with properties {{name:"{safe_title}", body:"{safe_body}"}}
        end tell
    end tell
    '''
    subprocess.run(["osascript", "-e", script], check=True)


def _format_apple_notes_video_block(video: dict, index: int, total: int) -> str:
    uploader = video.get("uploader") or "unknown"
    url = video.get("url") or ""
    description = (video.get("description") or "").strip()
    summary = (video.get("summary") or "(no summary)").strip()
    transcript = (video.get("transcript") or "").strip()

    parts = [f"[{index}/{total}] @{uploader}"]
    if url:
        parts.append(f"URL: {url}")
    parts.append(f"\nSummary:\n{summary}")
    if description:
        parts.append(f"\nCaption:\n{description}")
    if transcript:
        parts.append(f"\nTranscript:\n{transcript}")
    return "\n".join(parts)


def export_to_apple_notes_combined(videos: List[dict]) -> None:
    """Create a single Apple Note containing summaries of all videos."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    title = f"Instagram Summaries — {now}"

    sections = [
        _format_apple_notes_video_block(v, i + 1, len(videos))
        for i, v in enumerate(videos)
    ]
    body = "\n\n---\n\n".join(sections)

    print(f"\nCreating Apple Note: "{title}"")
    _apple_notes_create(title, body)
    print("Done — check Apple Notes.")


def export_to_apple_notes_individual(videos: List[dict]) -> None:
    """Create one Apple Note per video."""
    for i, video in enumerate(videos):
        uploader = video.get("uploader") or "unknown"
        video_id = video.get("id", f"video-{i+1}")
        title = f"@{uploader} — {video_id}"
        body = _format_apple_notes_video_block(video, 1, 1)

        print(f"  Creating Apple Note: "{title}"")
        _apple_notes_create(title, body)

    print(f"\nCreated {len(videos)} Apple Note(s).")
