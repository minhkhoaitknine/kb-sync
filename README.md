# OptiBot Mini Clone

Scrapes at least 30 OptiSigns support articles, converts them to Markdown, uploads only new or changed files to a provider search store, and exposes a small CLI for asking OptiBot-style questions.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.sample .env
```

Set these values in `.env`:

```text
AI_PROVIDER=gemini
GEMINI_API_KEY=...
GEMINI_FILE_SEARCH_STORE_NAME=fileSearchStores/...
```

`API_KEY` can also be used in Docker/CI as a generic key for the active provider.

## Run Locally

```powershell
python main.py
python assistant.py ask "How do I add a YouTube video?"
python -m unittest discover -s tests -p "test_*.py"
```

Use `python main.py --force-upload` only when intentionally re-uploading all discovered Markdown files. Normal runs compare content hashes and provider target IDs, then log `added`, `updated`, `skipped`, `upload_candidates`, `uploaded`, and estimated chunks.

## Docker

```powershell
docker build -t optibot-ingest .
docker run --rm --env-file .env -v ${PWD}/data:/app/data optibot-ingest
```

Do not run with literal placeholders such as `-e API_KEY=...`; Docker will pass the three dots as the actual value.

## Daily Job

`.github/workflows/daily-ingest.yml` runs once per day and can also be started manually with `workflow_dispatch`. It builds the Docker image, runs `main.py`, restores/saves `data/state.json` through GitHub Actions cache, and uploads `data/state.json` plus Markdown output as the `optibot-last-run` artifact.

Required GitHub secrets:

```text
GEMINI_API_KEY
GEMINI_FILE_SEARCH_STORE_NAME
```

CI tests run in `.github/workflows/ci.yml`. Screenshot: add the assistant answer screenshot under `screenshots/` before final submission. See `SUBMISSION_NOTES.md` for final review notes.
