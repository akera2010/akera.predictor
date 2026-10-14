package com.akeraten.valuebetmonitor.data.remote

import com.akeraten.valuebetmonitor.data.model.AppSettings
import com.akeraten.valuebetmonitor.data.model.Expert
import com.akeraten.valuebetmonitor.data.model.Health
import com.akeraten.valuebetmonitor.data.model.Match
import com.akeraten.valuebetmonitor.data.model.Prediction
import com.akeraten.valuebetmonitor.data.model.Stats
import com.akeraten.valuebetmonitor.data.model.ValueBet
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.PUT
import retrofit2.http.Path
import retrofit2.http.Query
import java.util.concurrent.TimeUnit

interface ApiService {
    @GET("api/health")
    suspend fun health(): Health

    @GET("api/matches")
    suspend fun matches(
        @Query("sport") sport: String?,
        @Query("status") status: String?,
    ): List<Match>

    @GET("api/matches/{id}")
    suspend fun match(@Path("id") id: String): Match

    @GET("api/value-bets")
    suspend fun valueBets(
        @Query("sport") sport: String?,
        @Query("min_edge") minEdge: Double?,
    ): List<ValueBet>

    @GET("api/predict/{match_id}")
    suspend fun predict(@Path("match_id") matchId: String): Prediction

    @GET("api/experts")
    suspend fun experts(): List<Expert>

    @GET("api/stats")
    suspend fun stats(): Stats

    @GET("api/settings")
    suspend fun settings(): AppSettings

    @PUT("api/settings")
    suspend fun updateSettings(@Body body: AppSettings): AppSettings
}

object Network {
    val json: Json = Json {
        ignoreUnknownKeys = true
        coerceInputValues = true
        isLenient = true
        explicitNulls = false
        encodeDefaults = true
    }

    val okHttp: OkHttpClient by lazy {
        OkHttpClient.Builder()
            .connectTimeout(6, TimeUnit.SECONDS)
            .readTimeout(15, TimeUnit.SECONDS)
            .writeTimeout(15, TimeUnit.SECONDS)
            .pingInterval(20, TimeUnit.SECONDS)
            .retryOnConnectionFailure(true)
            .build()
    }

    /** Ensures scheme + trailing slash; falls back to the emulator default. */
    fun normalizeBaseUrl(raw: String): String {
        var url = raw.trim()
        if (url.isEmpty()) url = DEFAULT_BASE_URL
        if (!url.startsWith("http://") && !url.startsWith("https://")) url = "http://$url"
        if (!url.endsWith("/")) url += "/"
        return url
    }

    fun webSocketUrl(baseUrl: String): String {
        val base = normalizeBaseUrl(baseUrl)
        val ws = when {
            base.startsWith("https://") -> "wss://" + base.removePrefix("https://")
            else -> "ws://" + base.removePrefix("http://")
        }
        return ws + "ws/live"
    }

    private var cachedUrl: String? = null
    private var cachedApi: ApiService? = null

    @Synchronized
    fun api(baseUrl: String): ApiService {
        val url = normalizeBaseUrl(baseUrl)
        val existing = cachedApi
        if (existing != null && cachedUrl == url) return existing
        val created = Retrofit.Builder()
            .baseUrl(url)
            .client(okHttp)
            .addConverterFactory(json.asConverterFactory("application/json; charset=UTF-8".toMediaType()))
            .build()
            .create(ApiService::class.java)
        cachedUrl = url
        cachedApi = created
        return created
    }

    const val DEFAULT_BASE_URL = "http://10.0.2.2:8000/"
}
