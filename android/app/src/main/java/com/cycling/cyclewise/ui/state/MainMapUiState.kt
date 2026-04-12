package com.cycling.cyclewise.ui.state

import com.cycling.cyclewise.data.model.FeasibilityResponse
import com.cycling.cyclewise.data.model.RouteAlert

sealed interface FeasibilityUiState {
    data object Empty : FeasibilityUiState
    data object Loading : FeasibilityUiState
    data class Success(val result: FeasibilityResponse) : FeasibilityUiState
    data class Error(val message: String) : FeasibilityUiState
}

sealed interface RoutingUiState {
    data object Empty : RoutingUiState
    data object Loading : RoutingUiState
    data class Success(val alerts: List<RouteAlert>) : RoutingUiState
    data class Error(val message: String) : RoutingUiState
}
