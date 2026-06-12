# Roadmap

This roadmap tracks planned improvements for LumiTrace. The project is currently a working prototype focused on AI-powered movie recommendation with BERT semantic embeddings.

## Near Term

- Add screenshots or a short demo GIF to the README.
- Add a small sample vector dataset for local smoke testing without requiring a full TMDB vector build.
- Improve startup checks so the backend clearly reports whether TMDB, RapidAPI, BERT search, and chat services are configured.
- Add clearer error messages when `movie_vectors.json` is missing.

## AI Recommendation Improvements

- Add conversational recommendation mode where users can describe preferences in natural language.
- Generate short recommendation explanations such as "recommended because it shares slow-burn sci-fi themes and noir atmosphere."
- Improve ranking by blending BERT similarity, genre overlap, popularity penalties, and user favorite history.
- Evaluate vector search quality with a small hand-labeled recommendation set.
- Explore a lightweight vector database for faster retrieval as the movie corpus grows.

## Data Pipeline Improvements

- Add a documented small-data mode for `generate_vectors.py`.
- Add resume and progress metadata for long vector generation runs.
- Keep generated vector files outside Git while documenting how to reproduce them.
- Add optional MovieLens setup instructions for the hybrid SVD + Genome + BERT engine.

## Security And Public Demo

- Keep `.env`, API keys, local databases, generated vectors, and model weights out of Git.
- Add stricter CORS configuration for deployed environments.
- Replace the demo username-based auth flow with token-based auth if the project becomes more than a prototype.
- Add deployment notes for running the Flask backend and BERT service on separate machines.

## Completed

- Add a local operations runbook.
- Add a public-safe local setup checker.
- Add contribution and security policy documents.
- Add a public-safe `/api/health` endpoint for backend status checks.
