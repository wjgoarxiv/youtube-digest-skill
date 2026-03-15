---
name: youtube-digest
description: "Extracts transcripts from YouTube videos and produces structured digests with TL;DR, key takeaways, core assertions with timestamps, topic timeline, and notable quotes. Builds on markitdown's raw transcript extraction by adding LLM-driven analysis and structured output.\nTRIGGER when: user pastes a YouTube URL and wants a summary, digest, or analysis of the video content; user asks \"what is this video about\"; user wants key points or takeaways from a YouTube video; user wants to decide whether a video is worth watching; user asks to summarize a YouTube talk, lecture, podcast, or interview; user wants structured notes from a video; user asks to digest or break down a YouTube video; user mentions a YouTube link and asks for insights.\nDO NOT TRIGGER when: user just wants the raw transcript text without analysis (use markitdown); user wants to download the video file; user wants to convert a local video or audio file to text."
allowed-tools: [Read, Write, Edit, Bash]
---

# YouTube Video Digest

Transforms YouTube videos into structured, actionable knowledge. Where markitdown gives you the raw transcript, this skill gives you understanding -- TL;DR, key takeaways, timestamped assertions, topic timeline, and notable quotes.

## When to Use This Skill

- **Quick triage:** Decide whether a video is worth watching
- **Full digest:** Get structured notes from a talk, lecture, or podcast
- **Claim extraction:** Identify the speaker's core assertions with timestamps
- **Study notes:** Create PKM-ready notes (Obsidian, Notion) from educational videos
- **Multi-video comparison:** Compare key points across 2-5 related videos

## How It Works

Three-stage pipeline:

```
[YouTube URL] --> [Extract] --> [Analyze] --> [Format]
                    |               |             |
              fetch_transcript.py  Claude      Markdown
              (transcript +      (summarize,    output
               metadata)         structure)
```

**Stage 1 -- Extract:** Run `scripts/fetch_transcript.py` to get timestamped transcript segments and video metadata (title, channel, duration, date). Uses `youtube-transcript-api` with `yt-dlp` for metadata. Falls back to `markitdown` if primary method fails.

**Stage 2 -- Analyze:** Read the extracted JSON and produce the structured digest. This is the value-add over raw transcript -- synthesize, identify themes, extract claims, build the timeline.

**Stage 3 -- Format:** Write the final Markdown, optionally with Obsidian YAML frontmatter.

## Digest Output Structure

Follow this template (also in `assets/digest_template.md`). The order is intentional -- users who stop reading early still get maximum value.

```markdown
# [Video Title]

**Channel:** [name] | **Duration:** [HH:MM:SS] | **Published:** [date]
**URL:** [original link]

---

## TL;DR
[1-2 sentence summary of the entire video's core message]

## Key Takeaways
- [3-7 bullet points, each a complete standalone insight]

## Core Assertions & Claims
- [Claim 1] (at [timestamp])
- [Claim 2] (at [timestamp])
- [Flag any claims that are controversial or unsubstantiated]

## Topic Timeline
| Timestamp | Topic | Summary |
|-----------|-------|---------|
| 0:00 | Introduction | ... |
| 3:42 | [Topic] | ... |

## Notable Quotes
> "[Exact or near-exact quote]" -- at [timestamp]

## Summary
[3-5 paragraph narrative covering the video's arc]

---
*Digest generated from transcript. Accuracy depends on caption quality.*
```

**Section rationale:**
- **TL;DR first** -- most users want the answer immediately
- **Key Takeaways** -- actionable points for those who want more
- **Core Assertions** -- for critical thinkers and fact-checkers
- **Timeline** -- for jumping to specific parts of the video
- **Quotes** -- for citation and sharing
- **Summary** -- full narrative for completeness

## Usage

### Basic Digest

User provides a YouTube URL:
```
Summarize this video: https://www.youtube.com/watch?v=VIDEO_ID
```

Steps:
1. Run the extraction script:
   ```bash
   python scripts/fetch_transcript.py "https://www.youtube.com/watch?v=VIDEO_ID" -o /tmp/transcript.json
   ```
2. Read the JSON output
3. Produce the digest following the template above
4. Save as `video_title_digest.md`

### Triage (Is It Worth Watching?)

When the user asks whether a video is worth their time, produce only:
- TL;DR (1-2 sentences)
- Key Takeaways (3-5 bullets)
- A verdict: "Worth watching if you care about [X]" or "Skip -- the key points are covered above"

### Obsidian Export

When the user wants Obsidian-compatible output, prepend YAML frontmatter:

```yaml
---
title: "Video Title"
channel: "Channel Name"
date: 2025-03-15
duration: "1h 23m 45s"
url: "https://youtube.com/watch?v=..."
tags: [youtube, digest, topic1, topic2]
type: youtube-digest
---
```

### Focused Digest

When the user specifies a topic of interest (e.g., "I only care about the part about battery technology"), weight the analysis toward that topic. Still produce the full structure but mark which sections are most relevant.

### Multiple Videos (2-5 URLs)

When the user provides multiple URLs:
1. Run `fetch_transcript.py` for each URL
2. Produce individual digests for each
3. Add a **Comparison** section at the end:
   - Points of agreement
   - Points of disagreement
   - Unique contributions from each video

## Edge Cases

| Situation | Handling |
|-----------|----------|
| **No transcript available** | Report clearly. Suggest the user try a different video. |
| **Auto-generated captions** | Add a quality warning in the output header. |
| **Non-English video** | youtube-transcript-api supports multiple languages. Note the language in the header. |
| **Very long videos (3+ hrs)** | The script chunks the transcript. Warn that timestamps may be less precise. |
| **Very short videos (<1 min)** | Skip the Timeline section. Produce only TL;DR + Key Takeaways. |
| **Music videos / no speech** | Detect short transcript relative to duration. Produce minimal digest from metadata only. |

## Dependencies

Install before first use:
```bash
pip install youtube-transcript-api
```

Optional (for richer metadata -- title, channel, duration, chapters):
```bash
pip install yt-dlp
```

Fallback (if youtube-transcript-api fails):
```bash
pip install 'markitdown[youtube-transcription]'
```

The extraction script checks for these and reports clear error messages if missing.

## Relationship to Other Skills

| Skill | Relationship |
|-------|-------------|
| **markitdown** | Upstream. Provides raw transcript extraction. youtube-digest adds the analysis layer. |
| **scientific-reading** | Sibling pattern. Does for papers what youtube-digest does for videos. |
| **scholar-paper-converter** | Analog. Raw PDF-to-Markdown extraction, like markitdown is to YouTube. |
