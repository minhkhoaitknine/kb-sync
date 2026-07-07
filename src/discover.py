from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Iterable
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

import requests


BASE_URL = "https://support.optisigns.com"
HELP_CENTER_API_URLS = (
    f"{BASE_URL}/api/v2/help_center/en-us/articles.json",
    f"{BASE_URL}/api/v2/help_center/articles.json",
)
SITEMAP_URLS = (
    f"{BASE_URL}/hc/sitemap.xml",
    f"{BASE_URL}/sitemap.xml",
)


@dataclass(frozen=True)
class Article:
    title: str
    url: str
    slug: str
    source_updated_at: str | None = None


class ArticleLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.urls: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return

        href = dict(attrs).get("href")
        if href and "/hc/" in href and "/articles/" in href:
            self.urls.add(urljoin(BASE_URL, href))


def discover_articles(limit: int = 30) -> list[Article]:
    articles = _discover_from_zendesk_api(limit)
    if len(articles) >= limit:
        return articles[:limit]

    sitemap_articles = _discover_from_sitemap(limit)
    merged = _merge_articles([*articles, *sitemap_articles])
    if len(merged) >= limit:
        return merged[:limit]

    crawled_articles = _discover_from_html(limit)
    return _merge_articles([*merged, *crawled_articles])[:limit]


def _discover_from_zendesk_api(limit: int) -> list[Article]:
    for api_url in HELP_CENTER_API_URLS:
        try:
            articles = _read_zendesk_pages(api_url, limit)
        except requests.RequestException:
            continue

        if articles:
            return articles

    return []


def _read_zendesk_pages(api_url: str, limit: int) -> list[Article]:
    articles: list[Article] = []
    next_url: str | None = api_url

    while next_url and len(articles) < limit:
        response = requests.get(next_url, params={"per_page": 100}, timeout=20)
        response.raise_for_status()
        payload = response.json()

        for item in payload.get("articles", []):
            html_url = item.get("html_url")
            title = item.get("title")
            if not html_url or not title:
                continue

            articles.append(
                Article(
                    title=title.strip(),
                    url=html_url,
                    slug=slug_from_url(html_url),
                    source_updated_at=item.get("updated_at"),
                )
            )

        next_url = payload.get("next_page")

    return articles


def _discover_from_sitemap(limit: int) -> list[Article]:
    for sitemap_url in SITEMAP_URLS:
        try:
            response = requests.get(sitemap_url, timeout=20)
            response.raise_for_status()
        except requests.RequestException:
            continue

        urls = _article_urls_from_sitemap(response.text)
        if urls:
            return [_article_from_url(url) for url in urls[:limit]]

    return []


def _article_urls_from_sitemap(xml_text: str) -> list[str]:
    root = ElementTree.fromstring(xml_text)
    urls: list[str] = []

    for loc in root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc"):
        if loc.text and "/hc/" in loc.text and "/articles/" in loc.text:
            urls.append(loc.text.strip())

    return urls


def _discover_from_html(limit: int) -> list[Article]:
    try:
        response = requests.get(BASE_URL, timeout=20)
        response.raise_for_status()
    except requests.RequestException:
        return []

    parser = ArticleLinkParser()
    parser.feed(response.text)

    urls = sorted(parser.urls)
    return [_article_from_url(url) for url in urls[:limit]]


def _article_from_url(url: str) -> Article:
    slug = slug_from_url(url)
    return Article(title=title_from_slug(slug), url=url, slug=slug)


def _merge_articles(articles: Iterable[Article]) -> list[Article]:
    seen: set[str] = set()
    merged: list[Article] = []

    for article in articles:
        if article.url in seen:
            continue
        seen.add(article.url)
        merged.append(article)

    return merged


def slug_from_url(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    last_part = path.split("/")[-1]
    return last_part or "article"


def title_from_slug(slug: str) -> str:
    without_id = slug.split("-", 1)[1] if "-" in slug else slug
    return without_id.replace("-", " ").strip().title()

