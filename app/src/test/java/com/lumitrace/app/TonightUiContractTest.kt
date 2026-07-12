package com.lumitrace.app

import org.junit.Assert.assertEquals
import org.junit.Test

class TonightUiContractTest {
    @Test
    fun unwatchedPickUsesActionCopyInsteadOfCompletedState() {
        assertEquals("Mark watched", watchedActionLabel(isWatched = false))
        assertEquals("Watched", watchedActionLabel(isWatched = true))
    }

    @Test
    fun recommendationButtonMakesRefreshBehaviorExplicit() {
        assertEquals("Run recommendation", recommendationActionLabel(hasResults = false, isLoading = false))
        assertEquals("Refresh recommendations", recommendationActionLabel(hasResults = true, isLoading = false))
        assertEquals("Ranking locally", recommendationActionLabel(hasResults = true, isLoading = true))
    }
}
