package com.cycling.cyclewise.ui.screen

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.cycling.cyclewise.ui.component.InfoItem
import com.cycling.cyclewise.ui.component.ScoreSummary
import com.cycling.cyclewise.ui.component.StatusPill

@Composable
fun MainMapScreen(
    modifier: Modifier = Modifier
) {
    var isHeatmapMode by rememberSaveable { mutableStateOf(false) }

    Box(
        modifier = modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.surface)
    ) {
        StaticMapSurface(
            isHeatmapMode = isHeatmapMode,
            modifier = Modifier.fillMaxSize()
        )

        LocationSearchOverlay(
            modifier = Modifier
                .align(Alignment.TopCenter)
                .padding(16.dp)
        )

        FilledTonalButton(
            onClick = { isHeatmapMode = !isHeatmapMode },
            modifier = Modifier
                .align(Alignment.CenterEnd)
                .padding(end = 16.dp)
        ) {
            Text(if (isHeatmapMode) "Route" else "Heatmap")
        }

        MainBottomSheet(
            isHeatmapMode = isHeatmapMode,
            modifier = Modifier.align(Alignment.BottomCenter)
        )
    }
}

@Composable
private fun StaticMapSurface(
    isHeatmapMode: Boolean,
    modifier: Modifier = Modifier
) {
    Box(
        modifier = modifier
            .background(if (isHeatmapMode) Color(0xFFEAF1EC) else Color(0xFFEAF3F2))
            .padding(20.dp)
    ) {
        Column(
            modifier = Modifier.align(Alignment.Center),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Text(
                text = if (isHeatmapMode) "Heatmap layer" else "Map component",
                style = MaterialTheme.typography.headlineMedium,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onSurface
            )
            Text(
                text = if (isHeatmapMode) {
                    "Community reports and risk intensity will be rendered here."
                } else {
                    "Start, destination, route segments, and alerts will be rendered here."
                },
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                StatusPill("Start", Color(0xFF006A67))
                StatusPill("Destination", Color(0xFF2F6F3E))
                StatusPill("Gap", Color(0xFFC62828))
            }
        }

        if (isHeatmapMode) {
            HeatSpot(
                label = "12 reports",
                color = Color(0xFFC62828),
                modifier = Modifier
                    .align(Alignment.CenterStart)
                    .padding(start = 18.dp)
            )
            HeatSpot(
                label = "5 reports",
                color = Color(0xFF9A6A00),
                modifier = Modifier
                    .align(Alignment.TopEnd)
                    .padding(top = 190.dp, end = 34.dp)
            )
        }
    }
}

@Composable
private fun HeatSpot(
    label: String,
    color: Color,
    modifier: Modifier = Modifier
) {
    Text(
        text = label,
        modifier = modifier
            .background(color.copy(alpha = 0.22f), RoundedCornerShape(8.dp))
            .border(1.dp, color, RoundedCornerShape(8.dp))
            .padding(horizontal = 12.dp, vertical = 8.dp),
        color = color,
        style = MaterialTheme.typography.labelLarge,
        fontWeight = FontWeight.SemiBold
    )
}

@Composable
private fun LocationSearchOverlay(
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(8.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 6.dp)
    ) {
        Column(
            modifier = Modifier.padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Text(
                text = "Where are you riding?",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold
            )
            OutlinedTextField(
                value = "-37.8136, 144.9631",
                onValueChange = {},
                modifier = Modifier.fillMaxWidth(),
                label = { Text("Start point") },
                readOnly = true,
                singleLine = true
            )
            OutlinedTextField(
                value = "-37.8200, 144.9700",
                onValueChange = {},
                modifier = Modifier.fillMaxWidth(),
                label = { Text("Destination") },
                readOnly = true,
                singleLine = true
            )
            Button(
                modifier = Modifier.fillMaxWidth(),
                onClick = {}
            ) {
                Text("Evaluate trip")
            }
        }
    }
}

@Composable
private fun MainBottomSheet(
    isHeatmapMode: Boolean,
    modifier: Modifier = Modifier
) {
    Surface(
        modifier = modifier
            .fillMaxWidth()
            .height(330.dp),
        shape = RoundedCornerShape(topStart = 8.dp, topEnd = 8.dp),
        tonalElevation = 8.dp,
        shadowElevation = 8.dp,
        color = MaterialTheme.colorScheme.surface
    ) {
        Column(
            modifier = Modifier.padding(top = 10.dp)
        ) {
            Box(
                modifier = Modifier
                    .align(Alignment.CenterHorizontally)
                    .fillMaxWidth(0.14f)
                    .height(4.dp)
                    .background(
                        MaterialTheme.colorScheme.outlineVariant,
                        RoundedCornerShape(8.dp)
                    )
            )
            LazyColumn(
                contentPadding = PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                if (isHeatmapMode) {
                    item { HeatmapReportPanel() }
                } else {
                    item { FeasibilityPanel() }
                }
            }
        }
    }
}

@Composable
private fun FeasibilityPanel() {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(
            text = "Feasibility analysis",
            style = MaterialTheme.typography.titleLarge,
            fontWeight = FontWeight.Bold
        )
        ScoreSummary(score = 85, label = "High feasibility")
        InfoItem(
            title = "Supported area",
            body = "This sample journey is inside the Melbourne service area."
        )
        InfoItem(
            title = "Why this score?",
            body = "High lane continuity and low traffic exposure make this route practical for cycling."
        )
        InfoItem(
            title = "Warning",
            body = "No warning for this sample trip. Low scores will display safety guidance here."
        )
    }
}

@Composable
private fun HeatmapReportPanel() {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(
            text = "Heatmap reports",
            style = MaterialTheme.typography.titleLarge,
            fontWeight = FontWeight.Bold
        )
        InfoItem(
            title = "Disconnected bike lane",
            body = "12 reports near La Trobe Street. Status: validated."
        )
        InfoItem(
            title = "Unsafe transition",
            body = "5 reports near Swanston Street. Status: pending review."
        )
        InfoItem(
            title = "Missing protected lane",
            body = "3 reports near Elizabeth Street. Status: pending validation."
        )
    }
}
