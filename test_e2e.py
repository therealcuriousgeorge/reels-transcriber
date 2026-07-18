#!/usr/bin/env python3
"""
test_e2e.py — End-to-end pipeline tests for ig-summarizer.

Stages tested:
  1. Imports        — all modules load without error
  2. CLI            — --help and missing-arg validation
  3. Downloader     — yt-dlp can reach a real public reel (network)
  4. Transcriber    — Whisper transcribes a synthetic 5-second audio clip
  5. Summarizer     — Claude API call with a short prompt (needs ANTHROPIC_API_KEY)
  6. Bear exporter  — URL is built correctly (Bear app not required)

Run with:
  python3 test_e2e.py
  python3 test_e2e.py --skip-download  # skip live Instagram download
  python3 test_e2e.py --skip-claude    # skip Claude API call
"""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
SKIP = "\033[93m○\033[0m"

results = []


def record(name: str, passed: bool, note: str = ""):
    results.append((name, passed, note))
    symbol = PASS if passed else FAIL
    suffix = f"  ({note})" if note else ""
    print(f"  {symbol} {name}{suffix}")


def section(title: str):
    print(f"\n{'━'*55}")
    print(f"  {title}")
    print(f"{'━'*55}")


# ── 1. Imports ────────────────────────────────────────────────────────────────
section("Stage 1 — Module imports")
try:
    import config          # noqa: E402
    import downloader      # noqa: E402
    import transcriber     # noqa: E402
    import notes_exporter  # noqa: E402
    import summarizer      # noqa: E402
    record("All project modules import", True)
except Exception as e:
    record("All project modules import", False, str(e))

try:
    import anthropic, whisper, click  # noqa: F401,E401
    record("Third-party packages (anthropic, whisper, click)", True)
except ImportError as e:
    record("Third-party packages (anthropic, whisper, click)", False, str(e))


# ── 2. CLI ────────────────────────────────────────────────────────────────────
section("Stage 2 — CLI")
try:
    from click.testing import CliRunner
    from main import main

    runner = CliRunner()

    r = runner.invoke(main, ["--help"])
    record("--help exits 0", r.exit_code == 0)

    r = runner.invoke(main, [])
    record("No args → UsageError (exit 2)", r.exit_code == 2)

    r = runner.invoke(main, ["--url", "https://example.com", "--app", "bad_app"])
    record("Bad --app value → error (exit 2)", r.exit_code == 2)

except Exception as e:
    record("CLI tests", False, str(e))


# ── 3. Downloader (live network) ──────────────────────────────────────────────
def test_downloader():
    section("Stage 3 — Downloader (live Instagram)")
    # A well-known public reel from Instagram's own account
    TEST_URL = "https://www.instagram.com/reel/C-example/"

    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir)
        result = subprocess.run(
            ["yt-dlp", "--simulate", "--no-warnings", TEST_URL],
            capture_output=True, text=True, timeout=30
        )
        ok = result.returncode == 0
        note = "" if ok else result.stderr.strip().splitlines()[-1] if result.stderr else "unknown error"
        record("yt-dlp --simulate on public reel", ok, note[:120])


# ── 4. Transcriber (synthetic audio) ─────────────────────────────────────────
def test_transcriber():
    section("Stage 4 — Transcriber (synthetic audio)")
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = Path(tmpdir) / "test_video.mp4"

        # Generate a 5-second silent video using ffmpeg
        r = subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "sine=frequency=440:duration=5",
            "-f", "lavfi", "-i", "color=c=black:size=320x240:duration=5",
            "-shortest", str(video_path)
        ], capture_output=True, text=True)

        if r.returncode != 0:
            record("ffmpeg generates synthetic video", False, "ffmpeg failed")
            return
        record("ffmpeg generates synthetic video", True)

        try:
            t = transcriber.Transcriber(model_size="tiny")
            transcript = t.transcribe(video_path)
            record("Whisper transcribes synthetic audio", True, f"{len(transcript)} chars returned")

            # Check sidecar cache was written
            cache = video_path.with_suffix(".transcript")
            record("Sidecar .transcript file written", cache.exists())

            # Second call should hit cache
            transcript2 = t.transcribe(video_path)
            record("Second call uses cache", transcript == transcript2)

        except Exception as e:
            record("Whisper transcription", False, str(e))


