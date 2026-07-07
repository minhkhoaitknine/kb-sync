from pathlib import Path

import requests

from src.discover import Article


REQUEST_HEADERS = {
    "User-Agent": "OptiBotMiniClone/1.0 (+https://support.optisigns.com)"
}


def fetch_article_html(article: Article, raw_dir: Path | None = None) -> str:
    response = requests.get(article.url, headers=REQUEST_HEADERS, timeout=30)
    response.raise_for_status()
    html = response.text

    if raw_dir:
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_path = raw_dir / f"{article.slug}.html"
        raw_path.write_text(html, encoding="utf-8")

    return html

