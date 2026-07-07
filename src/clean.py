from dataclasses import dataclass
import re

from bs4 import BeautifulSoup, Tag


ARTICLE_SELECTORS = (
    "div.article-body",
    "article .article-body",
    "[itemprop='articleBody']",
    "article",
    "main",
)

NOISE_TAGS = ("script", "style", "nav", "footer", "header", "aside", "form", "noscript", "svg")
NOISE_CLASS_OR_ID = re.compile(
    r"(breadcrumb|sidebar|footer|header|nav|search|subscribe|share|vote|comment|pagination|related)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CleanedArticle:
    html: str
    text: str
    selector: str


def clean_article_html(html: str) -> CleanedArticle:
    soup = BeautifulSoup(html, "html.parser")
    container, selector = _find_article_container(soup)

    for tag in container.find_all(NOISE_TAGS):
        tag.decompose()

    for tag in container.find_all(_is_noise_element):
        tag.decompose()

    cleaned_html = str(container).strip()
    cleaned_text = _normalize_text(container.get_text("\n"))

    if not cleaned_text:
        raise ValueError("Article body was found but cleaned text is empty.")

    return CleanedArticle(html=cleaned_html, text=cleaned_text, selector=selector)


def _find_article_container(soup: BeautifulSoup) -> tuple[Tag, str]:
    for selector in ARTICLE_SELECTORS:
        container = soup.select_one(selector)
        if container:
            return container, selector

    raise ValueError("Could not find article body with known selectors.")


def _is_noise_element(tag: Tag) -> bool:
    class_text = " ".join(tag.get("class", []))
    id_text = tag.get("id", "")
    return bool(NOISE_CLASS_OR_ID.search(f"{class_text} {id_text}"))


def _normalize_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    non_empty_lines = [line for line in lines if line]
    return "\n".join(non_empty_lines)

