# Repository Guidelines

## Project Structure & Module Organization
`main.py` runs the daily clipping pipeline end to end; `main_production.py` is the hardened path that reads only verified sources and publishes artifacts to `output/`. Configuration and shared paths live in `config.py` via the `settings` singleton, which also creates `data/`, `logs/`, and `templates/`. Scraping and enrichment code is separated by concern: collectors in `scraper.py` and `news_sources.py`, classifiers and LLM helpers in `classifier.py`, `llm_processor*.py`, and `fact_checker.py`, while delivery code (`mailchimp_integration.py`, `newsletter_composer.py`) handles exports. Tests and smoke utilities (`test_*.py`, `test_run.py`) stay co-located with the modules they exercise for quick discovery.

## Build, Test, and Development Commands
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python main.py                 # full clipping workflow
python main_production.py      # production-only run
pytest                         # run entire test suite
pytest -k izimedia             # target izimedia connectors
```
Activate the virtualenv before running scripts and keep `.env` aligned with `.env.example`; missing keys cause LLM and Mailchimp fallbacks.

## Coding Style & Naming Conventions
Use Python 3.10+, PEP 8 spacing, and 4-space indents. Continue the existing pattern of type hints, descriptive docstrings, and `Path` objects for filesystem work. Classes and enums use CamelCase (`NewsClassifier`, `NewsSection`), functions and variables stay snake_case, and constants or configurable values belong in `config.py`. Route all diagnostic output through `loguru` so logs rotate under `logs/`.

## Testing Guidelines
`pytest` is the primary framework; add new files as `test_<module>.py` next to the code they exercise. Mock external services (Mailchimp, Banco Central, LLMs) to keep suites offline-friendly and document any live calls. `test_run.py` works as a manual integration check—only run it when the keyword spreadsheet and API keys are present. Record skipped or flaky checks in the PR description.

## Commit & Pull Request Guidelines
When syncing into Git, follow Conventional Commits (`feat:`, `fix:`, `chore:`) with subjects under 72 characters and bodies that capture context, data sources, and feature flags. PRs must describe scope, list validation commands (`pytest`, manual scripts), call out configuration updates, and attach newsletter previews or screenshots when the rendered output changes.

## Security & Configuration Tips
Populate secrets exclusively through `.env`; never commit real credentials or client spreadsheets. Verify access to `/Users/alfil/Mi unidad/0_Consultorias/Proyecta/Palabras_Claves.xlsx` before classification runs and update `settings.KEYWORDS_FILE` if the path changes. Rotate API keys regularly, enable Sentry when available, and scrub generated logs before external sharing.
