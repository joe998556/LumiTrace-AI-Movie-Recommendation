package com.lumitrace.app.data

import com.google.gson.annotations.SerializedName

data class Movie(
    val id: Int = 0,
    val title: String = "Untitled",
    val overview: String = "",
    @SerializedName("poster_path") val posterPath: String? = null,
    @SerializedName("release_date") val releaseDate: String = "",
    @SerializedName("vote_average") val voteAverage: Double = 0.0,
    @SerializedName("original_language") val originalLanguage: String = "",
    @SerializedName("genre_ids") val genreIds: List<Int> = emptyList()
)

data class RecommendationRequest(
    val overviews: List<String>,
    @SerializedName("user_movie_ids") val userMovieIds: List<Int> = emptyList(),
    @SerializedName("exclude_ids") val excludeIds: List<Int> = emptyList(),
    @SerializedName("user_genre_ids") val userGenreIds: List<List<Int>> = emptyList(),
    @SerializedName("user_vote_counts") val userVoteCounts: List<Double> = emptyList(),
    @SerializedName("user_release_years") val userReleaseYears: List<Int> = emptyList(),
    @SerializedName("playlist_genre_ids") val playlistGenreIds: List<Int> = emptyList(),
    @SerializedName("preferred_languages") val preferredLanguages: List<String> = emptyList(),
    @SerializedName("top_k") val topK: Int = 18
)

data class RecommendationResponse(
    val results: List<Movie>,
    val fallback: String? = null,
    val error: String? = null
)

// Simplified wrapper for TMDB pagination
data class TmdbResponse<T>(
    val page: Int,
    val results: List<T>,
    @SerializedName("total_pages") val totalPages: Int,
    @SerializedName("total_results") val totalResults: Int
)
