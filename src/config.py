from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    ai_provider: str
    openai_api_key: str | None
    openai_vector_store_id: str | None
    openai_assistant_id: str | None
    openai_model: str
    gemini_api_key: str | None
    gemini_file_search_store_name: str | None
    gemini_model: str
    article_limit: int
    data_dir: str


def load_settings() -> Settings:
    load_dotenv()

    return Settings(
        ai_provider=os.getenv("AI_PROVIDER", "openai").strip().lower(),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_vector_store_id=os.getenv("OPENAI_VECTOR_STORE_ID"),
        openai_assistant_id=os.getenv("OPENAI_ASSISTANT_ID"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        gemini_file_search_store_name=os.getenv("GEMINI_FILE_SEARCH_STORE_NAME"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
        article_limit=int(os.getenv("ARTICLE_LIMIT", "30")),
        data_dir=os.getenv("DATA_DIR", "data"),
    )
