package com.cycling.cyclewise.ui.navigation

import androidx.compose.foundation.background
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.unit.dp
import com.cycling.cyclewise.ui.screen.MainMapScreen
import com.cycling.cyclewise.ui.screen.ProfileScreen
import com.cycling.cyclewise.ui.screen.ReportIssueScreen

@Composable
fun CycleWiseApp() {
    var currentScreen by rememberSaveable { mutableStateOf(AppScreen.Map) }
    var isMapPanelVisible by rememberSaveable { mutableStateOf(false) }
    val navItems = listOf(
        AppScreen.Map,
        AppScreen.Report,
        AppScreen.Profile
    )

    Scaffold(
        bottomBar = {
            if (currentScreen != AppScreen.Map || !isMapPanelVisible) {
                NavigationBar(
                    containerColor = MaterialTheme.colorScheme.surface,
                    tonalElevation = 8.dp
                ) {
                    navItems.forEach { screen ->
                        NavigationBarItem(
                            selected = currentScreen == screen,
                            onClick = {
                                currentScreen = screen
                                if (screen != AppScreen.Map) {
                                    isMapPanelVisible = false
                                }
                            },
                            label = { Text(screen.navLabel) },
                            icon = {
                                NavGlyph(
                                    screen = screen,
                                    selected = currentScreen == screen
                                )
                            },
                            colors = NavigationBarItemDefaults.colors(
                                selectedIconColor = MaterialTheme.colorScheme.onPrimary,
                                selectedTextColor = MaterialTheme.colorScheme.primary,
                                indicatorColor = MaterialTheme.colorScheme.primaryContainer,
                                unselectedIconColor = MaterialTheme.colorScheme.onSurfaceVariant,
                                unselectedTextColor = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        )
                    }
                }
            }
        }
    ) { innerPadding ->
        when (currentScreen) {
            AppScreen.Map -> MainMapScreen(
                modifier = Modifier.padding(innerPadding),
                onBottomPanelVisibilityChange = { isMapPanelVisible = it }
            )

            AppScreen.Report -> ReportIssueScreen(
                modifier = Modifier.padding(innerPadding)
            )

            AppScreen.Profile -> ProfileScreen(
                modifier = Modifier.padding(innerPadding)
            )
        }
    }
}

@Composable
private fun NavGlyph(
    screen: AppScreen,
    selected: Boolean,
    modifier: Modifier = Modifier
) {
    val iconColor = if (selected) {
        MaterialTheme.colorScheme.onPrimary
    } else {
        MaterialTheme.colorScheme.onSurfaceVariant
    }

    Box(
        modifier = modifier
            .size(30.dp)
            .background(
                if (selected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.surfaceContainer,
                RoundedCornerShape(8.dp)
            ),
        contentAlignment = Alignment.Center
    ) {
        Canvas(modifier = Modifier.size(18.dp)) {
            when (screen) {
                AppScreen.Map -> drawMapPinIcon(iconColor)
                AppScreen.Report -> drawReportIcon(iconColor)
                AppScreen.Profile -> drawProfileIcon(iconColor)
            }
        }
    }
}

private fun androidx.compose.ui.graphics.drawscope.DrawScope.drawMapPinIcon(color: Color) {
    val w = size.width
    val h = size.height
    val path = Path().apply {
        moveTo(w * 0.50f, h * 0.95f)
        cubicTo(w * 0.18f, h * 0.58f, w * 0.18f, h * 0.34f, w * 0.34f, h * 0.18f)
        cubicTo(w * 0.43f, h * 0.08f, w * 0.57f, h * 0.08f, w * 0.66f, h * 0.18f)
        cubicTo(w * 0.82f, h * 0.34f, w * 0.82f, h * 0.58f, w * 0.50f, h * 0.95f)
        close()
    }
    drawPath(path, color)
    drawCircle(Color.White.copy(alpha = 0.95f), radius = w * 0.16f, center = Offset(w * 0.50f, h * 0.39f))
}

private fun androidx.compose.ui.graphics.drawscope.DrawScope.drawReportIcon(color: Color) {
    val w = size.width
    val h = size.height
    val triangle = Path().apply {
        moveTo(w * 0.50f, h * 0.08f)
        lineTo(w * 0.92f, h * 0.84f)
        lineTo(w * 0.08f, h * 0.84f)
        close()
    }
    drawPath(triangle, color)
    drawLine(
        color = Color.White.copy(alpha = 0.95f),
        start = Offset(w * 0.50f, h * 0.34f),
        end = Offset(w * 0.50f, h * 0.58f),
        strokeWidth = w * 0.10f
    )
    drawCircle(Color.White.copy(alpha = 0.95f), radius = w * 0.055f, center = Offset(w * 0.50f, h * 0.69f))
}

private fun androidx.compose.ui.graphics.drawscope.DrawScope.drawProfileIcon(color: Color) {
    val w = size.width
    val h = size.height
    drawCircle(color, radius = w * 0.22f, center = Offset(w * 0.50f, h * 0.30f))
    val shoulders = Path().apply {
        moveTo(w * 0.18f, h * 0.92f)
        cubicTo(w * 0.20f, h * 0.68f, w * 0.34f, h * 0.56f, w * 0.50f, h * 0.56f)
        cubicTo(w * 0.66f, h * 0.56f, w * 0.80f, h * 0.68f, w * 0.82f, h * 0.92f)
        close()
    }
    drawPath(shoulders, color)
}
