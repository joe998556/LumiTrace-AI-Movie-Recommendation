package com.lumitrace.app.recommendation

import java.io.File
import java.util.Locale
import org.junit.Assert.assertTrue
import org.junit.Test

class ExpertTasteEvaluationTest {
    @Test
    fun expertProfilesProveRatingInfluenceAndRefreshVariation() {
        val fixture = ExpertProfileFixture.data
        val failures = mutableListOf<String>()
        val evaluations = fixture.profiles.map { profile -> evaluate(profile, failures) }
        val ratedGoodHits = evaluations.sumOf { it.ratedGoodHits }
        val neutralGoodHits = evaluations.sumOf { it.neutralGoodHits }
        val ratedBadHits = evaluations.sumOf { it.ratedBadHits }
        val neutralBadHits = evaluations.sumOf { it.neutralBadHits }
        if (ratedBadHits >= neutralBadHits) {
            failures += "Expert-labeled bad Top-$TOP_K hits did not fall with ratings: $ratedBadHits vs $neutralBadHits"
        }
        if (ratedGoodHits - ratedBadHits <= neutralGoodHits - neutralBadHits) {
            failures += "Expert preference utility did not improve with ratings: ${ratedGoodHits - ratedBadHits} vs ${neutralGoodHits - neutralBadHits}"
        }
        writeReport(fixture, evaluations)

        assertTrue(failures.joinToString(separator = "\n"), failures.isEmpty())
    }

