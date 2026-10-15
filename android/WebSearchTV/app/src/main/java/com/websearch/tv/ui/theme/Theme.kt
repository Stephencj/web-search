package com.websearch.tv.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val DarkColorScheme = darkColorScheme(
    primary = Color(0xFF0A84FF),
    secondary = Color(0xFF30D158),
    tertiary = Color(0xFFFF9F0A),
    background = Color(0xFF000000),
    surface = Color(0xFF1C1C1E),
    surfaceVariant = Color(0xFF2C2C2E),
    onPrimary = Color.White,
    onSecondary = Color.White,
    onTertiary = Color.Black,
    onBackground = Color.White,
    onSurface = Color.White,
    onSurfaceVariant = Color(0xFFAEAEB2),
    error = Color(0xFFFF453A),
    onError = Color.White
)

object AppColors {
    val youtube = Color(0xFFFF0000)
    val rumble = Color(0xFF85C742)
    val odysee = Color(0xFFE50054)
    val podcast = Color(0xFF8E44AD)
    val redbar = Color(0xFFFF6B35)

    fun platformColor(platform: String): Color = when (platform.lowercase()) {
        "youtube" -> youtube
        "rumble" -> rumble
        "odysee" -> odysee
        "podcast" -> podcast
        "redbar" -> redbar
        else -> Color(0xFF0A84FF)
    }
}

@Composable
fun WebSearchTVTheme(
    content: @Composable () -> Unit
) {
    MaterialTheme(
        colorScheme = DarkColorScheme,
        typography = Typography,
        content = content
    )
}
