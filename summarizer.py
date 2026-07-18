"""
summarizer.py — Summarizes Instagram videos using the Claude API.

Uses claude-opus-4-7 with:
  - Adaptive thinking for nuanced, high-quality summaries
  - Prompt caching on the system prompt (saves cost across a batch)
  - Streaming to avoid request timeouts on long transcripts
  - Sidecar .summary file caching so re-runs skip already-summarized videos
"""

from pathlib import Path

import anthropic

SYSTEM_PROMPT = """\
You are an expert content analyst specializing in social media video summaries.

Given an Instagram Reel's caption and its spoken transcript, produce a concise, \
engaging summary that captures:
- The core topic or message of the video
- Key points, tips, or insights shared
- The creator's tone and intent

Write 3–5 sentences in plain English. Do not use bullet points. \
Do not mention that this is an Instagram Reel. \
Do not start with "This video" or "In this video".\
"""


class Summarizer:
    """
    Wraps the Anthropic client and caches the system prompt for cost efficiency.

    The system prompt is marked with cache_control so it is only billed at
    full cost on the first request; subsequent requests read it from cache
    at ~10% of the normal input token cost.
    """

    def __init__(self, model: str = "claude-opus-4-7"):
        self._client = anthropic.Anthropic()
        self._model = model

    def summarize(self, video: dict) -> str:
        """
        Return a summary for a video dict.

        Reads from the .summary sidecar cache if available, otherwise calls
        the Claude API and writes the result to the sidecar file.
        """
        video_path: Path = video["path"]
        cache_file = video_path.with_suffix(".summary")

        if cache_file.exists():
            cached = cache_file.read_text(encoding="utf-8").strip()
            if cached:
                print(f"  [cache] Using existing summary for {video_path.name}")
                return cached

        print(f"  Summarizing {video_path.name} ...")

        description = video.get("description", "") or "(no caption)"
        transcript = video.get("transcript", "") or "(no transcript)"
        uploader = video.get("uploader", "") or "unknown creator"

        user_content = (
            f"Creator: {uploader}\n\n"
            f"Caption:\n{description}\n\n"
            f"Transcript:\n{transcript}"
        )

        try:
            # Use streaming + get_final_message() to handle long transcripts
            # without hitting HTTP timeouts.
            # cache_control on the system prompt ensures it is reused across
            # the entire batch at ~10% of normal input cost.
            with self._client.messages.stream(
                model=self._model,
                max_tokens=1024,
                thinking={"type": "adaptive"},
                system=[
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": user_content}],
            ) as stream:
                response = stream.get_final_message()

            summary = next(
                (block.text for block in response.content if block.type == "text"),
                "",
            ).strip()

        except anthropic.APIConnectionError:
            print("  Error: could not connect to the Anthropic API.")
            summary = ""
        except anthropic.AuthenticationError:
            raise SystemExit(
                "Anthropic API key is invalid. Set ANTHROPIC_API_KEY and retry."
            )
        except anthropic.APIStatusError as e:
            print(f"  API error {e.status_code}: {e.message}")
            summary = ""

        cache_file.write_text(summary, encoding="utf-8")
        return summary
