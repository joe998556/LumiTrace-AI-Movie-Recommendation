# Recommendation Algorithm

LumiTrace is organized around a recommendation engine rather than a traditional movie browsing website. The public demo collects user preference signals in the browser and uses TMDB metadata for a lightweight recommendation flow. The advanced mode documents a service-side BERT vector pipeline for deeper semantic experiments.

## 0. Public Demo Recommendation Flow

The default clone-and-run experience does not require registration, a database, or precomputed vectors.

Public demo flow:

```text
TMDB API key -> trending/search results -> browser-local favorites -> taste profile -> TMDB discover -> local ranking
```

When a user saves favorite movies, LumiTrace stores those movie records in browser `localStorage`. This browser storage is only for lightweight user state. It does not store BERT vectors or generated model indexes.

The recommendation button builds a taste profile from:

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

The one-command bootstrapper fetches movie data from TMDB and combines useful fields into model input text. Newer indexes use rich text enrichment rather than overview-only embeddings:

```text
title + genre names + original language + release year + audience rating + optional director/cast + overview
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

The index is loaded by `ai_engine/bert_service.py`, not by the browser. At startup, the service normalizes vectors into a Torch tensor so search can use tensor operations rather than repeatedly parsing JSON.

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

Current implementation detail:

```text
semantic_scores = movie_vector_tensor @ user_embedding
```

In code this is implemented as a single PyTorch matrix multiplication against the pre-normalized index:

```python
semantic_scores = torch.mm(movie_vector_tensor, user_embedding.T).squeeze(1)
top_scores, top_indices = torch.topk(adjusted_semantic_scores, k=pool_size)
```

This is still a linear scan over the loaded tensor, but it is vectorized and runs through optimized CPU/GPU tensor kernels rather than Python loops. It is reasonable for local single-user experiments at the included presets, especially on CUDA. It is not a production-scale high-concurrency retrieval layer. Larger corpora should move to Faiss, HNSWLib, SQLite vector extensions, or another ANN/vector index.

Defensive tensor handling:

- `movie_vector_tensor` is normalized and made contiguous at index load time
- `user_embedding` is forced to 2D before `torch.mm`
- if the embedding dimension does not match the loaded index dimension, the service returns a clear error instead of failing inside matrix multiplication

If multiple watched movies are provided, the service uses a rating-weighted taste profile. Ratings control contribution strength, not vector direction.

```text
semantic_weight = max(0.1, rating / 5.0)
```

For small histories, this is a single weighted taste center. Once the user has enough positive signals, LumiTrace switches to a lightweight multi-center profile:

```text
positive_movie_embeddings -> 2-3 weighted taste clusters
semantic_scores = max(movie_vector_tensor @ taste_center_i)
```

This prevents unrelated preferences from being averaged into a weak middle vector. A user who likes both hard sci-fi and absurd comedy can keep both taste regions alive during retrieval.

Low-rated movies are not included as negative vectors in the taste embedding. Instead, they are used as a shortlist re-ranking penalty:

```text
shortlist = topk(positive_or_baseline_scores)
negative_similarity = cosine_similarity(candidate, disliked_movie)
dislike_strength = (5 - rating) / 4
negative_penalty = clamp((negative_similarity - 0.55) / 0.45, 0, 1) * dislike_strength
penalty_multiplier = 1 - 0.8 * negative_penalty
adjusted_semantic_score = bert_score * penalty_multiplier
```

This means a candidate that is very close to a movie the user rated 1-4 is discounted after the normal semantic match is computed. The penalty is calculated only on the shortlist, not the full movie index. The service does not subtract disliked movie embeddings, because negative embedding vectors are not reliable "opposite taste" representations.

The final shortlist also receives small post-ranking adjustments:

- `year_score`: nudges candidates toward the release-year range the user tends to watch when clients send `user_release_years`
- `context_score`: boosts zero-shot prompt genre/language matches
- `diversified_score`: applies a small greedy rerank penalty when the top results repeat the same genre/language/collection too aggressively

These are intentionally small compared with semantic similarity. They refine the final Top-K list without drowning out the BERT match.

Cold-start and all-negative cases are handled explicitly:

- no taste text: return a metadata quality fallback from the local index
- only low-rated movies: build a metadata shortlist, then apply the low-rating penalty

## 4. Zero-Shot Semantic Playlist

Zero-shot playlist mode skips the watched-movie requirement. The user can describe an abstract viewing context, for example:

```text
I want a rainy-night European mystery with a quiet pace and a subtle twist.
```

The service treats that text as a semantic query:

```text
playlist_embedding = BERT(scene_prompt)
semantic_scores = movie_vector_tensor @ playlist_embedding
```

Optional metadata filters can be sent with the request:

- `playlist_genre_ids`: TMDB genre IDs such as Mystery `9648` or Thriller `53`
- `preferred_languages`: original-language codes such as `fr`, `de`, `es`, `it`, `ja`

The backend also has lightweight keyword inference for common prompts such as "European", "mystery", "thriller", "slow burn", "rainy night", or Chinese equivalents such as "歐洲", "懸疑", and "反轉". These inferred filters boost and filter candidates after the semantic shortlist. If filters are too strict and produce no results, the service relaxes them and returns the strongest semantic matches instead of failing empty.

This overlaps with hand-curated movie lists, but the behavior is different: the playlist is generated from the user's invented context at request time rather than selected from a fixed list taxonomy.

## 5. Hybrid Ranking

The optional `Final Boss Engine` can combine three offline item-vector signals:

```text
final_score =
  genome_similarity * 0.50 +
  svd_similarity    * 0.30 +
  bert_similarity   * 0.20
```

Signal meanings:

- `BERT`: plot meaning, theme, and semantic similarity from movie descriptions.
- `SVD`: pre-trained matrix-factorization item embeddings from MovieLens-style rating patterns.
- `Genome`: style and tag profile from MovieLens Genome features.

If SVD or Genome vectors are unavailable, the service falls back to the available signals and normalizes the weights.

This is not online personalized collaborative filtering. The public and Android flows do not maintain a central user-item matrix, so they cannot train fresh SVD from private single-user local history. SVD/Genome are optional experiments built from external datasets. A runtime recommender can compare the user's liked movie set with these pre-trained item embeddings, but it should be documented as pre-trained matrix factorization rather than local collaborative training.

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
- move large vector retrieval to a dedicated ANN/vector index if the corpus grows

For engineering limits and production hardening notes, see [docs/ARCHITECTURE_LIMITS.md](docs/ARCHITECTURE_LIMITS.md).
