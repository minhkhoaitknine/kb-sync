from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None
    openai_vector_store_id: str | None
    article_limit: int
    data_dir: str


def load_settings() -> Settings:
    load_dotenv()

    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_vector_store_id=os.getenv("OPENAI_VECTOR_STORE_ID"),
        article_limit=int(os.getenv("ARTICLE_LIMIT", "30")),
        data_dir=os.getenv("DATA_DIR", "data"),
    )

