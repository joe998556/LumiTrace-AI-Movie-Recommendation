# Recommendation Evaluation

This evaluation asks two concrete questions:

1. Does changing only the ratings, while keeping the watched collection fixed, materially change LumiTrace recommendations in the intended direction?
2. Does refreshing with an unchanged collection produce a different but still relevant result set?

It is a controlled expert-scenario evaluation over the 30,000-film, 768-dimensional BERT index. It is not a population estimate, an online A/B test, or proof that every recommendation is subjectively correct.

## Independent Taste Profiles

Six independent film-domain personas provide coherent high and low ratings:

| Profile | Domain | Watched | High ratings | Low ratings |
|---|---|---:|---:|---:|
| `cerebral_scifi` | Philosophical and formally controlled science fiction | 16 | 8 | 4 |
| `crime_noir` | Procedural crime, noir, corruption, and moral consequence | 16 | 9 | 3 |
| `patient_horror` | Psychological, occult, body, and patient-dread horror | 15 | 8 | 4 |
| `family_animation` | Authored animation, wonder, family, and moral growth | 15 | 8 | 4 |
| `auteur_drama` | International auteur and character-driven drama | 15 | 8 | 4 |
| `mainstream_mix` | Clean action, heists, comedy, and adult romance | 15 | 8 | 4 |

The profiles were originally authored against the earlier 1,000-film catalog. All 173 unique fixture IDs are present in the 30k index, but each narrow `goodUnseen` list is now an incomplete sample of a much larger relevant universe. Exact hits are retained as sparse anchors rather than treated as complete ground truth.

The machine-readable fixture is [`expert_profiles.json`](app/src/test/resources/recommendation/expert_profiles.json).

## Protocol

For each profile, the test runs the rating comparison plus a five-ranking refresh sequence:

1. **Rated:** the authored 1-10 ratings are used.
2. **Rating-neutral:** the exact same watched IDs are retained, but every rating is set to zero.
3. **Refresh sequence:** the rated collection is unchanged while the local refresh seed advances from `0` through `4`.

The comparison records Top-20 membership changes, focus-genre coverage, sparse positive and negative hits, strongest low-rating penalty, mean final score, watched-item leakage, and deterministic reproduction of the same refresh seed.

The 30k sensitivity check covers 12 combinations:

```text
semantic / genre / quality:
  0.70 / 0.22 / 0.08
  0.64 / 0.22 / 0.14
  0.58 / 0.22 / 0.20
  0.64 / 0.18 / 0.18

negative coefficient:
  0.24, 0.32, 0.40
```

The production development configuration is:

```text
semantic = 0.64
genre = 0.22
quality = 0.14
negative preference coefficient = 0.32
minimum large-index re-ranking pool = 1,000
```

Candidates with at least 50 votes and an average below 5.0 are excluded. Remaining quality scores use a Bayesian rating prior and logarithmic vote confidence.

## Results

| Persona | Rating changes | Refresh first/min | Focus rated/refresh | Good rated/neutral | Bad rated/neutral | Mean score rated/refresh |
|---|---:|---:|---:|---:|---:|---:|
| `cerebral_scifi` | 5/20 | 6/6 | 20/19 | 2/2 | 0/0 | 0.641/0.639 |
| `crime_noir` | 14/20 | 8/8 | 20/20 | 1/0 | 0/1 | 0.618/0.615 |
| `patient_horror` | 11/20 | 7/7 | 20/20 | 0/0 | 0/0 | 0.674/0.670 |
| `family_animation` | 13/20 | 7/6 | 20/20 | 0/0 | 0/0 | 0.629/0.623 |
| `auteur_drama` | 10/20 | 8/8 | 20/20 | 0/0 | 0/0 | 0.700/0.694 |
| `mainstream_mix` | 12/20 | 5/5 | 18/18 | 0/0 | 0/0 | 0.655/0.653 |

Aggregate observations:

