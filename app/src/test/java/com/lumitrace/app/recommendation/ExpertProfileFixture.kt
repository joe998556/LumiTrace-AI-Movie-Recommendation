package com.lumitrace.app.recommendation

import com.google.gson.Gson

internal object ExpertProfileFixture {
    val data: ExpertFixture by lazy {
        ExpertProfileFixture::class.java.getResourceAsStream("/recommendation/expert_profiles.json")
            ?.bufferedReader(Charsets.UTF_8)
            ?.use { Gson().fromJson(it, ExpertFixture::class.java) }
            ?: error("Expert profile fixture was not found")
    }
}

internal data class ExpertFixture(
    val version: Int = 0,
    val profiles: List<ExpertProfile> = emptyList()
)

internal data class ExpertProfile(
    val id: String = "",
    val persona: String = "",
    val focusGenreIds: Set<Int> = emptySet(),
    val minimumFocusHits: Int = 0,
    val watchedRatings: List<RatedMovie> = emptyList(),
    val goodUnseen: List<ExpectedMovie> = emptyList(),
    val badUnseen: List<ExpectedMovie> = emptyList(),
    val ratingInfluenceClaim: String = ""
)

internal data class RatedMovie(
    val id: Int = 0,
    val title: String = "",
    val rating: Float = 0f
)

internal data class ExpectedMovie(
    val id: Int = 0,
    val title: String = ""
)
