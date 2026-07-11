package com.lumitrace.app.network

import kotlin.math.roundToInt

object TraktSyncPlanner {
    fun historyToAdd(
        localTmdbIds: Iterable<Int>,
        remoteTmdbIds: Set<Int>
    ): List<TraktHistoryMovie> {
        return localTmdbIds
            .asSequence()
            .filter { it > 0 && it !in remoteTmdbIds }
            .distinct()
            .sorted()
            .map { TraktHistoryMovie(ids = TraktMovieIds(tmdb = it)) }
            .toList()
    }

    fun ratingsToUpload(
        localRatings: Map<Int, Float>,
        remoteRatings: Map<Int, Int>
    ): List<TraktRatingMovie> {
        return localRatings
            .asSequence()
            .filter { (movieId, rating) -> movieId > 0 && rating > 0f }
            .map { (movieId, rating) ->
                TraktRatingMovie(
                    rating = rating.roundToInt().coerceIn(1, 10),
                    ids = TraktMovieIds(tmdb = movieId)
                )
            }
            .filter { remoteRatings[it.ids.tmdb] != it.rating }
            .sortedBy { it.ids.tmdb }
            .toList()
    }
}
