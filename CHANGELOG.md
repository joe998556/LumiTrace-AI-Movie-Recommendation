# Changelog

## Unreleased

### Added

- Six independent film-domain taste fixtures with high ratings, low ratings, unseen positive examples, and unseen negative examples.
- Reproducible rating-neutral, calibrated-rating, and unchanged-collection refresh evaluation reports.
- A tested refresh-seed sequence that keeps load-more stable and changes only explicit refresh runs.

### Changed

- Calibrated semantic, genre, and quality weights to `0.78 / 0.14 / 0.08` across a 24-point grid.
- Increased post-ranking low-score suppression to `0.64`; low-rated vectors remain outside the positive taste centroid.
- Recommendation controls now say **Refresh recommendations** after the first result set.

## 1.2.1 - 2026-07-12

### Changed

- Reworked Tonight filters into compact, labeled groups.
- Replaced the static Tonight result list with animated swipeable pick cards.
- Refined the movie detail surface around the poster, actions, feedback, and journal.
- Removed the unusable Google AI Edge Gallery integration.

### Fixed

- Tonight recommendations now show their real watched state instead of a hard-coded `Watched` label.

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
- Android unit tests, lint, build CI, app-first website, setup guide, privacy boundary, and signed APK distribution.

### Removed

- Flask, Python, Docker, BERT service, remote gateway, and self-host deployment requirements.
- Browser application and server configuration paths.

The normal path is now one APK plus the user's own TMDB API key.
