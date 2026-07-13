# LumiTrace

<p align="center">
  <img src="assets/lumitrace-app-icon.png" width="112" height="112" alt="LumiTrace app icon">
</p>

<p align="center"><strong>A private, local-first movie taste engine for Android.</strong></p>

<p align="center">
  <a href="https://github.com/joe998556/LumiTrace-AI-Movie-Recommendation/releases/latest/download/LumiTrace.apk"><strong>Download the latest APK</strong></a>
  &nbsp;|&nbsp;
  <a href="https://joe998556.github.io/LumiTrace-AI-Movie-Recommendation/">Product page</a>
  &nbsp;|&nbsp;
  <a href="https://joe998556.github.io/LumiTrace-AI-Movie-Recommendation/guide.html">Setup guide</a>
</p>

<p align="center">
  <a href="https://github.com/joe998556/LumiTrace-AI-Movie-Recommendation/actions/workflows/ci.yml"><img src="https://github.com/joe998556/LumiTrace-AI-Movie-Recommendation/actions/workflows/ci.yml/badge.svg" alt="Android CI"></a>
  <img src="https://img.shields.io/badge/Android-7.0%2B-36d6c2" alt="Android 7.0 or newer">
  <img src="https://img.shields.io/badge/release-v1.3.0-f28c6f" alt="Version 1.3.0">
  <a href="LICENSE"><img src="https://img.shields.io/badge/code-MIT-9bc6b8" alt="MIT license"></a>
</p>

LumiTrace turns watched movies and 1-10 ratings into explainable recommendations without a LumiTrace account or recommendation server. Install one APK, enter your own TMDB API key, and the app is ready to browse, track, rate, and recommend.

> **Development status:** release and source builds now contain the 30,000-movie index described below.

## Start in Three Steps

1. Download [`LumiTrace.apk`](https://github.com/joe998556/LumiTrace-AI-Movie-Recommendation/releases/latest/download/LumiTrace.apk) from the latest GitHub Release.
2. Create a TMDB API key at [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api), then save it in **Settings > TMDB**.
3. Mark movies as watched and optionally rate them. Open **Recommend** to build a local taste profile.

Android may ask for permission to install an app from your browser or file manager. The APK is published directly from this repository; its SHA-256 checksum is attached to the release.

## What It Does

- Browse trending, popular, top-rated, upcoming, and genre collections from TMDB.
- Search the TMDB catalog and open poster-rich movie details.
- Record watched status, favorites, a 1-10 score, and private journal notes.
- Keep separate local viewing profiles for solo, partner, or family taste.
- Produce an infinite recommendation feed from watched and rated films.
- Refresh a recommendation run to explore a different set of near-tied matches without changing the saved collection.
- Build a focused **Tonight** shortlist with year, genre, language, runtime, and diversity controls.
- Explain each recommendation with semantic, genre, quality, negative-preference, and diversity signals.
- Export or import a local taste backup without exporting API credentials.
- Add a home-screen widget for the current Tonight pick.

## No LumiTrace Backend

The release app does not connect to a LumiTrace server. Its recommendation path is packaged inside the APK:

```text
watched movies + ratings
        |
        v
weighted local taste vector
        |
        v
30,000-movie rich-text BERT index
        |
        v
semantic score + genre affinity + quality prior
        |
        v
low-rating penalty + diversity re-ranking
```

The development index contains 30,000 normalized 768-dimensional float16 vectors generated ahead of time. The phone performs vector lookup and scoring; it does not run a Transformer model at recommendation time. Metadata and vectors are streamed from the APK to control peak loading memory. Read [ALGORITHM.md](ALGORITHM.md) for the exact weights, quality gate, and fallback behavior.

## Measured Rating Influence

Six independent film-domain personas created high- and low-rated collections from the bundled catalog. Against the same collections with all ratings neutralized:

- ratings changed an average of **10.8 movies per Top 20**;
- focus genres covered **118 of 120** rated recommendation slots;
- the narrow labeled negative set fell from **1 hit to 0**;
- an unchanged collection refresh changed **6.8 movies per Top 20** on average while keeping relevance loss below the test gate.

These are reproducible controlled scenarios, not production A/B results. The original exact-title positive sets cover only a tiny fraction of the expanded catalog, so broad focus coverage and an independent qualitative review are reported alongside exact hits. See [RECOMMENDATION_EVALUATION.md](RECOMMENDATION_EVALUATION.md) for the method and remaining weaknesses.

## Privacy Boundary

**Stored on the phone:** watched movies, ratings, notes, profiles, recommendation feedback, the TMDB key, and optional Trakt credentials.

**Sent to TMDB:** movie discovery, search, details, and image requests made with the user's own key.

**Never required:** a LumiTrace account, analytics, a lab endpoint, a BERT server, Docker, Python, or a public IP address.

Android cloud backup is disabled. Clearing the app's data removes the local profile. See the [live privacy boundary](https://joe998556.github.io/LumiTrace-AI-Movie-Recommendation/privacy.html) and [SECURITY.md](SECURITY.md) for the complete boundary.

## Optional Trakt Sync

Connect your own Trakt API application to deliberately import watched history and ratings or upload selected local changes. Trakt remains off until the user configures and invokes it.

## Build From Source

Use Android Studio with its bundled JDK and Android SDK 36, or run the Gradle wrapper from PowerShell after setting `JAVA_HOME`:

```powershell
git clone https://github.com/joe998556/LumiTrace-AI-Movie-Recommendation.git
cd LumiTrace-AI-Movie-Recommendation
.\gradlew.bat :app:testDebugUnitTest :app:lintDebug :app:assembleDebug
```

The debug APK is written to:

```text
app/build/outputs/apk/debug/app-debug.apk
```

No API key is needed to compile or test the project. Enter the key only inside the installed app.

## Project Map

```text
app/src/main/java/com/lumitrace/app/
  data/             Encrypted local taste state and profile operations
  recommendation/   On-device vector loading, ranking, penalties, traces
  network/          Direct TMDB and optional Trakt clients
  ui/               Jetpack Compose application and view model
app/src/main/assets/lumitrace/
  movies.json       30,000-movie evaluation metadata snapshot
  vectors.npy       Normalized 768-d float16 BERT vectors
  manifest.json     Index model, dimensions, and provenance
app/src/test/resources/recommendation/
  expert_profiles.json  Six independent high/low-rated taste fixtures
RECOMMENDATION_EVALUATION.md  Protocol, results, limitations, rerun steps
```

## Current Scope

The release build packages 30,000 candidates in a roughly 60 MiB debug APK (about 54 MiB unsigned release). Only movies represented in this index can contribute a semantic vector or be returned by the local semantic ranker. The index improves coverage substantially, but qualitative evaluation still finds weaker separation between authored animation and branded family titles, and between cerebral science fiction and effects-led genre films.

Software is released under the [MIT License](LICENSE). The bundled evaluation metadata and vector index have separate terms and a publication warning in [DATA_LICENSE.md](DATA_LICENSE.md).

Movie metadata and posters are provided by TMDB. This product uses the TMDB API but is not endorsed, certified, or otherwise approved by TMDB.
