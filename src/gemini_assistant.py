from __future__ import annotations

from dataclasses import dataclass
import time

from google import genai
from google.genai import types

from src.assistant_config import SYSTEM_PROMPT


FALLBACK_MODELS = ("gemini-2.5-flash", "gemini-2.5-flash-lite")
MAX_ATTEMPTS_PER_MODEL = 2
RETRYABLE_STATUS_CODES = {429, 503}


@dataclass(frozen=True)
class GeminiAnswer:
    text: str
    model: str


def ask_gemini_optibot(
    *,
    api_key: str,
    file_search_store_name: str,
    model: str,
    question: str,
) -> GeminiAnswer:
    client = genai.Client(api_key=api_key)
    prompt = f"{SYSTEM_PROMPT}\n\nUser question: {question}"

    last_error: Exception | None = None
    for candidate_model in model_candidates(model):
        for attempt in range(1, MAX_ATTEMPTS_PER_MODEL + 1):
            try:
                response = client.models.generate_content(
                    model=candidate_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        tools=[
                            types.Tool(
                                file_search=types.FileSearch(
                                    file_search_store_names=[file_search_store_name]
                                )
                            )
                        ]
                    ),
                )
                return GeminiAnswer(text=response.text or "", model=candidate_model)
            except Exception as exc:
                last_error = exc
                if not is_retryable_model_error(exc):
                    raise
                if attempt < MAX_ATTEMPTS_PER_MODEL:
                    time.sleep(3 * attempt)

    raise RuntimeError(
        "Gemini model calls failed after retrying fallback models."
    ) from last_error


def model_candidates(primary_model: str) -> list[str]:
    candidates = [primary_model, *FALLBACK_MODELS]
    deduped: list[str] = []
    for candidate in candidates:
        if candidate not in deduped:
            deduped.append(candidate)
    return deduped


def is_retryable_model_error(exc: Exception) -> bool:
    status_code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    return status_code in RETRYABLE_STATUS_CODES
