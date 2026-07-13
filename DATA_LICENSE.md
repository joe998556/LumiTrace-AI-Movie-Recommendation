# Bundled Index Data Notice

The Android asset directory [`app/src/main/assets/lumitrace/`](app/src/main/assets/lumitrace/) bundles 30,000 TMDB-linked movie metadata and precomputed 768d float16 vectors in the public v1.3.0 30k release (APK and repository).

The snapshot includes TMDB identifiers, titles, overviews, genre identifiers, release dates, vote aggregates, and poster paths. TMDB data remains subject to [TMDB's terms](https://www.themoviedb.org/terms-of-use) and attribution requirements. LumiTrace is not endorsed or certified by TMDB.

The vectors were generated with `AventIQ-AI/bert-movie-recommendation-system` from rich movie text and stored as normalized 768-dimensional float16 rows. At release preparation time, its Hugging Face model card/API did not expose an explicit license declaration. The model and generated vectors retain any terms that apply to their upstream model and input data.

The LumiTrace source code remains under the MIT License. The bundled metadata snapshot and vector index are not relicensed under MIT. Downstream redistribution and commercial users must independently verify all applicable upstream terms.
