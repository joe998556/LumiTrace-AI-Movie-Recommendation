# LumiTrace Android User Guide

This guide is for people who download the LumiTrace Android APK from GitHub Releases.

## What You Need

Required:

- Android 7.0 or newer
- A TMDB API key

Optional:

- A local Windows BERT server on the same Wi-Fi/LAN
- Or a HTTPS BERT recommendation gateway

LumiTrace does not include a shared TMDB key or a shared AI endpoint. This is intentional: API keys and private model servers should not be embedded in public APKs.

## Install The APK

1. Download `LumiTrace-v1.0.2-release.apk` from GitHub Releases.
2. Open the APK on your Android device.
3. If Android blocks the install, allow installs from this source.
4. Install LumiTrace.

If you previously installed a debug build, uninstall it first. Debug and release APKs use different signing keys.

## First Setup

1. Open LumiTrace.
2. Tap the settings button in the top-right area.
3. Paste your TMDB API key.
4. Tap **Save setup**.
5. Go back to the home screen.

After saving a valid TMDB key, the app loads trending, popular, top-rated, now-playing, and upcoming movies.

## Normal Mode: No AI Gateway Needed

You can use LumiTrace without an AI endpoint.

Available features:

- browse TMDB movie feeds
- search movies
- open movie detail pages
- mark movies as watched
- rate movies from 1.0 to 10.0
- write short private notes

Your TMDB key, watched list, ratings, and notes stay on the device.

## AI Recommendation Mode

The **AI Recommend** page needs a BERT gateway endpoint. If no endpoint is configured, the app will ask you to add one in Settings.

Open:

```text
Settings -> Connect BERT gateway
```

For local testing, paste the LAN endpoint printed by `LumiTrace-Windows-AI-Setup.bat`, for example:

```text
http://192.168.1.23:5001/search
```

For a public server, paste a HTTPS URL that accepts LumiTrace recommendation requests, for example:

```text
https://your-domain.example/lumitrace/api/recommend
```

Then:

1. Mark a few movies as watched.
2. Rate them from 1.0 to 10.0.
3. Open **AI Recommend**.
4. Tap **Run AI recommendation**.

High ratings boost similar movies. Low ratings reduce similar movies.

If you open **AI Recommend** before adding watched movies, a compatible LumiTrace BERT server can return a metadata fallback list instead of failing. This is useful for first-time setup testing.

## What Endpoint Should I Use?

Use your own gateway if you are running the LumiTrace BERT service.

Easiest local option:

1. Apply for a TMDB API key at `https://www.themoviedb.org/settings/api`.
2. Download the LumiTrace Source code zip from GitHub Releases.
3. Extract it on your Windows PC.
4. Double-click `LumiTrace-Windows-AI-Setup.bat`.
5. Choose the data size.
6. Wait for vectors to build.
7. Paste the printed endpoint into Android Settings.

Your phone and PC must be on the same Wi-Fi/LAN, and the Windows server window must stay open.

The Android app expects a `/search`-compatible POST endpoint:

```http
POST http://192.168.1.23:5001/search
Content-Type: application/json
```

Public HTTPS gateway example:

```http
POST https://your-domain.example/lumitrace/api/recommend
Content-Type: application/json
```

Request body:

```json
{
  "overviews": ["A sci-fi movie about space travel"],
  "exclude_ids": [123],
  "user_genre_ids": [[878, 12]],
  "user_vote_counts": [9],
  "top_k": 20
}
```

Response body:

```json
{
  "results": [
    {
      "id": 21078,
      "title": "Movie title",
      "overview": "Movie overview",
      "poster_path": "/poster.jpg",
      "vote_average": 8.1,
      "genre_ids": [878, 12]
    }
  ]
}
```

The endpoint should return TMDB-style movie fields. `poster_path` should be a TMDB poster path such as `/abc.jpg`.

## How To Host Your Own AI Gateway

Basic shape:

```text
Android app -> HTTPS reverse proxy -> private BERT service
```

Recommended setup:

1. Generate movie vectors with `LumiTrace-Windows-AI-Setup.bat` or `tools/bootstrap_recommender.py`.
2. Start `ai_engine/bert_service.py` on a private machine.
3. Put a HTTPS reverse proxy in front of it.
4. Add authentication, rate limits, and abuse protection at the proxy.
5. Paste the public HTTPS proxy URL into the Android Settings page.

Do not put private gateway tokens inside the Android app. APKs can be reverse engineered.

## Troubleshooting

### Home screen says to set an API key

Open Settings and save a valid TMDB API key.

### Movies do not load

Check:

- the TMDB key is valid
- the device has internet access
- TMDB is reachable from your network

### AI page says the backend is not ready

Check:

- the AI endpoint is not blank
- local LAN endpoints can use `http://192.168.x.x:5001/search`
- public internet endpoints should use `https://`
- the endpoint accepts LumiTrace request JSON
- the endpoint returns `results`
- your reverse proxy can reach the private BERT service

### I do not have an AI endpoint

Leave the AI endpoint blank. The app still works as a movie browser, watched list, rating journal, and personal note app.

## Privacy Notes

The public APK does not include:

- TMDB API keys
- gateway tokens
- private server IP addresses
- lab endpoints
- release keystore files

User-entered settings are stored on the device.
