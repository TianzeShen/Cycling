package com.cycling.cyclewise.ui.component.map

import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import com.cycling.cyclewise.ui.theme.UiTokens

@Composable
fun MainMapBottomSheet(
    isHeatmapMode: Boolean,
    feasibilityState: FeasibilityUiState,
    routingState: RoutingUiState,
    isRouteVisible: Boolean,
    heatmapReports: List<HeatmapReport>,
    selectedHeatmapRisk: RiskLevel?,
    onHeatmapRiskChange: (RiskLevel?) -> Unit,
    onViewRoute: () -> Unit,
    onHideRoute: () -> Unit,
    modifier: Modifier = Modifier
) {
    LazyColumn(
        modifier = modifier
            .fillMaxWidth()
            .background(MaterialTheme.colorScheme.surface),
        contentPadding = PaddingValues(horizontal = 18.dp, vertical = 14.dp),
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
                    isRouteVisible = isRouteVisible,
                    onViewRoute = onViewRoute,
                    onHideRoute = onHideRoute
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
        modifier = modifier
            .fillMaxWidth()
            .background(MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.42f), RoundedCornerShape(UiTokens.Radius))
            .border(1.dp, UiTokens.TechLine.copy(alpha = 0.65f), RoundedCornerShape(UiTokens.Radius))
            .padding(12.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth(0.14f)
                .background(
                    UiTokens.BrandGlow.copy(alpha = 0.56f),
                    RoundedCornerShape(UiTokens.Radius)
                )
                .padding(vertical = 2.dp)
        )
        Column(
            modifier = Modifier.fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(2.dp)
        ) {
            Text(
                text = if (title.contains("Heatmap")) "SAFETY LAYER" else "TRIP INTELLIGENCE",
                color = MaterialTheme.colorScheme.primary,
                style = MaterialTheme.typography.labelSmall,
                fontWeight = FontWeight.ExtraBold
            )
            Text(
                text = title,
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.ExtraBold
            )
            Text(
                text = subtitle,
                style = MaterialTheme.typography.bodyMedium,
                color = UiTokens.InkMuted
            )
        }
    }
}
