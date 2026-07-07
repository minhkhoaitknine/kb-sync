import argparse
import sys

from src.assistant_config import ask_optibot, create_optibot_assistant
from src.config import load_settings
from src.gemini_assistant import ask_gemini_optibot
from src.gemini_upload import create_file_search_store


DEFAULT_TEST_QUESTION = "How do I add a YouTube video?"


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Configure and test OptiBot assistant.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("create", help="Create provider search/assistant resource.")

    ask_parser = subparsers.add_parser("ask", help="Ask the assistant a test question.")
    ask_parser.add_argument("question", nargs="?", default=DEFAULT_TEST_QUESTION)

    args = parser.parse_args()
    settings = load_settings()

    if settings.ai_provider not in {"openai", "gemini"}:
        raise SystemExit("AI_PROVIDER must be either 'openai' or 'gemini'.")

    if args.command == "create":
        if settings.ai_provider == "gemini":
            if not settings.gemini_api_key:
                raise SystemExit("GEMINI_API_KEY is required.")

            store_name = create_file_search_store(
                api_key=settings.gemini_api_key,
                display_name="optibot-support-docs",
            )
            print(f"GEMINI_FILE_SEARCH_STORE_NAME={store_name}")
            print("Copy this value into your .env file.")
            return

        if not settings.openai_api_key:
            raise SystemExit("OPENAI_API_KEY is required.")
        if not settings.openai_vector_store_id:
            raise SystemExit("OPENAI_VECTOR_STORE_ID is required.")

        assistant_id = create_optibot_assistant(
            api_key=settings.openai_api_key,
            vector_store_id=settings.openai_vector_store_id,
            model=settings.openai_model,
        )
        print(f"OPENAI_ASSISTANT_ID={assistant_id}")
        print("Copy this value into your .env file.")
        return

    if args.command == "ask":
        if settings.ai_provider == "gemini":
            if not settings.gemini_api_key:
                raise SystemExit("GEMINI_API_KEY is required.")
            if not settings.gemini_file_search_store_name:
                raise SystemExit("GEMINI_FILE_SEARCH_STORE_NAME is required.")

            answer = ask_gemini_optibot(
                api_key=settings.gemini_api_key,
                file_search_store_name=settings.gemini_file_search_store_name,
                model=settings.gemini_model,
                question=args.question,
            )
            print(f"model={answer.model}")
            print(answer.text)
            return

        if not settings.openai_api_key:
            raise SystemExit("OPENAI_API_KEY is required.")
        if not settings.openai_assistant_id:
            raise SystemExit("OPENAI_ASSISTANT_ID is required.")

        answer = ask_optibot(
            api_key=settings.openai_api_key,
            assistant_id=settings.openai_assistant_id,
            question=args.question,
        )
        print(f"run_status={answer.run_status}")
        print(f"thread_id={answer.thread_id}")
        print(f"run_id={answer.run_id}")
        if answer.error_code or answer.error_message:
            print(f"error_code={answer.error_code}")
            print(f"error_message={answer.error_message}")
        print(answer.text)


if __name__ == "__main__":
    main()
