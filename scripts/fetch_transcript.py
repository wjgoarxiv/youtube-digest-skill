#!/usr/bin/env python3
"""Fetch YouTube transcript and metadata, output structured JSON.

Usage:
    python fetch_transcript.py "https://www.youtube.com/watch?v=VIDEO_ID" [-o output.json]
    python fetch_transcript.py "https://youtu.be/SHORT_ID" [-o output.json]

Dependencies:
    Required: youtube-transcript-api (pip install youtube-transcript-api)
    Optional: yt-dlp (pip install yt-dlp) -- for rich metadata
    Fallback: markitdown[youtube-transcription] -- if transcript-api fails
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def extract_video_id(url: str) -> str:
    """Extract video ID from various YouTube URL formats."""
    patterns = [
        r'(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})',
        r'(?:embed/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Could not extract video ID from: {url}")


def fetch_transcript(video_id: str, language: str = "en") -> list[dict]:
    """Fetch transcript using youtube-transcript-api."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        print("ERROR: youtube-transcript-api not installed.", file=sys.stderr)
        print("  pip install youtube-transcript-api", file=sys.stderr)
        sys.exit(1)

    try:
        segments = YouTubeTranscriptApi.get_transcript(video_id, languages=[language, "en"])
    except Exception:
        # Try without language preference (get whatever is available)
        try:
            segments = YouTubeTranscriptApi.get_transcript(video_id)
        except Exception as e:
            raise RuntimeError(f"Could not fetch transcript: {e}")

    return [
        {
            "start": round(s["start"], 1),
            "duration": round(s["duration"], 1),
            "text": s["text"],
        }
        for s in segments
    ]


def fetch_transcript_markitdown(url: str) -> list[dict]:
    """Fallback: fetch transcript using markitdown."""
    try:
        from markitdown import MarkItDown
        md = MarkItDown()
        result = md.convert(url)
        # markitdown returns flat text without timestamps
        return [{"start": 0, "duration": 0, "text": result.text_content}]
    except Exception as e:
        raise RuntimeError(f"markitdown fallback failed: {e}")


def fetch_metadata(video_id: str) -> dict:
    """Fetch video metadata using yt-dlp (if available)."""
    try:
        result = subprocess.run(
            ["yt-dlp", "--dump-json", "--no-download", f"https://www.youtube.com/watch?v={video_id}"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return {}
        data = json.loads(result.stdout)
        return {
            "title": data.get("title", ""),
            "channel": data.get("channel", data.get("uploader", "")),
            "duration": data.get("duration", 0),
            "upload_date": data.get("upload_date", ""),
            "description": data.get("description", "")[:500],
            "view_count": data.get("view_count", 0),
            "chapters": data.get("chapters") or [],
            "language": data.get("language", ""),
            "is_live": data.get("is_live", False),
            "tags": data.get("tags", [])[:10],
        }
    except FileNotFoundError:
        # yt-dlp not installed
        return {}
    except Exception:
        return {}


def clean_transcript(segments: list[dict]) -> list[dict]:
    """Clean auto-generated caption noise."""
    noise_patterns = re.compile(
        r'\[(?:Music|Applause|Laughter|음악|박수)\]', re.IGNORECASE
    )
    cleaned = []
    for seg in segments:
        text = noise_patterns.sub("", seg["text"]).strip()
        if text:
            cleaned.append({**seg, "text": text})
    return cleaned


def format_timestamp(seconds: float) -> str:
    """Convert seconds to HH:MM:SS or MM:SS format."""
    h, remainder = divmod(int(seconds), 3600)
    m, s = divmod(remainder, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def main():
    parser = argparse.ArgumentParser(description="Fetch YouTube transcript + metadata")
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument("-o", "--output", help="Output JSON file (default: stdout)")
    parser.add_argument("-l", "--language", default="en", help="Preferred transcript language")
    args = parser.parse_args()

    video_id = extract_video_id(args.url)

    # Fetch transcript
    try:
        segments = fetch_transcript(video_id, args.language)
        transcript_source = "youtube-transcript-api"
    except RuntimeError:
        try:
            segments = fetch_transcript_markitdown(args.url)
            transcript_source = "markitdown-fallback"
        except RuntimeError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)

    segments = clean_transcript(segments)

    # Fetch metadata
    metadata = fetch_metadata(video_id)

    # Build output
    output = {
        "video_id": video_id,
        "url": args.url,
        "transcript_source": transcript_source,
        "metadata": metadata,
        "segments": segments,
        "total_segments": len(segments),
    }

    # Add formatted duration
    if metadata.get("duration"):
        output["metadata"]["duration_formatted"] = format_timestamp(metadata["duration"])

    result = json.dumps(output, ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).write_text(result)
        print(f"Saved to {args.output}", file=sys.stderr)
    else:
        print(result)


if __name__ == "__main__":
    main()
