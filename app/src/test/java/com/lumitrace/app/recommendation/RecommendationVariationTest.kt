package com.lumitrace.app.recommendation

import org.junit.Assert.assertEquals
import org.junit.Test

class RecommendationVariationTest {
    @Test
    fun refreshAdvancesSeedWhileLoadMoreKeepsTheActiveRunStable() {
        val variation = RecommendationVariation()

        assertEquals(0L, variation.seedFor(expand = false))
        assertEquals(0L, variation.seedFor(expand = true))
        assertEquals(1L, variation.seedFor(expand = false))
        assertEquals(1L, variation.seedFor(expand = true))

        variation.reset()
        assertEquals(0L, variation.seedFor(expand = false))
    }
}
