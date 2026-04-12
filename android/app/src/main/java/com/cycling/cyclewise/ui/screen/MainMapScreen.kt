package com.cycling.cyclewise.ui.screen

import android.Manifest
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.BottomSheetScaffold
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Text
import androidx.compose.material3.rememberBottomSheetScaffoldState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.cycling.cyclewise.data.api.CyclingApiClient
import com.cycling.cyclewise.data.api.GeocodingClient
import com.cycling.cyclewise.data.mock.MockCyclingData
import com.cycling.cyclewise.data.model.FeasibilityRequest
import com.cycling.cyclewise.data.model.PlaceCandidate
import com.cycling.cyclewise.data.model.RiskLevel
import com.cycling.cyclewise.data.model.RouteAlert
import com.cycling.cyclewise.data.model.RouteSegment
import com.cycling.cyclewise.location.hasLocationPermission
import com.cycling.cyclewise.location.requestCurrentLocation
import com.cycling.cyclewise.ui.component.OpenStreetMapView
import com.cycling.cyclewise.ui.component.map.LocationSearchOverlay
import com.cycling.cyclewise.ui.component.map.MainMapBottomSheet
import com.cycling.cyclewise.ui.state.FeasibilityUiState
import com.cycling.cyclewise.ui.state.RoutingUiState
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import org.osmdroid.util.GeoPoint

private val MelbourneCenter = GeoPoint(-37.8136, 144.9631)
private val MonashClaytonCenter = GeoPoint(-37.9110, 145.1340)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainMapScreen(
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val scaffoldState = rememberBottomSheetScaffoldState()
    val coroutineScope = rememberCoroutineScope()
    var isHeatmapMode by rememberSaveable { mutableStateOf(false) }
    var selectedHeatmapRisk by rememberSaveable { mutableStateOf<RiskLevel?>(null) }
    var startPoint by rememberSaveable { mutableStateOf("") }
    var destination by rememberSaveable { mutableStateOf("") }
    var userLocation by remember { mutableStateOf<GeoPoint?>(null) }
    var selectedStart by remember { mutableStateOf<PlaceCandidate?>(null) }
    var selectedDestination by remember { mutableStateOf<PlaceCandidate?>(null) }
    var startSuggestions by remember { mutableStateOf(emptyList<PlaceCandidate>()) }
    var destinationSuggestions by remember { mutableStateOf(emptyList<PlaceCandidate>()) }
    var feasibilityState by remember { mutableStateOf<FeasibilityUiState>(FeasibilityUiState.Empty) }
    var routingState by remember { mutableStateOf<RoutingUiState>(RoutingUiState.Empty) }
    var routeSegments by remember { mutableStateOf(emptyList<RouteSegment>()) }
    var routeAlerts by remember { mutableStateOf(emptyList<RouteAlert>()) }
    var lastRequest by remember { mutableStateOf<FeasibilityRequest?>(null) }
    var locationStatus by rememberSaveable { mutableStateOf("Current location") }
    val filteredHeatmapReports = remember(selectedHeatmapRisk) {
        MockCyclingData.heatmapReports.filter { report ->
            selectedHeatmapRisk == null || report.riskLevel == selectedHeatmapRisk
        }
    }

    fun updateUserLocation(location: GeoPoint?) {
        if (location != null) {
            userLocation = location
            locationStatus = "Current location found"
        } else {
            locationStatus = "Location unavailable"
        }
    }

    val locationPermissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val granted = permissions[Manifest.permission.ACCESS_FINE_LOCATION] == true ||
            permissions[Manifest.permission.ACCESS_COARSE_LOCATION] == true
        if (granted) {
            requestCurrentLocation(context, ::updateUserLocation)
        } else {
            locationStatus = "Location permission needed"
        }
    }

    LaunchedEffect(Unit) {
        if (hasLocationPermission(context)) {
            requestCurrentLocation(context, ::updateUserLocation)
        } else {
            locationPermissionLauncher.launch(
                arrayOf(
                    Manifest.permission.ACCESS_FINE_LOCATION,
                    Manifest.permission.ACCESS_COARSE_LOCATION
                )
            )
        }
    }

    LaunchedEffect(startPoint) {
        selectedStart = selectedStart?.takeIf { it.displayName == startPoint }
        if (startPoint.length >= 3 && selectedStart == null) {
            delay(500)
            runCatching { GeocodingClient.searchPlaces(startPoint) }
                .onSuccess { startSuggestions = it }
                .onFailure { startSuggestions = emptyList() }
        } else {
            startSuggestions = emptyList()
        }
    }

    LaunchedEffect(destination) {
        selectedDestination = selectedDestination?.takeIf { it.displayName == destination }
        if (destination.length >= 3 && selectedDestination == null) {
            delay(500)
            runCatching { GeocodingClient.searchPlaces(destination) }
                .onSuccess { destinationSuggestions = it }
                .onFailure { destinationSuggestions = emptyList() }
        } else {
            destinationSuggestions = emptyList()
        }
    }

    BottomSheetScaffold(
        modifier = modifier.fillMaxSize(),
        scaffoldState = scaffoldState,
        sheetPeekHeight = 72.dp,
        sheetShape = RoundedCornerShape(topStart = 8.dp, topEnd = 8.dp),
        sheetDragHandle = null,
        sheetContent = {
            MainMapBottomSheet(
                isHeatmapMode = isHeatmapMode,
                feasibilityState = feasibilityState,
                routingState = routingState,
                heatmapReports = filteredHeatmapReports,
                selectedHeatmapRisk = selectedHeatmapRisk,
                onHeatmapRiskChange = { selectedHeatmapRisk = it },
                onViewRoute = {
                    val request = lastRequest ?: return@MainMapBottomSheet
                    coroutineScope.launch {
                        routingState = RoutingUiState.Loading
                        runCatching { CyclingApiClient.recommendRoute(request) }
                            .onSuccess { response ->
                                routeSegments = response.routeSegments
                                routeAlerts = response.alerts
                                routingState = RoutingUiState.Success(response.alerts)
                            }
                            .onFailure { error ->
                                routingState = RoutingUiState.Error(
                                    error.message ?: "Route recommendation failed."
                                )
                            }
                    }
                }
            )
        }
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .padding(innerPadding)
                .fillMaxSize()
        ) {
            OpenStreetMapView(
                center = if (isHeatmapMode) {
                    MonashClaytonCenter
                } else {
                    selectedDestination?.toGeoPoint()
                        ?: selectedStart?.toGeoPoint()
                        ?: userLocation
                        ?: MelbourneCenter
                },
                userLocation = userLocation,
                startLocation = selectedStart?.toGeoPoint() ?: userLocation,
                destinationLocation = selectedDestination?.toGeoPoint(),
                routeSegments = routeSegments,
                routeAlerts = routeAlerts,
                heatmapReports = filteredHeatmapReports,
                isHeatmapMode = isHeatmapMode,
                modifier = Modifier.fillMaxSize()
            )

            LocationSearchOverlay(
                startPoint = startPoint,
                onStartPointChange = {
                    startPoint = it
                    selectedStart = null
                },
                startSuggestions = startSuggestions,
                onStartSuggestionClick = { place ->
                    selectedStart = place
                    startPoint = place.displayName
                    startSuggestions = emptyList()
                },
                destination = destination,
                onDestinationChange = {
                    destination = it
                    selectedDestination = null
                },
                destinationSuggestions = destinationSuggestions,
                onDestinationSuggestionClick = { place ->
                    selectedDestination = place
                    destination = place.displayName
                    destinationSuggestions = emptyList()
                },
                locationStatus = locationStatus,
                onUseCurrentLocation = {
                    if (hasLocationPermission(context)) {
                        requestCurrentLocation(context, ::updateUserLocation)
                        startPoint = ""
                        selectedStart = null
                    } else {
                        locationPermissionLauncher.launch(
                            arrayOf(
                                Manifest.permission.ACCESS_FINE_LOCATION,
                                Manifest.permission.ACCESS_COARSE_LOCATION
                            )
                        )
                    }
                },
                onEvaluate = {
                    coroutineScope.launch {
                        feasibilityState = FeasibilityUiState.Loading
                        routingState = RoutingUiState.Empty
                        routeSegments = emptyList()
                        routeAlerts = emptyList()
                        val request = runCatching {
                            buildFeasibilityRequest(
                                startPoint = startPoint,
                                selectedStart = selectedStart,
                                userLocation = userLocation,
                                destination = destination,
                                selectedDestination = selectedDestination
                            )
                        }.getOrElse { error ->
                            feasibilityState = FeasibilityUiState.Error(
                                error.message ?: "Select a valid start and destination."
                            )
                            return@launch
                        }
                        lastRequest = request
                        runCatching { CyclingApiClient.evaluateFeasibility(request) }
                            .onSuccess { result ->
                                feasibilityState = FeasibilityUiState.Success(result)
                                scaffoldState.bottomSheetState.expand()
                            }
                            .onFailure { error ->
                                feasibilityState = FeasibilityUiState.Error(
                                    error.message ?: "Feasibility request failed."
                                )
                                scaffoldState.bottomSheetState.expand()
                            }
                    }
                },
                isEvaluating = feasibilityState == FeasibilityUiState.Loading,
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
        }
    }
}

