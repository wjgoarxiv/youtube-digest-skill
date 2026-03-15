#!/usr/bin/env python3
"""Fetch YouTube transcript and metadata, output structured JSON.

Usage:
    python fetch_transcript.py "https://www.youtube.com/watch?v=VIDEO_ID" [-o output.json]
    python fetch_transcript.py "https://youtu.be/SHORT_ID" [-o output.json]

No pip packages required -- uses Python stdlib by default.
Optional: youtube-transcript-api, yt-dlp (pip install for enhanced extraction).
"""

import argparse
import json
import re
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET
from html import unescape
from pathlib import Path

_HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


def _decode_json_string(s: str) -> str:
    """Safely decode a JSON-escaped string (handles unicode, special chars)."""
    try:
        return json.loads(f'"{s}"')
    except (json.JSONDecodeError, ValueError):
        return s


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


# ---------------------------------------------------------------------------
# YouTube page fetching & InnerTube API (stdlib only)
# ---------------------------------------------------------------------------

_INNERTUBE_CONTEXT = {
    "client": {"clientName": "ANDROID", "clientVersion": "20.10.38"}
}


def _fetch_youtube_page(video_id: str) -> str:
    """Fetch YouTube watch page HTML using stdlib."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    req = urllib.request.Request(url, headers=_HTTP_HEADERS)
    resp = urllib.request.urlopen(req, timeout=15)
    return resp.read().decode("utf-8")


def _fetch_innertube_captions(video_id: str, page_html: str) -> list[dict]:
    """Fetch captionTracks via InnerTube ANDROID API (bypasses PoToken)."""
    # Extract API key from page HTML
    match = re.search(r'"INNERTUBE_API_KEY":\s*"([a-zA-Z0-9_-]+)"', page_html)
    if not match:
        raise RuntimeError("Could not find INNERTUBE_API_KEY in page")

    api_key = match.group(1)
    innertube_url = (
        f"https://www.youtube.com/youtubei/v1/player?key={api_key}"
    )
    payload = json.dumps({
        "context": _INNERTUBE_CONTEXT,
        "videoId": video_id,
    }).encode("utf-8")

    req = urllib.request.Request(
        innertube_url,
        data=payload,
        headers={**_HTTP_HEADERS, "Content-Type": "application/json"},
        method="POST",
    )
    resp = urllib.request.urlopen(req, timeout=15)
    data = json.loads(resp.read().decode("utf-8"))

    captions = data.get("captions", {})
    renderer = captions.get("playerCaptionsTracklistRenderer", {})
    tracks = renderer.get("captionTracks", [])
    if not tracks:
        raise RuntimeError("No captions available for this video")
    return tracks


def _parse_transcript_xml(xml_content: str) -> list[dict]:
    """Parse transcript XML, handling both formats:
    - Legacy: <text start="sec" dur="sec">
    - ANDROID: <p t="ms" d="ms"> inside <body>
    """
    root = ET.fromstring(xml_content)
    segments = []

    # Try ANDROID format: <body><p t="ms" d="ms">text</p></body>
    for elem in root.iter("p"):
        t = elem.get("t")
        d = elem.get("d")
        if t is not None:
            start_ms = float(t)
            dur_ms = float(d) if d else 0
            text = unescape(elem.text or "").strip()
            if text:
                segments.append({
                    "start": round(start_ms / 1000, 1),
                    "duration": round(dur_ms / 1000, 1),
                    "text": text,
                })

    if segments:
        return segments

    # Fallback: legacy format <text start="sec" dur="sec">
    for elem in root.iter("text"):
        start_time = float(elem.get("start", 0))
        dur = float(elem.get("dur", 0))
        text = unescape(elem.text or "").strip()
        if text:
            segments.append({
                "start": round(start_time, 1),
                "duration": round(dur, 1),
                "text": text,
            })

    return segments


# ---------------------------------------------------------------------------
# Transcript extraction -- stdlib (primary, zero dependencies)
# ---------------------------------------------------------------------------

def fetch_transcript_stdlib(
    video_id: str, language: str = "en", page_html: str | None = None
) -> tuple[list[dict], str]:
    """Fetch transcript using Python stdlib only. Returns (segments, page_html)."""
    if page_html is None:
        page_html = _fetch_youtube_page(video_id)

    tracks = _fetch_innertube_captions(video_id, page_html)

    # Find preferred language track, fall back to first available
    track_url = None
    for track in tracks:
        if track.get("languageCode") == language:
            track_url = track.get("baseUrl")
            break
    if not track_url:
        track_url = tracks[0].get("baseUrl")
    if not track_url:
        raise RuntimeError("No caption track URL found")

    # Fetch transcript XML
    req = urllib.request.Request(track_url, headers=_HTTP_HEADERS)
    resp = urllib.request.urlopen(req, timeout=15)
    xml_content = resp.read().decode("utf-8")

    segments = _parse_transcript_xml(xml_content)
    if not segments:
        raise RuntimeError("Transcript XML contained no text segments")

    return segments, page_html


# ---------------------------------------------------------------------------
# Transcript extraction -- youtube-transcript-api (optional enhancement)
# ---------------------------------------------------------------------------

def fetch_transcript_api(video_id: str, language: str = "en") -> list[dict]:
    """Fetch transcript using youtube-transcript-api (if installed)."""
    from youtube_transcript_api import YouTubeTranscriptApi

    ytt = YouTubeTranscriptApi()
    try:
        transcript = ytt.fetch(video_id, languages=[language, "en"])
    except Exception:
        transcript = ytt.fetch(video_id)

    return [
        {
            "start": round(s.start, 1),
            "duration": round(s.duration, 1),
            "text": s.text,
        }
        for s in transcript
    ]


# ---------------------------------------------------------------------------
# Metadata extraction
# ---------------------------------------------------------------------------

def fetch_metadata_from_page(html: str) -> dict:
    """Extract video metadata from YouTube page HTML (no yt-dlp needed)."""
    metadata = {}
    field_patterns = {
        "title": r'"title":\s*"((?:[^"\\]|\\.)*)"',
        "channel": r'"ownerChannelName":\s*"((?:[^"\\]|\\.)*)"',
        "lengthSeconds": r'"lengthSeconds":\s*"(\d+)"',
        "upload_date": r'"uploadDate":\s*"([^"]*)"',
        "view_count": r'"viewCount":\s*"(\d+)"',
        "description": r'"shortDescription":\s*"((?:[^"\\]|\\.)*)"',
    }

    for key, pattern in field_patterns.items():
        match = re.search(pattern, html)
        if not match:
            continue
        val = match.group(1)

        if key in ("title", "channel", "description"):
            val = _decode_json_string(val)
        if key == "description":
            val = val[:500]
            metadata["description"] = val
        elif key == "lengthSeconds":
            metadata["duration"] = int(val)
        elif key == "view_count":
            metadata["view_count"] = int(val)
        elif key == "upload_date":
            metadata["upload_date"] = val.replace("-", "")
        else:
            metadata[key] = val

    return metadata


def fetch_metadata_ytdlp(video_id: str) -> dict:
    """Fetch video metadata using yt-dlp (if available)."""
    try:
        result = subprocess.run(
            [
                "yt-dlp", "--dump-json", "--no-download",
                f"https://www.youtube.com/watch?v={video_id}",
            ],
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
    except (FileNotFoundError, Exception):
        return {}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Fetch YouTube transcript + metadata (no pip packages required)"
    )
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument("-o", "--output", help="Output JSON file (default: stdout)")
    parser.add_argument(
        "-l", "--language", default="en",
        help="Preferred transcript language (default: en)",
    )
    args = parser.parse_args()

    video_id = extract_video_id(args.url)
    page_html = None

    # --- Transcript: try youtube-transcript-api → stdlib fallback -----------
    transcript_source = None
    segments = None

    try:
        segments = fetch_transcript_api(video_id, args.language)
        transcript_source = "youtube-transcript-api"
    except ImportError:
        pass  # Not installed -- fall through to stdlib
    except Exception as e:
        print(f"WARN: youtube-transcript-api failed: {e}", file=sys.stderr)

    if segments is None:
        try:
            segments, page_html = fetch_transcript_stdlib(video_id, args.language)
            transcript_source = "stdlib"
        except Exception as e:
            print(f"ERROR: Could not fetch transcript: {e}", file=sys.stderr)
            sys.exit(1)

    segments = clean_transcript(segments)

    # --- Metadata: try yt-dlp → page HTML fallback -------------------------
    metadata = fetch_metadata_ytdlp(video_id)

    if not metadata:
        if page_html is None:
            try:
                page_html = _fetch_youtube_page(video_id)
            except Exception:
                page_html = ""
        metadata = fetch_metadata_from_page(page_html)

    # --- Build output -------------------------------------------------------
    output = {
        "video_id": video_id,
        "url": args.url,
        "transcript_source": transcript_source,
        "metadata": metadata,
        "segments": segments,
        "total_segments": len(segments),
    }

    if metadata.get("duration"):
        output["metadata"]["duration_formatted"] = format_timestamp(
            metadata["duration"]
        )

    result = json.dumps(output, ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).write_text(result)
        print(f"Saved to {args.output}", file=sys.stderr)
    else:
        print(result)


if __name__ == "__main__":
    main()
