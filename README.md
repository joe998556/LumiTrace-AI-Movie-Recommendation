<div align="center">

# LumiTrace

### AI Movie Recommendation Engine

**An open-source movie taste engine with a Web demo, Android app, and optional BERT semantic recommender. Bring your own TMDB key, mark what you watched, rate it, and turn taste into recommendations.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask_API-Backend-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![BERT](https://img.shields.io/badge/BERT-Semantic%20Embeddings-FF6B6B?style=for-the-badge)](ALGORITHM.md)
[![TMDB](https://img.shields.io/badge/TMDB-Movie%20Metadata-01B4E4?style=for-the-badge)](https://www.themoviedb.org/)
[![Android](https://img.shields.io/badge/Android-Jetpack%20Compose-2DD4BF?style=for-the-badge&logo=android&logoColor=white)](android/README.md)
[![Status](https://img.shields.io/badge/Status-Active%20Prototype-22C55E?style=for-the-badge)](CHANGELOG.md)
[![CI](https://img.shields.io/github/actions/workflow/status/joe998556/LumiTrace-AI-Movie-Recommendation/ci.yml?branch=main&label=CI&style=for-the-badge)](https://github.com/joe998556/LumiTrace-AI-Movie-Recommendation/actions/workflows/ci.yml)

[Algorithm](ALGORITHM.md) | [Limits](docs/ARCHITECTURE_LIMITS.md) | [Android](android/README.md) | [Windows AI Quickstart](docs/WINDOWS_AI_QUICKSTART.md) | [Operations](docs/OPERATIONS.md) | [Roadmap](ROADMAP.md) | [Contributing](CONTRIBUTING.md) | [Security](SECURITY.md) | [Changelog](CHANGELOG.md) | [Setup](#quick-start)

</div>

---

## Why LumiTrace?

At-home movie watching has never had more choice, but choice is now the problem. Most people do not need another giant catalog. They need a faster way to find films that actually match their taste.

LumiTrace is built around a more personal question:

> If a user likes these stories, what other movies feel semantically close?

The website and Android app are only the surfaces. The core of the project is the recommendation pipeline:

```text
TMDB movies -> watched list -> ratings and notes -> taste profile -> ranked recommendations
```

The public flow works without registration or a hosted user database. User taste data stays local by default, while the optional BERT gateway can be connected for deeper semantic recommendations.

## What Makes It Interesting

| Layer | Why It Matters |
| --- | --- |
| No-account demo | Anyone can clone it, paste a TMDB key, and test movie discovery immediately. |
| Personal taste signals | Watched movies, ratings, genres, plots, and notes become a lightweight taste profile. |
| Rating-weighted BERT | A 9/10 watched movie boosts similar stories; a 2/10 movie suppresses similar matches. |
| Web plus mobile | The same idea works as a browser demo and a Kotlin/Jetpack Compose Android app. |
| Public-safe setup | The repo ships without private endpoints, tokens, vector indexes, APKs, or keystores. |
| Scalable experiment path | Start with TMDB metadata ranking, then plug in a BERT vector service for semantic retrieval. |

## Project Snapshot

| Area | What LumiTrace Does |
| --- | --- |
| Public demo core | TMDB metadata, favorite genres, rating/vote signals |
| Advanced engine | BERT semantic similarity over movie plots |
| User signal | Watched movies, ratings, genres, plot overviews, movie IDs |
| Retrieval | TMDB trending, search, and discover endpoints |
| Advanced retrieval | Precomputed movie vector index loaded by the optional BERT service |
| Ranking | Metadata ranking in demo, rating-weighted BERT service in advanced mode; SVD/Genome are offline experimental item-vector builders |
| Backend | Flask API for TMDB proxying and static app serving |
| Demo surface | Web UI for entering a TMDB key, collecting favorites, and showing recommendations |
| Mobile app | Android Kotlin/Jetpack Compose app with local TMDB key storage, watched movies, ratings, notes, and optional AI gateway |
| Safety | `.env`-based secrets, ignored local DB/vector/model files, Android local properties, APKs, and keystores |

## Current Status

LumiTrace is under active maintenance as an open-source AI recommendation prototype.

Recent maintenance work:

- Reworked the app into a public demo mode with no registration required.
- Added browser-local favorites and recommendations from user-provided TMDB API keys.
- Added a public-safe Android app under [android/](android/README.md).
- Added watched movies, 1.0-10.0 personal ratings, and short journal notes in the mobile app.
- Moved the Android AI endpoint into Settings so public builds do not embed a lab gateway.
- Added rating-weighted BERT recommendations: high scores boost similar movies, low scores reduce similar movies.
- Clarified current architecture limits: browser `localStorage` stores user taste only, while BERT vectors live in the service process.
- Added a low-rating post-ranking penalty so disliked movies reduce similar candidates without using negative vector subtraction.
- Hardened BERT search edge cases: contiguous vector tensors, 2D embedding guards, shortlist-only negative penalties, and metadata fallback for cold-start/all-negative taste input.
- Added a Windows AI quickstart BAT that asks for a TMDB key, lets users choose vector size, detects the LAN IP, and prints the Android endpoint.
- Simplified the backend to static serving, TMDB proxying, optional streaming proxying, and health checks.
- Added an optional semantic recommendation proxy so the web demo can use the BERT service when configured.
- Added a one-command recommender bootstrapper with selectable data sizes.
- Added GitHub Actions smoke checks for Python syntax, JavaScript syntax, setup validation, and backend health.
- Added a public-safe `/api/health` endpoint for backend readiness checks.
- Reframed the project around the recommendation algorithm instead of the web UI.
- Added [ALGORITHM.md](ALGORITHM.md) with a focused explanation of the scoring pipeline.
- Added public-safe environment configuration with `.env.example`.
- Removed hardcoded API keys from vector generation scripts.
- Ignored local secrets, SQLite databases, generated vectors, model files, IDE settings, and local agent settings.
- Added contribution and security policy documents for future maintainers.
- Added [ROADMAP.md](ROADMAP.md) and [CHANGELOG.md](CHANGELOG.md) for ongoing development.

## How The Recommendation Works

### 1. Public Demo: Build A Taste Profile

In the public demo flow, users paste their own TMDB API key, browse live TMDB movies, and save films that match their taste. LumiTrace stores those signals locally and builds a lightweight taste profile from:

- favorite movie genres
- vote averages
- vote counts
- movie IDs to exclude from recommendations

### 2. Public Demo: Rank Candidates

The recommendation button queries TMDB Discover with the user's strongest genre signals, excludes already-saved movies, and ranks candidates by genre overlap, rating, vote history, and similarity to the user's average rating.

```text
favorite movies -> genre profile -> TMDB discover -> local ranking -> recommendations
```

### 3. Advanced Mode: Build Movie Vectors

The vector generation script fetches movie metadata from TMDB and builds a text representation for each movie:

```text
title + overview + vote_average + genre_ids
```

That text is embedded with:

```text
AventIQ-AI/bert-movie-recommendation-system
```

The generated semantic index is saved as:

```text
movie_vectors.json
```

Generated vector files are intentionally ignored by Git because they can be large and can be regenerated. They are not stored in browser `localStorage`; the optional BERT service loads them server-side as a normalized Torch tensor.

Newly generated indexes use rich-text embeddings instead of overview-only embeddings. The vector input includes title, TMDB genre names, original language, release year, audience rating, optional director/cast fields when present, and the plot overview. If you already have an older `movie_vectors.json`, regenerate it with `--overwrite` to get the richer semantic index:

```powershell
python tools/bootstrap_recommender.py --preset xlarge --overwrite
```

### 4. Advanced Mode: Build A User Taste Query

When a user marks movies as watched, the client can send the BERT service:

- watched movie overviews
- watched movie IDs to exclude from results
- genre IDs as taste constraints
- personal ratings as preference weights

The BERT service embeds the watched movie overviews and uses them as the user's taste query. Ratings change the strength of the signal:

| User rating | Effect |
| --- | --- |
| 1-4 | Reduce the movie's contribution and clamp related genre weight |
| 5 | Neutral taste signal |
| 6-10 | Boost similar genre/semantic matches |

This means a movie you loved and a movie you disliked do not teach the recommender the same thing. The service does not subtract disliked movie vectors from the taste embedding; low ratings are conservative negative feedback rather than a claim that embedding-space "opposites" are meaningful.

When a user has several positive signals, the service can split taste into multiple lightweight centers before retrieval. This keeps independent tastes from collapsing into one average embedding, so a profile that contains both sci-fi and comedy can still recall good candidates from both regions.

### 5. Advanced Mode: Zero-Shot Semantic Playlists

LumiTrace can also generate a playlist from a free-form scene prompt, without requiring watched movies first.

Example:

```text
A rainy-night European mystery with a quiet pace and a subtle twist.
```

The client sends that text as the semantic query, optionally with language and genre filters:

```json
{
  "overviews": ["A rainy-night European mystery with a quiet pace and a subtle twist."],
  "playlist_genre_ids": [9648, 53],
  "preferred_languages": ["fr", "de", "es", "it"],
  "top_k": 30
}
```

The BERT service embeds the prompt, compares it with the local movie vector tensor via `torch.mm`, and combines the semantic score with TMDB genre/language metadata. This makes LumiTrace closer to an on-demand semantic playlist generator than a fixed hand-curated list system.

### 6. Advanced Mode: Score Candidate Movies

The service compares the user's taste query with every precomputed movie vector in the local BERT service.

```text
bert_score = cosine_similarity(user_embedding, movie_embedding)
```

Implementation detail:

```python
semantic_scores = torch.mm(movie_vector_tensor, user_embedding.T).squeeze(1)
top_scores, top_indices = torch.topk(adjusted_semantic_scores, k=pool_size)
```

`movie_vector_tensor` is pre-normalized when the BERT service starts, so this matrix multiplication acts as batched cosine similarity. At the current 30k local index scale, this keeps retrieval lightweight without introducing a heavier vector database. A public high-concurrency service should still move to an ANN/vector index such as Faiss, HNSWLib, SQLite vector extensions, or a managed vector database.

The service also applies two defensive tensor safeguards:

- vector indexes are normalized and stored as contiguous 2D tensors at startup
- user embeddings are forced to 2D before matrix multiplication, so single-vector inputs do not break `torch.mm`
- positive histories with enough examples can use 2-3 taste centers; candidates are recalled by the best center score
- final ranking adds small year-affinity and diversity adjustments so the Top-K list is not just a stack of near-duplicates

In rating-weighted mode, semantic matching is combined with metadata preferences so the model can explain recommendations in human terms:

```text
rating_delta = user_rating - 5
genre_weight = max(0, 1 + rating_delta)
semantic_weight = max(0.1, user_rating / 5)
```

High-rated watched movies pull similar candidates upward. Low-rated watched movies reduce the same region of the taste space.

Low ratings are applied as a shortlist re-ranking penalty rather than negative vector subtraction:

```text
shortlist = topk(positive_or_baseline_scores)
negative_similarity = cosine_similarity(candidate, disliked_movie)
negative_penalty = clamp((negative_similarity - 0.55) / 0.45, 0, 1) * dislike_strength
penalty_multiplier = 1 - 0.8 * negative_penalty
adjusted_semantic_score = bert_score * penalty_multiplier
```

This keeps disliked movies from pointing the taste vector into noisy "opposite embedding" space. The penalty is computed only for the shortlist rather than the full index, so negative feedback stays cheap even when the local index is large.

If there are no positive taste inputs yet, LumiTrace falls back to a metadata quality shortlist and still applies low-rating penalties when disliked movies are available.

### 7. Advanced Mode: Hybrid Ranking

The optional `final_boss_engine.py` experiment can blend three offline item-vector signals:

```text
final_score =
  genome_similarity * 0.50 +
  svd_similarity    * 0.30 +
  bert_similarity   * 0.20
```

| Signal | Meaning |
| --- | --- |
| BERT | Plot meaning, theme, atmosphere, story similarity |
| SVD | Offline item vectors trained from external MovieLens-style rating patterns |
| Genome | MovieLens-style tag and style profile |

If SVD or Genome vectors are missing, the service falls back to the available signals and normalizes the weights. The public and Android flows do not train online collaborative filtering from a private single-user history.

For the full breakdown, see [ALGORITHM.md](ALGORITHM.md).
For current performance and production limits, see [docs/ARCHITECTURE_LIMITS.md](docs/ARCHITECTURE_LIMITS.md).

## Architecture

```text
Browser UI
  |
  v
Flask Backend (app.py)
  |-- static app serving
  |-- TMDB API proxy
  |-- optional streaming API proxy
  |
  v
Browser localStorage
  |-- TMDB API key
  |-- favorite movies
  |-- recommendation profile
  |
  v
Recommended Movies
```

The default clone-and-run path uses only the Flask backend and browser-local favorites. The BERT service can still run separately for advanced semantic recommendation experiments.

Browser storage is intentionally limited to lightweight user settings and movie records. Large vector indexes stay in the BERT service process, not in `localStorage`.

## Android App

The Android app lives in [android/](android/README.md). It is a public-safe mobile client for the same recommendation idea:

- paste and store a TMDB API key locally
- browse TMDB movie feeds and search results
- mark movies as watched
- rate watched movies from 1.0 to 10.0
- write short private notes
- open an independent recommendation page
- optionally connect a local Windows BERT server such as `http://192.168.x.x:5001/search`, or a public HTTPS gateway, from Settings

The open-source Android build does not include a private AI endpoint. This is intentional. APKs can be reverse engineered, so long-lived gateway tokens and private model hosts should stay behind a server-side reverse proxy.

```text
Android app
  |-- local TMDB key
  |-- local watched movies
  |-- local ratings and notes
  |
  | optional LAN or HTTPS gateway
  v
BERT recommendation service
```

## Repository Structure

```text
.
|-- app.py                         # Flask backend, TMDB proxy, static app serving
|-- index.html                     # Demo UI
|-- recommendations.html           # Redirects to the main page recommendation section
|-- script.js                      # Frontend logic
|-- ai_engine/
|   |-- bert_service.py            # Semantic recommendation API
|   |-- generate_vectors.py        # Compatibility wrapper for the vector bootstrapper
|   |-- generate_vectors_massive.py
|   |-- generate_vectors_infinity.py
|   |-- final_boss_engine.py       # Merge BERT, SVD, and Genome vectors
|   `-- train_collaborative_vectors.py
|-- tools/
|   |-- bootstrap_recommender.py   # Download TMDB data and build BERT vectors
|   `-- check_setup.py             # Local readiness checker
|-- android/                       # Kotlin/Jetpack Compose mobile app
|   |-- README.md                  # Android setup, AI gateway, and release notes
|   |-- USER_GUIDE.md              # APK install and endpoint setup guide
|   `-- app/                       # Android app module
|-- LumiTrace-Windows-AI-Setup.bat # Windows guided BERT setup for APK users
|-- setup_recommender.bat          # Windows one-click recommender setup
|-- docs/
|   |-- ARCHITECTURE_LIMITS.md     # Current search, storage, and production limits
|   |-- WINDOWS_AI_QUICKSTART.md   # Non-technical APK + local BERT setup guide
|   `-- OPERATIONS.md              # Local operations runbook
|-- ALGORITHM.md                   # Recommendation algorithm explanation
|-- CONTRIBUTING.md                # Contribution guide
|-- SECURITY.md                    # Public security policy
|-- ROADMAP.md                     # Planned AI and product improvements
|-- CHANGELOG.md                   # Maintenance history
|-- .env.example                   # Safe environment template
`-- .gitignore
```

## Quick Start

Choose one surface:

| Surface | Path | Use When |
| --- | --- | --- |
| Web demo | repository root | You want the fastest clone-and-run recommendation demo. |
| Android app | [android/](android/README.md) | You want the mobile UI with watched movies, ratings, notes, and optional AI gateway. |
| BERT service | [ai_engine/](ai_engine/) | You want semantic recommendation over generated movie vectors. |

Before using LumiTrace, apply for your own TMDB API key:

```text
https://www.themoviedb.org/settings/api
```

TMDB provides the movie catalog, posters, genres, titles, and overviews. LumiTrace does not ship a shared key.

## Fastest Android + Local AI Setup

This is the easiest path for people who just want to install the APK and try BERT recommendations on their own Windows PC.

1. Go to the latest GitHub Release.
2. Download and install the latest `LumiTrace-*-release.apk`.
3. Download the Source code zip and extract it on your Windows PC.
4. Double-click:

```text
LumiTrace-Windows-AI-Setup.bat
```

The BAT will:

- remind you to apply for or copy your TMDB API key
- ask you to paste the TMDB API key
- let you choose data size: `demo`, `small`, `medium`, `large`, or `xlarge`
- install Python dependencies
- download TMDB movie metadata
- build the local BERT vector index
- detect your PC LAN IP
- print a phone endpoint such as:

```text
http://192.168.1.23:5001/search
```

On Android, open Settings and paste:

- your TMDB API key
- the endpoint printed by the BAT

Then keep the Windows BAT/server window open, mark and rate watched movies, open **AI Recommend**, and run recommendations.

Full step-by-step guide: [docs/WINDOWS_AI_QUICKSTART.md](docs/WINDOWS_AI_QUICKSTART.md).

## Web Demo Quick Start

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a local environment file:

```bash
cp .env.example .env
```

This file is optional for the public demo. You can also paste your TMDB API key directly into the web UI after opening the app.

Optional `.env` values:

```text
TMDB_API_KEY=your_tmdb_key
RAPID_API_KEY=your_rapidapi_key
REMOTE_SEARCH_URL=http://127.0.0.1:5001/search
LUMITRACE_VECTOR_FILE=movie_vectors.json
LUMITRACE_DEVICE=auto
SSL_VERIFY=false
```

Start the Flask backend:

```bash
python app.py
```

Open:

```text
http://localhost:8080
```

Paste your TMDB API key into the page, click "Save and Load Trending", save movies you like, then click "Show My Recommendations".

The public demo UI is English-only. TMDB requests default to `en-US` so movie titles and overviews are also pulled in English when available.

Check backend readiness:

```text
http://localhost:8080/api/health
```

The health endpoint reports whether the backend is running and which integrations are configured. It only returns booleans/status values, never API keys or private service URLs.

Run a local setup check:

```bash
python tools/check_setup.py
```

The setup checker reports required files, environment variable presence, and whether generated vector indexes exist. It does not print secret values.

## One-Command Recommendation Model Setup

The public demo works without vectors. For deeper semantic recommendations, build a local BERT movie index. New users can choose how much TMDB data to download:

| Preset | Approx. movies | Best for |
| --- | ---: | --- |
| `demo` | 200 | Fast smoke test |
| `small` | 1,000 | First usable local model |
| `medium` | 5,000 | Better coverage, GPU recommended |
| `large` | 15,000 | Wide recommendation coverage |
| `xlarge` | 30,000 | Long overnight/GPU build |

More movies usually means better coverage, but the TMDB download and BERT embedding step take longer.

Interactive setup:

```bash
python tools/bootstrap_recommender.py
```

Non-interactive setup:

```bash
python tools/bootstrap_recommender.py --preset small --tmdb-key YOUR_TMDB_KEY
```

For a GPU machine on the same LAN, clone this repository on that machine and run:

```bash
pip install -r requirements.txt
python tools/bootstrap_recommender.py --preset medium --tmdb-key YOUR_TMDB_KEY --device cuda
python ai_engine/bert_service.py --host 0.0.0.0 --port 5001
```

Then set the CPU/backend machine's `.env` to:

```text
REMOTE_SEARCH_URL=http://GPU_PC_IP:5001/search
```

Windows users can also run the guided APK/local-AI setup:

```text
LumiTrace-Windows-AI-Setup.bat
```

For developer-only vector generation, `setup_recommender.bat` still works. Both scripts create or update:

```text
movie_vectors.json
```

The file is ignored by Git because it can be large and is reproducible.

## Running The Advanced BERT Service

After generating vectors, start the semantic recommendation service:

```bash
python ai_engine/bert_service.py
```

To let the web app use BERT recommendations, set this in `.env`:

```text
REMOTE_SEARCH_URL=http://127.0.0.1:5001/search
```

Then restart the Flask backend:

```bash
python app.py
```

The old vector command still works and forwards to the same English bootstrapper:

```bash
python ai_engine/generate_vectors.py --preset small
```

The BERT service expects one of these files:

```text
movie_vectors.json
final_boss_vectors.json
```

## Security Notes

This repository is prepared for public GitHub release.

Ignored local files include:

- `.env`
- `dev_v4.db`
- `.venv/`
- `.vscode/`
- `.claude/`
- `.agents/`
- `scratch/`
- `movie_vectors.json`
- `final_boss_vectors.json`
- model weights and array files such as `*.pt`, `*.pth`, `*.pkl`, `*.npy`, `*.npz`
- Android `local.properties`
- Android build outputs, APKs, AABs, and keystores

API keys are loaded from `.env` and are not committed to the repository.

For the public demo, the TMDB API key entered in the UI is stored only in browser localStorage and sent to the local Flask proxy as a request header.

For the Android app, the TMDB key and optional AI endpoint are stored on the device. The public source does not embed a lab endpoint, fixed server IP, gateway token, or signing key.

For contribution and security guidelines, see [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

## Roadmap

Next planned improvements:

- conversational recommendation mode
- recommendation explanations
- small sample vector index for smoke tests
- vector search optimization
- optional ANN/vector index integration for larger local indexes

See [ROADMAP.md](ROADMAP.md) for the full plan.

For local service operation and troubleshooting, see [docs/OPERATIONS.md](docs/OPERATIONS.md).

## Attribution

This product uses TMDB and the TMDB APIs but is not endorsed, certified, or otherwise approved by TMDB.

Movie metadata, posters, and backdrop images are provided by TMDB. Streaming availability data depends on the configured provider API.