    private fun evaluate(profile: ExpertProfile, failures: MutableList<String>): ProfileEvaluation {
        validateProfile(profile, failures)
        val ratedSignals = profile.watchedRatings.map { BundledTestCatalog.signal(it.id, it.rating) }
        val neutralSignals = profile.watchedRatings.map { BundledTestCatalog.signal(it.id, 0f) }
        val rated = LocalRecommendationRanker.rank(
            BundledTestCatalog.catalog,
            ratedSignals,
            requestedTopK = TOP_K,
            variationSeed = 0L
        )
        val neutral = LocalRecommendationRanker.rank(
            BundledTestCatalog.catalog,
            neutralSignals,
            requestedTopK = TOP_K,
            variationSeed = 0L
        )
        val refreshed = LocalRecommendationRanker.rank(
            BundledTestCatalog.catalog,
            ratedSignals,
            requestedTopK = TOP_K,
            variationSeed = 1L
        )
        val repeatedRefresh = LocalRecommendationRanker.rank(
            BundledTestCatalog.catalog,
            ratedSignals,
            requestedTopK = TOP_K,
            variationSeed = 1L
        )
        val refreshSeries = listOf(rated) + (1L..4L).map { seed ->
            LocalRecommendationRanker.rank(
                BundledTestCatalog.catalog,
                ratedSignals,
                requestedTopK = TOP_K,
                variationSeed = seed
            )
        }
        val ratedTop100 = LocalRecommendationRanker.rank(
            BundledTestCatalog.catalog,
            ratedSignals,
            requestedTopK = 100,
            variationSeed = 0L
        )

        val ratedIds = rated.movies.map { it.id }
        val neutralIds = neutral.movies.map { it.id }
        val refreshedIds = refreshed.movies.map { it.id }
        val watchedIds = profile.watchedRatings.mapTo(hashSetOf()) { it.id }
        val ratingChanged = TOP_K - ratedIds.toSet().intersect(neutralIds.toSet()).size
        val refreshChanged = TOP_K - ratedIds.toSet().intersect(refreshedIds.toSet()).size
        val minimumSequentialRefreshChanges = refreshSeries.zipWithNext { previous, next ->
            TOP_K - previous.movies.mapTo(hashSetOf()) { it.id }
                .intersect(next.movies.mapTo(hashSetOf()) { it.id }).size
        }.minOrNull() ?: 0
        val goodIds = profile.goodUnseen.mapTo(hashSetOf()) { it.id }
        val badIds = profile.badUnseen.mapTo(hashSetOf()) { it.id }
        val focusHits = rated.movies.count { movie -> movie.genreIds.any { it in profile.focusGenreIds } }
        val refreshedFocusHits = refreshed.movies.count { movie -> movie.genreIds.any { it in profile.focusGenreIds } }
        val ratedMeanScore = rated.traces.values.map { it.finalScore }.average().toFloat()
        val refreshedMeanScore = refreshed.traces.values.map { it.finalScore }.average().toFloat()
        val strongestPenalty = ratedTop100.traces.values.maxOfOrNull { it.negativePreferencePenalty } ?: 0f

        if (ratedIds.any { it in watchedIds }) failures += "${profile.id}: watched movie leaked into recommendations"
        if (ratingChanged < MIN_RATING_SET_CHANGES) {
            failures += "${profile.id}: ratings changed only $ratingChanged of $TOP_K recommendations"
        }
        if (refreshChanged < MIN_REFRESH_SET_CHANGES) {
            failures += "${profile.id}: refresh changed only $refreshChanged of $TOP_K recommendations"
        }
        if (minimumSequentialRefreshChanges < MIN_REFRESH_SET_CHANGES) {
            failures += "${profile.id}: repeated refresh eventually changed only $minimumSequentialRefreshChanges movies"
        }
        if (refreshedIds != repeatedRefresh.movies.map { it.id }) {
            failures += "${profile.id}: the same refresh seed was not reproducible"
        }
        if (strongestPenalty <= 0.001f) failures += "${profile.id}: low ratings produced no measurable penalty"
        if (focusHits < profile.minimumFocusHits) {
            failures += "${profile.id}: only $focusHits of $TOP_K matched its focus genres"
        }
        if (refreshedFocusHits < profile.minimumFocusHits) {
            failures += "${profile.id}: refreshed list had only $refreshedFocusHits focus-genre matches"
        }
        if (refreshedMeanScore < ratedMeanScore - MAX_REFRESH_SCORE_LOSS) {
            failures += "${profile.id}: refresh relevance fell by more than $MAX_REFRESH_SCORE_LOSS"
        }

        return ProfileEvaluation(
            profile = profile,
            ratedTitles = rated.movies.map { it.title },
            neutralTitles = neutral.movies.map { it.title },
            refreshedTitles = refreshed.movies.map { it.title },
            ratingChanged = ratingChanged,
            refreshChanged = refreshChanged,
            minimumSequentialRefreshChanges = minimumSequentialRefreshChanges,
            focusHits = focusHits,
            refreshedFocusHits = refreshedFocusHits,
            ratedGoodHits = ratedIds.count { it in goodIds },
            neutralGoodHits = neutralIds.count { it in goodIds },
            ratedBadHits = ratedIds.count { it in badIds },
            neutralBadHits = neutralIds.count { it in badIds },
            strongestPenalty = strongestPenalty,
            ratedMeanScore = ratedMeanScore,
            refreshedMeanScore = refreshedMeanScore
        )
    }

    private fun validateProfile(profile: ExpertProfile, failures: MutableList<String>) {
        val watchedIds = profile.watchedRatings.map { it.id }
        val unseenIds = (profile.goodUnseen + profile.badUnseen).map { it.id }
        if (profile.watchedRatings.size !in 12..16) failures += "${profile.id}: expected 12-16 watched movies"
        if (profile.watchedRatings.count { it.rating >= 8f } < 5) failures += "${profile.id}: fewer than five high ratings"
        if (profile.watchedRatings.count { it.rating <= 4f } < 3) failures += "${profile.id}: fewer than three low ratings"
        if (watchedIds.size != watchedIds.toSet().size) failures += "${profile.id}: duplicate watched IDs"
        if (watchedIds.any { it in unseenIds }) failures += "${profile.id}: expected unseen movie is already watched"

        (profile.watchedRatings.map { ExpectedMovie(it.id, it.title) } + profile.goodUnseen + profile.badUnseen).forEach { expected ->
            val catalogMovie = BundledTestCatalog.moviesById[expected.id]
            if (catalogMovie == null) {
                failures += "${profile.id}: TMDB ${expected.id} is absent from the bundled catalog"
            } else if (catalogMovie.title != expected.title) {
                failures += "${profile.id}: title mismatch for ${expected.id}: '${expected.title}' != '${catalogMovie.title}'"
            }
        }
    }

