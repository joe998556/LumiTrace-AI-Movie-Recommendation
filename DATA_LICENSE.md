# Demo Index Data License

The optional bundled `demo_index/` is a transformation of **MovieLens Latest Small**, downloaded from GroupLens Research at the University of Minnesota.

Source: <https://grouplens.org/datasets/movielens/latest/>

The complete upstream README and usage license are included unchanged at [`demo_index/MOVIELENS_README.txt`](demo_index/MOVIELENS_README.txt). The MovieLens usage conditions apply to the demo index, including:

- Do not state or imply endorsement by the University of Minnesota or GroupLens Research.
- Acknowledge MovieLens in publications resulting from use of the data.
- Redistribution, including transformations, must retain the same license conditions.
- Commercial or revenue-bearing use requires prior permission from GroupLens Research.
- The data and scripts are provided without warranty.

Recommended citation:

> F. Maxwell Harper and Joseph A. Konstan. 2015. The MovieLens Datasets: History and Context. ACM Transactions on Interactive Intelligent Systems 5, 4, Article 19. <https://doi.org/10.1145/2827872>

The demo vectors are generated with `sentence-transformers/all-MiniLM-L6-v2`, whose model card declares the Apache License 2.0. The main LumiTrace source code remains under the MIT License; the MovieLens-derived demo index does not become MIT-licensed.

LumiTrace does not distribute indexes generated from TMDB API content. TMDB metadata and poster requests made by an end user remain subject to TMDB's current API terms.
