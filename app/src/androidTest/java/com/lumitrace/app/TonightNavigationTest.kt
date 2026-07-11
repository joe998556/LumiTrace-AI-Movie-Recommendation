package com.lumitrace.app

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class TonightNavigationTest {
    @get:Rule
    val composeRule = createAndroidComposeRule<MainActivity>()

    @Test
    fun tonightOpensCompactNamedFilterGroups() {
        composeRule.onNodeWithText("Tonight").performClick()

        composeRule.onNodeWithTag("tonight_filters").assertIsDisplayed()
        composeRule.onNodeWithText("Mood").assertIsDisplayed()
        composeRule.onNodeWithText("Language").assertIsDisplayed()
        composeRule.onNodeWithText("Pace").assertIsDisplayed()
        composeRule.onNodeWithText("Company").assertIsDisplayed()
        composeRule.onNodeWithText("Genre").assertIsDisplayed()
        composeRule.onNodeWithText("[fast]").assertDoesNotExist()
    }
}
