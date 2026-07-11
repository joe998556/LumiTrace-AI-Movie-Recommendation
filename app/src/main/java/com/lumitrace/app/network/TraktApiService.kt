package com.lumitrace.app.network

import com.google.gson.annotations.SerializedName
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.Headers
import retrofit2.http.POST

private const val TRAKT_API_VERSION = "2"
private const val LUMITRACE_USER_AGENT = "LumiTrace/1.2.0 (Android)"

interface TraktApiService {
    @Headers(
        "Content-Type: application/json",
        "trakt-api-version: $TRAKT_API_VERSION",
        "User-Agent: $LUMITRACE_USER_AGENT"
    )
    @POST("oauth/device/code")
    suspend fun requestDeviceCode(
        @Header("trakt-api-key") clientId: String,
        @Body request: TraktDeviceCodeRequest
    ): Response<TraktDeviceCodeResponse>

    @Headers(
        "Content-Type: application/json",
        "trakt-api-version: $TRAKT_API_VERSION",
        "User-Agent: $LUMITRACE_USER_AGENT"
    )
    @POST("oauth/device/token")
    suspend fun pollDeviceToken(
        @Header("trakt-api-key") clientId: String,
        @Body request: TraktDeviceTokenRequest
    ): Response<TraktTokenResponse>

    @Headers(
        "Content-Type: application/json",
        "trakt-api-version: $TRAKT_API_VERSION",
        "User-Agent: $LUMITRACE_USER_AGENT"
    )
    @POST("oauth/token")
    suspend fun refreshToken(
        @Header("trakt-api-key") clientId: String,
        @Body request: TraktRefreshTokenRequest
    ): Response<TraktTokenResponse>

    @Headers(
        "Content-Type: application/json",
        "trakt-api-version: $TRAKT_API_VERSION",
        "User-Agent: $LUMITRACE_USER_AGENT"
    )
    @POST("oauth/revoke")
    suspend fun revokeToken(
        @Header("trakt-api-key") clientId: String,
        @Body request: TraktRevokeTokenRequest
    ): Response<Unit>

    @Headers(
        "Content-Type: application/json",
        "trakt-api-version: $TRAKT_API_VERSION",
        "User-Agent: $LUMITRACE_USER_AGENT"
    )
    @GET("sync/watched/movies")
    suspend fun getWatchedMovies(
        @Header("trakt-api-key") clientId: String,
        @Header("Authorization") authorization: String
    ): List<TraktWatchedMovie>

    @Headers(
        "Content-Type: application/json",
        "trakt-api-version: $TRAKT_API_VERSION",
        "User-Agent: $LUMITRACE_USER_AGENT"
    )
    @GET("users/me/ratings/movies")
    suspend fun getMovieRatings(
        @Header("trakt-api-key") clientId: String,
        @Header("Authorization") authorization: String
    ): List<TraktRatedMovie>

    @Headers(
        "Content-Type: application/json",
        "trakt-api-version: $TRAKT_API_VERSION",
        "User-Agent: $LUMITRACE_USER_AGENT"
    )
    @POST("sync/history")
    suspend fun addWatchedHistory(
        @Header("trakt-api-key") clientId: String,
        @Header("Authorization") authorization: String,
        @Body request: TraktHistorySyncRequest
    ): TraktSyncResponse

    @Headers(
        "Content-Type: application/json",
        "trakt-api-version: $TRAKT_API_VERSION",
        "User-Agent: $LUMITRACE_USER_AGENT"
    )
    @POST("sync/ratings")
    suspend fun addRatings(
        @Header("trakt-api-key") clientId: String,
        @Header("Authorization") authorization: String,
        @Body request: TraktRatingSyncRequest
    ): TraktSyncResponse
}

data class TraktDeviceCodeRequest(
    @SerializedName("client_id") val clientId: String
)

data class TraktDeviceCodeResponse(
    @SerializedName("device_code") val deviceCode: String,
    @SerializedName("user_code") val userCode: String,
    @SerializedName("verification_url") val verificationUrl: String,
    @SerializedName("expires_in") val expiresIn: Int,
    val interval: Int
)

data class TraktDeviceTokenRequest(
    val code: String,
    @SerializedName("client_id") val clientId: String,
    @SerializedName("client_secret") val clientSecret: String
)

data class TraktRefreshTokenRequest(
    @SerializedName("refresh_token") val refreshToken: String,
    @SerializedName("client_id") val clientId: String,
    @SerializedName("client_secret") val clientSecret: String,
    @SerializedName("redirect_uri") val redirectUri: String = TRAKT_OAUTH_REDIRECT_URI,
    @SerializedName("grant_type") val grantType: String = "refresh_token"
)

data class TraktTokenResponse(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("token_type") val tokenType: String,
    @SerializedName("expires_in") val expiresIn: Long,
    @SerializedName("refresh_token") val refreshToken: String,
    val scope: String,
    @SerializedName("created_at") val createdAt: Long
)

data class TraktRevokeTokenRequest(
    val token: String,
    @SerializedName("client_id") val clientId: String,
    @SerializedName("client_secret") val clientSecret: String
)

data class TraktMovieIds(
    val trakt: Int? = null,
    val slug: String? = null,
    val imdb: String? = null,
    val tmdb: Int? = null
)

data class TraktMovie(
    val title: String = "Untitled",
    val year: Int? = null,
    val ids: TraktMovieIds = TraktMovieIds()
)

data class TraktWatchedMovie(
    val plays: Int = 0,
    @SerializedName("last_watched_at") val lastWatchedAt: String? = null,
    val movie: TraktMovie = TraktMovie()
)

data class TraktRatedMovie(
    @SerializedName("rated_at") val ratedAt: String? = null,
    val rating: Int = 0,
    val movie: TraktMovie = TraktMovie()
)

data class TraktHistorySyncRequest(
    val movies: List<TraktHistoryMovie>
)

data class TraktHistoryMovie(
    val ids: TraktMovieIds,
    @SerializedName("watched_at") val watchedAt: String = "unknown"
)

data class TraktRatingSyncRequest(
    val movies: List<TraktRatingMovie>
)

data class TraktRatingMovie(
    val rating: Int,
    val ids: TraktMovieIds
)

data class TraktSyncResponse(
    val added: TraktSyncCounts = TraktSyncCounts(),
    val updated: TraktSyncCounts = TraktSyncCounts(),
    @SerializedName("not_found") val notFound: TraktNotFound = TraktNotFound()
)

data class TraktSyncCounts(
    val movies: Int = 0
)

data class TraktNotFound(
    val movies: List<TraktMovie> = emptyList()
)

const val TRAKT_OAUTH_REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"
