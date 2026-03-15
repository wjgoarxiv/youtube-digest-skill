---
name: youtube-digest
description: |
  Extracts transcripts from YouTube videos and produces structured digests with TL;DR, key takeaways, core assertions with timestamps, topic timeline, and notable quotes. Builds on markitdown's raw transcript extraction by adding LLM-driven analysis and structured output.
  TRIGGER when: user pastes a YouTube URL and wants a summary, digest, or analysis of the video content; user asks "what is this video about"; user wants key points or takeaways from a YouTube video; user wants to decide whether a video is worth watching; user asks to summarize a YouTube talk, lecture, podcast, or interview; user wants structured notes from a video; user asks to digest or break down a YouTube video; user mentions a YouTube link and asks for insights.
  DO NOT TRIGGER when: user just wants the raw transcript text without analysis (use markitdown); user wants to download the video file; user wants to convert a local video or audio file to text.
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - WebFetch
  - WebSearch
---

# YouTube Video Digest

Transforms YouTube videos into structured, actionable knowledge. Where markitdown gives you the raw transcript, this skill gives you understanding -- TL;DR, key takeaways, timestamped assertions, topic timeline, and notable quotes.

## When to Use This Skill

- **Quick triage:** Decide whether a video is worth watching
- **Full digest:** Get structured notes from a talk, lecture, or podcast
- **Claim extraction:** Identify the speaker's core assertions with timestamps
- **Study notes:** Create PKM-ready notes (Obsidian, Notion) from educational videos
- **Multi-video comparison:** Compare key points across 2-5 related videos

## Environment Detection

Before starting, detect your runtime capabilities and select the appropriate tier:

```
Check 1: Can I run Bash + Python?
  YES → Tier 1 (fetch_transcript.py -- works WITHOUT pip packages)
  NO  → Check 2: Can I use WebFetch?
    YES → Tier 2 (WebFetch-based extraction)
    NO  → Tier 3 (User-provided transcript -- last resort)
```

| Tier | Environment | Capabilities | Extraction Method |
|------|-------------|--------------|-------------------|
| **Tier 1** | Claude Code, Codex CLI, any terminal | Bash + Python (stdlib only, no pip needed) | `fetch_transcript.py` uses `urllib` + `xml.etree` |
| **Tier 2** | Claude App (Web) with web access | WebFetch | Fetch YouTube page HTML → extract captionTracks → fetch timedtext XML |
| **Tier 3** | Fully restricted (no network at all) | Text generation only | Ask user to paste transcript (last resort) |

## How It Works

Three-stage pipeline, with the extraction stage adapting to the environment:

```
[YouTube URL] --> [Extract] --> [Analyze] --> [Format]
                    |               |             |
              Tier 1: script   Claude LLM     Markdown
              Tier 2: web                      output
              Tier 3: user
```

**Stage 1 -- Extract (environment-dependent):**
- **Tier 1:** Run `scripts/fetch_transcript.py` -- works with **zero pip packages**. Uses Python stdlib (`urllib.request` + `xml.etree`) to fetch the YouTube page, extract `captionTracks`, and parse the timedtext XML. If `youtube-transcript-api` or `yt-dlp` are installed, uses them for enhanced extraction, but they are optional.
- **Tier 2:** Use WebFetch to replicate the same extraction:
  1. `WebFetch("https://www.youtube.com/watch?v=VIDEO_ID")` → get page HTML
  2. Find `"captionTracks":` in the HTML → extract the `baseUrl` for the preferred language
  3. `WebFetch(baseUrl)` → get transcript XML
  4. Parse `<text start="..." dur="...">content</text>` elements into segments
  5. Extract metadata from page: `"title"`, `"ownerChannelName"`, `"lengthSeconds"`, `"uploadDate"`
- **Tier 3 (last resort):** Ask the user to provide the transcript. Suggest: (1) Click "Show transcript" on YouTube, (2) Use an online transcript extractor, (3) Paste any text from the video.

**Stage 2 -- Analyze:** Read the extracted content and produce the structured digest. Synthesize, identify themes, extract claims, build the timeline.

**Stage 3 -- Format:** Output the final Markdown, optionally with Obsidian YAML frontmatter.

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

#### Tier 1 Steps (Bash + Python -- no pip needed)
1. Run the extraction script (works with Python stdlib only):
   ```bash
   python scripts/fetch_transcript.py "https://www.youtube.com/watch?v=VIDEO_ID" -o /tmp/transcript.json
   ```
2. Read the JSON output
3. Produce the digest following the template above
4. Save as `video_title_digest.md`

#### Tier 2 Steps (WebFetch)
1. Fetch the YouTube page:
   ```
   WebFetch("https://www.youtube.com/watch?v=VIDEO_ID")
   ```
2. In the returned HTML, find `"captionTracks":` and extract the `baseUrl` for the desired language
3. Fetch the transcript XML:
   ```
   WebFetch(baseUrl)
   ```
4. Parse the `<text start="..." dur="...">content</text>` elements into timestamped segments
5. Extract metadata from the page HTML: `"title"`, `"ownerChannelName"`, `"lengthSeconds"`, `"uploadDate"`
6. Produce the digest from the extracted data

#### Tier 3 Steps (No Network -- last resort)
1. Tell the user:
   > I don't have network access in this environment. To create a digest, I need the transcript:
   > 1. **YouTube app/web:** Open the video → click `···` (More) → **Show transcript** → copy all text
   > 2. **Online tool:** Search "YouTube transcript extractor" and paste the video URL
2. Once the user provides text, produce the digest from that content
3. Omit timestamps if they are not present in the provided text
4. Note in the header: `*Digest generated from user-provided transcript.*`

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
1. Extract content for each URL using the appropriate tier
2. Produce individual digests for each
3. Add a **Comparison** section at the end:
   - Points of agreement
   - Points of disagreement
   - Unique contributions from each video

## Edge Cases

| Situation | Handling |
|-----------|----------|
| **No transcript available** | Report clearly. Suggest the user try a different video. In Tier 2/3, suggest the user manually copy the transcript. |
| **Auto-generated captions** | Add a quality warning in the output header. |
| **Non-English video** | youtube-transcript-api supports multiple languages. Note the language in the header. In Tier 2/3, ask the user to specify the language. |
| **Very long videos (3+ hrs)** | The script chunks the transcript. Warn that timestamps may be less precise. In Tier 3, warn the user that pasting may be impractical and suggest using a transcript extractor tool. |
| **Very short videos (<1 min)** | Skip the Timeline section. Produce only TL;DR + Key Takeaways. |
| **Music videos / no speech** | Detect short transcript relative to duration. Produce minimal digest from metadata only. |
| **Restricted environment (no Bash/Network)** | Automatically fall back to Tier 2 or Tier 3. Never report an error without offering the fallback path. |

## Dependencies

**Required:** Python 3.8+ (stdlib only -- no pip packages needed).

The extraction script uses `urllib.request` and `xml.etree.ElementTree` from Python's standard library to fetch transcripts directly from YouTube.

**Optional** (enhanced extraction if available):
```bash
pip install youtube-transcript-api   # more robust transcript fetching
pip install yt-dlp                   # richer metadata (chapters, tags, language)
```

The script auto-detects installed packages and uses them when available, but works fully without them.

## Relationship to Other Skills

| Skill | Relationship |
|-------|-------------|
| **markitdown** | Upstream. Provides raw transcript extraction. youtube-digest adds the analysis layer. |
| **scientific-reading** | Sibling pattern. Does for papers what youtube-digest does for videos. |
| **scholar-paper-converter** | Analog. Raw PDF-to-Markdown extraction, like markitdown is to YouTube. |
