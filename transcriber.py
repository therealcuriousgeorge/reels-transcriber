"""
transcriber.py — Transcribes video audio using OpenAI Whisper.

Results are cached as <video_id>.transcript sidecar files next to the video,
so re-runs skip already-transcribed videos without loading Whisper again.
"""

from pathlib import Path
from typing import Optional


class Transcriber:
    """Loads a Whisper model once and reuses it across multiple videos."""

    def __init__(self, model_size: str = "base"):
        print(f"Loading Whisper model ({model_size})...")
        import whisper  # imported here so the CLI can load fast without it
        self._model = whisper.load_model(model_size)
        print("Whisper ready.\n")

    def transcribe(self, video_path: Path) -> str:
        """
        Return the transcript for a video, loading from the sidecar cache
        if it already exists.

        The sidecar file is stored as <video_path>.transcript alongside the
        video so the cache survives between runs.
        """
        cache_file = video_path.with_suffix(".transcript")

        if cache_file.exists():
            cached = cache_file.read_text(encoding="utf-8").strip()
            if cached:
                print(f"  [cache] Using existing transcript for {video_path.name}")
                return cached

        print(f"  Transcribing {video_path.name} ...")
        try:
            result = self._model.transcribe(str(video_path))
            transcript = result["text"].strip()
        except Exception as e:
            print(f"  Warning: transcription failed for {video_path.name}: {e}")
            transcript = ""

        # Write cache even if empty so we don't retry a broken file
        cache_file.write_text(transcript, encoding="utf-8")
        return transcript
