# LumiTrace - AI Movie Recommendation

LumiTrace is an AI-powered movie recommendation system that uses BERT semantic embeddings to recommend movies from a user's favorites. It combines TMDB movie metadata, streaming provider information, a Flask API backend, and a standalone BERT recommendation service.

This project is designed as a working prototype of an AI recommendation workflow: collect movie metadata, turn plots into vectors, compare semantic similarity, and explain recommendations through a web interface.

## Current Status

LumiTrace is under active maintenance as an open-source AI recommendation prototype. The current focus is making the BERT recommendation pipeline easier to understand, safer to run locally, and clearer for future contributors.

Recent maintenance work:

- Renamed and documented the project as LumiTrace.
- Added public-safe environment configuration with `.env.example`.
- Removed hardcoded API keys from vector generation scripts.
- Added a clearer BERT architecture and data pipeline overview.
- Ignored local secrets, SQLite databases, generated vectors, model files, IDE settings, and local agent settings.
- Added project roadmap and changelog files for ongoing development.

Repository:

```text
https://github.com/joe998556/LumiTrace-AI-Movie-Recommendation
```

## Core Idea

Most simple movie recommenders rely on genres, ratings, or popularity. LumiTrace focuses on semantic similarity. If a user saves several movies they like, the system extracts the plot overviews, converts them into BERT embeddings, and searches for movies with similar story, theme, and style signals.

The goal is not only to recommend "popular action movies" or "high-rated dramas", but to recommend movies whose narrative meaning is close to what the user already enjoys.

## What This Project Does

This project lets users browse movies, save favorites, and receive AI-powered recommendations. The recommendation engine does not only compare genres or popularity. It converts movie plots into BERT semantic vectors, compares the meaning of the user's favorite movies against a movie vector database, and returns movies with similar story/theme signals.

In short: users collect movies they like, and the system recommends other movies whose plots and style are semantically close.

## Highlights

- Browse trending movies and search TMDB movie data.
- Save favorite movies by user.
- Generate recommendations from a user's favorite movie plots.
- Use a backend proxy so TMDB and RapidAPI keys are not exposed in frontend code.
- Support a remote BERT recommendation service for semantic movie matching.
- Optional hybrid recommendation engine with BERT, SVD, and MovieLens genome features.

## AI Architecture

```text
Browser UI
  -> Flask backend (app.py)
      -> TMDB / streaming API proxy
      -> user favorites stored in SQLite
      -> recommendation request
          -> BERT service (ai_engine/bert_service.py)
              -> load movie_vectors.json or final_boss_vectors.json
              -> embed user's favorite movie overviews
              -> compare vectors with cosine similarity
              -> return ranked movie recommendations
```

The backend and the BERT service are separated on purpose. The Flask app handles user-facing APIs and hides external API keys. The BERT service focuses on model loading, vector search, and recommendation scoring, so it can run on another machine if needed.

## How The AI Recommendation Works

The BERT model used in this project is:

```text
AventIQ-AI/bert-movie-recommendation-system
```

It is loaded with Hugging Face Transformers in `ai_engine/bert_service.py` and the vector generation scripts.

The core recommendation flow starts from the movies a user has already liked. For each favorite movie, the system collects text signals such as title, overview, genres, vote count, and TMDB metadata.

The BERT pipeline turns movie overviews into dense semantic vectors. Instead of only matching exact keywords, the model compares the meaning of plots. For example, two films can be considered similar even when they do not share the same title words, as long as their story structure, genre signals, or themes are close in embedding space.

At recommendation time, the backend sends the user's recent favorite movie overviews to the semantic search service. The service embeds the input text, compares it against the movie vector database with cosine similarity, excludes movies the user already saved, and returns the closest candidates.

The advanced `Final Boss Engine` can combine three signals:

- Genome features: style and theme profile from MovieLens genome data.
- SVD taste vectors: collaborative filtering signal from user-rating patterns.
- BERT vectors: semantic similarity from movie descriptions.

The current default weighting in the BERT service is:

