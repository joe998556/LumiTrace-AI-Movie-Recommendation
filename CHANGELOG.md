# Changelog

## 1.2.0 - 2026-07-11

This is the first Android-only public release of LumiTrace.

### Added

- Jetpack Compose Android app for TMDB discovery, search, details, and poster browsing.
- Device-local viewing profiles, watched state, favorites, queue, 1-10 ratings, notes, feedback, and timeline.
- Bundled 1,000-film MovieLens/MiniLM index for on-device semantic recommendation.
- Rating-weighted taste profiles, low-rating shortlist penalties, diversity re-ranking, and per-result traces.
- Tonight contextual shortlist and Android home-screen widget.
- Local taste backup import and export without API credentials.
- Optional Trakt device authorization, import, and deliberate upload.
- Optional evidence-only recommendation explanations through Google AI Edge Gallery and `Gemma-4-E4B-it`.
- Android unit tests, lint, build CI, app-first website, setup guide, privacy boundary, and signed APK distribution.

### Removed

- Flask, Python, Docker, BERT service, remote gateway, and self-host deployment requirements.
- Browser application and server configuration paths.

The normal path is now one APK plus the user's own TMDB API key.
