package com.cycling.cyclewise.ui.screen

import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import com.cycling.cyclewise.ui.component.InfoItem
import com.cycling.cyclewise.ui.component.MapPlaceholder
import com.cycling.cyclewise.ui.component.PageIntro
import com.cycling.cyclewise.ui.component.ReadOnlyField
import com.cycling.cyclewise.ui.component.StaticScreen

@Composable
fun ReportIssueScreen(
    modifier: Modifier = Modifier
) {
    StaticScreen(modifier = modifier) {
        item {
            PageIntro(
                title = "Report issue",
                body = "One-tap reporting will capture GPS, time, route context, and an issue type suggestion."
            )
        }
        item {
            MapPlaceholder(
                title = "Issue location",
                subtitle = "Future GPS marker and manual location confirmation"
            )
        }
        item {
            ReadOnlyField(label = "Suggested issue type", value = "Disconnected bike lane")
        }
        item {
            ReadOnlyField(label = "Location", value = "-37.8155, 144.9655")
        }
        item {
            InfoItem(
                title = "Offline state",
                body = "If the user is offline, the report will be saved locally and synced later."
            )
        }
        item {
            Button(
                modifier = Modifier.fillMaxWidth(),
                onClick = {}
            ) {
                Text("Create report")
            }
        }
    }
}
