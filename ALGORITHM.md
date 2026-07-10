# LumiTrace Recommendation Algorithm

LumiTrace is a content-based, local-first recommendation system. User taste remains in the browser; the recommendation request contains only bounded TMDB movie IDs, 1-10 ratings, optional genre IDs, and explicit query controls.

## 1. Offline Catalog Encoding

The expensive Transformer stage runs while building the catalog, not while serving ordinary recommendations. Each movie is converted into enriched text:

```text
title + genres + language + release year + audience rating
+ director + leading cast + collection + overview
```

For movie `i`, the encoder produces an L2-normalized vector:

```text
x_i = normalize(BERT(rich_text_i))
```

All rows form `X` with shape `N x D`. The default compact index stores normalized rows as float16 in `vectors.npy`, metadata in `movies.json`, and model/dimension checks in `manifest.json`. Serving converts the matrix to float32 for reliable CPU matrix multiplication.

The legacy JSON vector format remains readable only as a migration path.

## 2. Online Input Contract

The preferred request format keeps each rating aligned with its movie:

```json
{
  "items": [
    { "tmdb_id": 329865, "rating": 9, "genre_ids": [18, 878] }
  ]
}
```

- `6-10`: positive taste seed.
- `5`: neutral; excluded from the semantic center.
- `1-4`: negative seed used only during shortlist re-ranking.
- More/Less feedback becomes a local `9` or `2` signal.

Notes and journal text never enter the recommendation API.

## 3. Positive Taste Retrieval

For positive seed vectors `p_j` with ratings `r_j`, LumiTrace creates one normalized weighted center:

```text
w_j = r_j / 5
u = normalize(sum(w_j * p_j))
```

Exact cosine similarity is one matrix multiplication because both `X` and `u` are normalized:

```python
semantic_scores = torch.mm(X, u.T).squeeze(1)
```

The service takes a bounded shortlist, currently `max(180, top_k * 24)`, before applying more expensive per-candidate adjustments. At 30,000 movies this remains a small exact-retrieval workload and avoids a vector-database dependency.

For watched-and-rated requests, no Transformer model is loaded. The server only looks up precomputed rows and performs tensor operations.

## 4. Negative Preference Penalty

LumiTrace never subtracts a disliked embedding from the positive center. A negative direction in embedding space does not reliably represent an opposite movie preference.

Instead, negative seed vectors are compared only with the retrieved shortlist:

```text
negative_penalty = clamp((max_negative_similarity - 0.52) / 0.48, 0, 1)

score = semantic_score * (1 - 0.75 * negative_penalty)
        + genre_bonus
        + language_bonus
        + Bayesian_quality_adjustment
```

This preserves the positive retrieval geometry and reduces the work from a full-catalog negative scan to `shortlist_size x negative_seed_count`.

The quality adjustment uses TMDB vote average with a catalog prior and vote-count confidence. Candidates below a configurable minimum vote count are skipped, preventing unrated or near-empty catalog records from dominating a public demo through unstable metadata.

## 5. Diversity Re-ranking

The Familiar-to-Surprise control affects the final short list only. It applies small deterministic penalties when selected results repeatedly use the same:

- genres,
- original language,
- franchise or collection.

The control does not fabricate a different user profile and does not call a second model.

## 6. Evidence

Each result contains structured evidence:

- closest positive seed titles,
- matching genre IDs,
- strongest rating signal,
- low-rated titles that caused a penalty,
- semantic and diversity penalty values.

The Web UI displays this evidence directly. On a trusted self-host, an optional LLM may narrate only the supplied evidence. It cannot select, filter, or reorder candidates.

## 7. Optional Free-Text Search

A scene prompt requires a query vector produced by the same model that built the index. Deployments choose one mode:

- `disabled`: public CPU demo; rated movie IDs only.
- `auto`: load the encoder on the first free-text request.
- `preload`: load the encoder at service startup.

The index manifest and model hidden size are checked before text retrieval, preventing silent cross-model dimension errors.

## 8. Metadata Fallback

Without an index, the browser ranks TMDB discovery results using genre overlap, TMDB rating, vote count, and the viewer's ratings. This is deliberately labeled as a fallback and keeps a fresh clone useful without pretending that semantic retrieval ran.

## 9. Scope

Exact retrieval is appropriate for LumiTrace's current catalog scale. A much larger corpus or sustained high concurrency should add measured caching, queueing, observability, and an ANN index such as Faiss or HNSW only after profiling shows that exact matrix retrieval is the bottleneck.