    private fun writeReport(fixture: ExpertFixture, evaluations: List<ProfileEvaluation>) {
        val root = if (File("app").isDirectory) File("app") else File(".")
        val output = File(root, "build/reports/recommendation/expert-evaluation.md")
        output.parentFile?.mkdirs()
        val averageRatingChanges = evaluations.map { it.ratingChanged }.average()
        val averageRefreshChanges = evaluations.map { it.refreshChanged }.average()
        val report = buildString {
            appendLine("# LumiTrace Expert Taste Evaluation")
            appendLine()
            appendLine("Fixture version: ${fixture.version}. Catalog: ${BundledTestCatalog.catalog.movies.size} bundled movies. Top-K: $TOP_K.")
            appendLine()
            appendLine("Six independent film-domain personas supplied high and low ratings plus unseen positive and negative examples. The rated run is compared with the same watched collection made rating-neutral, then refreshed with an unchanged collection.")
            appendLine()
            appendLine("| Persona | Rating changes | Refresh changes/min across 4 | Focus rated/refresh | Good hits rated/neutral | Bad hits rated/neutral | Mean score rated/refresh | Max low-score penalty |")
            appendLine("|---|---:|---:|---:|---:|---:|---:|---:|")
            evaluations.forEach { row ->
                appendLine("| ${row.profile.id} | ${row.ratingChanged}/$TOP_K | ${row.refreshChanged}/${row.minimumSequentialRefreshChanges} | ${row.focusHits}/${row.refreshedFocusHits} | ${row.ratedGoodHits}/${row.neutralGoodHits} | ${row.ratedBadHits}/${row.neutralBadHits} | ${row.ratedMeanScore.format(3)}/${row.refreshedMeanScore.format(3)} | ${row.strongestPenalty.format(3)} |")
            }
            appendLine()
            appendLine("Average top-$TOP_K membership changed by ratings: ${averageRatingChanges.format(1)} movies.")
            appendLine()
            appendLine("Average top-$TOP_K membership changed by refresh: ${averageRefreshChanges.format(1)} movies.")
            evaluations.forEach { row ->
                appendLine()
                appendLine("## ${row.profile.id}")
                appendLine()
                appendLine(row.profile.persona)
                appendLine()
                appendLine("Rating claim: ${row.profile.ratingInfluenceClaim}")
                appendLine()
                appendLine("- Rated top $TOP_K: ${row.ratedTitles.joinToString()}.")
                appendLine("- Rating-neutral top $TOP_K: ${row.neutralTitles.joinToString()}.")
                appendLine("- Refreshed top $TOP_K: ${row.refreshedTitles.joinToString()}.")
            }
        }
        output.writeText(report, Charsets.UTF_8)
        println("EXPERT_EVALUATION_REPORT=${output.absolutePath}")
    }

    private fun Number.format(decimals: Int): String = String.format(Locale.US, "%.${decimals}f", toDouble())

    private companion object {
        const val TOP_K = 20
        const val MIN_RATING_SET_CHANGES = 3
        const val MIN_REFRESH_SET_CHANGES = 2
        const val MAX_REFRESH_SCORE_LOSS = 0.05f
    }
}

private data class ProfileEvaluation(
    val profile: ExpertProfile,
    val ratedTitles: List<String>,
    val neutralTitles: List<String>,
    val refreshedTitles: List<String>,
    val ratingChanged: Int,
    val refreshChanged: Int,
    val minimumSequentialRefreshChanges: Int,
    val focusHits: Int,
    val refreshedFocusHits: Int,
    val ratedGoodHits: Int,
    val neutralGoodHits: Int,
    val ratedBadHits: Int,
    val neutralBadHits: Int,
    val strongestPenalty: Float,
    val ratedMeanScore: Float,
    val refreshedMeanScore: Float
)
