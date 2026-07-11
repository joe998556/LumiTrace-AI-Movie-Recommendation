package com.lumitrace.app.data

import com.google.gson.annotations.SerializedName

data class TmdbGenre(
    val id: Int = 0,
    val name: String = ""
)

data class Movie(
    val id: Int = 0,
    val title: String = "Untitled",
    val overview: String = "",
    @SerializedName("poster_path") val posterPath: String? = null,
    @SerializedName("release_date") val releaseDate: String = "",
    @SerializedName("vote_average") val voteAverage: Double = 0.0,
    @SerializedName("original_language") val originalLanguage: String = "",
    @SerializedName("genre_ids") val genreIds: List<Int> = emptyList(),
    /** TMDB /movie/{id} returns genres as objects, not genre_ids. */
    val genres: List<TmdbGenre> = emptyList(),
    @SerializedName("runtime") val runtimeMinutes: Int = 0,
    val reason: String? = null
) {
    /** Prefer genre_ids (list endpoints); fall back to detail-payload genres. */
    fun resolvedGenreIds(): List<Int> = genreIds.ifEmpty { genres.map { it.id }.filter { it > 0 } }
}

// Simplified wrapper for TMDB pagination
data class TmdbResponse<T>(
    val page: Int,
    val results: List<T>,
    @SerializedName("total_pages") val totalPages: Int,
    @SerializedName("total_results") val totalResults: Int
)
