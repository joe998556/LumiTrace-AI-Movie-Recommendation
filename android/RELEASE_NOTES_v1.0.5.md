# LumiTrace Android v1.0.5

This release connects the Android taste payload to the server-side MovieLens hybrid recommender.

## What Changed

- Sends watched TMDB movie IDs with the recommendation request.
- Keeps movie IDs, 1-10 ratings, genres, release years, and semantic text aligned in the same taste profile.
- Enables a BERT server loaded with `final_boss_vectors.json` to use MovieLens SVD and Genome vectors at runtime.
- Keeps private endpoints, gateway tokens, TMDB keys, and signing keys out of the public APK.

## Server Requirement

For the best recommendations, update the BERT server and run it with the hybrid index:

```text
python ai_engine/final_boss_engine.py --ratings_path <MovieLens folder> --genome_path <Genome folder> --bert_file movie_vectors.json --output final_boss_vectors.json
python ai_engine/bert_service.py --host 0.0.0.0 --port 5001 --device cuda --vectors final_boss_vectors.json
```

If `final_boss_vectors.json` is not available, the app still works with regular BERT vectors.
