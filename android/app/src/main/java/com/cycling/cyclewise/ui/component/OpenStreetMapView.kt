package com.cycling.cyclewise.ui.component

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.drawable.BitmapDrawable
import android.view.View
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.platform.LocalContext
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
import org.osmdroid.views.CustomZoomButtonsController
import org.osmdroid.views.MapView
import org.osmdroid.views.overlay.Marker
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
    val context = LocalContext.current
    val iconCache = remember { MapIconCache(context) }
    val lastOverlayKey = remember { mutableStateOf("") }
    val lastCenter = remember { mutableStateOf<GeoPoint?>(null) }
    val overlayKey = rememberOverlayKey(
        userLocation = userLocation,
        startLocation = startLocation,
        destinationLocation = destinationLocation,
        routeSegments = routeSegments,
        routeAlerts = routeAlerts,
        heatmapReports = heatmapReports,
        isHeatmapMode = isHeatmapMode
    )

    AndroidView(
        modifier = modifier,
        factory = { mapView },
        update = { map ->
            if (!center.isSamePointAs(lastCenter.value)) {
                map.controller.setCenter(center)
                lastCenter.value = center
            }

            if (overlayKey != lastOverlayKey.value) {
                map.overlays.clear()
                userLocation
                    ?.takeUnless { location ->
                        location.isSamePointAs(startLocation) || location.isSamePointAs(destinationLocation)
                    }
                    ?.let { location ->
                        map.overlays.add(
                            Marker(map).apply {
                                position = location
                                title = "Current location"
                                icon = iconCache.userLocation()
                                infoWindow = null
                                setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_CENTER)
                            }
                        )
                    }
                startLocation?.let { location ->
                    map.overlays.add(
                        Marker(map).apply {
                            position = location
                            title = "Start point"
                            icon = iconCache.startPin()
                            infoWindow = null
                            setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM)
                        }
                    )
                }
                destinationLocation?.let { location ->
                    map.overlays.add(
                        Marker(map).apply {
                            position = location
                            title = "Destination"
                            icon = iconCache.destinationPin()
                            infoWindow = null
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
                                icon = iconCache.gapWarning()
                                infoWindow = null
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
                            icon = iconCache.routeWarning()
                            infoWindow = null
                            setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM)
                        }
                    )
                }
                if (isHeatmapMode) {
                    heatmapReports.forEach { report ->
                        val color = report.riskLevel.toHeatmapColor()
                        val location = GeoPoint(report.lat, report.lng)
                        map.overlays.add(
                            Marker(map).apply {
                                position = location
                                title = "${report.riskLevel.label}: ${report.title}"
                                icon = iconCache.riskIcon(report.riskLevel)
                                infoWindow = null
                                setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM)
                            }
                        )
                    }
                }
                lastOverlayKey.value = overlayKey
                map.invalidate()
            }
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
            zoomController.setVisibility(CustomZoomButtonsController.Visibility.NEVER)
            setLayerType(View.LAYER_TYPE_SOFTWARE, null)
            setUseDataConnection(true)
            setTilesScaledToDpi(true)
            isHorizontalMapRepetitionEnabled = false
            isVerticalMapRepetitionEnabled = false
            minZoomLevel = 4.0
            maxZoomLevel = 18.0
            controller.setZoom(14.5)
            controller.setCenter(center)
        }
    }

    DisposableEffect(mapView) {
        mapView.onResume()
        onDispose {
            mapView.onPause()
            mapView.onDetach()
        }
    }

    return mapView
}

@Composable
private fun rememberOverlayKey(
    userLocation: GeoPoint?,
    startLocation: GeoPoint?,
    destinationLocation: GeoPoint?,
    routeSegments: List<RouteSegment>,
    routeAlerts: List<RouteAlert>,
    heatmapReports: List<HeatmapReport>,
    isHeatmapMode: Boolean
): String {
    return remember(
        userLocation,
        startLocation,
        destinationLocation,
        routeSegments,
        routeAlerts,
        heatmapReports,
        isHeatmapMode
    ) {
        buildString {
            append("mode=").append(isHeatmapMode)
            append("|user=").append(userLocation.keyPart())
            append("|start=").append(startLocation.keyPart())
            append("|end=").append(destinationLocation.keyPart())
            append("|segments=")
            routeSegments.forEach { segment ->
                append(segment.riskLevel).append(segment.isGap)
                segment.coordinates.forEach { append(it.lat).append(',').append(it.lng).append(';') }
            }
            append("|alerts=")
            routeAlerts.forEach { append(it.location.lat).append(',').append(it.location.lng).append(it.message) }
            append("|heat=")
            heatmapReports.forEach {
                append(it.title).append(it.riskLevel).append(it.lat).append(',').append(it.lng)
            }
        }
    }
}

private class MapIconCache(context: Context) {
    private val resources = context.resources
    private val userLocationBitmap = createUserLocationBitmap(context)
    private val startPinBitmap = createLocationPinBitmap(context, Color.rgb(47, 128, 237))
    private val destinationPinBitmap = createLocationPinBitmap(context, Color.rgb(185, 106, 247))
    private val gapWarningBitmap = createWarningBitmap(context, Color.rgb(198, 40, 40))
    private val routeWarningBitmap = createWarningBitmap(context, Color.rgb(249, 128, 70))
    private val riskIcons = RiskLevel.entries.associateWith { risk ->
        createRiskMarkerBitmap(context, risk.toHeatmapColor())
    }

