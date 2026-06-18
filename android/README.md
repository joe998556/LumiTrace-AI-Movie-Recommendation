# LumiTrace Android

LumiTrace is an Android movie discovery app built with Kotlin and Jetpack Compose. It lets users bring their own TMDB API key, browse live movie data, mark watched films, write short viewing notes, rate movies from 1.0 to 10.0, and optionally connect a BERT-powered recommendation gateway.

## What It Does

- Browse TMDB trending, popular, top-rated, now-playing, and upcoming movie feeds.
- Search movies directly through TMDB.
- Save watched movies locally on the device.
- Add personal ratings and short journal notes.
- Send watched movie taste signals to an optional BERT semantic recommendation endpoint.
- Keep TMDB keys and AI gateway URLs in local encrypted preferences when supported by the device.

For APK users, see the step-by-step [User Guide](USER_GUIDE.md).

## Privacy Defaults

The open-source build does not include a TMDB API key, gateway token, lab server IP, or private BERT endpoint.

This means users can browse and journal with only a TMDB key. AI recommendations require either their own local LAN BERT server or their own HTTPS BERT gateway.

Users configure these from the app:

1. Open **Settings**.
2. Paste a TMDB API key.
3. Optionally paste a local BERT endpoint such as `192.168.1.23:5001/search`, or a HTTPS gateway URL.
4. Save setup.

If the AI gateway is left blank, LumiTrace still works as a TMDB movie browser and personal taste journal.

## AI Gateway Contract

For the easiest local setup, download the Source code zip from GitHub Releases and run:

```text
LumiTrace-Windows-AI-Setup.bat
```

The BAT asks for a TMDB API key, lets users choose the movie data size, builds vectors, detects the PC LAN IP, and prints an Android endpoint such as:

```text
http://192.168.1.23:5001/search
```

The phone and PC must be on the same Wi-Fi/LAN. Public internet deployments should use HTTPS behind a reverse proxy.

The optional AI gateway should accept:

```http
POST /search-compatible-endpoint
Content-Type: application/json
```

Request body:

```json
{
  "overviews": ["A sci-fi movie about space travel"],
  "exclude_ids": [123],
  "user_genre_ids": [[878, 12]],
  "user_vote_counts": [9],
  "user_release_years": [2014],
  "playlist_genre_ids": [878],
  "preferred_languages": ["en"],
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

Ratings are sent as 1-10 preference weights. Higher ratings boost similar semantic and genre signals; lower ratings reduce similar signals. Release years are optional taste hints used for small final-rank adjustments.

For zero-shot semantic playlists, `overviews` can contain a free-form scene prompt instead of watched movie plots. `playlist_genre_ids` and `preferred_languages` are optional filters used by the BERT gateway when available.

## Build

Requirements:

- Android Studio
- JDK bundled with Android Studio
- Android SDK

Debug build:

```powershell
$env:JAVA_HOME='C:\Program Files\Android\Android Studio\jbr'
$env:ANDROID_HOME="$env:LOCALAPPDATA\Android\Sdk"
.\gradlew.bat :app:assembleDebug
```

Optional: prefill a non-secret public AI endpoint for a local build:

```powershell
.\gradlew.bat :app:assembleDebug -PLUMITRACE_REMOTE_SEARCH_URL=https://your-domain.example/lumitrace/api/recommend
```

Do not use this for secrets. APKs can be reverse engineered, so long-lived gateway tokens must stay on a server-side reverse proxy.

## Release Notes

Before publishing an APK or AAB:

- Use a release keystore stored outside the repository.
- Keep `local.properties`, keystore files, API keys, and gateway tokens out of Git.
- Put rate limiting and abuse protection in front of any public BERT gateway.
- Prefer a reverse proxy that injects private gateway headers server-side.
- Do not publish debug APKs as official releases.

## Repository Safety

The project `.gitignore` excludes:

- local Android SDK paths
- Gradle and Kotlin build caches
- generated APK/AAB files
- keystores and certificates
- local secret property files
- old generated Android project artifacts

If you fork LumiTrace, use your own TMDB key and your own recommendation gateway.
