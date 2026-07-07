from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import re
import time

from google import genai

from src.state import ArticleDelta


CHUNK_MAX_TOKENS = 512
CHUNK_OVERLAP_TOKENS = 128
POLL_SECONDS = 5


@dataclass(frozen=True)
class GeminiUploadResult:
    delta: ArticleDelta
    file_search_store_name: str
    operation_name: str
    estimated_chunks: int


def create_file_search_store(*, api_key: str, display_name: str) -> str:
    client = genai.Client(api_key=api_key)
    store = client.file_search_stores.create(
        config={
            "display_name": display_name,
        }
    )
    return store.name


def upload_delta_files_to_gemini(
    deltas: list[ArticleDelta],
    *,
    api_key: str,
    file_search_store_name: str,
) -> list[GeminiUploadResult]:
    client = genai.Client(api_key=api_key)
    results: list[GeminiUploadResult] = []

    for delta in deltas:
        result = upload_one_delta_file(
            client,
            file_search_store_name=file_search_store_name,
            delta=delta,
        )
        results.append(result)

    return results


def upload_delta_file_to_gemini(
    delta: ArticleDelta,
    *,
    api_key: str,
    file_search_store_name: str,
) -> GeminiUploadResult:
    client = genai.Client(api_key=api_key)
    return upload_one_delta_file(
        client,
        file_search_store_name=file_search_store_name,
        delta=delta,
    )


def upload_one_delta_file(
    client: genai.Client,
    *,
    file_search_store_name: str,
    delta: ArticleDelta,
) -> GeminiUploadResult:
    operation = client.file_search_stores.upload_to_file_search_store(
        file_search_store_name=file_search_store_name,
        file=delta.markdown_path,
        config={
            "display_name": delta.markdown_path.name,
            "chunking_config": {
                "white_space_config": {
                    "max_tokens_per_chunk": CHUNK_MAX_TOKENS,
                    "max_overlap_tokens": CHUNK_OVERLAP_TOKENS,
                }
            },
        },
    )

    operation = wait_for_operation(client, operation)

    return GeminiUploadResult(
        delta=delta,
        file_search_store_name=file_search_store_name,
        operation_name=operation.name,
        estimated_chunks=estimate_chunks(delta.markdown_path),
    )


def wait_for_operation(client: genai.Client, operation):
    while not operation.done:
        time.sleep(POLL_SECONDS)
        operation = client.operations.get(operation)
    if getattr(operation, "error", None):
        raise RuntimeError(operation.error)
    return operation


def estimate_chunks(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    estimated_tokens = estimate_tokens(text)
    effective_chunk_size = CHUNK_MAX_TOKENS - CHUNK_OVERLAP_TOKENS
    return max(1, math.ceil(estimated_tokens / effective_chunk_size))


def estimate_tokens(text: str) -> int:
    words = re.findall(r"\S+", text)
    return math.ceil(len(words) / 0.75)
