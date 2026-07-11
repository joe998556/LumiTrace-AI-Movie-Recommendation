package com.lumitrace.app.network

import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object ApiClient {
    private const val TMDB_BASE_URL = "https://api.themoviedb.org/3/"
    private const val TRAKT_BASE_URL = "https://api.trakt.tv/"

    private val okHttpClient = OkHttpClient.Builder().build()

    private val tmdbRetrofit = Retrofit.Builder()
        .baseUrl(TMDB_BASE_URL)
        .client(okHttpClient)
        .addConverterFactory(GsonConverterFactory.create())
        .build()

    private val traktRetrofit = Retrofit.Builder()
        .baseUrl(TRAKT_BASE_URL)
        .client(okHttpClient)
        .addConverterFactory(GsonConverterFactory.create())
        .build()

    val tmdbService: TmdbApiService = tmdbRetrofit.create(TmdbApiService::class.java)
    val traktService: TraktApiService = traktRetrofit.create(TraktApiService::class.java)
}
