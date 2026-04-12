package com.cycling.cyclewise.ui.screen

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Bundle
import android.os.Looper
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.BottomSheetScaffold
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.rememberBottomSheetScaffoldState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import com.cycling.cyclewise.ui.component.InfoItem
import com.cycling.cyclewise.ui.component.OpenStreetMapView
import com.cycling.cyclewise.ui.component.ScoreSummary
import com.cycling.cyclewise.ui.component.StatusPill
import org.osmdroid.util.GeoPoint

private val MelbourneCenter = GeoPoint(-37.8136, 144.9631)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainMapScreen(
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val scaffoldState = rememberBottomSheetScaffoldState()
    var isHeatmapMode by rememberSaveable { mutableStateOf(false) }
    var startPoint by rememberSaveable { mutableStateOf("") }
    var destination by rememberSaveable { mutableStateOf("") }
    var userLocation by remember { mutableStateOf<GeoPoint?>(null) }
    var locationStatus by rememberSaveable { mutableStateOf("Current location") }
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

    BottomSheetScaffold(
        modifier = modifier.fillMaxSize(),
        scaffoldState = scaffoldState,
        sheetPeekHeight = 72.dp,
        sheetShape = RoundedCornerShape(topStart = 8.dp, topEnd = 8.dp),
        sheetDragHandle = null,
        sheetContent = {
            BottomSheetContent(isHeatmapMode = isHeatmapMode)
        }
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .padding(innerPadding)
                .fillMaxSize()
        ) {
            OpenStreetMapView(
                center = userLocation ?: MelbourneCenter,
                userLocation = userLocation,
                isHeatmapMode = isHeatmapMode,
                modifier = Modifier.fillMaxSize()
            )

            LocationSearchOverlay(
                startPoint = startPoint,
                onStartPointChange = { startPoint = it },
                destination = destination,
                onDestinationChange = { destination = it },
                locationStatus = locationStatus,
                onUseCurrentLocation = {
                    if (hasLocationPermission(context)) {
                        requestCurrentLocation(context, ::updateUserLocation)
                        startPoint = ""
                    } else {
                        locationPermissionLauncher.launch(
                            arrayOf(
                                Manifest.permission.ACCESS_FINE_LOCATION,
                                Manifest.permission.ACCESS_COARSE_LOCATION
                            )
                        )
                    }
                },
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

@Composable
private fun LocationSearchOverlay(
    startPoint: String,
    onStartPointChange: (String) -> Unit,
    destination: String,
    onDestinationChange: (String) -> Unit,
    locationStatus: String,
    onUseCurrentLocation: () -> Unit,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(8.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 6.dp)
    ) {
        Column(
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 10.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            OutlinedTextField(
                value = startPoint,
                onValueChange = onStartPointChange,
                modifier = Modifier.fillMaxWidth(),
                label = { Text("Start point") },
                placeholder = { Text("Current location or search start") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Next)
            )
            OutlinedTextField(
                value = destination,
                onValueChange = onDestinationChange,
                modifier = Modifier.fillMaxWidth(),
                label = { Text("Destination") },
                placeholder = { Text("Search a place") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Done)
            )
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                FilledTonalButton(
                    modifier = Modifier.weight(1f),
                    onClick = onUseCurrentLocation
                ) {
                    Text("Locate me")
                }
                Button(
                    modifier = Modifier.weight(1f),
                    onClick = {}
                ) {
                    Text("Evaluate")
                }
            }
            Text(
                text = locationStatus,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
private fun BottomSheetContent(
    isHeatmapMode: Boolean,
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
            item { HeatmapReportPanel() }
        } else {
            item { FeasibilityPanel() }
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

@Composable
private fun FeasibilityPanel() {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
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
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            StatusPill("Validated", Color(0xFF2E7D32))
            StatusPill("Pending", Color(0xFF9A6A00))
            StatusPill("High risk", Color(0xFFC62828))
        }
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

private fun hasLocationPermission(context: Context): Boolean {
    return ContextCompat.checkSelfPermission(
        context,
        Manifest.permission.ACCESS_FINE_LOCATION
    ) == PackageManager.PERMISSION_GRANTED ||
        ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.ACCESS_COARSE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED
}

@SuppressLint("MissingPermission")
private fun getLastKnownLocation(context: Context): GeoPoint? {
    if (!hasLocationPermission(context)) return null
    val locationManager = context.getSystemService(Context.LOCATION_SERVICE) as LocationManager
    val providers = locationManager.getProviders(true)
    val location = providers
        .mapNotNull { provider -> locationManager.getLastKnownLocation(provider) }
        .maxByOrNull { it.time }

    return location?.let { GeoPoint(it.latitude, it.longitude) }
}

@SuppressLint("MissingPermission")
@Suppress("DEPRECATION")
private fun requestCurrentLocation(
    context: Context,
    onLocationResult: (GeoPoint?) -> Unit
) {
    if (!hasLocationPermission(context)) {
        onLocationResult(null)
        return
    }

    val locationManager = context.getSystemService(Context.LOCATION_SERVICE) as LocationManager
    val fallbackLocation = getLastKnownLocation(context)
    if (fallbackLocation != null) {
        onLocationResult(fallbackLocation)
    }

    val providers = listOf(
        LocationManager.GPS_PROVIDER,
        LocationManager.NETWORK_PROVIDER
    ).filter { provider ->
        locationManager.getProviders(true).contains(provider) &&
            locationManager.isProviderEnabled(provider)
    }

    if (providers.isEmpty()) {
        if (fallbackLocation == null) onLocationResult(null)
        return
    }

    var deliveredFreshLocation = false
    val listener = object : LocationListener {
        override fun onLocationChanged(location: Location) {
            if (!deliveredFreshLocation) {
                deliveredFreshLocation = true
                locationManager.removeUpdates(this)
                onLocationResult(GeoPoint(location.latitude, location.longitude))
            }
        }

        @Deprecated("Deprecated in Java")
        override fun onStatusChanged(provider: String?, status: Int, extras: Bundle?) = Unit
    }

    providers.forEach { provider ->
        locationManager.requestSingleUpdate(provider, listener, Looper.getMainLooper())
    }
}
