# Architecture Notes And Current Limits

This document records what LumiTrace does today and where the architecture is intentionally limited.

LumiTrace is an open-source recommendation prototype. It is useful for local experimentation, Android demos, and learning how semantic movie recommendation can be wired end to end. It is not presented as a production-scale recommender platform.

## Browser Storage vs Vector Storage

The browser flow stores only lightweight user state in `localStorage`:

- TMDB API key entered by the user
- saved/watched movie records
- local recommendation preferences

The browser does not store `movie_vectors.json`.

Large semantic indexes are handled by the optional BERT service:

```text
browser or Android app -> Flask/API or direct LAN endpoint -> ai_engine/bert_service.py -> movie_vectors.json loaded as a Torch tensor
```

This separation matters because browser `localStorage` is usually limited to a few MB, while a 30,000 movie vector index can be tens of MB or more.

## Current Search Strategy

`ai_engine/bert_service.py` currently loads the generated JSON vector file once at startup and normalizes it into a Torch tensor.

At query time it performs a dense matrix multiplication:

```text
semantic_scores = movie_vector_tensor @ user_embedding
```

This is a linear scan over the local vector index. It is acceptable for single-user local/lab experiments at the current presets, especially on CUDA, but it is not the right architecture for a high-concurrency public service.

If the corpus grows beyond the current local presets or the service needs multiple concurrent users, the next retrieval layer should be an ANN/vector index such as:

- Faiss
- HNSWLib
- SQLite with vector extension
- a managed vector database

## Rating Weights

Ratings are treated as preference strength, not as negative semantic vectors.

Current behavior:

- high ratings increase the semantic contribution of that watched movie
- low ratings reduce the semantic contribution of that watched movie
- genre weights are clamped to `>= 0`

The service does not currently subtract disliked movie embeddings from the taste vector. This avoids the common vector-space mistake where a negative embedding is interpreted as an "opposite movie" even though embedding spaces usually do not work that way.

This also means low ratings are conservative: they reduce influence more than they actively ban a semantic region. Stronger dislike modeling would need an explicit negative-candidate penalty or a separate contrastive ranking stage.

## SVD And Genome Signals

The default public and Android flows do not train collaborative filtering from the user's private local history.

The optional `ai_engine/final_boss_engine.py` script can build offline item vectors from external MovieLens-style datasets:

- MovieLens ratings for SVD item vectors
- MovieLens Genome/tag data for tag-profile vectors
- TMDB BERT vectors for semantic vectors

That path is an offline experiment. It should not be described as online personalized collaborative filtering. In a privacy-first single-user local setup, there is no central user-item matrix large enough to train fresh SVD per user.

## Production Hardening Needed

Before treating LumiTrace as a public service, these items should be addressed:

- replace JSON vector loading with an indexed vector retrieval layer
- add request queueing, timeout limits, and concurrency controls
- benchmark latency for each preset on CPU and GPU
- add rate limiting in front of any public BERT gateway
- separate public HTTPS gateway code from private model workers
- add model/index version metadata
- add automated integration tests for `/search` response quality and latency

These limits are part of the current roadmap, not hidden production claims.
