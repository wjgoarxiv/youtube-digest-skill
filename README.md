<p align="center"><img src="./cover.png" width="100%" /></p>

<h1 align="center">youtube-digest</h1>
<p align="center">
  <em>Transform YouTube videos into structured knowledge -- TL;DR, key takeaways, timestamped claims, and more.</em>
</p>
<p align="center">
  <a href="#quick-start">Quick Start</a> · <a href="#features">Features</a> · <a href="#usage">Usage</a> · <a href="./README-Ko-KR.md">한국어</a>
</p>
<p align="center">
  <img src="https://img.shields.io/github/stars/wjgoarxiv/youtube-digest-skill?style=social" />
  <img src="https://img.shields.io/badge/license-MIT-blue" />
  <img src="https://img.shields.io/badge/python-3.8+-green" />
  <img src="https://img.shields.io/badge/skill-Claude%20Code-blueviolet" />
</p>

---

> [!NOTE]
> A Claude Code skill that extracts YouTube transcripts and produces structured digests with TL;DR, key takeaways, timestamped assertions, topic timelines, and notable quotes -- turning hours of video into minutes of reading.

## Features

- **Instant TL;DR** -- Get the core message of any video in 1-2 sentences
- **Key Takeaways** -- 3-7 standalone insights you can act on immediately
- **Timestamped Claims** -- Every assertion linked to its source moment, tagged as `[cited study]`, `[opinion]`, or `[anecdote]`
- **Topic Timeline** -- Jump-table with timestamps, topics, and one-line summaries
- **Notable Quotes** -- The speaker's most impactful statements, ready to cite
- **Triage Mode** -- Quick "worth watching?" verdict before you commit 2 hours
- **Obsidian Export** -- YAML frontmatter with tags, ready for your PKM vault
- **Multi-Video Comparison** -- Compare 2-5 videos side-by-side: agreements, disagreements, unique contributions

## Quick Start

### Zip Upload (Claude App)

1. Download [`youtube-digest.zip`](./youtube-digest.zip) from this repo
2. Open **Claude App** → **Settings** → **Skills** → **Upload Skill**
3. Upload the zip file
4. Install the Python dependency: `pip install youtube-transcript-api`

### Copy-Paste Install

> [!TIP]
> Works with any LLM CLI that supports skills (Claude Code, Codex, Gemini CLI). Just paste the block below into your chat.

```
I want to install the youtube-digest skill. Do these steps:
1. git clone https://github.com/wjgoarxiv/youtube-digest-skill.git /tmp/youtube-digest-skill
2. mkdir -p ~/.claude/skills/youtube-digest && cp -r /tmp/youtube-digest-skill/SKILL.md /tmp/youtube-digest-skill/scripts /tmp/youtube-digest-skill/assets ~/.claude/skills/youtube-digest/
3. pip install youtube-transcript-api
4. Test: python ~/.claude/skills/youtube-digest/scripts/fetch_transcript.py "https://youtu.be/dQw4w9WgXcQ" 2>/dev/null | python3 -c "import sys,json;d=json.load(sys.stdin);print(f'OK: {d[\"total_segments\"]} segments')"
5. Say "youtube-digest skill installed successfully"
```

### Manual Install

```bash
# Clone the repo
git clone https://github.com/wjgoarxiv/youtube-digest-skill.git
cd youtube-digest-skill

# Symlink into your skills directory
mkdir -p ~/.claude/skills
ln -s "$(pwd)" ~/.claude/skills/youtube-digest

# Install dependencies
pip install youtube-transcript-api
pip install yt-dlp              # optional: richer metadata
```

### Other Tools

| Tool | Skills Path | Install Command |
|------|-------------|-----------------|
| **Claude Code** | `~/.claude/skills/youtube-digest/` | See above |
| **Codex CLI** | `~/.codex/skills/youtube-digest/` | `mkdir -p ~/.codex/skills && ln -s "$(pwd)" ~/.codex/skills/youtube-digest` |
| **Gemini CLI** | `~/.gemini/skills/youtube-digest/` | `mkdir -p ~/.gemini/skills && ln -s "$(pwd)" ~/.gemini/skills/youtube-digest` |

