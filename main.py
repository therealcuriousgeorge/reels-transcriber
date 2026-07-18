#!/usr/bin/env python3
"""
main.py — Instagram Reel Summarizer CLI

Usage examples:

  # Summarize a public profile's reels → one combined Bear note
  python main.py --url https://www.instagram.com/username/reels/

  # Summarize a single reel
  python main.py --url https://www.instagram.com/reel/ABC123/

  # Summarize a list of reel URLs from a text file (one URL per line)
  python main.py --urls-file my_reels.txt

  # Create one Bear note per video instead of a combined note
  python main.py --urls-file my_reels.txt --individual

  # Use cookies from Chrome (needed for private/age-restricted content)
  python main.py --url https://www.instagram.com/username/ --cookies chrome

  # Export to Apple Notes instead of Bear
  python main.py --urls-file my_reels.txt --app apple_notes

  # Use a more accurate (but slower) Whisper model
  python main.py --urls-file my_reels.txt --whisper-model medium

  # Limit downloads from a profile page to 10 videos
  python main.py --url https://www.instagram.com/username/reels/ --limit 10
"""

import sys
from pathlib import Path

import click

import config
from downloader import download_from_url, download_from_url_list
from notes_exporter import (
    export_to_apple_notes_combined,
    export_to_apple_notes_individual,
    export_to_bear_combined,
    export_to_bear_individual,
)
from summarizer import Summarizer
from transcriber import Transcriber


@click.command()
@click.option("--url", default=None, help="Instagram profile or reel URL.")
@click.option(
    "--urls-file",
    default=None,
    type=click.Path(exists=True),
    help="Path to a text file with one Instagram URL per line.",
)
@click.option(
    "--app",
    default="bear",
    type=click.Choice(["bear", "apple_notes"], case_sensitive=False),
    show_default=True,
    help="Note-taking app to export summaries to.",
)
@click.option(
    "--combined/--individual",
    default=True,
    show_default=True,
    help="Create one combined note (default) or one note per video.",
)
@click.option(
    "--whisper-model",
    default=config.WHISPER_MODEL,
    show_default=True,
    help="Whisper model size: tiny | base | small | medium | large.",
)
@click.option(
    "--cookies",
    default=None,
    metavar="BROWSER",
    help="Browser to extract cookies from (e.g. chrome, firefox, safari).",
)
@click.option(
    "--limit",
    default=None,
    type=int,
    help="Max number of videos to download from a profile URL.",
)
@click.option(
    "--output-dir",
    default=str(config.OUTPUT_DIR),
    show_default=True,
    help="Directory to store downloaded videos and sidecar files.",
)
def main(url, urls_file, app, combined, whisper_model, cookies, limit, output_dir):
    """Download Instagram Reels, transcribe them, summarise with Claude, and save to Bear or Apple Notes."""

    if not url and not urls_file:
        raise click.UsageError("Provide --url or --urls-file.")

    output_path = Path(output_dir)

    # ── Step 1: Download ─────────────────────────────────────────────────────
    click.echo("━" * 60)
    click.echo("Step 1/3 — Downloading videos")
    click.echo("━" * 60)

    if urls_file:
        urls = Path(urls_file).read_text().splitlines()
        urls = [u.strip() for u in urls if u.strip() and not u.startswith("#")]
        click.echo(f"Found {len(urls)} URL(s) in {urls_file}")
        videos = download_from_url_list(
            urls,
            output_path,
            cookies_browser=cookies,
            delay=config.DOWNLOAD_DELAY,
        )
    else:
        videos = download_from_url(
            url,
            output_path,
            cookies_browser=cookies,
            limit=limit,
        )

    if not videos:
        click.echo("No videos downloaded. Check the URL and try again.", err=True)
        sys.exit(1)

    click.echo(f"\n✓ Downloaded {len(videos)} video(s).\n")

    # ── Step 2: Transcribe ───────────────────────────────────────────────────
    click.echo("━" * 60)
    click.echo("Step 2/3 — Transcribing audio")
    click.echo("━" * 60)

    transcriber = Transcriber(model_size=whisper_model)
    for video in videos:
        video["transcript"] = transcriber.transcribe(video["path"])

    click.echo(f"\n✓ Transcribed {len(videos)} video(s).\n")

    # ── Step 3: Summarize ────────────────────────────────────────────────────
    click.echo("━" * 60)
    click.echo("Step 3/3 — Summarizing with Claude")
    click.echo("━" * 60)

    summarizer = Summarizer(model=config.CLAUDE_MODEL)
    for video in videos:
        video["summary"] = summarizer.summarize(video)

    click.echo(f"\n✓ Summarized {len(videos)} video(s).\n")

    # ── Export ───────────────────────────────────────────────────────────────
    click.echo("━" * 60)
    click.echo(f"Exporting to {app.replace('_', ' ').title()}")
    click.echo("━" * 60)

    if app == "bear":
        if combined:
            export_to_bear_combined(videos, tags=config.BEAR_TAGS)
        else:
            export_to_bear_individual(videos, tags=config.BEAR_TAGS)
    else:
        if combined:
            export_to_apple_notes_combined(videos)
        else:
            export_to_apple_notes_individual(videos)


if __name__ == "__main__":
    main()