- Ratings changed **65 of 120** Top-20 memberships, or **10.8 movies per profile**.
- Sparse positive anchors changed from **2 to 3** hits.
- Sparse negative anchors fell from **1 to 0** hits.
- Focus-genre coverage was **118/120** for rated results and **117/120** after refresh.
- The first refresh changed **41 of 120** memberships, or **6.8 movies per profile**.
- Across four consecutive refreshes, every adjacent Top-20 pair changed by at least **5 movies**; per-profile minimums ranged from **5 to 8**.
- Average refresh relevance-score loss was approximately **0.004**.
- Repeating refresh seed `1` reproduced exactly the same order for every profile.

Because watched IDs are identical in the rated and neutral runs, membership changes are caused by rating-weighted positive vectors, negative genre evidence, and post-ranking negative-similarity penalties.

## Independent Google Agent Review

The local `agy.exe` Google agent was invoked twice in read-only mode to inspect the six complete rated, neutral, and refreshed lists. It was prohibited from editing files or changing thresholds.

The qualitative review found:

- final profile scores were **8/10 science fiction, 9/10 crime noir, 5/10 horror, 6/10 animation, 9/10 auteur drama, and 6/10 mainstream mix**;
- `crime_noir` and `auteur_drama` were the strongest profiles;
- the larger index surfaced relevant long-tail films that were impossible in the 1k catalog;
- `cerebral_scifi` still mixes concept-driven work with effects-led or low-budget science fiction;
- `family_animation` still struggles to separate authored animation from branded family titles;
- `patient_horror` can still surface torture or jump-scare titles despite a patient-dread profile;
- the review itself is advisory and must be checked against fixture facts rather than treated as ground truth.

The final agent verdict was suitable for local personal testing and conditional for public release. This is a subjective list audit, not a device-performance measurement or legal clearance. The review directly motivated the 1,000-candidate re-ranking pool, reduced broad negative penalty, Bayesian quality prior, and established-low-quality gate. It does not justify claiming that all six profiles are solved.

## Acceptance Gates

The automated evaluation fails when any of these conditions is violated:

- a watched seed leaks into recommendations;
- ratings change fewer than 3 of 20 movies for any persona;
- any of four consecutive refreshes changes fewer than 2 of 20 movies;
- repeating the same refresh seed changes the order;
- a rated or refreshed list falls below its profile focus threshold;
- refresh lowers mean final relevance by more than `0.05`;
- low ratings produce no measurable post-ranking penalty;
- aggregate negative hits do not fall;
- aggregate positive-minus-negative utility does not improve;
- the production weights fail the 12-point sensitivity gates for utility, negative reduction, focus coverage, or rating influence.

## Reproduce

From the repository root on Windows with Android Studio installed:

```powershell
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
$env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
.\gradlew.bat :app:testDebugUnitTest --tests "com.lumitrace.app.recommendation.ExpertTasteEvaluationTest"
.\gradlew.bat :app:testDebugUnitTest --tests "com.lumitrace.app.recommendation.RankingCalibrationTest"
```

The generated detail report is written to `app/build/reports/recommendation/expert-evaluation.md`.

## Build Footprint

Measured on the 30k development build:

| Artifact | Size |
|---|---:|
| Debug APK | 59.79 MiB |
| Unsigned release APK | 54.07 MiB |
| Float16 NPY asset | 43.95 MiB |
| Metadata JSON asset | 15.59 MiB |
| Decoded float32 vector matrix | about 87.9 MiB |

Metadata and NPY decoding are streamed to avoid retaining extra full-size input copies during catalog loading.

## Limitations

- The original exact-title positive lists are incomplete for a catalog expanded by 30 times.
- Focus genres measure broad coherence, not tone, pacing, authorship, franchise style, or cultural context.
- The six profiles are structured scenarios, not representative users.
- The 12-point sensitivity check and reported effects use the same six scenarios; held-out profiles are still needed.
- The system remains content-based and has no population-level collaborative signal at runtime.
- The 30k snapshot's redistribution rights and upstream model terms require verification before public release.

The bounded conclusion is: **ratings materially change the 30k recommendations, negative anchors improve, and refresh produces reproducible variety without large score loss; subjective precision remains uneven across taste domains.**
