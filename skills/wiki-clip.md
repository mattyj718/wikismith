---
name: wiki-clip
description: Clip a URL, YouTube video, PDF, or local file into the Obsidian vault. Use when the user says "clip this", "save this to obsidian", "clip <url>", "add to my vault", "save this article", or wants to ingest a web page, YouTube video, PDF document, or file into their knowledge base. Also activates on /wiki-clip. For YouTube videos, generates an AI summary of the transcript inline.
---

# Wiki Clip

Clip a source into the Obsidian vault for later compilation.

## Environment

The wikismith CLI lives in a venv at `~/dev/wikismith/.venv/`. Always invoke via:
```bash
~/dev/wikismith/.venv/bin/wikismith clip "<source>"
```

Config file: `~/dev/wikismith/wikismith.yaml` (or pass `--config <path>`)

## Steps

1. Read `wikismith.yaml` to get clip configuration.
2. Determine the source type:
   - **YouTube URL** (`youtube.com`, `youtu.be`): Run the clip command via Bash. Then read the output file and replace the summary placeholder with an actual AI summary of the transcript (you ARE the LLM).
   - **Web URL** (`http://`, `https://`): Run the clip command via Bash.
   - **PDF file**: Run the clip command via Bash.
   - **Local file**: Run the clip command via Bash.
3. Report the output file path to the user.

## YouTube Special Handling

When clipping a YouTube video:
1. Run `wikismith clip "<url>"` to get metadata + transcript
2. Read the generated file
3. Find the `> [!summary]+ Summary of Transcript` section
4. If it contains a placeholder, read the transcript section and write a concise 2-5 sentence summary of the key points
5. Update the file with the real summary

This uses your session tokens for the summary instead of a separate API call.

## After Clipping

Remind the user: "Clip saved. Run `/wiki-compile` to incorporate it into your wiki."
