package com.lumitrace.app.data

import org.junit.Assert.assertEquals
import org.junit.Test

class RatingRegressionTest {
    private val first = Movie(id = 1, title = "First", originalLanguage = "en", genreIds = listOf(18), releaseDate = "2024-01-01")

    @Test
    fun `direct assertions against normalizeUserRating`() {
        assertEquals(0f, normalizeUserRating(Float.NaN))
        assertEquals(10f, normalizeUserRating(Float.POSITIVE_INFINITY))
        assertEquals(0f, normalizeUserRating(Float.NEGATIVE_INFINITY))
        assertEquals(0f, normalizeUserRating(0f))
        assertEquals(1f, normalizeUserRating(0.01f))
        assertEquals(10f, normalizeUserRating(10.01f))
        assertEquals(7.3f, normalizeUserRating(7.34f))
    }

    @Test
    fun `below and above range clamping`() {
        val library = LocalTasteLibrary(now = { 1L })
        library.markWatched(first)

        // Test below range: should clamp to 1.0
        library.setRating(first.id, 0.5f)
        assertEquals(1.0f, library.recommendationSeeds().first().rating)

        // Test above range: should clamp to 10.0
        library.setRating(first.id, 11.5f)
        assertEquals(10.0f, library.recommendationSeeds().first().rating)

        // Test exactly 0.0: should be allowed (cleared)
        library.setRating(first.id, 0.0f)
        assertEquals(0.0f, library.recommendationSeeds().first().rating)
    }

    @Test
    fun `0_1 decimal persistence`() {
        val library = LocalTasteLibrary(now = { 1L })
        library.markWatched(first)

        library.setRating(first.id, 7.34f)
        assertEquals(7.3f, library.recommendationSeeds().first().rating)

        library.setRating(first.id, 8.87f)
        assertEquals(8.9f, library.recommendationSeeds().first().rating)
    }
}
