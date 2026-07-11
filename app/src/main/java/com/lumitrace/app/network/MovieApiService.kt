package com.lumitrace.app.network

import com.lumitrace.app.data.Movie
import com.lumitrace.app.data.TmdbResponse
import retrofit2.http.GET
import retrofit2.http.Path
import retrofit2.http.Query

interface TmdbApiService {
    // TMDB Direct (e.g., endpoint="movie/popular")
    @GET("{endpoint}")
    suspend fun getTmdbData(
        @Path("endpoint", encoded = true) endpoint: String,
        @Query("api_key") apiKey: String,
        @Query("page") page: Int = 1,
        @Query("query") query: String? = null
    ): TmdbResponse<Movie>

    @GET("movie/{movieId}")
    suspend fun getMovieDetails(
        @Path("movieId") movieId: Int,
        @Query("api_key") apiKey: String
    ): Movie
}
