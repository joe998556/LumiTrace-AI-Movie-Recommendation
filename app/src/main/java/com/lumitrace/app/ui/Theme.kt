package com.lumitrace.app.ui

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

val Ink = Color(0xFF080807)
val Ink2 = Color(0xFF0F0E0C)
val Ink3 = Color(0xFF15130F)
val Text = Color(0xFFF5EFE3)
val TextSoft = Color(0xFFCFC5B4)
val Muted = Color(0xFF8B8171)
val Dim = Color(0xFF5F574B)
val Teal = Color(0xFF20D0BA)
val Teal2 = Color(0xFF9FF5E7)
val TealDeep = Color(0xFF0F7F75)
val Sage = Color(0xFF8FBEA9)
val Clay = Color(0xFFCC7B5E)
val PanelStrong = Color(0xED1D1A16)
val PanelSoft = Color(0x0EF5EFE3)
val OuterShell = Color(0x0CFFFFFF)
val InnerHighlight = Color(0x26FFFFFF)
val Line = Color(0x21F5EFE3)
val LineStrong = Color(0x3DF5EFE3)
val Danger = Color(0xFFDE816F)
val GlassBg = PanelSoft

private val DarkColors = darkColorScheme(
    primary = Teal,
    secondary = Sage,
    background = Ink,
    surface = PanelStrong,
    surfaceVariant = GlassBg,
    onPrimary = Ink,
    onSecondary = Ink,
    onBackground = Text,
    onSurface = Text,
    onSurfaceVariant = TextSoft,
    error = Danger,
    outline = Line,
    outlineVariant = LineStrong
)

private val LumiTypography = Typography(
    displayLarge = TextStyle(
        fontFamily = FontFamily.Serif,
        fontWeight = FontWeight.Medium,
        fontSize = 54.sp,
        lineHeight = 52.sp,
        letterSpacing = 0.sp
    ),
    headlineSmall = TextStyle(
        fontFamily = FontFamily.Serif,
        fontWeight = FontWeight.Medium,
        fontSize = 28.sp,
        lineHeight = 32.sp,
        letterSpacing = 0.sp
    ),
    bodyLarge = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Normal,
        fontSize = 15.sp,
        lineHeight = 23.sp,
        letterSpacing = 0.sp
    ),
    labelSmall = TextStyle(
        fontFamily = FontFamily.Monospace,
        fontWeight = FontWeight.Bold,
        fontSize = 10.sp,
        lineHeight = 14.sp,
        letterSpacing = 1.8.sp
    )
)

@Composable
fun AppTheme(
    darkTheme: Boolean = true,
    content: @Composable () -> Unit
) {
    MaterialTheme(
        colorScheme = DarkColors,
        typography = LumiTypography,
        content = content
    )
}
