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
base_score = 0.82 * semantic_similarity
           + 0.10 * genre_affinity
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
negative_penalty = max(candidate_similarity_to_negative * strength) * 0.24
```

This keeps positive semantic geometry intact while suppressing candidates that closely resemble a clearly disliked movie.

## 5. Diversity Re-Ranking

The top candidate pool is re-ranked greedily. A candidate loses a small score proportional to its maximum genre overlap with an already selected result:

```text
selection_score = current_score - genre_jaccard_overlap * diversity_strength
```

The strength is bounded to `0.0..0.2`. A zero value preserves the original relevance order; higher values trade a small amount of similarity for a broader final list.

## 6. Constraints and Exclusions

- Watched seed movies are excluded from results.
- `topK` is bounded to the catalog size and a maximum of 300.
- Tonight can apply required genre groups and minimum or maximum release year before ranking.
- A wider bounded pool is retained before diversity and negative-preference re-ranking.

## 7. Explainability

Each result has a local recommendation trace containing:

- semantic similarity,
- genre affinity,
- quality prior,
- negative-preference penalty,
- diversity adjustment,
- base score,
- final score.

The app also names the closest positive watched movie when that evidence exists. These explanations are deterministic and generated from the same local score trace used for ranking.

## 8. Limits

The starter index is a demo-scale catalog, not a complete movie universe. A live TMDB result that is absent from the index may still be saved and rated, but it cannot add semantic dimensions to the local profile. Enlarging the index requires a redistributable data source, measured APK-size and memory budgets, and regenerated vectors with exactly the model declared by the manifest.

MovieLens provenance and terms are documented in [DATA_LICENSE.md](DATA_LICENSE.md).