# ── 5. Summarizer (Claude API) ────────────────────────────────────────────────
def test_summarizer():
    section("Stage 5 — Summarizer (Claude API)")

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        record("ANTHROPIC_API_KEY is set", False, "export ANTHROPIC_API_KEY=sk-ant-... and re-run")
        return
    record("ANTHROPIC_API_KEY is set", True)

    with tempfile.TemporaryDirectory() as tmpdir:
        fake_video_path = Path(tmpdir) / "test.mp4"
        fake_video_path.touch()  # placeholder so cache path resolves

        fake_video = {
            "id": "test123",
            "path": fake_video_path,
            "description": "A quick tutorial on making sourdough bread at home.",
            "transcript": "Today I'm going to show you how I make my sourdough bread. "
                          "First, you need a starter that's been fed 8 hours ago. "
                          "Mix 450g flour with 350ml water and 100g starter, then let it rest.",
            "uploader": "testcreator",
            "url": "https://www.instagram.com/reel/test123/",
        }

        try:
            s = summarizer.Summarizer()
            summary = s.summarize(fake_video)
            ok = bool(summary and len(summary) > 20)
            record("Claude returns non-empty summary", ok, f"{len(summary)} chars")

            cache = fake_video_path.with_suffix(".summary")
            record("Sidecar .summary file written", cache.exists())

        except Exception as e:
            record("Claude API call", False, str(e))


# ── 6. Bear export ────────────────────────────────────────────────────────────
def test_bear_export():
    section("Stage 6 — Bear exporter (URL construction)")
    import urllib.parse

    fake_videos = [
        {
            "id": "abc123",
            "path": Path("/tmp/abc123.mp4"),
            "description": "Test caption",
            "transcript": "Test transcript text.",
            "summary": "A short test summary of the video content.",
            "uploader": "testuser",
            "url": "https://www.instagram.com/reel/abc123/",
        }
    ]

    try:
        # Intercept the subprocess.run call to avoid opening Bear
        import unittest.mock as mock

        opened_urls = []
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess([], 0)
            notes_exporter.export_to_bear_combined(fake_videos, tags="test")
            calls = [str(c) for c in mock_run.call_args_list]

        bear_call = next((c for c in calls if "bear://" in c), None)
        record("Bear URL constructed and subprocess.run called", bear_call is not None)

        if bear_call:
            # Extract URL from the call string
            start = bear_call.find("bear://")
            end = bear_call.find("'", start)
            url = bear_call[start:end] if end > start else bear_call[start:]
            parsed = urllib.parse.urlparse(url)
            qs = urllib.parse.parse_qs(parsed.query)
            record("Bear URL has 'title' param", "title" in qs)
            record("Bear URL has 'text' param", "text" in qs)
            record("Bear URL has 'tags' param", "tags" in qs)

    except Exception as e:
        record("Bear URL construction", False, str(e))


# ── Run ───────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--skip-download", action="store_true", help="Skip live Instagram download test")
parser.add_argument("--skip-claude", action="store_true", help="Skip Claude API test")
args = parser.parse_args()

if args.skip_download:
    section("Stage 3 — Downloader (live Instagram)")
    print(f"  {SKIP} Skipped (--skip-download)")
else:
    test_downloader()

test_transcriber()

if args.skip_claude:
    section("Stage 5 — Summarizer (Claude API)")
    print(f"  {SKIP} Skipped (--skip-claude)")
else:
    test_summarizer()

test_bear_export()

# ── Summary ───────────────────────────────────────────────────────────────────
section("Results")
passed = sum(1 for _, ok, _ in results if ok)
failed = sum(1 for _, ok, _ in results if not ok)
print(f"  {PASS} {passed} passed   {FAIL} {failed} failed\n")
sys.exit(0 if failed == 0 else 1)
