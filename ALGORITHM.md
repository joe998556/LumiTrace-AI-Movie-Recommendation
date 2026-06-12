# Recommendation Algorithm

LumiTrace is organized around a recommendation engine rather than a traditional movie browsing website. The public demo collects user preference signals in the browser and uses TMDB metadata for a lightweight recommendation flow. The advanced mode documents a BERT vector pipeline and ranking service for deeper semantic experiments.

## 0. Public Demo Recommendation Flow

The default clone-and-run experience does not require registration, a database, or precomputed vectors.

Public demo flow:

```text
TMDB API key -> trending/search results -> browser-local favorites -> taste profile -> TMDB discover -> local ranking
```

When a user saves favorite movies, LumiTrace stores those movie records in browser `localStorage`. The recommendation button builds a taste profile from:

- favorite movie genre IDs
- favorite movie vote averages
- favorite movie vote counts
- favorite movie IDs to exclude from results

The public demo then queries TMDB Discover with the strongest genre signals and scores candidates locally.

Conceptually:

```text
genre_score = overlap(candidate_genres, favorite_genres)
rating_score = candidate_vote_average
vote_score = log(candidate_vote_count)
taste_score = closeness(candidate_rating, user_average_rating)

final_demo_score =
  genre_score +
  rating_score +
  vote_score +
  taste_score
```

This public mode is intentionally lightweight so anyone can clone the repo, run the backend, paste a TMDB API key, and get recommendations immediately.

## 1. Movie Representation

Each movie is represented as structured metadata plus a semantic text embedding.

The one-command bootstrapper fetches movie data from TMDB and combines useful fields into model input text:

```text
title + overview + vote_average + genre_ids
```

The BERT model used by the project is:

```text
AventIQ-AI/bert-movie-recommendation-system
```

The model converts each movie description into a dense vector. These vectors are saved in:

```text
movie_vectors.json
```

This file acts as the semantic movie index. It is ignored by Git because it can become large and can be regenerated from the scripts.

The bootstrapper supports selectable data sizes:

```text
demo -> small -> medium -> large -> xlarge
```

Larger indexes usually improve recommendation coverage because the semantic service has more candidate movies to compare against. The tradeoff is longer TMDB download time, longer BERT embedding time, and a larger generated JSON file.

## 2. User Taste Profile

When a user saves favorite movies, LumiTrace treats those favorites as positive preference signals.

For a recommendation request, the backend collects recent favorite movies and sends these fields to the recommendation service:

- movie IDs to exclude from results
- movie overviews as semantic input text
- genre IDs as additional taste constraints
- vote counts as a popularity signal

The BERT service embeds the user's favorite movie overviews and compares them against the stored movie vector database.

## 3. Semantic Similarity Search

The recommendation service uses normalized vector similarity to find candidates whose meanings are close to the user's favorite movies.

Conceptually:

```text
user_embedding = BERT(favorite_movie_overviews)
movie_embedding = precomputed BERT(movie_overview)
bert_score = cosine_similarity(user_embedding, movie_embedding)
```

If multiple favorite movies are provided, the service keeps the strongest match signal for each candidate. This lets a recommendation match one strong part of the user's taste rather than averaging everything into a blurry profile.

## 4. Hybrid Ranking

The advanced `Final Boss Engine` can combine three recommendation signals:

```text
final_score =
  genome_similarity * 0.50 +
  svd_similarity    * 0.30 +
  bert_similarity   * 0.20
```

Signal meanings:

- `BERT`: plot meaning, theme, and semantic similarity from movie descriptions.
- `SVD`: collaborative filtering signal from MovieLens-style rating patterns.
- `Genome`: style and tag profile from MovieLens Genome features.

If SVD or Genome vectors are unavailable, the service falls back to the available signals and normalizes the weights.

## 5. Filtering And Practical Ranking Rules

After scoring, LumiTrace applies practical filters:

- exclude movies already saved by the user
- exclude movies with very low or missing ratings
- exclude candidates with too little vote history
- optionally reduce over-popular blockbusters when the user's history suggests indie or niche taste
- optionally reduce genre mismatches when the user's favorite history does not support that genre

This makes the result less like a generic popularity list and more like a personalized recommendation list.

## 6. Why This Approach Matters

Genre-based recommendation can only say "these movies are both sci-fi." BERT-based recommendation can capture softer relationships such as atmosphere, pacing, story structure, and theme.

For example, two films might share few keywords but still feel similar because they both have:

- slow-burn mystery structure
- dystopian science fiction atmosphere
- character-driven psychological tension
- nostalgic coming-of-age tone

LumiTrace is built to capture those semantic connections and use them as recommendation signals.

## 7. Current Model Tooling

The advanced model path now has a reproducible local setup:

- `tools/bootstrap_recommender.py` downloads TMDB movie metadata and creates `movie_vectors.json`.
- `ai_engine/generate_vectors.py` remains as a compatibility wrapper for the same bootstrapper.
- `ai_engine/bert_service.py` loads the generated vectors and exposes `/search`, `/embed`, `/reload_db`, and `/status`.
- `app.py` can forward recommendation requests to the BERT service through `REMOTE_SEARCH_URL`.

## 8. Future Algorithm Work

Planned improvements:

- add explanation generation for each recommendation
- add conversational preference input
- evaluate recommendation quality with hand-labeled examples
- add a small demo vector index for easier local testing
- move large vector retrieval to a dedicated vector database if the corpus grows
