from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.discover import Article
from src.markdown import MarkdownDocument
from src.state import StateStore


class StateStoreTests(unittest.TestCase):
    def test_new_article_needs_upload(self) -> None:
        with TemporaryDirectory() as temp_dir:
            state = StateStore(Path(temp_dir) / "state.json")

            delta = state.classify(
                article=sample_article(),
                document=sample_document(Path(temp_dir), "hash-1"),
                upload_key="gemini_upload",
                upload_target_id="fileSearchStores/current",
            )

            self.assertEqual(delta.status, "added")
            self.assertTrue(delta.needs_upload)

    def test_uploaded_article_with_same_store_is_skipped(self) -> None:
        with TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "state.json"
            article = sample_article()
            document = sample_document(Path(temp_dir), "hash-1")
            state = StateStore(state_path)

            state.classify(
                article=article,
                document=document,
                upload_key="gemini_upload",
                upload_target_id="fileSearchStores/current",
            )
            state.record_gemini_upload(
                article.url,
                file_search_store_name="fileSearchStores/current",
                operation_name="operations/upload-1",
                estimated_chunks=3,
            )
            state.save()

            reloaded_state = StateStore(state_path)
            delta = reloaded_state.classify(
                article=article,
                document=document,
                upload_key="gemini_upload",
                upload_target_id="fileSearchStores/current",
            )

            self.assertEqual(delta.status, "skipped")
            self.assertFalse(delta.needs_upload)

    def test_same_content_needs_upload_when_store_changes(self) -> None:
        with TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "state.json"
            article = sample_article()
            document = sample_document(Path(temp_dir), "hash-1")
            state = StateStore(state_path)

            state.classify(
                article=article,
                document=document,
                upload_key="gemini_upload",
                upload_target_id="fileSearchStores/old",
            )
            state.record_gemini_upload(
                article.url,
                file_search_store_name="fileSearchStores/old",
                operation_name="operations/upload-1",
                estimated_chunks=3,
            )
            state.save()

            reloaded_state = StateStore(state_path)
            delta = reloaded_state.classify(
                article=article,
                document=document,
                upload_key="gemini_upload",
                upload_target_id="fileSearchStores/new",
            )

            self.assertEqual(delta.status, "skipped")
            self.assertTrue(delta.needs_upload)

    def test_force_upload_overrides_existing_upload(self) -> None:
        with TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "state.json"
            article = sample_article()
            document = sample_document(Path(temp_dir), "hash-1")
            state = StateStore(state_path)

            state.classify(
                article=article,
                document=document,
                upload_key="gemini_upload",
                upload_target_id="fileSearchStores/current",
            )
            state.record_gemini_upload(
                article.url,
                file_search_store_name="fileSearchStores/current",
                operation_name="operations/upload-1",
                estimated_chunks=3,
            )
            state.save()

            reloaded_state = StateStore(state_path)
            delta = reloaded_state.classify(
                article=article,
                document=document,
                upload_key="gemini_upload",
                upload_target_id="fileSearchStores/current",
                force_upload=True,
            )

            self.assertEqual(delta.status, "skipped")
            self.assertTrue(delta.needs_upload)

    def test_latest_gemini_store_name_comes_from_upload_metadata(self) -> None:
        with TemporaryDirectory() as temp_dir:
            state = StateStore(Path(temp_dir) / "state.json")
            article = sample_article()
            document = sample_document(Path(temp_dir), "hash-1")

            state.classify(
                article=article,
                document=document,
                upload_key="gemini_upload",
                upload_target_id="fileSearchStores/current",
            )
            state.record_gemini_upload(
                article.url,
                file_search_store_name="fileSearchStores/current",
                operation_name="operations/upload-1",
                estimated_chunks=3,
            )

            self.assertEqual(
                state.latest_gemini_file_search_store_name(),
                "fileSearchStores/current",
            )


def sample_article() -> Article:
    return Article(
        title="Sample Article",
        url="https://support.optisigns.com/hc/en-us/articles/123-sample",
        slug="123-sample",
        source_updated_at="2026-07-08T00:00:00Z",
    )


def sample_document(temp_dir: Path, content_hash: str) -> MarkdownDocument:
    return MarkdownDocument(
        path=temp_dir / "123-sample.md",
        content_hash=content_hash,
        body="Article URL: https://support.optisigns.com/hc/en-us/articles/123-sample",
        text="# Sample Article\n",
    )


if __name__ == "__main__":
    unittest.main()
