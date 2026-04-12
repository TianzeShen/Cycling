package com.cycling.cyclewise.ui.component.map

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.cycling.cyclewise.data.model.HeatmapReport
import com.cycling.cyclewise.data.model.RiskLevel
import com.cycling.cyclewise.ui.state.FeasibilityUiState
import com.cycling.cyclewise.ui.state.RoutingUiState

@Composable
fun MainMapBottomSheet(
    isHeatmapMode: Boolean,
    feasibilityState: FeasibilityUiState,
    routingState: RoutingUiState,
    heatmapReports: List<HeatmapReport>,
    selectedHeatmapRisk: RiskLevel?,
    onHeatmapRiskChange: (RiskLevel?) -> Unit,
    onViewRoute: () -> Unit,
    modifier: Modifier = Modifier
) {
    LazyColumn(
        modifier = modifier
            .fillMaxWidth()
            .background(MaterialTheme.colorScheme.surface),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            SheetHandle(
                title = if (isHeatmapMode) "Heatmap reports" else "Feasibility analysis",
                subtitle = if (isHeatmapMode) {
                    "Existing community reports near the current map area"
                } else {
                    "Enter a destination to assess your ride"
                }
            )
        }
        if (isHeatmapMode) {
            item {
                HeatmapReportPanel(
                    reports = heatmapReports,
                    selectedRisk = selectedHeatmapRisk,
                    onRiskChange = onHeatmapRiskChange
                )
            }
        } else {
            item {
                FeasibilityPanel(
                    feasibilityState = feasibilityState,
                    routingState = routingState,
                    onViewRoute = onViewRoute
                )
            }
        }
    }
}

@Composable
private fun SheetHandle(
    title: String,
    subtitle: String,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier.fillMaxWidth(),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth(0.14f)
                .background(
                    MaterialTheme.colorScheme.outlineVariant,
                    RoundedCornerShape(8.dp)
                )
                .padding(vertical = 2.dp)
        )
        Column(
            modifier = Modifier.fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(2.dp)
        ) {
            Text(
                text = title,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold
            )
            Text(
                text = subtitle,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}
