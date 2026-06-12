# Changelog

All notable project maintenance updates are tracked here.

## 2026-06-13

- Reworked the main app into a clone-and-run public demo with no login or registration flow.
- Added browser-local TMDB API key entry, local favorites, and a "你適合看以下這些" recommendation button.
- Simplified the backend to static serving, TMDB proxying, optional streaming proxying, and public-safe health checks.
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
