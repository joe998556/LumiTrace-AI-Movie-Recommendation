package com.lumitrace.app

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.espresso.Espresso.pressBack
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class SettingsBackNavigationTest {
    @get:Rule
    val composeRule = createAndroidComposeRule<MainActivity>()

    @Test
    fun pressingSystemBackFromSettingsReturnsHomeWithoutClosingApp() {
        composeRule.onNodeWithContentDescription("Settings").performClick()
        composeRule.onNodeWithText("Your TMDB connection").assertIsDisplayed()

        pressBack()

        composeRule.onNodeWithText("Your TMDB connection").assertDoesNotExist()
        composeRule.onNodeWithContentDescription("Settings").assertIsDisplayed()
    }
}