```text
Genome 50% + SVD 30% + BERT 20%
```

This makes the recommendation less dependent on one signal. BERT helps understand plot meaning, SVD captures audience taste patterns, and genome features add genre/style structure.

## BERT Model And Data Pipeline

The project has two main AI steps.

Step 1: build movie vectors

```bash
python ai_engine/generate_vectors.py
```

This script fetches movie metadata from TMDB, combines movie title, overview, rating, and genre metadata into text, then uses the BERT model to generate one semantic vector per movie. The generated output is:

```text
movie_vectors.json
```

Step 2: serve recommendations

```bash
python ai_engine/bert_service.py
```

The service loads `movie_vectors.json` or `final_boss_vectors.json`, receives favorite movie overviews from the Flask backend, embeds the query text, compares it against all stored movie vectors, excludes movies already saved by the user, and returns the highest scoring candidates.

For the hybrid version, `ai_engine/final_boss_engine.py` can merge:

- BERT semantic vectors from TMDB movie descriptions.
- SVD collaborative filtering vectors from MovieLens ratings.
- MovieLens Genome style and tag features.

Generated vector files are intentionally ignored by Git because they can be large and are environment-specific.

## Project Structure

```text
.
|-- app.py                         # Flask backend, API proxy, auth, favorites, recommendations
|-- index.html                     # Main movie browsing UI
|-- recommendations.html           # Recommendation result UI
|-- script.js                      # Frontend logic
|-- ai_engine/
|   |-- bert_service.py            # Semantic recommendation API
|   |-- generate_vectors.py        # Build BERT movie vectors from TMDB data
|   |-- generate_vectors_massive.py
|   |-- generate_vectors_infinity.py
|   |-- final_boss_engine.py       # Merge BERT, SVD, and genome vectors
|   `-- train_collaborative_vectors.py
|-- .env.example                   # Safe environment template
|-- CHANGELOG.md                   # Maintenance history
|-- ROADMAP.md                     # Planned AI and product improvements
`-- .gitignore
```

## Environment Variables

Create a local `.env` file from `.env.example`:

```bash
cp .env.example .env
```

Then fill in your local values:

```text
TMDB_API_KEY=your_tmdb_key
RAPID_API_KEY=your_rapidapi_key
REMOTE_SEARCH_URL=your_bert_search_service_url
OLLAMA_URL=your_ollama_chat_service_url
SSL_VERIFY=false
```

Do not commit `.env`. The repository includes `.env.example` only.

## Running Locally

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the Flask app:

```bash
python app.py
```

Open:

```text
http://localhost:8080
```

To run the BERT recommendation service separately:

```bash
python ai_engine/bert_service.py
```

Then set the Flask app to call the local recommendation service:

```text
REMOTE_SEARCH_URL=http://127.0.0.1:5001/search
```

The BERT recommendation service requires a generated vector file in the project root:

```text
movie_vectors.json
```

If that file does not exist, run `ai_engine/generate_vectors.py` first.

## Public Repository Notes

This repo intentionally ignores local secrets, databases, generated vectors, model weights, and virtual environments.

Ignored examples:

- `.env`
- `dev_v4.db`
- `.venv/`
- `movie_vectors.json`
- `final_boss_vectors.json`
- `*.pt`, `*.pth`, `*.pkl`, `*.npy`, `*.npz`

Security-related cleanup already applied:

- API keys are read from `.env` instead of being hardcoded in frontend code.
- `.env.example` is provided as a safe template.
- Local database files and generated vector files are ignored.
- Local IDE and agent settings are ignored.

## Roadmap

See `ROADMAP.md` for planned improvements, including conversational recommendations, richer recommendation explanations, vector search optimization, and a cleaner public demo setup.

## Changelog

See `CHANGELOG.md` for recent maintenance notes.

## Attribution

This product uses TMDB and the TMDB APIs but is not endorsed, certified, or otherwise approved by TMDB.

Movie metadata, posters, and backdrop images are provided by TMDB. Streaming availability data depends on the configured provider API.
