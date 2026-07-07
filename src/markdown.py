from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from markdownify import markdownify

from src.clean import CleanedArticle
from src.discover import Article


@dataclass(frozen=True)
class MarkdownDocument:
    path: Path
    content_hash: str
    body: str
    text: str


def build_markdown_article(
    article: Article,
    cleaned_article: CleanedArticle,
    markdown_dir: Path,
    scraped_at: datetime | None = None,
) -> MarkdownDocument:
    article_body = html_to_markdown(cleaned_article.html)
    body = f"Article URL: {article.url}\n\n{article_body}"
    content_hash = calculate_content_hash(body)
    timestamp = scraped_at or datetime.now(timezone.utc)
    frontmatter = build_frontmatter(article, timestamp, content_hash)
    document_text = f"{frontmatter}\n\n{body}\n"
    path = markdown_dir / f"{article.slug}.md"

    return MarkdownDocument(
        path=path,
        content_hash=content_hash,
        body=body,
        text=document_text,
    )


def write_markdown_document(document: MarkdownDocument) -> None:
    document.path.parent.mkdir(parents=True, exist_ok=True)
    document.path.write_text(document.text, encoding="utf-8")


def write_markdown_article(
    article: Article,
    cleaned_article: CleanedArticle,
    markdown_dir: Path,
    scraped_at: datetime | None = None,
) -> MarkdownDocument:
    document = build_markdown_article(article, cleaned_article, markdown_dir, scraped_at)
    write_markdown_document(document)
    return document


def html_to_markdown(html: str) -> str:
    markdown = markdownify(
        html,
        heading_style="ATX",
        bullets="-",
        strip=("script", "style"),
    )
    return _normalize_markdown(markdown)


def calculate_content_hash(markdown_body: str) -> str:
    normalized = _normalize_markdown(markdown_body)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def build_frontmatter(article: Article, scraped_at: datetime, content_hash: str) -> str:
    fields = {
        "title": article.title,
        "article_url": article.url,
        "scraped_at": scraped_at.isoformat(),
        "source_updated_at": article.source_updated_at or "",
        "content_hash": content_hash,
    }

    lines = ["---"]
    for key, value in fields.items():
        lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
    lines.append("---")
    return "\n".join(lines)


def _normalize_markdown(markdown: str) -> str:
    markdown = markdown.replace("\r\n", "\n")
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    lines = [line.rstrip() for line in markdown.splitlines()]
    return "\n".join(lines).strip()
