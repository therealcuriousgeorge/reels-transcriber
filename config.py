from pathlib import Path

# Directory where downloaded videos and sidecar files are stored
OUTPUT_DIR = Path.home() / "ig-summarizer-downloads"

# Whisper model size: "base" is fastest, "large" is most accurate
# Options: tiny | base | small | medium | large
WHISPER_MODEL = "base"

# Claude model used for summarization
CLAUDE_MODEL = "claude-opus-4-7"

# Tags applied to every Bear note (comma-separated, no # prefix needed)
BEAR_TAGS = "instagram,video-summary"

# Seconds to wait between yt-dlp downloads to avoid rate limiting
DOWNLOAD_DELAY = 2.0
