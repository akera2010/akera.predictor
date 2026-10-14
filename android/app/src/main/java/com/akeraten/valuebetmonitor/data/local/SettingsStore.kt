package com.akeraten.valuebetmonitor.data.local

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.doublePreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.akeraten.valuebetmonitor.data.model.AppSettings
import com.akeraten.valuebetmonitor.data.remote.Network
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.map

private val Context.akeratenDataStore: DataStore<Preferences> by preferencesDataStore(name = "akeraten_settings")

/** Local, user-facing preferences (persisted with DataStore). */
data class LocalPrefs(
    val baseUrl: String = Network.DEFAULT_BASE_URL,
    val notificationsEnabled: Boolean = true,
    val settings: AppSettings = AppSettings(),
)

class SettingsStore(context: Context) {

    private val store = context.applicationContext.akeratenDataStore

    private object Keys {
        val BASE_URL = stringPreferencesKey("base_url")
        val NOTIFICATIONS = booleanPreferencesKey("notifications")
        val BANKROLL = doublePreferencesKey("bankroll")
        val KELLY = doublePreferencesKey("kelly_fraction")
        val MIN_EDGE_TENNIS = doublePreferencesKey("min_edge_tennis")
        val MIN_EDGE_TT = doublePreferencesKey("min_edge_tt")
        val SUSPICIOUS = doublePreferencesKey("suspicious_edge")
        val RISK = stringPreferencesKey("risk_profile")
        val MAX_STAKE = doublePreferencesKey("max_stake_pct")
    }

    val prefs: Flow<LocalPrefs> = store.data
        .catch { emit(androidx.datastore.preferences.core.emptyPreferences()) }
        .map { p ->
            val d = AppSettings()
            LocalPrefs(
                baseUrl = p[Keys.BASE_URL] ?: Network.DEFAULT_BASE_URL,
                notificationsEnabled = p[Keys.NOTIFICATIONS] ?: true,
                settings = AppSettings(
                    bankroll = p[Keys.BANKROLL] ?: d.bankroll,
                    kellyFraction = p[Keys.KELLY] ?: d.kellyFraction,
                    minEdgeTennis = p[Keys.MIN_EDGE_TENNIS] ?: d.minEdgeTennis,
                    minEdgeTt = p[Keys.MIN_EDGE_TT] ?: d.minEdgeTt,
                    suspiciousEdge = p[Keys.SUSPICIOUS] ?: d.suspiciousEdge,
                    riskProfile = p[Keys.RISK] ?: d.riskProfile,
                    maxStakePct = p[Keys.MAX_STAKE] ?: d.maxStakePct,
                ),
            )
        }
        .distinctUntilChanged()

    val baseUrl: Flow<String> = prefs.map { it.baseUrl }.distinctUntilChanged()

    suspend fun setBaseUrl(url: String) {
        store.edit { it[Keys.BASE_URL] = Network.normalizeBaseUrl(url) }
    }

    suspend fun setNotifications(enabled: Boolean) {
        store.edit { it[Keys.NOTIFICATIONS] = enabled }
    }

    suspend fun saveSettings(s: AppSettings) {
        store.edit {
            it[Keys.BANKROLL] = s.bankroll
            it[Keys.KELLY] = s.kellyFraction
            it[Keys.MIN_EDGE_TENNIS] = s.minEdgeTennis
            it[Keys.MIN_EDGE_TT] = s.minEdgeTt
            it[Keys.SUSPICIOUS] = s.suspiciousEdge
            it[Keys.RISK] = s.riskProfile
            it[Keys.MAX_STAKE] = s.maxStakePct
        }
    }
}
