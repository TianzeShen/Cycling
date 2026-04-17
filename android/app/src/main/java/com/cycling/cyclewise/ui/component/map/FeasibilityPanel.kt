package com.cycling.cyclewise.ui.component.map

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.cycling.cyclewise.data.model.FeasibilityResponse
import com.cycling.cyclewise.ui.component.InfoItem
import com.cycling.cyclewise.ui.component.ScoreSummary
import com.cycling.cyclewise.ui.state.FeasibilityUiState
import com.cycling.cyclewise.ui.state.RoutingUiState

@Composable
fun FeasibilityPanel(
    feasibilityState: FeasibilityUiState,
    routingState: RoutingUiState,
    isRouteVisible: Boolean,
    onViewRoute: () -> Unit,
    onHideRoute: () -> Unit,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier,
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        when (feasibilityState) {
            FeasibilityUiState.Empty -> InfoItem(
                title = "Ready to assess",
                body = "Select a start point and destination, then tap Evaluate."
            )

            FeasibilityUiState.Loading -> {
                CircularProgressIndicator()
                Text("Evaluating trip...", style = MaterialTheme.typography.bodyMedium)
            }

            is FeasibilityUiState.Error -> RiskInfoItem(
                title = "Unable to evaluate trip",
                body = feasibilityState.message,
                risk = "High"
            )

            is FeasibilityUiState.Success -> FeasibilitySuccessPanel(
                result = feasibilityState.result,
                routingState = routingState,
                isRouteVisible = isRouteVisible,
                onViewRoute = onViewRoute,
                onHideRoute = onHideRoute
            )
        }
    }
}

@Composable
private fun FeasibilitySuccessPanel(
    result: FeasibilityResponse,
    routingState: RoutingUiState,
    isRouteVisible: Boolean,
    onViewRoute: () -> Unit,
    onHideRoute: () -> Unit
) {
    val label = when {
        result.score >= 75 -> "High feasibility"
        result.score >= 50 -> "Moderate feasibility"
        else -> "Low feasibility"
    }

    ScoreSummary(score = result.score, label = label)
    InfoItem(
        title = "Supported area",
        body = if (result.isSupportedArea) {
            "This journey is inside the supported service area."
        } else {
            "This journey is outside the supported service area."
        }
    )
    if (result.warningMessage != null) {
        RiskInfoItem(title = "Warning", body = result.warningMessage, risk = "High")
    }
    if (result.explanations.isEmpty()) {
        InfoItem(
            title = "Why this score?",
            body = "No detailed explanation was returned. The backend result is still shown above."
        )
    } else {
        result.explanations.forEach { explanation ->
            RiskInfoItem(
                title = explanation.factor,
                body = "Impact: ${explanation.impact}",
                risk = explanation.impact
            )
        }
    }
    when {
        routingState == RoutingUiState.Loading -> Text(
            "Generating risk route...",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        isRouteVisible -> Button(onClick = onHideRoute) {
            Text("Hide risk route")
        }
    }
    when (routingState) {
        is RoutingUiState.Error -> RiskInfoItem(
            title = "Unable to load route",
            body = routingState.message,
            risk = "High"
        )

        is RoutingUiState.Success -> {
            if (routingState.alerts.isEmpty()) {
                InfoItem(title = "Route alerts", body = "No alerts returned for this route.")
            } else {
                routingState.alerts.forEach { alert ->
                    RiskInfoItem(title = "Route alert", body = alert.message, risk = "High")
                }
            }
        }

        else -> Unit
    }
}

@Composable
private fun RiskInfoItem(
    title: String,
    body: String,
    risk: String,
    modifier: Modifier = Modifier
) {
    val color = risk.toRiskColor()
    Column(
        modifier = modifier
            .fillMaxWidth()
            .background(color.copy(alpha = 0.12f), RoundedCornerShape(8.dp))
            .border(1.dp, color.copy(alpha = 0.34f), RoundedCornerShape(8.dp))
            .padding(14.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        Text(
            title,
            style = MaterialTheme.typography.titleSmall,
            color = color,
            fontWeight = FontWeight.ExtraBold
        )
        Text(
            body,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}

private fun String.toRiskColor(): Color {
    return when (lowercase()) {
        "high", "red" -> Color(0xFFEF4444)
        "medium", "yellow", "moderate" -> Color(0xFFF59E0B)
        "low", "green" -> Color(0xFF16A34A)
        else -> Color(0xFF2563EB)
    }
}
