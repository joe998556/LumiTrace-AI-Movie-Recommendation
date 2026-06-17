# LumiTrace Android v1.0

This is the first public-safe Android APK release for LumiTrace.

## Highlights

- Kotlin + Jetpack Compose Android app.
- New LT teal launcher icon.
- TMDB movie browsing and search.
- Local watched movie list.
- 1.0-10.0 personal rating slider.
- Short private movie notes.
- Dedicated AI Recommendation page.
- Optional HTTPS BERT gateway configured from Settings.
- No embedded lab endpoint, fixed server IP, gateway token, TMDB key, APK signing key, or private infrastructure detail.

## Install

Download:

```text
LumiTrace-v1.0-release.apk
```

If a debug build is already installed, uninstall it first before installing this release APK.

## First Use

1. Open LumiTrace.
2. Go to Settings.
3. Paste your TMDB API key.
4. Tap Save setup.
5. Browse movies, mark watched titles, add ratings and notes.

## AI Endpoint Setup

AI recommendations are optional. Without an endpoint, LumiTrace still works as a TMDB browser, watched list, rating journal, and note app.

To enable AI recommendations, paste your own HTTPS `/search`-compatible BERT gateway in Settings:

```text
https://your-domain.example/lumitrace/api/recommend
```

The Android app expects a POST endpoint that accepts watched movie overviews, genre IDs, user ratings, excluded movie IDs, and `top_k`, then returns a JSON object with `results`.

See [android/USER_GUIDE.md](USER_GUIDE.md) for the full setup guide.

## Security

Do not put long-lived gateway tokens in the APK. Use this deployment shape:

```text
Android app -> HTTPS reverse proxy -> private BERT service
```

Put authentication, rate limits, and gateway-token injection on the reverse proxy or backend.
