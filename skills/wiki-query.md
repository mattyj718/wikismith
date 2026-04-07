---
name: wiki-query
description: Query the compiled wiki knowledge base to answer questions. Use when the user says "wiki query", "search my wiki", "what does my wiki say about", "look up in my knowledge base", "based on my notes", or asks any question that should be grounded in their compiled wiki content. Also activates on /wiki-query. This skill searches the wiki index, reads relevant articles, and answers inline using session tokens.
---

# Wiki Query

Answer a question using the compiled wiki as your knowledge source.

## Steps

1. Read `wikismith.yaml` to find `{output.path}`.
2. Read `{output.path}/_index.md` to get the concept catalog.
3. Based on the user's question, identify which concept articles are relevant (scan the index for matching titles/summaries).
4. Read the relevant concept articles from `{output.path}/concepts/`.
5. Answer the question grounded in the wiki content:
   - Cite sources using `[[concept-id]]` wikilinks
   - If the wiki doesn't contain enough information, say so explicitly
   - Don't hallucinate beyond what the wiki contains

## Output

Answer directly in the conversation. If the user passes `--save`, also write the answer to `{output.path}/queries/{date}-{slug}.md`.

## Filing Back

If the answer synthesizes new insight worth preserving, offer to file it back into the wiki as a new concept article. The user's queries should compound their knowledge base over time.