private suspend fun buildFeasibilityRequest(
    startPoint: String,
    selectedStart: PlaceCandidate?,
    userLocation: GeoPoint?,
    destination: String,
    selectedDestination: PlaceCandidate?
): FeasibilityRequest {
    val start = if (startPoint.isBlank()) {
        userLocation?.let {
            PlaceCandidate(
                name = "Current location",
                displayName = "Current location",
                lat = it.latitude,
                lng = it.longitude
            )
        }
    } else {
        selectedStart
            ?: parseCoordinateInput(startPoint)
            ?: resolveFirstPlace(startPoint)
    } ?: throw IllegalArgumentException("Select a start point or use current location.")

    val end = selectedDestination
        ?: parseCoordinateInput(destination)
        ?: resolveFirstPlace(destination)
        ?: throw IllegalArgumentException("Select a destination from search results.")

    return FeasibilityRequest(
        startLat = start.lat,
        startLng = start.lng,
        endLat = end.lat,
        endLng = end.lng
    )
}

private suspend fun resolveFirstPlace(query: String): PlaceCandidate? {
    if (query.length < 3) return null
    return runCatching { GeocodingClient.searchPlaces(query).firstOrNull() }.getOrNull()
}

private fun parseCoordinateInput(input: String): PlaceCandidate? {
    val parts = input.split(",").map { it.trim() }
    if (parts.size != 2) return null
    val lat = parts[0].toDoubleOrNull() ?: return null
    val lng = parts[1].toDoubleOrNull() ?: return null
    if (lat !in -90.0..90.0 || lng !in -180.0..180.0) return null
    return PlaceCandidate(
        name = "Coordinate",
        displayName = "$lat, $lng",
        lat = lat,
        lng = lng
    )
}

private fun PlaceCandidate.toGeoPoint(): GeoPoint = GeoPoint(lat, lng)
