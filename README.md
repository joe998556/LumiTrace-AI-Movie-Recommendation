<div align="center">

# LumiTrace

### AI Movie Recommendation Engine

**A BERT-powered recommender that traces a user's movie taste from saved favorites and turns plot semantics into ranked recommendations.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask_API-Backend-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![BERT](https://img.shields.io/badge/BERT-Semantic%20Embeddings-FF6B6B?style=for-the-badge)](ALGORITHM.md)
[![TMDB](https://img.shields.io/badge/TMDB-Movie%20Metadata-01B4E4?style=for-the-badge)](https://www.themoviedb.org/)
[![Status](https://img.shields.io/badge/Status-Active%20Prototype-22C55E?style=for-the-badge)](CHANGELOG.md)

[Algorithm](ALGORITHM.md) | [Roadmap](ROADMAP.md) | [Contributing](CONTRIBUTING.md) | [Security](SECURITY.md) | [Changelog](CHANGELOG.md) | [Setup](#quick-start)

</div>

---

## Why LumiTrace?

Most movie recommenders lean on broad labels like genre, rating, or popularity. LumiTrace is built around a different question:

> If a user likes these stories, what other movies feel semantically close?

The web app is only the demo surface. The core of the project is the recommendation pipeline:

```text
favorite movies -> plot text -> BERT embeddings -> similarity search -> hybrid ranking -> recommendations
```

LumiTrace uses saved favorites as preference signals, embeds movie plots with BERT, compares candidate movies in vector space, and can optionally blend semantic similarity with collaborative filtering and MovieLens Genome-style features.

## Project Snapshot

| Area | What LumiTrace Does |
| --- | --- |
| Recommendation core | BERT semantic similarity over movie plots |
| User signal | Saved favorite movies, genres, vote counts, movie IDs |
| Retrieval | Precomputed movie vector index from TMDB metadata |
| Ranking | BERT similarity, optional SVD, optional Genome features |
| Backend | Flask API for user data, API proxying, and recommendation calls |
| Demo surface | Web UI for collecting favorites and showing recommendations |
| Safety | `.env`-based secrets, ignored local DB/vector/model files |

## Current Status

LumiTrace is under active maintenance as an open-source AI recommendation prototype.

Recent maintenance work:

- Added a public-safe `/api/health` endpoint for backend readiness checks.
- Reframed the project around the recommendation algorithm instead of the web UI.
- Added [ALGORITHM.md](ALGORITHM.md) with a focused explanation of the scoring pipeline.
- Added public-safe environment configuration with `.env.example`.
- Removed hardcoded API keys from vector generation scripts.
- Ignored local secrets, SQLite databases, generated vectors, model files, IDE settings, and local agent settings.
- Added contribution and security policy documents for future maintainers.
- Added [ROADMAP.md](ROADMAP.md) and [CHANGELOG.md](CHANGELOG.md) for ongoing development.

## How The Recommendation Works

### 1. Build Movie Vectors

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

Generated vector files are intentionally ignored by Git because they can be large and can be regenerated.

### 2. Build A User Taste Query

When a user saves favorite movies, the backend collects recent favorites and sends the BERT service:

- favorite movie overviews
- favorite movie IDs to exclude from results
- genre IDs as taste constraints
- vote counts as a popularity signal

The BERT service embeds the favorite overviews and uses them as the user's taste query.

### 3. Score Candidate Movies

The service compares the user's taste query with every precomputed movie vector.

```text
bert_score = cosine_similarity(user_embedding, movie_embedding)
```

For multiple favorites, LumiTrace keeps the strongest semantic match signal so a candidate can match one clear part of the user's taste.

### 4. Hybrid Ranking

The advanced engine can blend three signals:

```text
final_score =
  genome_similarity * 0.50 +
  svd_similarity    * 0.30 +
  bert_similarity   * 0.20
```

| Signal | Meaning |
| --- | --- |
| BERT | Plot meaning, theme, atmosphere, story similarity |
| SVD | Collaborative filtering signal from rating patterns |
| Genome | MovieLens-style tag and style profile |

If SVD or Genome vectors are missing, the service falls back to the available signals and normalizes the weights.

For the full breakdown, see [ALGORITHM.md](ALGORITHM.md).

## Architecture

```text
Browser UI
  |
  v
Flask Backend (app.py)
  |-- TMDB / streaming API proxy
  |-- SQLite favorites
  |-- recommendation request
  |
  v
BERT Service (ai_engine/bert_service.py)
  |-- loads movie_vectors.json or final_boss_vectors.json
  |-- embeds favorite movie overviews
  |-- compares vectors with cosine similarity
  |-- ranks and filters candidates
  |
  v
Recommended Movies
```

The backend and recommendation service are separated so the BERT service can run on another machine, such as a GPU workstation, while the Flask backend serves the web app.

## Repository Structure

```text
.
|-- app.py                         # Flask backend, API proxy, auth, favorites, recommendations
|-- index.html                     # Demo UI
|-- recommendations.html           # Recommendation UI
|-- script.js                      # Frontend logic
|-- ai_engine/
|   |-- bert_service.py            # Semantic recommendation API
|   |-- generate_vectors.py        # Build BERT movie vectors from TMDB data
|   |-- generate_vectors_massive.py
|   |-- generate_vectors_infinity.py
|   |-- final_boss_engine.py       # Merge BERT, SVD, and Genome vectors
|   `-- train_collaborative_vectors.py
|-- tools/
|   `-- check_setup.py             # Local readiness checker
|-- ALGORITHM.md                   # Recommendation algorithm explanation
|-- CONTRIBUTING.md                # Contribution guide
|-- SECURITY.md                    # Public security policy
|-- ROADMAP.md                     # Planned AI and product improvements
|-- CHANGELOG.md                   # Maintenance history
|-- .env.example                   # Safe environment template
`-- .gitignore
```

## Quick Start

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a local environment file:

```bash
cp .env.example .env
```

Fill in your local values:

```text
TMDB_API_KEY=your_tmdb_key
RAPID_API_KEY=your_rapidapi_key
REMOTE_SEARCH_URL=http://127.0.0.1:5001/search
OLLAMA_URL=
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

Check backend readiness:

```text
http://localhost:8080/api/health
```

The health endpoint reports whether the local database is reachable and which integrations are configured. It only returns booleans/status values, never API keys or private service URLs.

Run a local setup check:

```bash
python tools/check_setup.py
```

The setup checker reports required files, environment variable presence, and whether generated vector indexes exist. It does not print secret values.

## Running The BERT Service

Generate movie vectors first:

```bash
python ai_engine/generate_vectors.py
```

Then start the recommendation service:

```bash
python ai_engine/bert_service.py
```

The BERT service expects one of these files in the project root:

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
- `scratch/`
- `movie_vectors.json`
- `final_boss_vectors.json`
- model weights and array files such as `*.pt`, `*.pth`, `*.pkl`, `*.npy`, `*.npz`

API keys are loaded from `.env` and are not committed to the repository.

For contribution and security guidelines, see [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

## Roadmap

Next planned improvements:

- conversational recommendation mode
- recommendation explanations
- small sample vector index for smoke tests
- vector search optimization
- cleaner deployment notes for running backend and BERT service on separate machines

See [ROADMAP.md](ROADMAP.md) for the full plan.

## Attribution

This product uses TMDB and the TMDB APIs but is not endorsed, certified, or otherwise approved by TMDB.

Movie metadata, posters, and backdrop images are provided by TMDB. Streaming availability data depends on the configured provider API.