## Usage

### 1. Basic Digest

```
Summarize this video: https://www.youtube.com/watch?v=VIDEO_ID
```

Produces a full structured digest: TL;DR, Key Takeaways, Core Assertions, Topic Timeline, Notable Quotes, and Summary.

### 2. Triage -- "Is It Worth Watching?"

```
I found this 3-hour lecture. Is it worth watching for someone interested in battery tech?
https://www.youtube.com/watch?v=VIDEO_ID
```

Returns a condensed verdict: TL;DR + filtered takeaways + watch/skip recommendation.

### 3. Obsidian Export

```
Digest this video and save to my Obsidian vault at ~/vault/YouTube/.
Tag it with "machine-learning" and "tutorial".
https://www.youtube.com/watch?v=VIDEO_ID
```

Outputs a Markdown file with YAML frontmatter (`title`, `channel`, `date`, `duration`, `url`, `tags`, `type: youtube-digest`).

### 4. Multi-Video Comparison

```
Compare these two talks on climate policy:
https://www.youtube.com/watch?v=VIDEO_1
https://www.youtube.com/watch?v=VIDEO_2
```

Individual digests for each, plus a comparison section highlighting agreements, disagreements, and unique contributions.

## Output Format

Every digest follows this structure (abbreviated):

```markdown
# Video Title

**Channel:** name | **Duration:** HH:MM:SS | **Published:** date
**URL:** link

---

## TL;DR
One to two sentence summary.

## Key Takeaways
- Insight 1
- Insight 2
- ...

## Core Assertions & Claims
- Claim text (at 3:42) [cited study]
- Claim text (at 12:15) [opinion]

## Topic Timeline
| Timestamp | Topic       | Summary                |
|-----------|-------------|------------------------|
| 0:00      | Intro       | Sets up the problem... |
| 3:42      | Main thesis | Argues that...         |

## Notable Quotes
> "Exact quote" -- at 5:30

## Summary
Full narrative arc in 3-5 paragraphs.

---
*Digest generated from transcript. Accuracy depends on caption quality.*
```

> [!IMPORTANT]
> The section order is intentional. Users who stop reading early still get maximum value (TL;DR first, full summary last).

## How It Works

```
                    youtube-digest pipeline
                    ~~~~~~~~~~~~~~~~~~~~~~

 [YouTube URL]
      |
      v
 +-------------------+
 | 1. EXTRACT        |     fetch_transcript.py
 |   - transcript    |     youtube-transcript-api
 |   - metadata      |     yt-dlp (optional)
 +-------------------+
      |
      v
 +-------------------+
 | 2. ANALYZE        |     Claude LLM
 |   - summarize     |     Structured analysis
 |   - find claims   |     of transcript JSON
 |   - build timeline|
 +-------------------+
      |
      v
 +-------------------+
 | 3. FORMAT         |     Markdown output
 |   - digest.md     |     Optional: Obsidian
 |   - frontmatter   |     YAML frontmatter
 +-------------------+
```

## Requirements

| Dependency | Required | Purpose |
|-----------|----------|---------|
| Python 3.8+ | Yes | Runtime |
| `youtube-transcript-api` | Yes | Transcript extraction |
| `yt-dlp` | No (recommended) | Rich metadata (title, channel, duration, chapters) |
| `markitdown[youtube-transcription]` | No (fallback) | Backup transcript source if primary fails |

> [!WARNING]
> Without `yt-dlp`, metadata (title, channel, duration) will be unavailable. The digest will still work, but the header will be incomplete. Install it with `pip install yt-dlp`.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes
4. Open a Pull Request

For bug reports or feature requests, please [open an issue](https://github.com/wjgoarxiv/youtube-digest-skill/issues).

## License

This project is licensed under the [MIT License](./LICENSE).
