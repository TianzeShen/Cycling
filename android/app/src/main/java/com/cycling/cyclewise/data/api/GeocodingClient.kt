package com.cycling.cyclewise.data.api

import com.cycling.cyclewise.data.model.PlaceCandidate
import java.net.HttpURLConnection
import java.net.URI
import java.net.URLEncoder
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray

object GeocodingClient {
    private const val BASE_URL = "https://nominatim.openstreetmap.org/search"

    suspend fun searchPlaces(query: String): List<PlaceCandidate> = withContext(Dispatchers.IO) {
        if (query.trim().length < 3) return@withContext emptyList()

        val encodedQuery = URLEncoder.encode(query.trim(), "UTF-8")
        val url = URI(
            "$BASE_URL?format=json&limit=5&addressdetails=1&countrycodes=au&q=$encodedQuery"
        ).toURL()
        val connection = (url.openConnection() as HttpURLConnection).apply {
            requestMethod = "GET"
            connectTimeout = 8_000
            readTimeout = 8_000
            setRequestProperty("User-Agent", "CycleWise Android")
        }

        try {
            val response = connection.inputStream.bufferedReader().use { it.readText() }
            val json = JSONArray(response)
            buildList {
                for (index in 0 until json.length()) {
                    val item = json.getJSONObject(index)
                    val displayName = item.optString("display_name")
                    val name = item.optString("name").ifBlank {
                        displayName.substringBefore(",").ifBlank { displayName }
                    }
                    add(
                        PlaceCandidate(
                            name = name,
                            displayName = displayName,
                            lat = item.getString("lat").toDouble(),
                            lng = item.getString("lon").toDouble()
                        )
                    )
                }
            }
        } finally {
            connection.disconnect()
        }
    }
}
