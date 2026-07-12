# Recommendation Evaluation

This evaluation asks two concrete questions:

1. Does changing only the ratings, while keeping the watched collection fixed, materially change LumiTrace recommendations in the intended direction?
2. Does refreshing with an unchanged collection produce a different but still relevant result set?

It is a controlled expert-scenario evaluation over the 1,000-film bundled MovieLens/MiniLM catalog. It is not a population estimate, an online A/B test, or proof that every recommendation is subjectively correct.

## Independent Taste Profiles

Six independent film-domain agents inspected only the bundled catalog and authored coherent, nontrivial profiles before seeing any LumiTrace output:

| Profile | Domain | Watched | High ratings | Low ratings |
|---|---|---:|---:|---:|
| `cerebral_scifi` | Philosophical and formally controlled science fiction | 16 | 8 | 4 |
| `crime_noir` | Procedural crime, noir, corruption, and moral consequence | 16 | 9 | 3 |
| `patient_horror` | Psychological, occult, body, and patient-dread horror | 15 | 8 | 4 |
| `family_animation` | Authored animation, wonder, family, and moral growth | 15 | 8 | 4 |
| `auteur_drama` | International auteur and character-driven drama | 15 | 8 | 4 |
| `mainstream_mix` | Clean action, heists, comedy, and adult romance | 15 | 8 | 4 |

Every profile also identifies a narrow set of unseen movies considered strong recommendations and five unseen movies considered bad recommendations. Low ratings deliberately include tempting near-neighbors, such as a liked franchise entry paired with a disliked sequel.

The machine-readable fixture is [`expert_profiles.json`](app/src/test/resources/recommendation/expert_profiles.json).

## Protocol

For each profile, the test runs the rating comparison plus a five-ranking refresh sequence:

1. **Rated:** the authored 1-10 ratings are used.
2. **Rating-neutral:** the exact same watched IDs are retained, but every rating is set to zero.
3. **Refresh sequence:** the rated collection is unchanged while the local refresh seed advances from `0` through `4`.

The comparison records:

- Top-20 membership changed by ratings;
- Top-20 membership changed by the first refresh and the minimum change across all four consecutive refreshes;
- focus-genre coverage;
- exact hits from the narrow unseen positive and negative sets;
- strongest low-rating penalty;
- mean final relevance score before and after refresh;
- reproducibility when the same refresh seed is repeated.

The production weights were selected from 24 combinations:

```text
semantic: 0.82, 0.78, 0.74, 0.70
genre:    0.10, 0.14, 0.18, 0.22
negative: 0.24, 0.32, 0.40, 0.48, 0.56, 0.64
quality:  fixed at 0.08
```

The selected general configuration is:

```text
semantic = 0.78
genre = 0.14
quality = 0.08
negative preference coefficient = 0.64
```

It produced the strongest aggregate preference lift, reduced negative hits, preserved focus coverage, and changed at least seven Top-20 members for every persona when ratings were enabled.

## Results

| Persona | Rating changes | Refresh changes first/min | Focus rated/refresh | Good hits rated/neutral | Bad hits rated/neutral | Mean score rated/refresh |
|---|---:|---:|---:|---:|---:|---:|
| `cerebral_scifi` | 7/20 | 3/3 | 16/17 | 4/3 | 0/0 | 0.492/0.486 |
| `crime_noir` | 7/20 | 5/5 | 19/19 | 2/2 | 1/1 | 0.447/0.443 |
| `patient_horror` | 9/20 | 7/5 | 20/19 | 6/4 | 1/3 | 0.445/0.441 |
| `family_animation` | 13/20 | 6/5 | 14/13 | 5/4 | 0/1 | 0.379/0.375 |
| `auteur_drama` | 9/20 | 4/4 | 20/20 | 1/0 | 0/0 | 0.509/0.505 |
| `mainstream_mix` | 12/20 | 4/4 | 17/16 | 1/1 | 0/0 | 0.494/0.491 |

Aggregate observations:

- Ratings changed **57 of 120** Top-20 memberships, or **9.5 movies per profile**.
- Narrow expert-labeled positive hits increased from **14 to 19**.
- Narrow expert-labeled negative hits fell from **5 to 2**.
- Focus-genre coverage was **106/120** for rated results and **104/120** after refresh.
- The first refresh changed **29 of 120** memberships, or **4.8 movies per profile**.
- Across four consecutive refreshes, every adjacent Top-20 pair changed by at least **3 movies**; the per-profile minimum ranged from **3 to 5**.
- The average refresh relevance-score decrease was approximately **0.004**, well inside the `0.05` per-profile gate.
- Repeating refresh seed `1` reproduced exactly the same order for every profile.

Because the watched IDs are identical in the rated and neutral runs, the 57 membership changes are caused by the rating path: positive weighting, negative genre evidence, and post-ranking negative similarity penalties.

## Representative Behavior

- The horror profile increased positive-set hits from 4 to 6 and reduced negative-set hits from 3 to 1.
- The animation profile increased positive-set hits from 4 to 5 and removed its one negative-set hit.
- The science-fiction profile retained 16 focus matches while adding `Gattaca`, `Pi`, `Contact`, and `Dark City` from its narrow positive set.
- The crime profile still surfaced `The Godfather: Part III`, its one labeled negative hit.
- The auteur profile achieved full Drama focus coverage but only one exact narrow positive hit, showing that genre coherence is stronger than fine-grained auteur sensitivity in the compact index.

## Acceptance Gates

The automated evaluation fails when any of these conditions is violated:

- a watched seed leaks into recommendations;
- ratings change fewer than 3 of 20 movies for any persona;
- refresh changes fewer than 2 of 20 movies for any persona;
- any of four consecutive refreshes changes fewer than 2 of 20 movies;
- repeating the same refresh seed changes the order;
- a rated or refreshed list falls below its profile focus threshold;
- refresh lowers mean final relevance by more than `0.05`;
- low ratings produce no measurable post-ranking penalty;
- aggregate negative hits do not fall;
- aggregate positive-minus-negative preference utility does not improve;
- the selected production weights are not the best row in the declared 24-point grid.

## Reproduce

From the repository root on Windows with Android Studio installed:

```powershell
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
$env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
.\gradlew.bat :app:testDebugUnitTest --tests "com.lumitrace.app.recommendation.ExpertTasteEvaluationTest"
.\gradlew.bat :app:testDebugUnitTest --tests "com.lumitrace.app.recommendation.RankingCalibrationTest"
```

The detailed generated report is written to:

```text
app/build/reports/recommendation/expert-evaluation.md
```

## Limitations

- The 1,000-film starter index constrains coverage; a valid recommendation absent from the bundle cannot be returned.
- The unseen positive and negative sets are deliberately narrow. A recommendation not listed as positive is not automatically wrong.
- Focus genres measure broad coherence, not tone, pacing, authorship, or cultural context.
- The six profiles are structured expert scenarios, not representative users.
- The 24-point weight grid and the reported effect measurements use the same six scenarios; a separate held-out profile set is still needed to estimate generalization.
- The system remains content-based and has no population-level collaborative signal at runtime.
- Some weaknesses remain visible: crime still has one labeled franchise-negative hit, horror can surface broad horror-comedy, and auteur taste is only coarsely represented.

The evaluation therefore supports a bounded claim: **ratings have a measurable and generally beneficial causal effect within these controlled local scenarios, and refresh changes near-tied recommendations without materially weakening relevance.**
