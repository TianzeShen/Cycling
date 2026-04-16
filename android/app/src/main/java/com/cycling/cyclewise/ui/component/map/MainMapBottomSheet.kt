package com.cycling.cyclewise.ui.component.map

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.cycling.cyclewise.data.model.HeatmapReport
import com.cycling.cyclewise.data.model.HeatmapRegion
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
    heatmapRegions: List<HeatmapRegion>,
    isHeatmapLoading: Boolean,
    heatmapStatusMessage: String?,
    selectedHeatmapRisk: RiskLevel?,
    onHeatmapRiskChange: (RiskLevel?) -> Unit,
    onClose: () -> Unit,
    onViewRoute: () -> Unit,
    onHideRoute: () -> Unit,
    modifier: Modifier = Modifier
) {
    LazyColumn(
        modifier = modifier
            .fillMaxWidth()
            .background(
                Brush.verticalGradient(
                    listOf(
                        Color.White.copy(alpha = 0.96f),
                        Color(0xFFEFF6FF).copy(alpha = 0.92f)
                    )
                )
            ),
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
                },
                onClose = onClose
            )
        }
        if (isHeatmapMode) {
            item {
                HeatmapReportPanel(
                    reports = heatmapReports,
                    regions = heatmapRegions,
                    isLoading = isHeatmapLoading,
                    statusMessage = heatmapStatusMessage,
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
    onClose: () -> Unit,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .shadow(12.dp, RoundedCornerShape(8.dp), ambientColor = Color(0x222563EB), spotColor = Color(0x332563EB))
            .background(
                Brush.linearGradient(
                    listOf(
                        Color.White.copy(alpha = 0.88f),
                        Color(0xFFDBEAFE).copy(alpha = 0.72f),
                        Color(0xFFE0F2FE).copy(alpha = 0.62f)
                    )
                ),
                RoundedCornerShape(8.dp)
            )
            .border(1.dp, Color.White.copy(alpha = 0.82f), RoundedCornerShape(8.dp))
            .padding(12.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(modifier = Modifier.weight(1f))
            Box(
                modifier = Modifier
                    .width(42.dp)
                    .background(
                        Brush.horizontalGradient(
                            listOf(Color(0xFF2563EB), Color(0xFF0EA5E9), Color(0xFF93C5FD))
                        ),
                        RoundedCornerShape(UiTokens.Radius)
                    )
                    .padding(vertical = 2.dp)
            )
            Box(
                modifier = Modifier.weight(1f),
                contentAlignment = Alignment.CenterEnd
            ) {
                IconButton(
                    onClick = onClose,
                    modifier = Modifier.size(32.dp)
                        .background(Color.White.copy(alpha = 0.72f), RoundedCornerShape(8.dp))
                        .border(1.dp, UiTokens.TechLine.copy(alpha = 0.66f), RoundedCornerShape(8.dp))
                ) {
                    Text(
                        text = "x",
                        style = MaterialTheme.typography.titleMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        fontWeight = FontWeight.Bold
                    )
                }
            }
        }
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
