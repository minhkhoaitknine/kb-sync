from src.config import load_settings
from src.clean import clean_article_html
from src.discover import discover_articles
from src.fetch import fetch_article_html
from pathlib import Path


def main() -> None:
    settings = load_settings()
    articles = discover_articles(limit=settings.article_limit)

    print(f"discovered={len(articles)}")
    if len(articles) < settings.article_limit:
        raise SystemExit(
            f"Expected at least {settings.article_limit} articles, got {len(articles)}."
        )

    raw_dir = Path(settings.data_dir) / "raw"
    fetched = 0
    cleaned = 0
    failed = 0

    for index, article in enumerate(articles, start=1):
        try:
            html = fetch_article_html(article, raw_dir=raw_dir)
            fetched += 1
            clean_article = clean_article_html(html)
            cleaned += 1
        except Exception as exc:
            failed += 1
            print(f"{index}. FAILED: {article.url}")
            print(f"   error: {exc}")
            continue

        preview = clean_article.text[:160].replace("\n", " ")
        print(f"{index}. {article.title}")
        print(f"   URL: {article.url}")
        print(f"   slug: {article.slug}")
        print(f"   selector: {clean_article.selector}")
        print(f"   cleaned_chars={len(clean_article.text)}")
        print(f"   preview: {preview}")

    print(f"fetched={fetched} cleaned={cleaned} failed={failed}")

    if failed:
        raise SystemExit(f"Failed to fetch/clean {failed} articles.")


if __name__ == "__main__":
    main()
