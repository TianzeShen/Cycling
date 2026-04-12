package com.cycling.cyclewise.ui.navigation

import androidx.compose.foundation.layout.padding
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import com.cycling.cyclewise.ui.screen.MainMapScreen
import com.cycling.cyclewise.ui.screen.ProfileScreen
import com.cycling.cyclewise.ui.screen.ReportIssueScreen

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CycleWiseApp() {
    var currentScreen by rememberSaveable { mutableStateOf(AppScreen.Map) }
    val navItems = listOf(
        AppScreen.Map,
        AppScreen.Report,
        AppScreen.Profile
    )

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(currentScreen.title) }
            )
        },
        bottomBar = {
            NavigationBar {
                navItems.forEach { screen ->
                    NavigationBarItem(
                        selected = currentScreen == screen,
                        onClick = { currentScreen = screen },
                        label = { Text(screen.navLabel) },
                        icon = { Text(screen.navLabel.take(1)) }
                    )
                }
            }
        }
    ) { innerPadding ->
        when (currentScreen) {
            AppScreen.Map -> MainMapScreen(
                modifier = Modifier.padding(innerPadding)
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
