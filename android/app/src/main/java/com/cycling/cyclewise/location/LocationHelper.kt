package com.cycling.cyclewise.location

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Bundle
import android.os.Looper
import androidx.core.content.ContextCompat
import org.osmdroid.util.GeoPoint

fun hasLocationPermission(context: Context): Boolean {
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
fun getLastKnownLocation(context: Context): GeoPoint? {
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
fun requestCurrentLocation(
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
