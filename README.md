# LumiTrace - AI Movie Recommendation

LumiTrace is an AI movie recommendation web app. It combines TMDB movie metadata, streaming provider information, user favorites, and a BERT-based semantic recommendation engine to suggest movies that are close to a user's taste.

The project is designed as a demo of an AI recommendation workflow rather than a production authentication system.

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

## Public Repository Notes

This repo intentionally ignores local secrets, databases, generated vectors, model weights, and virtual environments.

Ignored examples:

- `.env`
- `dev_v4.db`
- `.venv/`
- `movie_vectors.json`
- `final_boss_vectors.json`
- `*.pt`, `*.pth`, `*.pkl`, `*.npy`, `*.npz`

## Attribution

This product uses TMDB and the TMDB APIs but is not endorsed, certified, or otherwise approved by TMDB.

Movie metadata, posters, and backdrop images are provided by TMDB. Streaming availability data depends on the configured provider API.
