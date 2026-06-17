# LumiTrace Android v1.0.2

This release hardens the final setup experience for users running their own local BERT server.

## Highlights

- Android now sends an empty taste request to the BERT endpoint so the server can return a cold-start metadata fallback.
- Android movie parsing is more tolerant of partial/fallback recommendation JSON.
- Android keeps personal ratings as decimals when sending them to the recommender.
- BERT service logs cold-start fallback, all-negative rating fallback, unloaded index, empty index, and embedding/index dimension mismatch paths.
- BERT search keeps vectors contiguous, guards 2D tensor shape, and applies low-rating penalties only on the shortlist.

## User Setup

1. Apply for a TMDB API key:

```text
https://www.themoviedb.org/settings/api
```

2. Install:

```text
LumiTrace-v1.0.2-release.apk
```

3. Download the Source code zip from this release and extract it on Windows.
4. Run:

```text
LumiTrace-Windows-AI-Setup.bat
```

5. Paste the printed local endpoint into Android Settings.

If you open **AI Recommend** before adding watched movies, the BERT server can return a metadata fallback list for setup testing.