    fun userLocation(): BitmapDrawable = BitmapDrawable(resources, userLocationBitmap)
    fun startPin(): BitmapDrawable = BitmapDrawable(resources, startPinBitmap)
    fun destinationPin(): BitmapDrawable = BitmapDrawable(resources, destinationPinBitmap)
    fun gapWarning(): BitmapDrawable = BitmapDrawable(resources, gapWarningBitmap)
    fun routeWarning(): BitmapDrawable = BitmapDrawable(resources, routeWarningBitmap)
    fun riskIcon(riskLevel: RiskLevel): BitmapDrawable = BitmapDrawable(
        resources,
        riskIcons.getValue(riskLevel)
    )
}

private fun GeoPoint?.keyPart(): String {
    return this?.let { "${it.latitude},${it.longitude}" } ?: "null"
}

private fun configureOsmdroid(context: Context) {
    Configuration.getInstance().apply {
        userAgentValue = context.packageName
        tileFileSystemCacheMaxBytes = 6L * 1024L * 1024L
        tileFileSystemCacheTrimBytes = 4L * 1024L * 1024L
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

private fun createRiskMarkerBitmap(context: Context, color: Int): Bitmap {
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

    return bitmap
}

private fun createUserLocationBitmap(context: Context): Bitmap {
    val density = context.resources.displayMetrics.density
    val size = (28 * density).toInt()
    val bitmap = Bitmap.createBitmap(size, size, Bitmap.Config.ARGB_8888)
    val canvas = Canvas(bitmap)
    val scale = size / 28f
    val haloPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        this.color = Color.argb(55, 37, 99, 235)
        style = Paint.Style.FILL
    }
    val fillPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        this.color = Color.rgb(37, 99, 235)
        style = Paint.Style.FILL
    }
    val strokePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        this.color = Color.WHITE
        style = Paint.Style.STROKE
        strokeWidth = 2.5f * scale
    }

    canvas.drawCircle(14f * scale, 14f * scale, 12f * scale, haloPaint)
    canvas.drawCircle(14f * scale, 14f * scale, 6f * scale, fillPaint)
    canvas.drawCircle(14f * scale, 14f * scale, 6f * scale, strokePaint)

    return bitmap
}

private fun createLocationPinBitmap(context: Context, color: Int): Bitmap {
    val density = context.resources.displayMetrics.density
    val size = (44 * density).toInt()
    val bitmap = Bitmap.createBitmap(size, size, Bitmap.Config.ARGB_8888)
    val canvas = Canvas(bitmap)
    val scale = size / 44f

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

    val path = android.graphics.Path().apply {
        moveTo(22f * scale, 40f * scale)
        cubicTo(13f * scale, 29f * scale, 8f * scale, 22f * scale, 8f * scale, 15f * scale)
        cubicTo(8f * scale, 7f * scale, 14f * scale, 2f * scale, 22f * scale, 2f * scale)
        cubicTo(30f * scale, 2f * scale, 36f * scale, 7f * scale, 36f * scale, 15f * scale)
        cubicTo(36f * scale, 22f * scale, 31f * scale, 29f * scale, 22f * scale, 40f * scale)
        close()
    }

    canvas.drawPath(path, fillPaint)
    canvas.drawPath(path, strokePaint)
    canvas.drawCircle(22f * scale, 15f * scale, 5.5f * scale, innerPaint)

    return bitmap
}

private fun createWarningBitmap(context: Context, color: Int): Bitmap {
    val density = context.resources.displayMetrics.density
    val size = (46 * density).toInt()
    val bitmap = Bitmap.createBitmap(size, size, Bitmap.Config.ARGB_8888)
    val canvas = Canvas(bitmap)
    val scale = size / 46f

    val fillPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        this.color = color
        style = Paint.Style.FILL
    }
    val strokePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        this.color = Color.WHITE
        style = Paint.Style.STROKE
        strokeWidth = 3f * scale
        strokeJoin = Paint.Join.ROUND
    }
    val markPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        this.color = Color.WHITE
        style = Paint.Style.STROKE
        strokeWidth = 3.2f * scale
        strokeCap = Paint.Cap.ROUND
    }
    val dotPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        this.color = Color.WHITE
        style = Paint.Style.FILL
    }

    val triangle = android.graphics.Path().apply {
        moveTo(23f * scale, 5f * scale)
        lineTo(41f * scale, 37f * scale)
        lineTo(5f * scale, 37f * scale)
        close()
    }

    canvas.drawPath(triangle, fillPaint)
    canvas.drawPath(triangle, strokePaint)
    canvas.drawLine(23f * scale, 16f * scale, 23f * scale, 27f * scale, markPaint)
    canvas.drawCircle(23f * scale, 32f * scale, 2.2f * scale, dotPaint)

    return bitmap
}

private fun RiskLevel.toHeatmapColor(): Int {
    return when (this) {
        RiskLevel.High -> Color.rgb(239, 68, 68)
        RiskLevel.Medium -> Color.rgb(249, 128, 70)
        RiskLevel.Low -> Color.rgb(242, 201, 76)
    }
}

private fun GeoPoint.isSamePointAs(other: GeoPoint?): Boolean {
    if (other == null) return false
    return kotlin.math.abs(latitude - other.latitude) < 0.000001 &&
        kotlin.math.abs(longitude - other.longitude) < 0.000001
}
