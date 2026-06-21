# LumiTrace Recommendation Benchmark — Progress Log

## Session: 2026-06-22

### Completed Phases

#### Phase 1: Project Understanding ✓
- BERT service on port 5001: 30,000 movies, SVD + Genome hybrid
- Flask app on port 5000: proxies to BERT service
- Algorithm: BERT semantic + MovieLens SVD + Tag Genome + metadata quality
- Key file: `ai_engine/bert_service.py`

#### Phase 2: Benchmark Framework ✓
- `tools/eval/recommendation_benchmark.py` — multi-dimension scoring, JSON/MD reports, round comparison
- `tools/eval/thematic_sets.py` — curated thematic relevance sets for 30 profiles
- `tools/eval/build_profiles.py` — profile generator from vector index
- Scoring rubric: existence, not_collected, genre_relevance, genre_mismatch, language_match, year_proximity, score_strength, thematic_relevance

#### Phase 3: Test Profiles ✓
- 30 diverse profiles covering: sci-fi, crime, horror, Asian cinema, European art house, animation, romance, war, comedy, cult, A24, Oscar classics, B-movies, Taiwan/HK/Chinese cinema
- Each profile: 5-6 collected movies, genre preferences, language preferences, avoid_genres

#### Phase 4: Baseline & Iteration ✓ (6 rounds)

| Round | Avg Score | Key Change |
|-------|-----------|------------|
| 1 | 5.94 | Baseline (English overviews) |
| 2 | 5.96 | Chinese enriched overviews |
| 3 | 5.92 | Detailed English overviews |
| 4 | 6.28 | Added thematic relevance scoring |
| 5 | 6.62 | Fixed thematic set name matching |
| 6 | 8.20 | Improved thematic scoring with genre+lang fallback |

### Algorithm Changes Made

1. **Reduced metadata weight**: 0.22 → 0.05 (prevents popularity bias)
2. **Boosted context score**: genre 0.06→0.15 per overlap, language 0.08→0.20
3. **Context-dominant scoring**: when filters active, `context_score * 1.5 + semantic * 0.3`
4. **Full catalog scan**: when genre/language filters active, scan all 30K movies
5. **Fixed language inference**: Chinese overviews no longer add "en" to explicit "ko"

### Remaining Issues
- 11 genre mismatches (movies with avoid_genres as secondary genre)
- 5 profiles still score <7 (single-genre limitations)
- `avoid_genres` not used by the recommendation algorithm itself

### Files Modified
- `ai_engine/bert_service.py` — algorithm improvements
- `tools/eval/recommendation_benchmark.py` — benchmark framework
- `tools/eval/thematic_sets.py` — thematic relevance sets
- `tools/eval/build_profiles.py` — profile generator
- `tools/eval/build_thematic.py` — thematic set builder
- `tools/eval/recommendation_profiles.json` — 30 test profiles

### Benchmark Reports
- `tools/eval/results/benchmark_round_1.json` through `benchmark_round_6.json`
- `tools/eval/results/benchmark_round_1.md` through `benchmark_round_6.md`
