package com.lumitrace.app.network

import com.google.gson.Gson
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class TraktSyncPlannerTest {
    @Test
    fun historyPlanExcludesRemoteAndDuplicateMovies() {
        val plan = TraktSyncPlanner.historyToAdd(
            localTmdbIds = listOf(0, 603, 603, 27205, 157336),
            remoteTmdbIds = setOf(603)
        )

        assertEquals(listOf(27205, 157336), plan.map { it.ids.tmdb })
        assertTrue(plan.all { it.watchedAt == "unknown" })
    }

    @Test
    fun ratingPlanRoundsOnlyForTraktAndSkipsUnchangedValues() {
        val plan = TraktSyncPlanner.ratingsToUpload(
            localRatings = mapOf(
                603 to 8.4f,
                27205 to 8.6f,
                157336 to 0f,
                335984 to 10f
            ),
            remoteRatings = mapOf(603 to 8, 27205 to 8)
        )

        assertEquals(listOf(27205, 335984), plan.map { it.ids.tmdb })
        assertEquals(listOf(9, 10), plan.map { it.rating })
    }

    @Test
    fun deviceAndSyncJsonUseTraktFieldNamesWithoutBundledCredentials() {
        val gson = Gson()
        val deviceJson = gson.toJson(TraktDeviceTokenRequest("device", "client", "secret"))
        val syncJson = gson.toJson(
            TraktRatingSyncRequest(
                movies = listOf(TraktRatingMovie(9, TraktMovieIds(tmdb = 27205)))
            )
        )

        assertTrue(deviceJson.contains("\"client_id\":\"client\""))
        assertTrue(deviceJson.contains("\"client_secret\":\"secret\""))
        assertTrue(syncJson.contains("\"tmdb\":27205"))
        assertTrue(syncJson.contains("\"rating\":9"))
        assertFalse(syncJson.contains("client_secret"))
    }
}
