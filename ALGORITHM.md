# LumiTrace Recommendation Algorithm

LumiTrace has a browser-local metadata fallback and an optional semantic path. Both use the same saved-film and 1-10 rating records; neither requires an account or a centralized user profile.

## 1. Input Signals

Each saved movie carries its TMDB metadata. The browser can also attach a 1-10 rating, a short note, and immediate **More like this** or **Less like this** feedback.

- `6-10`: a positive taste signal.
- `5`: neutral; it does not move the semantic taste center.
- `1-4`: a negative signal used only for a post-ranking penalty.
- More/Less feedback becomes a local `9` or `2` signal until the user changes it.

Free-text prompts, such as "a quiet mystery for a rainy evening", are treated as an additional positive semantic query rather than a fabricated movie preference.

## 2. Lite Semantic Retrieval

`tools/bootstrap_recommender.py` creates `movie_vectors.json` from enriched TMDB text:

```text
title + genre names + language + release year + TMDB rating + overview
```

`ai_engine/bert_service.py` loads the vectors once, converts them into one L2-normalized matrix `X`, and keeps it resident on the selected CPU or GPU. Positive user vectors are weighted by rating and combined into a normalized taste center `u`.

```python
semantic_scores = torch.mm(movie_vector_tensor, user_embedding.T).squeeze(1)
```

This is exact vector retrieval, not a hidden secondary recommender. The service retrieves a short semantic candidate set before any adjustment is applied.

## 3. Negative Preference Without Negative Vectors

A disliked movie is not multiplied by `-1` and added to the taste center. That would not mean "the opposite of this movie" in a semantic embedding space.

Instead, for a short candidate list, LumiTrace measures similarity to each low-rated seed and calculates a bounded penalty. The final candidate score is reduced only when that similarity is high:

```text
final = semantic_score * (1 - 0.75 * negative_penalty)
        + genre_bonus + language_bonus
```

This keeps positive retrieval stable while making obvious near-neighbours of low-rated films less likely to surface.

## 4. Familiar Versus Surprise

The Familiar-to-Surprise control changes only the final diversity re-rank. A higher value adds a small deterministic penalty for repeated genres, languages, and collection IDs in the already retrieved list. It does not invent a different taste profile or call a second model.

## 5. Grounded Recommendation Reasons

Each semantic result ships with machine-readable evidence:

- the closest saved positive films,
- matched genre IDs,
- rating strength,
- whether similarity to low-rated films was reduced.

The Web UI renders that evidence directly. If the user has configured an LLM narrator, it receives the evidence JSON and may turn it into a concise spoiler-free sentence. It is not allowed to choose candidates, alter their scores, add plot facts, or access the full user history.

## 6. Metadata Fallback

When no vector service is configured, the Web client uses TMDB discovery data and a transparent profile based on genre overlap, TMDB rating, vote count, and the viewer's own rating pattern. This keeps the clone-and-run path useful while making the semantic service an explicit upgrade rather than a hidden dependency.

## 7. Operational Limits

The semantic service is designed for personal or small self-hosted catalogs. It uses exact linear retrieval over one local tensor index. Larger deployments should add rate limiting, queueing, observability, and an approximate-nearest-neighbour index such as Faiss or HNSW.
