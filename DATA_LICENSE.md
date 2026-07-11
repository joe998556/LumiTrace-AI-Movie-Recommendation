# Bundled Index Data Notice

The Android asset directory [`app/src/main/assets/lumitrace/`](app/src/main/assets/lumitrace/) contains a compact transformation of **MovieLens Latest Small**, downloaded from GroupLens Research at the University of Minnesota.

Source: <https://grouplens.org/datasets/movielens/latest/>

The complete upstream README and usage conditions are included unchanged at [`app/src/main/assets/lumitrace/MOVIELENS_README.txt`](app/src/main/assets/lumitrace/MOVIELENS_README.txt). Those conditions apply to the MovieLens-derived metadata and vector index, including:

- Do not state or imply endorsement by the University of Minnesota or GroupLens Research.
- Acknowledge MovieLens in publications resulting from use of the data.
- Retain the applicable conditions when redistributing the data or a transformation.
- Obtain prior permission from GroupLens Research for commercial or revenue-bearing use when required by those conditions.
- The data and scripts are provided without warranty.

Recommended citation:

> F. Maxwell Harper and Joseph A. Konstan. 2015. The MovieLens Datasets: History and Context. ACM Transactions on Interactive Intelligent Systems 5, 4, Article 19. <https://doi.org/10.1145/2827872>

The bundled vectors were generated with `sentence-transformers/all-MiniLM-L6-v2`, whose model card declares the Apache License 2.0. The LumiTrace source code remains under the MIT License; the MovieLens-derived assets do not become MIT-licensed.

TMDB metadata and poster requests are made at runtime with an end user's own key and remain subject to TMDB's current terms. No TMDB-derived vector index is distributed by this repository.
