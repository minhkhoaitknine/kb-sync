# Submission Notes

## What This Project Does

- Discovers the latest OptiSigns Zendesk support articles.
- Fetches article HTML and extracts only the article body.
- Converts cleaned content to Markdown with frontmatter and an `Article URL:` citation line.
- Computes a stable content hash for delta detection.
- Uploads only new, changed, or missing documents to the configured provider store.
- Uses Gemini File Search by default, with OpenAI Vector Store support kept in the code.
- Runs as a one-shot Docker job and as a scheduled GitHub Actions workflow.

## Chunking Strategy

Gemini File Search is configured with whitespace chunking:

- `max_tokens_per_chunk = 512`
- `max_overlap_tokens = 128`

The overlap keeps nearby context together across chunk boundaries. The chunk size stays within Gemini's current API limit and is small enough for support articles where answers usually come from one section.

## Delta Strategy

`data/state.json` stores article metadata, content hashes, provider upload metadata, and target store IDs. On each run:

- `added`: no previous record exists.
- `updated`: content hash changed.
- `skipped`: content hash is unchanged.
- `needs_upload`: true if content changed, upload metadata is missing, target store changed, or `--force-upload` is used.

`data/state.json` is ignored by Git because it is runtime state. The daily workflow restores and saves it through GitHub Actions cache.

## Final Checklist

- Run `python -m unittest discover -s tests -p "test_*.py"`.
- Run `docker build -t optibot-ingest .`.
- Run `docker run --rm --env-file .env -v ${PWD}/data:/app/data optibot-ingest`.
- Run `python assistant.py ask "How do I add a YouTube video?"`.
- If the first run auto-created a Gemini store, paste the printed `GEMINI_FILE_SEARCH_STORE_NAME` into `.env` and GitHub Actions secrets.
- Save a screenshot of the assistant answer under `screenshots/`.
- Add GitHub secrets `GEMINI_API_KEY` and `GEMINI_FILE_SEARCH_STORE_NAME`.
- Trigger `Daily OptiBot Ingest` manually once and copy the run URL into the README before final submission.

## Review Talking Points

- I used the Zendesk API first because it is more stable than scraping list pages.
- I stored Markdown locally because it gives a debuggable artifact between scraping and retrieval.
- I used hashes instead of timestamps alone because web timestamps can be missing or unreliable.
- I kept upload state outside Git because vector store file IDs are environment-specific runtime metadata.
- I made the Docker job one-shot because scheduled jobs should exit cleanly and produce clear logs.
