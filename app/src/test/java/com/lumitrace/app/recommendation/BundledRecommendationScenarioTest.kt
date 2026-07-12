package com.lumitrace.app.recommendation

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class BundledRecommendationScenarioTest {
    @Test
    fun scienceFictionTasteReturnsCoherentUnwatchedPicks() {
        val seeds = listOf(
            signal(329865, 9f), // Arrival
            signal(157336, 9f), // Interstellar
            signal(27205, 8.5f), // Inception
            signal(348, 2f) // Alien: explicit negative preference
        )

        val result = LocalRecommendationRanker.rank(BundledTestCatalog.catalog, seeds, requestedTopK = 20)
        val titles = result.movies.joinToString { it.title }
        println("SCI_FI_SCENARIO=$titles")

        assertEquals(20, result.movies.size)
        assertFalse("Seeds leaked into recommendations: $titles", result.movies.any { movie -> seeds.any { it.movie.id == movie.id } })
        assertTrue(
            "Expected a clear science-fiction signal, got: $titles",
            result.movies.count { 878 in it.genreIds } >= 8
        )
        assertTrue(result.movies.all { it.reason.orEmpty().startsWith("Semantically close to") })
        assertEquals(result.movies.map { it.id }.toSet(), result.traces.keys)
    }

    @Test
    fun familyTasteKeepsFamilyAndAnimationProminent() {
        val seeds = listOf(signal(862, 9f), signal(12, 9f)) // Toy Story, Finding Nemo

        val result = LocalRecommendationRanker.rank(BundledTestCatalog.catalog, seeds, requestedTopK = 12)
        val titles = result.movies.joinToString { it.title }
        val familyGenres = setOf(16, 10751)
        println("FAMILY_SCENARIO=$titles")

        assertFalse(result.movies.any { movie -> seeds.any { it.movie.id == movie.id } })
        assertTrue(
            "Expected family or animation picks, got: $titles",
            result.movies.count { movie -> movie.genreIds.any { it in familyGenres } } >= 6
        )
    }

    @Test
    fun crimeDramaTasteReturnsGenreRelevantCandidates() {
        val seeds = listOf(
            signal(238, 9.5f), // The Godfather
            signal(680, 9f), // Pulp Fiction
            signal(155, 8.5f) // The Dark Knight
        )

        val result = LocalRecommendationRanker.rank(BundledTestCatalog.catalog, seeds, requestedTopK = 12)
        val titles = result.movies.joinToString { it.title }
        val relatedGenres = setOf(80, 18, 53)
        println("CRIME_SCENARIO=$titles")

        assertFalse(result.movies.any { movie -> seeds.any { it.movie.id == movie.id } })
        assertTrue(
            "Expected crime, drama, or thriller picks, got: $titles",
            result.movies.count { movie -> movie.genreIds.any { it in relatedGenres } } >= 8
        )
    }

    @Test
    fun explicitLowRatingCreatesARealPostRankingPenalty() {
        val seeds = listOf(signal(329865, 9f), signal(348, 1f)) // Arrival liked, Alien disliked

        val result = LocalRecommendationRanker.rank(BundledTestCatalog.catalog, seeds, requestedTopK = 100)
        val strongestPenalty = result.traces.values.maxOf { it.negativePreferencePenalty }

        assertTrue("Expected the disliked Alien signal to penalize a nearby candidate.", strongestPenalty > 0.05f)
        assertTrue(result.traces.values.all { it.finalScore <= it.baseScore + 0.0001f })
    }

    private fun signal(id: Int, rating: Float): TasteSignal = BundledTestCatalog.signal(id, rating)
}
