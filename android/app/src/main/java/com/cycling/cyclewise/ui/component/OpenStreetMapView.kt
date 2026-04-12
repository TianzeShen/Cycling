package com.cycling.cyclewise.ui.component

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.drawable.BitmapDrawable
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.viewinterop.AndroidView
import com.cycling.cyclewise.data.model.HeatmapReport
import com.cycling.cyclewise.data.model.RiskLevel
import com.cycling.cyclewise.data.model.RouteAlert
import com.cycling.cyclewise.data.model.RouteSegment
import com.cycling.cyclewise.data.model.midpointTo
import org.osmdroid.config.Configuration
import org.osmdroid.tileprovider.tilesource.TileSourceFactory
import org.osmdroid.util.GeoPoint
import org.osmdroid.views.MapView
import org.osmdroid.views.overlay.Marker
import org.osmdroid.views.overlay.Polygon
import org.osmdroid.views.overlay.Polyline

@Composable
fun OpenStreetMapView(
    center: GeoPoint,
    userLocation: GeoPoint?,
    startLocation: GeoPoint?,
    destinationLocation: GeoPoint?,
    routeSegments: List<RouteSegment>,
    routeAlerts: List<RouteAlert>,
    heatmapReports: List<HeatmapReport>,
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
            startLocation?.let { location ->
                map.overlays.add(
                    Marker(map).apply {
                        position = location
                        title = "Start point"
                        setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM)
                    }
                )
            }
            destinationLocation?.let { location ->
                map.overlays.add(
                    Marker(map).apply {
                        position = location
                        title = "Destination"
                        setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM)
                    }
                )
            }
            routeSegments.forEach { segment ->
                map.overlays.add(
                    Polyline().apply {
                        setPoints(segment.coordinates.map { GeoPoint(it.lat, it.lng) })
                        outlinePaint.color = segment.riskLevel.toRouteColor()
                        outlinePaint.strokeWidth = if (segment.isGap) 12f else 8f
                        title = "${segment.riskLevel} segment"
                    }
                )
                if (segment.isGap && segment.coordinates.size >= 2) {
                    val midpoint = segment.coordinates.first().midpointTo(segment.coordinates.last())
                    map.overlays.add(
                        Marker(map).apply {
                            position = GeoPoint(midpoint.lat, midpoint.lng)
                            title = "Infrastructure gap"
                            setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM)
                        }
                    )
                }
            }
            routeAlerts.forEach { alert ->
                map.overlays.add(
                    Marker(map).apply {
                        position = GeoPoint(alert.location.lat, alert.location.lng)
                        title = alert.message
                        setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM)
                    }
                )
            }
            if (isHeatmapMode) {
                heatmapReports.forEach { report ->
                    val color = report.riskLevel.toHeatmapColor()
                    val location = GeoPoint(report.lat, report.lng)
                    map.overlays.add(
                        Polygon().apply {
                            points = createCirclePoints(location, report.radiusMeters)
                            fillPaint.color = color.withAlpha(45)
                            outlinePaint.color = color.withAlpha(90)
                            outlinePaint.strokeWidth = 2f
                        }
                    )
                    map.overlays.add(
                        Marker(map).apply {
                            position = location
                            title = "${report.riskLevel.label}: ${report.title}"
                            icon = createRiskMarkerIcon(map.context, color)
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

private fun String.toRouteColor(): Int {
    return when (lowercase()) {
        "green" -> Color.rgb(46, 125, 50)
        "yellow" -> Color.rgb(154, 106, 0)
        "red" -> Color.rgb(198, 40, 40)
        else -> Color.rgb(0, 106, 103)
    }
}

private fun createRiskMarkerIcon(context: Context, color: Int): BitmapDrawable {
    val density = context.resources.displayMetrics.density
    val size = (48 * density).toInt()
    val bitmap = Bitmap.createBitmap(size, size, Bitmap.Config.ARGB_8888)
    val canvas = Canvas(bitmap)
    val scale = size / 48f

    val fillPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        this.color = color
        style = Paint.Style.FILL
    }
    val strokePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        this.color = Color.WHITE
        style = Paint.Style.STROKE
        strokeWidth = 2.8f * scale
    }
    val innerPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        this.color = Color.WHITE
        style = Paint.Style.FILL
    }

    canvas.drawCircle(24f * scale, 20f * scale, 14f * scale, fillPaint)
    canvas.drawCircle(24f * scale, 20f * scale, 14f * scale, strokePaint)
    canvas.drawOval(RectF(18f * scale, 32f * scale, 30f * scale, 43f * scale), fillPaint)
    canvas.drawCircle(24f * scale, 20f * scale, 5f * scale, innerPaint)
    canvas.drawCircle(24f * scale, 20f * scale, 2.5f * scale, fillPaint)

    return BitmapDrawable(context.resources, bitmap)
}

private fun createCirclePoints(center: GeoPoint, radiusMeters: Double): List<GeoPoint> {
    val points = mutableListOf<GeoPoint>()
    val earthRadius = 6_371_000.0
    val latRadians = Math.toRadians(center.latitude)
    val lngRadians = Math.toRadians(center.longitude)
    val angularDistance = radiusMeters / earthRadius

    for (bearingDegrees in 0..360 step 12) {
        val bearing = Math.toRadians(bearingDegrees.toDouble())
        val lat = kotlin.math.asin(
            kotlin.math.sin(latRadians) * kotlin.math.cos(angularDistance) +
                kotlin.math.cos(latRadians) * kotlin.math.sin(angularDistance) *
                kotlin.math.cos(bearing)
        )
        val lng = lngRadians + kotlin.math.atan2(
            kotlin.math.sin(bearing) * kotlin.math.sin(angularDistance) *
                kotlin.math.cos(latRadians),
            kotlin.math.cos(angularDistance) -
                kotlin.math.sin(latRadians) * kotlin.math.sin(lat)
        )
        points.add(GeoPoint(Math.toDegrees(lat), Math.toDegrees(lng)))
    }

    return points
}

private fun Int.withAlpha(alpha: Int): Int {
    return Color.argb(alpha, Color.red(this), Color.green(this), Color.blue(this))
}

private fun RiskLevel.toHeatmapColor(): Int {
    return when (this) {
        RiskLevel.High -> Color.rgb(239, 68, 68)
        RiskLevel.Medium -> Color.rgb(249, 128, 70)
        RiskLevel.Low -> Color.rgb(242, 201, 76)
    }
}
