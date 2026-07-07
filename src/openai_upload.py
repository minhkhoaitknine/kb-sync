from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import re

from openai import OpenAI

from src.state import ArticleDelta


CHUNK_MAX_TOKENS = 800
CHUNK_OVERLAP_TOKENS = 200


@dataclass(frozen=True)
class UploadResult:
    delta: ArticleDelta
    openai_file_id: str
    vector_store_file_id: str
    estimated_chunks: int


def upload_delta_files(
    deltas: list[ArticleDelta],
    *,
    api_key: str,
    vector_store_id: str,
) -> list[UploadResult]:
    client = OpenAI(api_key=api_key)
    results: list[UploadResult] = []

    for delta in deltas:
        result = upload_one_delta_file(client, vector_store_id, delta)
        results.append(result)

    return results


def upload_one_delta_file(
    client: OpenAI,
    vector_store_id: str,
    delta: ArticleDelta,
) -> UploadResult:
    with delta.markdown_path.open("rb") as file_handle:
        uploaded_file = client.files.create(
            file=file_handle,
            purpose="assistants",
        )

    vector_store_file = client.vector_stores.files.create(
        vector_store_id=vector_store_id,
        file_id=uploaded_file.id,
        chunking_strategy={
            "type": "static",
            "static": {
                "max_chunk_size_tokens": CHUNK_MAX_TOKENS,
                "chunk_overlap_tokens": CHUNK_OVERLAP_TOKENS,
            },
        },
        attributes={
            "article_url": delta.article.url,
            "slug": delta.article.slug[:512],
            "content_hash": delta.content_hash,
            "delta_status": delta.status,
        },
    )

    return UploadResult(
        delta=delta,
        openai_file_id=uploaded_file.id,
        vector_store_file_id=vector_store_file.id,
        estimated_chunks=estimate_chunks(delta.markdown_path),
    )


def estimate_chunks(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    estimated_tokens = estimate_tokens(text)
    effective_chunk_size = CHUNK_MAX_TOKENS - CHUNK_OVERLAP_TOKENS
    return max(1, math.ceil(estimated_tokens / effective_chunk_size))


def estimate_tokens(text: str) -> int:
    words = re.findall(r"\S+", text)
    return math.ceil(len(words) / 0.75)
