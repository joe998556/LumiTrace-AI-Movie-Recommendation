package com.lumitrace.app.network

import com.lumitrace.app.data.Movie
import com.lumitrace.app.data.RecommendationRequest
import com.lumitrace.app.data.TmdbResponse
import okhttp3.ResponseBody
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query
import retrofit2.http.Url

interface TmdbApiService {
    // TMDB Direct (e.g., endpoint="movie/popular")
    @GET("{endpoint}")
    suspend fun getTmdbData(
        @Path("endpoint", encoded = true) endpoint: String,
        @Query("api_key") apiKey: String,
        @Query("page") page: Int = 1,
        @Query("query") query: String? = null
    ): TmdbResponse<Movie>
}

interface BertApiService {
    // Semantic AI Recommendations - connecting directly to Remote Server
    // Use @Url to pass the full dynamic URL from BuildConfig
    @POST
    suspend fun getSemanticRecommendations(
        @Url url: String,
        @Body request: RecommendationRequest
    ): ResponseBody
}
