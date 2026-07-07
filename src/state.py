from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Literal

from src.discover import Article
from src.markdown import MarkdownDocument


DeltaStatus = Literal["added", "updated", "skipped"]


@dataclass(frozen=True)
class ArticleDelta:
    status: DeltaStatus
    article: Article
    markdown_path: Path
    content_hash: str
    needs_upload: bool


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._state = _load_state(path)
        self._articles: dict[str, dict[str, Any]] = dict(
            self._state.get("articles", {})
        )

    def classify(
        self,
        article: Article,
        document: MarkdownDocument,
        upload_key: str = "openai_upload",
        upload_target_id: str | None = None,
        force_upload: bool = False,
    ) -> ArticleDelta:
        previous = self._articles.get(article.url)

        if previous is None:
            status: DeltaStatus = "added"
        elif previous.get("content_hash") != document.content_hash:
            status = "updated"
        else:
            status = "skipped"

        previous_upload = previous.get(upload_key) if previous else None
        needs_upload = (
            force_upload
            or status != "skipped"
            or not previous_upload
            or not _matches_upload_target(previous_upload, upload_target_id)
        )

        record = {
            "title": article.title,
            "url": article.url,
            "slug": article.slug,
            "source_updated_at": article.source_updated_at,
            "content_hash": document.content_hash,
            "markdown_path": str(document.path),
            "last_seen_at": datetime.now(timezone.utc).isoformat(),
        }

        if status == "skipped" and previous:
            for key, value in previous.items():
                if key.endswith("_upload"):
                    record[key] = value

        self._articles[article.url] = record

        return ArticleDelta(
            status=status,
            article=article,
            markdown_path=document.path,
            content_hash=document.content_hash,
            needs_upload=needs_upload,
        )

    def record_openai_upload(
        self,
        article_url: str,
        *,
        openai_file_id: str,
        vector_store_file_id: str,
        vector_store_id: str,
        estimated_chunks: int,
    ) -> None:
        record = self._articles[article_url]
        record["openai_upload"] = {
            "openai_file_id": openai_file_id,
            "vector_store_file_id": vector_store_file_id,
            "vector_store_id": vector_store_id,
            "estimated_chunks": estimated_chunks,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }

    def record_gemini_upload(
        self,
        article_url: str,
        *,
        file_search_store_name: str,
        operation_name: str,
        estimated_chunks: int,
    ) -> None:
        record = self._articles[article_url]
        record["gemini_upload"] = {
            "file_search_store_name": file_search_store_name,
            "operation_name": operation_name,
            "estimated_chunks": estimated_chunks,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "articles": self._articles,
        }
        self.path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def latest_gemini_file_search_store_name(self) -> str | None:
        latest_uploaded_at = ""
        latest_store_name = None

        for record in self._articles.values():
            upload = record.get("gemini_upload")
            if not upload:
                continue

            uploaded_at = upload.get("uploaded_at", "")
            store_name = upload.get("file_search_store_name")
            if store_name and uploaded_at >= latest_uploaded_at:
                latest_uploaded_at = uploaded_at
                latest_store_name = store_name

        return latest_store_name


def _load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "articles": {}}

    return json.loads(path.read_text(encoding="utf-8"))


def _matches_upload_target(
    previous_upload: dict[str, Any],
    upload_target_id: str | None,
) -> bool:
    if not upload_target_id:
        return True

    known_target_ids = {
        previous_upload.get("vector_store_id"),
        previous_upload.get("file_search_store_name"),
    }
    return upload_target_id in known_target_ids
