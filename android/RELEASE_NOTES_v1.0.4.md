# LumiTrace Android v1.0.4

This release focuses on real-device recommendation reliability and better taste signals.

## What Changed

- Fixed release-build JSON parsing for Retrofit/Gson after R8 minification.
- Prevented the `java.lang.Class cannot be cast to java.lang.reflect.ParameterizedType` recommendation error.
- Improved AI recommendation requests by combining:
  - explicit prompt text from the search box
  - watched movie titles and plots
  - 1-10 personal ratings
  - genre metadata
  - personal journal notes
- Kept prompt, rating, and genre arrays aligned so the BERT service receives clean user taste data.

## How To Try It

1. Install:

```text
LumiTrace-v1.0.4-release.apk
```

2. Open Settings.
3. Add your TMDB API key.
4. Add your BERT endpoint, for example:

```text
https://your-domain.example/lumitrace/api/recommend
```

5. Mark movies as watched, give 1-10 ratings, optionally add short notes, then run AI recommendation.

## Security

This release does not include private gateway tokens, lab IP addresses, keystore files, or API keys.
