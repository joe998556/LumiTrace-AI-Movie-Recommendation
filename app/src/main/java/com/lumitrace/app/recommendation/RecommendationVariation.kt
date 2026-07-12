package com.lumitrace.app.recommendation

internal class RecommendationVariation {
    private var activeSeed = -1L

    fun seedFor(expand: Boolean): Long {
        if (!expand) activeSeed += 1L
        return activeSeed.coerceAtLeast(0L)
    }

    fun reset() {
        activeSeed = -1L
    }
}
