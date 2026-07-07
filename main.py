import argparse
from pathlib import Path

from src.config import load_settings
from src.clean import clean_article_html
from src.discover import discover_articles
from src.fetch import fetch_article_html
from src.markdown import build_markdown_article, write_markdown_document
from src.gemini_upload import create_file_search_store, upload_delta_file_to_gemini
from src.openai_upload import upload_delta_files
from src.state import StateStore


def has_openai_upload_config(api_key: str | None, vector_store_id: str | None) -> bool:
    if not api_key or not vector_store_id:
        return False
    if api_key.startswith("your_") or vector_store_id.startswith("your_"):
        return False
    return True


def has_gemini_upload_config(api_key: str | None) -> bool:
    if not api_key or api_key.startswith("your_"):
        return False
    return True


def active_upload_target_id(provider: str, settings) -> str | None:
    if provider == "openai":
        return usable_setting(settings.openai_vector_store_id)
    if provider == "gemini":
        return usable_setting(settings.gemini_file_search_store_name)
    return None


def usable_setting(value: str | None) -> str | None:
    if not value or value.startswith("your_"):
        return None
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape, clean, index, and upload OptiSigns docs.")
    parser.add_argument(
        "--force-upload",
        action="store_true",
        help="Upload all discovered Markdown files even if state says they were uploaded.",
    )
    args = parser.parse_args()

    settings = load_settings()
    if settings.ai_provider not in {"openai", "gemini"}:
        raise SystemExit("AI_PROVIDER must be either 'openai' or 'gemini'.")

    articles = discover_articles(limit=settings.article_limit)

    print(f"discovered={len(articles)}")
    if len(articles) < settings.article_limit:
        raise SystemExit(
            f"Expected at least {settings.article_limit} articles, got {len(articles)}."
        )

    raw_dir = Path(settings.data_dir) / "raw"
    markdown_dir = Path(settings.data_dir) / "markdown"
    state = StateStore(Path(settings.data_dir) / "state.json")
    upload_key = f"{settings.ai_provider}_upload"
    upload_target_id = active_upload_target_id(settings.ai_provider, settings)
    fetched = 0
    cleaned = 0
    markdown_written = 0
    added = 0
    updated = 0
    skipped = 0
    upload_candidates = []
    failed = 0

    for index, article in enumerate(articles, start=1):
        try:
            html = fetch_article_html(article, raw_dir=raw_dir)
            fetched += 1
            clean_article = clean_article_html(html)
            cleaned += 1
            markdown_document = build_markdown_article(
                article,
                clean_article,
                markdown_dir=markdown_dir,
            )
            delta = state.classify(
                article,
                markdown_document,
                upload_key=upload_key,
                upload_target_id=upload_target_id,
                force_upload=args.force_upload,
            )

            if delta.status == "added":
                added += 1
            elif delta.status == "updated":
                updated += 1
            else:
                skipped += 1

            if delta.status != "skipped" or not markdown_document.path.exists():
                write_markdown_document(markdown_document)
                markdown_written += 1

            if delta.needs_upload:
                upload_candidates.append(delta)
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
        print(f"   status: {delta.status}")
        print(f"   needs_upload: {delta.needs_upload}")
        print(f"   markdown: {markdown_document.path}")
        print(f"   content_hash: {markdown_document.content_hash[:12]}...")
        print(f"   preview: {preview}")

    uploaded = 0
    upload_failed = 0
    estimated_chunks = 0

    if not failed:
        if settings.ai_provider == "openai":
            openai_configured = has_openai_upload_config(
                settings.openai_api_key,
                settings.openai_vector_store_id,
            )

            if upload_candidates and not openai_configured:
                print(
                    f"upload_skipped={len(upload_candidates)} "
                    "reason=missing_openai_api_key_or_vector_store_id"
                )
            elif upload_candidates:
                try:
                    upload_results = upload_delta_files(
                        upload_candidates,
                        api_key=settings.openai_api_key,
                        vector_store_id=settings.openai_vector_store_id,
                    )
                except Exception as exc:
                    upload_failed = len(upload_candidates)
                    print(f"upload_failed={upload_failed} error={exc}")
                else:
                    uploaded = len(upload_results)
                    estimated_chunks = sum(
                        result.estimated_chunks for result in upload_results
                    )
                    for result in upload_results:
                        state.record_openai_upload(
                            result.delta.article.url,
                            openai_file_id=result.openai_file_id,
                            vector_store_file_id=result.vector_store_file_id,
                            vector_store_id=settings.openai_vector_store_id,
                            estimated_chunks=result.estimated_chunks,
                        )
        elif settings.ai_provider == "gemini":
            gemini_configured = has_gemini_upload_config(settings.gemini_api_key)

            if upload_candidates and not gemini_configured:
                print(
                    f"upload_skipped={len(upload_candidates)} "
                    "reason=missing_gemini_api_key"
                )
            elif upload_candidates:
                file_search_store_name = settings.gemini_file_search_store_name
                if not file_search_store_name or file_search_store_name.startswith("your_"):
                    file_search_store_name = create_file_search_store(
                        api_key=settings.gemini_api_key,
                        display_name="optibot-support-docs",
                    )
                    print(f"GEMINI_FILE_SEARCH_STORE_NAME={file_search_store_name}")
                    print("Copy this value into your .env file.")

                for upload_index, delta in enumerate(upload_candidates, start=1):
                    try:
                        result = upload_delta_file_to_gemini(
                            delta,
                            api_key=settings.gemini_api_key,
                            file_search_store_name=file_search_store_name,
                        )
                    except Exception as exc:
                        upload_failed += 1
                        print(
                            f"upload_failed_file={upload_index}/{len(upload_candidates)} "
                            f"path={delta.markdown_path} error={exc}",
                            flush=True,
                        )
                        continue

                    uploaded += 1
                    estimated_chunks += result.estimated_chunks
                    state.record_gemini_upload(
                        result.delta.article.url,
                        file_search_store_name=result.file_search_store_name,
                        operation_name=result.operation_name,
                        estimated_chunks=result.estimated_chunks,
                    )
                    state.save()
                    print(
                        f"uploaded_gemini={uploaded}/{len(upload_candidates)} "
                        f"chunks={result.estimated_chunks} "
                        f"path={result.delta.markdown_path}",
                        flush=True,
                    )
        else:
            print("upload_skipped=0 reason=no_delta")

        state.save()

    print(
        f"fetched={fetched} cleaned={cleaned} "
        f"markdown_written={markdown_written} "
        f"added={added} updated={updated} skipped={skipped} "
        f"provider={settings.ai_provider} "
        f"upload_candidates={len(upload_candidates)} uploaded={uploaded} "
        f"force_upload={args.force_upload} "
        f"estimated_chunks={estimated_chunks} "
        f"failed={failed} upload_failed={upload_failed}"
    )

    if failed:
        raise SystemExit(f"Failed to fetch/clean/write {failed} articles.")
    if upload_failed:
        raise SystemExit(f"Failed to upload {upload_failed} files.")


if __name__ == "__main__":
    main()
