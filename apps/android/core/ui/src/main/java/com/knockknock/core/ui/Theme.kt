package com.knockknock.core.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

val Pine = Color(0xFF155C4B)
val PineLight = Color(0xFF438C76)
val Mint = Color(0xFFDDEFE5)
val Cream = Color(0xFFF5F6F1)
val Paper = Color(0xFFFFFFFF)
val Amber = Color(0xFFF1BD70)
val Ink = Color(0xFF19231F)
val MutedInk = Color(0xFF66716B)
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
    surfaceVariant = Color(0xFFEAF2EE),
    onSurfaceVariant = MutedInk,
    outline = Color(0xFFAAB8B0),
    outlineVariant = Color(0xFFDCE5DF),
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

private val DoorMemoTypography = androidx.compose.material3.Typography(
    displaySmall = TextStyle(
        fontFamily = FontFamily.Serif,
        fontWeight = FontWeight.Bold,
        fontSize = 36.sp,
        lineHeight = 40.sp,
    ),
    headlineSmall = TextStyle(fontWeight = FontWeight.SemiBold, fontSize = 26.sp, lineHeight = 31.sp),
    titleLarge = TextStyle(fontWeight = FontWeight.SemiBold, fontSize = 20.sp, lineHeight = 26.sp),
    titleMedium = TextStyle(fontWeight = FontWeight.SemiBold, fontSize = 16.sp),
    bodyLarge = TextStyle(fontSize = 16.sp, lineHeight = 23.sp),
    bodyMedium = TextStyle(fontSize = 14.sp, lineHeight = 20.sp),
    labelLarge = TextStyle(fontWeight = FontWeight.Bold, fontSize = 14.sp),
)

@Composable
fun DoorMemoTheme(
    // Keep the demo bright and readable even when the tablet is using dark mode.
    darkTheme: Boolean = false,
    content: @Composable () -> Unit,
) {
    MaterialTheme(
        colorScheme = if (darkTheme) DarkColors else LightColors,
        typography = DoorMemoTypography,
        content = content,
    )
}
