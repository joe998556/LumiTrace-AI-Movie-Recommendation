package com.lumitrace.app.recommendation

import java.util.Locale
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class RankingCalibrationTest {
    @Test
    fun reportsWeightSensitivityAcrossAllExpertProfiles() {
        val componentWeights = listOf(
            Triple(0.70f, 0.22f, 0.08f),
            Triple(0.64f, 0.22f, 0.14f),
            Triple(0.58f, 0.22f, 0.20f),
            Triple(0.64f, 0.18f, 0.18f)
        )
        val negativeWeights = listOf(0.24f, 0.32f, 0.40f)
        val rows = componentWeights.flatMap { (semantic, genre, quality) ->
            negativeWeights.map { negative ->
                evaluate(
                    RankingWeights(
                        semantic = semantic,
                        genre = genre,
                        quality = quality,
                        negativePenalty = negative,
                        refreshSpread = 0.04f
                    )
                )
            }
        }.sortedWith(
            compareByDescending<CalibrationRow> { it.preferenceLift }
                .thenByDescending { it.badReduction }
                .thenByDescending { it.ratedGoodHits }
                .thenByDescending { it.focusHits }
        )

        println("CALIBRATION semantic genre quality negative | ratedGood neutralGood ratedBad neutralBad | lift badReduction focus ratingChanges minChanges")
        rows.forEach { row ->
            println(
                "CALIBRATION ${row.weights.semantic.f(2)} ${row.weights.genre.f(2)} ${row.weights.quality.f(2)} ${row.weights.negativePenalty.f(2)} | " +
                    "${row.ratedGoodHits} ${row.neutralGoodHits} ${row.ratedBadHits} ${row.neutralBadHits} | " +
                    "${row.preferenceLift} ${row.badReduction} ${row.focusHits} ${row.ratingChanges} ${row.minimumProfileChanges}"
            )
        }

        assertEquals(12, rows.size)
        val production = rows.single { it.weights == RankingWeights() }
        assertTrue(production.preferenceLift > 0)
        assertTrue(production.badReduction > 0)
        assertTrue(production.focusHits >= 115)
        assertTrue(production.minimumProfileChanges >= 3)
    }

    private fun evaluate(weights: RankingWeights): CalibrationRow {
        var ratedGoodHits = 0
        var neutralGoodHits = 0
        var ratedBadHits = 0
        var neutralBadHits = 0
        var focusHits = 0
        var ratingChanges = 0
        var minimumProfileChanges = Int.MAX_VALUE
        ExpertProfileFixture.data.profiles.forEach { profile ->
            val rated = LocalRecommendationRanker.rank(
                catalog = BundledTestCatalog.catalog,
                rawSignals = profile.watchedRatings.map { BundledTestCatalog.signal(it.id, it.rating) },
                requestedTopK = TOP_K,
                weights = weights
            )
            val neutral = LocalRecommendationRanker.rank(
                catalog = BundledTestCatalog.catalog,
                rawSignals = profile.watchedRatings.map { BundledTestCatalog.signal(it.id, 0f) },
                requestedTopK = TOP_K,
                weights = weights
            )
            val ratedIds = rated.movies.mapTo(hashSetOf()) { it.id }
            val neutralIds = neutral.movies.mapTo(hashSetOf()) { it.id }
            val goodIds = profile.goodUnseen.mapTo(hashSetOf()) { it.id }
            val badIds = profile.badUnseen.mapTo(hashSetOf()) { it.id }
            val changed = TOP_K - ratedIds.intersect(neutralIds).size
            ratedGoodHits += ratedIds.count { it in goodIds }
            neutralGoodHits += neutralIds.count { it in goodIds }
            ratedBadHits += ratedIds.count { it in badIds }
            neutralBadHits += neutralIds.count { it in badIds }
            focusHits += rated.movies.count { movie -> movie.genreIds.any { it in profile.focusGenreIds } }
            ratingChanges += changed
            minimumProfileChanges = minOf(minimumProfileChanges, changed)
        }
        val ratedUtility = ratedGoodHits - ratedBadHits
        val neutralUtility = neutralGoodHits - neutralBadHits
        return CalibrationRow(
            weights = weights,
            ratedGoodHits = ratedGoodHits,
            neutralGoodHits = neutralGoodHits,
            ratedBadHits = ratedBadHits,
            neutralBadHits = neutralBadHits,
            preferenceLift = ratedUtility - neutralUtility,
            badReduction = neutralBadHits - ratedBadHits,
            focusHits = focusHits,
            ratingChanges = ratingChanges,
            minimumProfileChanges = minimumProfileChanges
        )
    }

    private fun Float.f(decimals: Int): String = String.format(Locale.US, "%.${decimals}f", this)

    private companion object {
        const val TOP_K = 20
    }
}

private data class CalibrationRow(
    val weights: RankingWeights,
    val ratedGoodHits: Int,
    val neutralGoodHits: Int,
    val ratedBadHits: Int,
    val neutralBadHits: Int,
    val preferenceLift: Int,
    val badReduction: Int,
    val focusHits: Int,
    val ratingChanges: Int,
    val minimumProfileChanges: Int
)
