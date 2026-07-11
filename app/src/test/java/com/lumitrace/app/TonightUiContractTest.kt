package com.lumitrace.app

import org.junit.Assert.assertEquals
import org.junit.Test

class TonightUiContractTest {
    @Test
    fun unwatchedPickUsesActionCopyInsteadOfCompletedState() {
        assertEquals("Mark watched", watchedActionLabel(isWatched = false))
        assertEquals("Watched", watchedActionLabel(isWatched = true))
    }
}
