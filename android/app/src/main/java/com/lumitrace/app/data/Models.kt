package com.lumitrace.app.data

import com.google.gson.annotations.SerializedName

data class Movie(
    val id: Int,
    val title: String,
    val overview: String,
    @SerializedName("poster_path") val posterPath: String?,
    @SerializedName("vote_average") val voteAverage: Double,
    @SerializedName("genre_ids") val genreIds: List<Int>
)

data class RecommendationRequest(
    val overviews: List<String>,
    @SerializedName("exclude_ids") val excludeIds: List<Int> = emptyList(),
    @SerializedName("user_genre_ids") val userGenreIds: List<List<Int>> = emptyList(),
    @SerializedName("user_vote_counts") val userVoteCounts: List<Int> = emptyList(),
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
