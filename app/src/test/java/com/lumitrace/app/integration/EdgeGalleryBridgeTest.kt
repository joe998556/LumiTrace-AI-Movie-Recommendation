package com.lumitrace.app.integration

import com.lumitrace.app.data.Movie
import com.lumitrace.app.ui.MovieJournalEntry
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class EdgeGalleryBridgeTest {
    @Test
    fun bridgeTargetsTheInstalledGemmaFourModel() {
        assertTrue(EdgeGalleryBridge.PREFERRED_MODEL_NAME == "Gemma-4-E4B-it")
    }

    @Test
    fun promptIncludesGroundedTasteAndRecommendationContext() {
        val prompt = EdgeGalleryBridge.buildRecommendationPrompt(
            watchedMovies = listOf(
                Movie(id = 1, title = "Arrival"),
                Movie(id = 2, title = "Aftersun")
            ),
            journalEntries = mapOf(
                1 to MovieJournalEntry(rating = 9.2f),
                2 to MovieJournalEntry(rating = 7f)
            ),
            recommendations = listOf(
                Movie(
                    id = 3,
                    title = "Contact",
                    overview = "A scientist receives an extraterrestrial signal.",
                    reason = "Semantic match to reflective science fiction."
                )
            )
        )

        assertTrue(prompt.contains("Arrival (9.2/10)"))
        assertTrue(prompt.contains("Contact"))
        assertTrue(prompt.contains("Semantic match to reflective science fiction."))
        assertTrue(prompt.contains("Do not invent actors, directors, awards"))
        assertFalse(prompt.contains("Christopher Nolan"))
    }

    @Test
    fun promptLimitsPrivateTasteContext() {
        val watched = (1..30).map { Movie(id = it, title = "Watched $it") }
        val recommendations = (1..20).map { Movie(id = 100 + it, title = "Match $it") }

        val prompt = EdgeGalleryBridge.buildRecommendationPrompt(
            watchedMovies = watched,
            journalEntries = emptyMap(),
            recommendations = recommendations
        )

        assertTrue(prompt.contains("Watched 12"))
        assertFalse(prompt.contains("Watched 13"))
        assertTrue(prompt.contains("Match 8"))
        assertFalse(prompt.contains("Match 9"))
    }
}
