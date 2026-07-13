# On-Device Recommendation Algorithm

LumiTrace is a content-based Android recommender. Ranking runs locally from explicit watched and rating signals. The app does not call a LumiTrace recommendation API.

## 1. Bundled Catalog

The current development APK contains a precomputed rich-text semantic index:

```text
30,000 movies x 768 dimensions x float16
```

Each movie vector was generated ahead of time with `AventIQ-AI/bert-movie-recommendation-system` from rich movie text. Rows are L2-normalized. At app startup, the loader validates the manifest, movie count, dimensions, data type, and vector file size before accepting the index.

No Transformer model runs on the phone. Movie metadata and float16 vectors are parsed as streams, avoiding temporary copies of the 16 MB JSON and 46 MB NPY assets. The vectors are decoded once into memory and the app performs dot products against the precomputed catalog.

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
base_score = 0.64 * semantic_similarity
           + 0.22 * genre_affinity
           + 0.14 * quality_prior
```

- `semantic_similarity` is the dot product between normalized movie and taste vectors.
- `genre_affinity` summarizes the user's explicit rating-weighted genre history.
- `quality_prior` combines a Bayesian-adjusted TMDB vote average with logarithmic vote-count confidence.

The Bayesian quality prior uses a 1,000-vote prior centered at `6.2/10`:

```text
adjusted_rating = (vote_count * vote_average + 1000 * 6.2)
                  / (vote_count + 1000)
confidence = clamp(log(1 + vote_count) / log(20001), 0, 1)
quality_prior = 0.80 * adjusted_rating / 10 + 0.20 * confidence
```

Candidates with at least 50 votes and a vote average below `5.0` are excluded. Movies with fewer than 50 votes remain eligible because their public rating is not yet stable.

If none of the watched films can be mapped into the bundled index, ranking falls back to:

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
negative_penalty = max(candidate_similarity_to_negative * strength) * 0.32
```

This keeps positive semantic geometry intact while suppressing candidates that resemble a clearly disliked movie. The coefficient was reduced for the denser 30k BERT space after sensitivity testing showed that the old `0.64` coefficient over-penalized broad categories; see [RECOMMENDATION_EVALUATION.md](RECOMMENDATION_EVALUATION.md).

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
- Large catalogs retain at least 1,000 candidates before negative-preference and diversity re-ranking.
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

Six independent film-domain personas supplied 90+ watched ratings, including explicit high and low scores. On the 30k index, compared with identical watched collections made rating-neutral, ratings changed an average of 10.8 movies in each Top 20. Narrow labeled positive hits changed from 2 to 3 and negative hits from 1 to 0; these exact-title sets were authored for the earlier 1k catalog and are now treated only as sparse anchors. Refresh changed an average of 6.8 movies while preserving focus-genre and score-loss gates.

The fixtures and assertions live under `app/src/test/resources/recommendation/` and `app/src/test/java/com/lumitrace/app/recommendation/`. These are controlled expert scenarios, not population-level accuracy or an online A/B test. The full protocol and limitations are in [RECOMMENDATION_EVALUATION.md](RECOMMENDATION_EVALUATION.md).

## 10. Limits

The 30k index still does not cover the complete TMDB universe. A live TMDB result that is absent from the index may still be saved and rated, but it cannot add semantic dimensions to the local profile. The current unsigned release APK is approximately 54 MiB, but the decoded float32 matrix occupies about 92 MiB before metadata and UI caches.

The current 30k snapshot is for local evaluation. Its redistribution rights and upstream model terms must be verified before publishing it in a public APK or repository release; see [DATA_LICENSE.md](DATA_LICENSE.md).
