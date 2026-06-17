package com.lumitrace.app.network

import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object ApiClient {
    private const val TMDB_BASE_URL = "https://api.themoviedb.org/3/"

    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.NONE
    }

    private val okHttpClient = OkHttpClient.Builder()
        .addInterceptor(loggingInterceptor)
        .build()

    // Retrofit instance specifically for TMDB
    private val tmdbRetrofit = Retrofit.Builder()
        .baseUrl(TMDB_BASE_URL)
        .client(okHttpClient)
        .addConverterFactory(GsonConverterFactory.create())
        .build()

    // Retrofit instance for the BERT Remote Server
    // Since we use @Url in the interface, the baseUrl here is just a dummy placeholder
    private val bertRetrofit = Retrofit.Builder()
        .baseUrl("https://dummy.com/")
        .addConverterFactory(GsonConverterFactory.create())
        .client(OkHttpClient.Builder().addInterceptor(loggingInterceptor).build())
        .build()

    val tmdbService: TmdbApiService = tmdbRetrofit.create(TmdbApiService::class.java)
    val bertService: BertApiService = bertRetrofit.create(BertApiService::class.java)
}
