package com.cycling.cyclewise.ui.component.map

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
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
    onViewRoute: () -> Unit,
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

            is FeasibilityUiState.Error -> InfoItem(
                title = "Unable to evaluate trip",
                body = feasibilityState.message
            )

            is FeasibilityUiState.Success -> FeasibilitySuccessPanel(
                result = feasibilityState.result,
                routingState = routingState,
                onViewRoute = onViewRoute
            )
        }
    }
}

@Composable
private fun FeasibilitySuccessPanel(
    result: FeasibilityResponse,
    routingState: RoutingUiState,
    onViewRoute: () -> Unit
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
        InfoItem(title = "Warning", body = result.warningMessage)
    }
    if (result.explanations.isEmpty()) {
        InfoItem(
            title = "Why this score?",
            body = "No detailed explanation was returned. The backend result is still shown above."
        )
    } else {
        result.explanations.forEach { explanation ->
            InfoItem(
                title = explanation.factor,
                body = "Impact: ${explanation.impact}"
            )
        }
    }
    Button(onClick = onViewRoute) {
        Text(
            when (routingState) {
                RoutingUiState.Loading -> "Loading route..."
                is RoutingUiState.Success -> "Refresh route"
                else -> "View risk route"
            }
        )
    }
    when (routingState) {
        is RoutingUiState.Error -> InfoItem(
            title = "Unable to load route",
            body = routingState.message
        )

        is RoutingUiState.Success -> {
            if (routingState.alerts.isEmpty()) {
                InfoItem(title = "Route alerts", body = "No alerts returned for this route.")
            } else {
                routingState.alerts.forEach { alert ->
                    InfoItem(title = "Route alert", body = alert.message)
                }
            }
        }

        else -> Unit
    }
}
