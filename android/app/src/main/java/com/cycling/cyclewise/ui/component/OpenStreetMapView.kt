package com.cycling.cyclewise.ui.component

import android.content.Context
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.viewinterop.AndroidView
import org.osmdroid.config.Configuration
import org.osmdroid.tileprovider.tilesource.TileSourceFactory
import org.osmdroid.util.GeoPoint
import org.osmdroid.views.MapView
import org.osmdroid.views.overlay.Marker

@Composable
fun OpenStreetMapView(
    center: GeoPoint,
    userLocation: GeoPoint?,
    isHeatmapMode: Boolean,
    modifier: Modifier = Modifier
) {
    val mapView = rememberMapViewWithLifecycle(center)

    AndroidView(
        modifier = modifier,
        factory = { mapView },
        update = { map ->
            map.controller.setCenter(center)
            map.overlays.clear()
            userLocation?.let { location ->
                map.overlays.add(
                    Marker(map).apply {
                        position = location
                        title = "Current location"
                        setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM)
                    }
                )
            }
            if (isHeatmapMode) {
                listOf(
                    GeoPoint(-37.8109, 144.9631) to "12 reports near La Trobe Street",
                    GeoPoint(-37.8171, 144.9671) to "5 reports near Swanston Street",
                    GeoPoint(-37.8124, 144.9588) to "3 reports near Elizabeth Street"
                ).forEach { (point, title) ->
                    map.overlays.add(
                        Marker(map).apply {
                            position = point
                            this.title = title
                            setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM)
                        }
                    )
                }
            }
            map.invalidate()
        }
    )
}

@Composable
private fun rememberMapViewWithLifecycle(center: GeoPoint): MapView {
    val context = androidx.compose.ui.platform.LocalContext.current
    val mapView = remember {
        configureOsmdroid(context)
        MapView(context).apply {
            setTileSource(TileSourceFactory.MAPNIK)
            setMultiTouchControls(true)
            minZoomLevel = 4.0
            maxZoomLevel = 20.0
            controller.setZoom(14.5)
            controller.setCenter(center)
        }
    }

    DisposableEffect(mapView) {
        mapView.onResume()
        onDispose {
            mapView.onPause()
        }
    }

    return mapView
}

private fun configureOsmdroid(context: Context) {
    Configuration.getInstance().apply {
        userAgentValue = context.packageName
        load(context, context.getSharedPreferences("osmdroid", Context.MODE_PRIVATE))
    }
}
