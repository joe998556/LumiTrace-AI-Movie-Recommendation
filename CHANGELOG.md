# Changelog

All notable project maintenance updates are tracked here.

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
