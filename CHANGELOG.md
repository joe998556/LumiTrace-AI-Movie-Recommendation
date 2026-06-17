# Changelog

All notable project maintenance updates are tracked here.

## 2026-06-17

- Added a Windows AI quickstart BAT for APK users who want to run the BERT service on their own PC.
- Added a step-by-step Windows AI quickstart guide covering TMDB API setup, data-size selection, LAN endpoint detection, and Android Settings setup.
- Updated Android documentation for private LAN endpoints such as `http://192.168.x.x:5001/search` and public HTTPS gateways.
- Updated the Android client to allow private LAN HTTP BERT endpoints while keeping public gateway guidance on HTTPS.
- Added Android v1.0.1 release notes for the local AI setup flow.
- Added architecture limit notes that separate browser-local state from service-side vector indexes.
- Clarified that SVD/Genome support is an offline experiment, not online collaborative filtering over private local user history.
- Clarified that current BERT retrieval uses a linear Torch tensor scan and should move to ANN/vector indexing for larger or public workloads.
- Optimized BERT search scoring with Torch matrix multiplication, `torch.topk` shortlist ranking, decimal user ratings, and post-ranking penalties for low-rated movies.
- Added defensive BERT search handling for 2D tensor shape, contiguous vector storage, shortlist-only penalties, invalid `top_k`, cold-start fallback, and all-negative rating input.
- Added clearer BERT fallback/error logging and hardened Android parsing for fallback recommendation responses and decimal ratings.
- Reduced Android recommendation-page jank by throttling auto load-more, removing per-row reveal animations from result rows, and using lighter poster image sizes for grid cards.
- Fixed Android release JSON parsing after minification so recommendation API responses no longer fail with generic type errors.
- Improved Android recommendation accuracy by sending aligned taste signals: explicit prompt text, watched movie plots, 1-10 ratings, genre metadata, and personal notes.
- Added zero-shot semantic playlist support with free-form scene prompts, optional language/genre filters, Web UI controls, and Android recommendation-page prompt input.

## 2026-06-15

- Added GitHub Actions smoke CI for Python syntax, JavaScript syntax, setup validation, and Flask health checks.
- Added a README CI status badge for easier public maintenance visibility.
- Converted the public demo UI, model setup notes, and TMDB metadata defaults to English.

## 2026-06-13

- Reworked the main app into a clone-and-run public demo with no login or registration flow.
- Added browser-local TMDB API key entry, local favorites, and a "Show My Recommendations" recommendation button.
- Simplified the backend to static serving, TMDB proxying, optional streaming proxying, and public-safe health checks.
- Added an optional `/api/semantic-recommendations` proxy for BERT-powered recommendations.
- Added `tools/bootstrap_recommender.py` with selectable dataset sizes for building `movie_vectors.json`.
- Replaced the legacy vector generator entry point with a compatibility wrapper.
- Reworked `ai_engine/bert_service.py` into a clean standalone semantic recommendation service.
- Added `setup_recommender.bat` for Windows one-click recommender setup.
- Redirected the old recommendation page back to the main page recommendation section.
- Updated documentation for the public demo flow and optional advanced BERT mode.

## 2026-06-12

- Added `.editorconfig` to keep formatting consistent across Python, JavaScript, HTML, JSON, YAML, and Markdown files.
- Added `tools/check_setup.py` for public-safe local setup checks.
- Documented the setup checker in the README.
- Added `docs/OPERATIONS.md` with local runbook, health check, BERT service, and troubleshooting notes.
- Added Dependabot configuration for weekly Python dependency maintenance.

## 2026-06-09

- Added `CONTRIBUTING.md` with setup, testing, and recommendation-pipeline contribution guidance.
- Added `SECURITY.md` with secret handling rules and current hardening notes.
- Linked contribution and security documents from the README.

## 2026-06-05

- Added GitHub issue templates for bug reports and feature requests.
- Added a pull request template with security and documentation checks.
- Improved repository maintenance workflow for future open-source collaboration.

## 2026-06-02

- Added a public-safe `/api/health` endpoint for backend readiness checks.
- Documented the health endpoint in the README.
- Kept health output limited to status values and integration booleans so secrets are not exposed.

## 2026-06-01

- Reframed the README around the recommendation algorithm rather than the web UI.
- Added `ALGORITHM.md` with a focused explanation of movie vectors, user taste profiles, semantic similarity, hybrid ranking, and filtering rules.
- Strengthened the public README with a clearer AI architecture overview.
- Documented the BERT model and movie vector generation pipeline.
- Added local setup notes for running the Flask backend and BERT recommendation service.
- Added public repository safety notes for ignored secrets, databases, vector files, and local agent settings.
- Added this changelog to make project maintenance easier to follow.
- Added a roadmap for upcoming AI recommendation improvements.

## 2026-05-31

- Renamed the project to LumiTrace - AI Movie Recommendation.
- Prepared the repository for public GitHub release.
- Added `.env.example` and expanded `.gitignore`.
- Removed hardcoded TMDB API keys from vector generation scripts.
- Replaced private default service URLs with environment-based configuration.
- Verified that `.env`, local SQLite databases, generated vectors, virtual environments, and local settings are not committed.
