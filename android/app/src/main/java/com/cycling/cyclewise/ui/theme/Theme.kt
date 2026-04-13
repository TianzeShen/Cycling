package com.cycling.cyclewise.ui.theme

import android.app.Activity
import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext

private val DarkColorScheme = darkColorScheme(
    primary = Green80,
    secondary = Teal80,
    tertiary = Red80
)

private val LightColorScheme = lightColorScheme(
    primary = Green40,
    secondary = Teal40,
    tertiary = Red40,
    background = AppBackground,
    surface = AppSurface,
    surfaceContainer = AppSurfaceContainer,
    surfaceContainerHigh = AppSurfaceContainer,
    primaryContainer = Color(0xFFDBEAFE),
    secondaryContainer = Color(0xFFE0F2FE),
    tertiaryContainer = Color(0xFFFFDAD5),
    outlineVariant = AppOutline,
    onPrimary = AppSurface,
    onSecondary = AppSurface,
    onTertiary = AppSurface,
    onBackground = AppText,
    onSurface = AppText
)

@Composable
fun CycleWiseTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    // Dynamic color is available on Android 12+
    dynamicColor: Boolean = false,
    content: @Composable () -> Unit
) {
    val colorScheme = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val context = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        }

        darkTheme -> DarkColorScheme
        else -> LightColorScheme
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = Typography,
        content = content
    )
}
