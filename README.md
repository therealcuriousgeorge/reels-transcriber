# ig-summarizer

Download Instagram Reels, transcribe the audio with [Whisper](https://github.com/openai/whisper), summarize with [Claude](https://www.anthropic.com), and push the results straight into **Bear** or **Apple Notes**.

## How it works

```
Instagram URL / URL list
        ↓
   yt-dlp (download video + caption)
        ↓
   Whisper (transcribe audio)
        ↓
   Claude claude-opus-4-7 (summarize)
        ↓
   Bear Notes / Apple Notes
```

## Setup

### 1. Install system dependencies

```bash
brew install ffmpeg yt-dlp
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

> Python 3.10+ recommended.

### 3. Set your Anthropic API key

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

Add it to your `~/.zshrc` or `~/.zprofile` to persist it.

## Usage

### Summarize a single Reel

```bash
python main.py --url https://www.instagram.com/reel/ABC123/
```

### Summarize all Reels from a profile

```bash
python main.py --url https://www.instagram.com/username/reels/ --limit 20
```

### Summarize a saved list of URLs

Create a text file with one URL per line (lines starting with `#` are ignored):

```
# my saved reels
https://www.instagram.com/reel/ABC123/
https://www.instagram.com/reel/DEF456/
```

Then run:

```bash
python main.py --urls-file my_reels.txt
```

### One note per video instead of a combined note

```bash
python main.py --urls-file my_reels.txt --individual
```

### Export to Apple Notes

```bash
python main.py --urls-file my_reels.txt --app apple_notes
```

### Use a more accurate Whisper model

```bash
python main.py --urls-file my_reels.txt --whisper-model medium
```

| Model  | Speed  | Accuracy |
|--------|--------|----------|
| tiny   | fastest | lowest  |
| base   | fast    | good    |
| small  | medium  | better  |
| medium | slow    | great   |
| large  | slowest | best    |

### Private or age-restricted content

Pass your browser name to extract session cookies:

```bash
python main.py --url https://www.instagram.com/username/ --cookies chrome
```

Supported browsers: `chrome`, `firefox`, `safari`, `edge`.

## All options

```
Options:
  --url TEXT                  Instagram profile or reel URL.
  --urls-file PATH            Text file with one Instagram URL per line.
  --app [bear|apple_notes]    Note-taking app to export to.  [default: bear]
  --combined / --individual   One combined note or one note per video.  [default: combined]
  --whisper-model TEXT        Whisper model size.  [default: base]
  --cookies BROWSER           Browser to extract cookies from.
  --limit INTEGER             Max videos to download from a profile URL.
  --output-dir PATH           Directory for downloaded videos.  [default: ~/ig-summarizer-downloads]
  --help                      Show this message and exit.
```

## Caching

Downloaded videos, transcripts (`.transcript`), and summaries (`.summary`) are saved as sidecar files next to each video in `~/ig-summarizer-downloads/`. Re-running the tool skips already-processed videos automatically.

## Notes on Instagram

- **Public profiles** work without cookies.
- **Private profiles / saved collections** require `--cookies <browser>` with a logged-in session.
- Instagram rate-limits aggressively — a 2-second delay between downloads is applied by default.
- Instagram does not have official "playlists". To use a saved collection, export the URLs manually into a `--urls-file`.
