# LumiTrace Android v1.0.3

This release focuses on recommendation-page smoothness on real phones.

## Highlights

- Throttled automatic recommendation load-more so dragging near the bottom does not repeatedly hammer the BERT endpoint.
- Prevented duplicate load-more requests for the same recommendation result size.
- Removed per-row reveal animations from recommendation result rows to reduce recomposition and GPU work.
- Switched grid poster cards to lighter TMDB poster sizes while keeping higher-quality images for hero/detail surfaces.
- AI recommendation can run even before watched movies are added, allowing the BERT server to return its metadata fallback list.

## When To Update

Install this version if the recommendation page becomes laggy while scrolling down through posters or while triggering more AI results.

## User Setup

1. Install:

```text
LumiTrace-v1.0.3-release.apk
```

2. Keep using your own BERT endpoint in Settings, for example:

```text
https://your-domain.example/lumitrace/api/recommend
```

No server-side vector rebuild is required for this Android performance update.
