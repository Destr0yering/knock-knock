package com.knockknock.core.ui

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

val Pine = Color(0xFF183A32)
val PineLight = Color(0xFF2F6658)
val Mint = Color(0xFFDCEEE5)
val Cream = Color(0xFFF7F3E8)
val Paper = Color(0xFFFFFCF5)
val Amber = Color(0xFFF4B942)
val Ink = Color(0xFF17231F)
val MutedInk = Color(0xFF586660)
val AlertRed = Color(0xFF9C3B3B)

private val LightColors = lightColorScheme(
    primary = Pine,
    onPrimary = Color.White,
    primaryContainer = Mint,
    onPrimaryContainer = Pine,
    secondary = PineLight,
    onSecondary = Color.White,
    tertiary = Amber,
    background = Cream,
    onBackground = Ink,
    surface = Paper,
    onSurface = Ink,
    surfaceVariant = Color(0xFFE9E9DF),
    onSurfaceVariant = MutedInk,
    error = AlertRed,
)

private val DarkColors = darkColorScheme(
    primary = Color(0xFF9BD4C2),
    onPrimary = Color(0xFF0A2A22),
    primaryContainer = Color(0xFF214B40),
    secondary = Color(0xFFAECFC4),
    tertiary = Color(0xFFFFD27A),
    background = Color(0xFF101815),
    surface = Color(0xFF17211D),
)

private val KnockKnockTypography = androidx.compose.material3.Typography(
    displaySmall = TextStyle(
        fontFamily = FontFamily.Serif,
        fontWeight = FontWeight.Bold,
        fontSize = 36.sp,
        lineHeight = 40.sp,
    ),
    headlineSmall = TextStyle(
        fontFamily = FontFamily.Serif,
        fontWeight = FontWeight.Bold,
        fontSize = 25.sp,
        lineHeight = 30.sp,
    ),
    titleLarge = TextStyle(
        fontFamily = FontFamily.Serif,
        fontWeight = FontWeight.Bold,
        fontSize = 21.sp,
    ),
    titleMedium = TextStyle(fontWeight = FontWeight.SemiBold, fontSize = 16.sp),
    bodyLarge = TextStyle(fontSize = 16.sp, lineHeight = 23.sp),
    bodyMedium = TextStyle(fontSize = 14.sp, lineHeight = 20.sp),
    labelLarge = TextStyle(fontWeight = FontWeight.Bold, fontSize = 14.sp),
)

@Composable
fun KnockKnockTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    MaterialTheme(
        colorScheme = if (darkTheme) DarkColors else LightColors,
        typography = KnockKnockTypography,
        content = content,
    )
}
