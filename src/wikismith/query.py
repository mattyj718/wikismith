"""Query engine: Q&A against compiled wiki."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from wikismith.config import Config
from wikismith.utils import slugify


def _call_llm_query(question: str, context: str, config: Config) -> str:
    """Call the LLM to answer a question. Mockable in tests."""
    raise NotImplementedError("LLM call not implemented for standalone mode yet")


def run_query(question: str, config: Config, save: bool = False) -> str:
    """Run a query against the compiled wiki."""
    wiki_path = config.output.path
    index_path = wiki_path / config.output.index_file

    if not index_path.exists():
        return "No wiki compiled yet. Run `wikismith compile` first."

    index = index_path.read_text(encoding="utf-8")

    # Read all concept articles for context
    concepts_dir = wiki_path / "concepts"
    articles = {}
    if concepts_dir.exists():
        for f in concepts_dir.glob("*.md"):
            articles[f.stem] = f.read_text(encoding="utf-8")

    context = f"## Wiki Index\n\n{index}\n\n"
    for name, content in articles.items():
        context += f"## Article: {name}\n\n{content}\n\n---\n\n"

    answer = _call_llm_query(question, context, config)

    if save:
        queries_dir = wiki_path / "queries"
        queries_dir.mkdir(parents=True, exist_ok=True)
        slug = slugify(question, max_len=50)
        date = dt.date.today().strftime("%Y-%m-%d")
        out_path = queries_dir / f"{date}-{slug}.md"
        out_path.write_text(f"# Query: {question}\n\n{answer}\n", encoding="utf-8")

    return answer
