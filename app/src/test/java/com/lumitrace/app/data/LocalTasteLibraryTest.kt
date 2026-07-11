package com.lumitrace.app.data

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class LocalTasteLibraryTest {
    private val first = Movie(id = 1, title = "First", originalLanguage = "en", genreIds = listOf(18), releaseDate = "2024-01-01")
    private val second = Movie(id = 2, title = "Second", originalLanguage = "ja", genreIds = listOf(16), releaseDate = "2022-01-01")

    @Test
    fun `watchlist entries do not become recommendation seeds`() {
        val library = LocalTasteLibrary(now = { 1L }, ids = { "family" })

        library.addToWatchlist(first)

        assertTrue(library.recommendationSeeds().isEmpty())
        library.markWatched(first)
        assertEquals(listOf(first.id), library.recommendationSeeds().map { it.movie.id })
    }

    @Test
    fun `profiles isolate library state and feedback`() {
        val library = LocalTasteLibrary(now = { 1L }, ids = { "family" })
        library.markWatched(first)
        val family = library.createProfile("Family")
        library.addToWatchlist(second)
        library.recordFeedback(second.id, FeedbackKind.NOT_TONIGHT)

        assertEquals(listOf(second.id), library.snapshot().profiles.first { it.id == family.id }.entries.map { it.movie.id })
        library.selectProfile("default")
        assertEquals(listOf(first.id), library.recommendationSeeds().map { it.movie.id })
        assertTrue(library.snapshot().profiles.first { it.id == "default" }.feedback.isEmpty())
    }

    @Test
    fun `tonight filters only apply local context and already seen feedback`() {
        val library = LocalTasteLibrary(now = { 1L })
        library.recordFeedback(first.id, FeedbackKind.ALREADY_SEEN)

        val picks = library.tonightShortlist(
            candidates = listOf(first, second),
            context = ViewingContext(language = "ja", genreIds = setOf(16), minYear = 2020)
        )

        assertEquals(listOf(second.id), picks.map { it.id })
        assertFalse(picks.any { it.id == first.id })
    }

    @Test
    fun `tonight uses hard runtime and deterministic mood preferences on device`() {
        val warm = first.copy(id = 3, title = "Warm", genreIds = listOf(35), runtimeMinutes = 90)
        val tense = first.copy(id = 4, title = "Tense", genreIds = listOf(53), runtimeMinutes = 150)
        val library = LocalTasteLibrary(now = { 1L })

        val picks = library.tonightShortlist(
            candidates = listOf(tense, warm),
            context = ViewingContext(maxRuntimeMinutes = 110, mood = "warm")
        )

        assertEquals(listOf(warm.id), picks.map { it.id })
    }

    @Test
    fun `tonight excludes not-tonight feedback and watched movies`() {
        val keep = first.copy(id = 10, title = "Keep", genreIds = listOf(35), runtimeMinutes = 95)
        val skipped = first.copy(id = 11, title = "Skipped", genreIds = listOf(35), runtimeMinutes = 90)
        val watched = first.copy(id = 12, title = "Watched", genreIds = listOf(35), runtimeMinutes = 88)
        val library = LocalTasteLibrary(now = { 1L })
        library.recordFeedback(skipped.id, FeedbackKind.NOT_TONIGHT)
        library.markWatched(watched)

        val picks = library.tonightShortlist(
            candidates = listOf(skipped, watched, keep),
            context = ViewingContext(mood = "warm")
        )

        assertEquals(listOf(keep.id), picks.map { it.id })
    }

    @Test
    fun `tonight requires every selected context dimension instead of loose genre union`() {
        // Friends + warm: action/thriller alone used to pass via the old union filter.
        val actionOnly = first.copy(id = 20, title = "Action", genreIds = listOf(28), runtimeMinutes = 100)
        val warmComedy = first.copy(id = 21, title = "Warm comedy", genreIds = listOf(35), runtimeMinutes = 100)
        val library = LocalTasteLibrary(now = { 1L })

        val picks = library.tonightShortlist(
            candidates = listOf(actionOnly, warmComedy),
            context = ViewingContext(mood = "warm", companion = "friends")
        )

        assertEquals(listOf(warmComedy.id), picks.map { it.id })
        assertFalse(picks.any { it.id == actionOnly.id })
    }

    @Test
    fun `tonight ranks stronger context fit and watchlist ahead of weaker taste order`() {
        val weakTasteStrongFit = first.copy(
            id = 30,
            title = "Queued warm",
            genreIds = listOf(35, 10749),
            runtimeMinutes = 90,
            voteAverage = 7.5
        )
        val strongTasteWeakFit = first.copy(
            id = 31,
            title = "Barely warm",
            genreIds = listOf(35, 28, 53),
            runtimeMinutes = 109,
            voteAverage = 6.0
        )
        val library = LocalTasteLibrary(now = { 1L })
        library.addToWatchlist(weakTasteStrongFit)

        val picks = library.tonightShortlist(
            candidates = listOf(strongTasteWeakFit, weakTasteStrongFit),
            context = ViewingContext(maxRuntimeMinutes = 110, mood = "warm"),
            limit = 2,
            // Equal taste so context precision + watchlist decide the order.
            tasteScores = mapOf(strongTasteWeakFit.id to 0.5f, weakTasteStrongFit.id to 0.5f)
        )

        assertEquals(listOf(weakTasteStrongFit.id, strongTasteWeakFit.id), picks.map { it.id })
    }

    @Test
    fun `tonight blends real taste scores instead of candidate list order`() {
        val watchlistFiller = first.copy(
            id = 40,
            title = "Queued filler",
            genreIds = listOf(35),
            runtimeMinutes = 100,
            voteAverage = 6.0
        )
        val trueTasteMatch = first.copy(
            id = 41,
            title = "Strong taste match",
            genreIds = listOf(35),
            runtimeMinutes = 100,
            voteAverage = 6.0
        )
        val library = LocalTasteLibrary(now = { 1L })
        library.addToWatchlist(watchlistFiller)

        // Watchlist is first in the list (old bug: that stole taste rank 0).
        val picks = library.tonightShortlist(
            candidates = listOf(watchlistFiller, trueTasteMatch),
            context = ViewingContext(mood = "warm"),
            limit = 1,
            tasteScores = mapOf(watchlistFiller.id to 0.1f, trueTasteMatch.id to 1.0f)
        )

        assertEquals(listOf(trueTasteMatch.id), picks.map { it.id })
    }

    @Test
    fun `not-tonight feedback expires after the evening window`() {
        var clock = 1_000L
        val keep = first.copy(id = 50, title = "Keep", genreIds = listOf(35), runtimeMinutes = 95)
        val skipped = first.copy(id = 51, title = "Skipped", genreIds = listOf(35), runtimeMinutes = 90)
        val library = LocalTasteLibrary(now = { clock })
        library.recordFeedback(skipped.id, FeedbackKind.NOT_TONIGHT)

        val blocked = library.tonightShortlist(
            candidates = listOf(skipped, keep),
            context = ViewingContext(mood = "warm")
        )
        assertEquals(listOf(keep.id), blocked.map { it.id })

        clock += 19L * 60L * 60L * 1000L
        val afterTtl = library.tonightShortlist(
            candidates = listOf(skipped, keep),
            context = ViewingContext(mood = "warm"),
            limit = 2,
            tasteScores = mapOf(skipped.id to 1f, keep.id to 0.2f)
        )
        assertTrue(afterTtl.any { it.id == skipped.id })
    }

    @Test
    fun `Trakt merge keeps a local rating while adding imported watched movies`() {
        val library = LocalTasteLibrary(now = { 1L })
        library.markWatched(first)
        library.setRating(first.id, 8.5f, "Local note")

        library.mergeWatchedFromExternal(
            movies = listOf(first, second),
            ratings = mapOf(first.id to 3f, second.id to 7f)
        )

        val entries = library.recommendationSeeds().associateBy { it.movie.id }
        assertEquals(8.5f, entries.getValue(first.id).rating)
        assertEquals("Local note", entries.getValue(first.id).note)
        assertEquals(7f, entries.getValue(second.id).rating)
    }

    @Test
    fun `feedback retains the movie locally for private recommendation signals`() {
        val library = LocalTasteLibrary(now = { 1L })

        library.recordFeedback(first, FeedbackKind.MORE_LIKE_THIS)

        val feedback = library.snapshot().profiles.single().feedback.single()
        assertEquals(first, feedback.movie)
        assertEquals(FeedbackKind.MORE_LIKE_THIS, feedback.kind)
    }
}
