# On-Device Recommendation Algorithm

LumiTrace is a content-based Android recommender. Ranking runs locally from explicit watched and rating signals. The app does not call a LumiTrace recommendation API.

## 1. Bundled Catalog

The APK contains a compact index generated from MovieLens Latest Small:

```text
1,000 movies x 384 dimensions x float16
```

Each movie vector was generated ahead of time with `sentence-transformers/all-MiniLM-L6-v2` from MovieLens title, genre, and community-tag text. Rows are L2-normalized. At app startup, the loader validates the manifest, movie count, dimensions, data type, and vector file size before accepting the index.

No Transformer model runs on the phone. The app decodes the float16 rows into memory and performs dot products against this precomputed catalog.

## 2. Taste Signals

For watched movie `j`, the positive-profile weight is:

```text
unrated watched movie: w_j = 1
rating below 5:        w_j = 0
rating 5 to 10:        w_j = rating_j - 4
```

The normalized taste vector is:

```text
u = normalize(sum(w_j * x_j))
```

An unrated watched movie therefore contributes a modest positive signal. A high rating contributes more. Ratings below 5 do not distort the positive vector; they are handled separately as negative evidence.

## 3. Candidate Score

When a semantic profile is available, each candidate receives:

```text
base_score = 0.78 * semantic_similarity
           + 0.14 * genre_affinity
           + 0.08 * quality_prior
```

- `semantic_similarity` is the dot product between normalized movie and taste vectors.
- `genre_affinity` summarizes the user's explicit rating-weighted genre history.
- `quality_prior` combines normalized TMDB vote average and vote-count confidence.

If none of the watched films can be mapped into the starter index, ranking falls back to:

```text
base_score = 0.72 * genre_affinity + 0.28 * quality_prior
```

This fallback is reported as metadata ranking rather than semantic AI.

## 4. Negative Preference

Ratings below 5 become negative seeds with strength:

```text
negative_strength = clamp((5 - rating) / 4, 0, 1)
```

LumiTrace does not subtract disliked vectors from the taste vector. Instead, it first retrieves a bounded candidate pool, compares only those candidates with negative seeds, and subtracts at most:

```text
negative_penalty = max(candidate_similarity_to_negative * strength) * 0.64
```

This keeps positive semantic geometry intact while strongly suppressing candidates that closely resemble a clearly disliked movie. The coefficient was selected from a 24-point weight grid evaluated across six independently authored film-taste profiles; see [RECOMMENDATION_EVALUATION.md](RECOMMENDATION_EVALUATION.md).

## 5. Diversity Re-Ranking

The top candidate pool is re-ranked greedily. A candidate loses a small score proportional to its maximum genre overlap with an already selected result:

```text
selection_score = current_score - genre_jaccard_overlap * diversity_strength
```

The strength is bounded to `0.0..0.2`. A zero value preserves the original relevance order; higher values trade a small amount of similarity for a broader final list.

## 6. Refresh Variation

An explicit refresh advances a local variation seed. Each shortlisted movie receives a reproducible adjustment in the bounded range `-0.02..0.02`:

```text
selection_score = current_score
                + stable_refresh_adjustment(movie_id, refresh_seed)
                - genre_overlap_penalty
```

The adjustment is deliberately smaller than the taste score components. It changes near-tied membership without turning refresh into random discovery. Loading more results reuses the active seed, while pressing **Refresh recommendations** advances it. Repeating the same seed reproduces the same order, and the adjustment is excluded from the displayed relevance trace.

## 7. Constraints and Exclusions

- Watched seed movies are excluded from results.
- `topK` is bounded to the catalog size and a maximum of 300.
- Tonight can apply required genre groups and minimum or maximum release year before ranking.
- A wider bounded pool is retained before diversity and negative-preference re-ranking.

## 8. Explainability

Each result has a local recommendation trace containing:

- semantic similarity,
- genre affinity,
- quality prior,
- negative-preference penalty,
- diversity adjustment,
- base score,
- final score.

The app also names the closest positive watched movie when that evidence exists. These explanations are deterministic and generated from the same local score trace used for ranking.

## 9. Evaluation

Six independent film-domain personas supplied 90+ watched ratings, including explicit high and low scores, plus narrow unseen positive and negative sets. Compared with the identical watched collections made rating-neutral, calibrated ratings changed an average of 9.5 movies in each Top 20, increased labeled positive hits from 14 to 19, and reduced labeled negative hits from 5 to 2. Refresh changed an average of 4.8 movies while preserving focus-genre and score-loss gates.

The fixtures and assertions live under `app/src/test/resources/recommendation/` and `app/src/test/java/com/lumitrace/app/recommendation/`. These are controlled expert scenarios, not population-level accuracy or an online A/B test. The full protocol and limitations are in [RECOMMENDATION_EVALUATION.md](RECOMMENDATION_EVALUATION.md).

## 10. Limits

The starter index is a demo-scale catalog, not a complete movie universe. A live TMDB result that is absent from the index may still be saved and rated, but it cannot add semantic dimensions to the local profile. Enlarging the index requires a redistributable data source, measured APK-size and memory budgets, and regenerated vectors with exactly the model declared by the manifest.

MovieLens provenance and terms are documented in [DATA_LICENSE.md](DATA_LICENSE.md).
