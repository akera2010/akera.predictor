package com.akeraten.valuebetmonitor.data

import com.akeraten.valuebetmonitor.data.demo.DemoData
import com.akeraten.valuebetmonitor.data.local.LocalPrefs
import com.akeraten.valuebetmonitor.data.local.SettingsStore
import com.akeraten.valuebetmonitor.data.model.AppSettings
import com.akeraten.valuebetmonitor.data.model.ConnectionState
import com.akeraten.valuebetmonitor.data.model.DataMode
import com.akeraten.valuebetmonitor.data.model.Expert
import com.akeraten.valuebetmonitor.data.model.Health
import com.akeraten.valuebetmonitor.data.model.Match
import com.akeraten.valuebetmonitor.data.model.Prediction
import com.akeraten.valuebetmonitor.data.model.Stats
import com.akeraten.valuebetmonitor.data.model.ValueBet
import com.akeraten.valuebetmonitor.data.model.WsMessage
import com.akeraten.valuebetmonitor.data.remote.LanDiscovery
import com.akeraten.valuebetmonitor.data.remote.LiveSocket
import com.akeraten.valuebetmonitor.data.remote.Network
import com.akeraten.valuebetmonitor.data.remote.SocketEvent
import com.akeraten.valuebetmonitor.notifications.Notifier
import com.akeraten.valuebetmonitor.util.asDoubleOrNull
import com.akeraten.valuebetmonitor.util.asFraction
import com.akeraten.valuebetmonitor.util.asStringOrNull
import com.akeraten.valuebetmonitor.util.signedPct
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlin.math.min

/** Value + whether it came from the offline demo generator. */
data class Loaded<T>(val data: T, val demo: Boolean)

/**
 * Single source of truth. Combines REST (initial load / fallback polling) with the
 * `/ws/live` WebSocket stream, and falls back to offline demo data when the backend
 * is unreachable so the app is always navigable.
 */
class Repository(
    private val settingsStore: SettingsStore,
    private val notifier: Notifier,
    private val scope: CoroutineScope,
    private val discovery: LanDiscovery,
) {
    private val _discovering = MutableStateFlow(false)
    val discovering: StateFlow<Boolean> = _discovering.asStateFlow()

    private val _matches = MutableStateFlow<List<Match>>(emptyList())
    val matches: StateFlow<List<Match>> = _matches.asStateFlow()

    private val _valueBets = MutableStateFlow<List<ValueBet>>(emptyList())
    val valueBets: StateFlow<List<ValueBet>> = _valueBets.asStateFlow()

    private val _mode = MutableStateFlow(DataMode.CONNECTING)
    val mode: StateFlow<DataMode> = _mode.asStateFlow()

    private val _connection = MutableStateFlow(ConnectionState.CONNECTING)
    val connection: StateFlow<ConnectionState> = _connection.asStateFlow()

    private val _health = MutableStateFlow<Health?>(null)
    val health: StateFlow<Health?> = _health.asStateFlow()

    private val _refreshing = MutableStateFlow(false)
    val refreshing: StateFlow<Boolean> = _refreshing.asStateFlow()

    private val _lastUpdate = MutableStateFlow(0L)
    val lastUpdate: StateFlow<Long> = _lastUpdate.asStateFlow()

    val prefs: StateFlow<LocalPrefs> =
        settingsStore.prefs.stateIn(scope, SharingStarted.Eagerly, LocalPrefs())

    private val reconnectSignal = MutableStateFlow(0)
    private val notifiedAlerts = HashSet<String>()
    private var started = false

    fun start() {
        if (started) return
        started = true
        scope.launch {
            combine(settingsStore.baseUrl, reconnectSignal) { url, _ -> url }
                .collectLatest { url -> runLiveLoop(url) }
        }
        scope.launch { demoTicker() }
    }

    fun reconnect() {
        reconnectSignal.value = reconnectSignal.value + 1
    }

    private suspend fun runLiveLoop(url: String) {
        _connection.value = ConnectionState.CONNECTING
        if (!refresh(url) && autoDiscover(url)) return
        var backoff = 2_000L
        while (currentCoroutineContext().isActive) {
            try {
                LiveSocket.events(url).collect { event ->
                    when (event) {
                        is SocketEvent.Open -> {
                            _connection.value = ConnectionState.REALTIME
                            backoff = 2_000L
                        }
                        is SocketEvent.Message -> handleMessage(event.message)
                    }
                }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                // socket failed: fall through to REST polling + retry
            }
            _connection.value =
                if (_mode.value == DataMode.OFFLINE_DEMO) ConnectionState.OFFLINE else ConnectionState.REST_ONLY
            delay(backoff)
            backoff = min(backoff * 2, 30_000L)
            // Backend unreachable: look for the PC on the Wi-Fi (UDP beacon, a few seconds).
            if (!refresh(url) && autoDiscover(url)) return
        }
    }

    /**
     * Listens briefly for the PC's LAN beacon. When a different, working backend is found it is
     * saved as the base URL, which restarts [runLiveLoop] against it. Returns true in that case.
     */
    private suspend fun autoDiscover(current: String): Boolean {
        val found = discovery.find(listenMillis = 3_000, scanSubnet = false) ?: return false
        if (Network.normalizeBaseUrl(found) == Network.normalizeBaseUrl(current)) return false
        settingsStore.setBaseUrl(found)
        return true
    }

    /** Manual "Buscar mi PC": beacon first, then a full subnet scan. Returns the URL found, or null. */
    suspend fun discoverPc(): String? {
        _discovering.value = true
        try {
            val found = discovery.find(listenMillis = 4_000, scanSubnet = true) ?: return null
            settingsStore.setBaseUrl(found)
            reconnect()
            return Network.normalizeBaseUrl(found)
        } finally {
            _discovering.value = false
        }
    }

    private suspend fun demoTicker() {
        while (currentCoroutineContext().isActive) {
            delay(3_500L)
            if (_mode.value == DataMode.OFFLINE_DEMO && _matches.value.isNotEmpty()) {
                _matches.value = DemoData.tick(_matches.value)
                _lastUpdate.value = System.currentTimeMillis()
            }
        }
    }

    /** REST refresh of matches + value bets. Returns true when the backend answered. */
    suspend fun refresh(url: String = prefs.value.baseUrl): Boolean {
        _refreshing.value = true
        try {
            val api = Network.api(url)
            val health = try {
                api.health()
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                null
            }
            val matches = api.matches(null, null)
            val bets = try {
                api.valueBets(null, null)
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                emptyList()
            }
            _health.value = health
            _matches.value = matches
            _valueBets.value = sortBets(bets)
            _mode.value = modeFromHealth(health)
            if (_connection.value == ConnectionState.OFFLINE || _connection.value == ConnectionState.CONNECTING) {
                _connection.value = ConnectionState.REST_ONLY
            }
            _lastUpdate.value = System.currentTimeMillis()
            return true
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            enterOfflineDemo()
            return false
        } finally {
            _refreshing.value = false
        }
    }

    private fun modeFromHealth(health: Health?): DataMode =
        if (health == null || health.mode.equals("live", ignoreCase = true)) DataMode.LIVE else DataMode.BACKEND_DEMO

    private fun enterOfflineDemo() {
        if (_mode.value != DataMode.OFFLINE_DEMO || _matches.value.isEmpty()) {
            val s = prefs.value.settings
            _matches.value = DemoData.matches()
            _valueBets.value = DemoData.valueBets(s.bankroll, s.kellyFraction)
        }
        _health.value = null
        _mode.value = DataMode.OFFLINE_DEMO
        _connection.value = ConnectionState.OFFLINE
        _lastUpdate.value = System.currentTimeMillis()
    }

    private fun sortBets(bets: List<ValueBet>): List<ValueBet> =
        bets.sortedWith(compareByDescending<ValueBet> { it.edge.asFraction() }.thenByDescending { it.confidenceScore ?: 0.0 })

    // ------------------------------------------------------------------ WebSocket

    private fun handleMessage(msg: WsMessage) {
        when (msg.type.lowercase()) {
            "snapshot" -> {
                val obj = msg.data as? JsonObject
                val ms = decodeMatches(obj?.get("matches") ?: msg.data)
                val bs = decodeBets(obj?.get("value_bets"))
                if (ms != null) _matches.value = ms
                if (bs != null) _valueBets.value = sortBets(bs)
                if (_mode.value == DataMode.OFFLINE_DEMO || _mode.value == DataMode.CONNECTING) {
                    _mode.value = modeFromHealth(_health.value)
                }
            }
            // The backend broadcasts the full match list every tick: replace (merge only small deltas).
            "matches" -> decodeMatches(msg.data)?.let { incoming ->
                if (incoming.size >= _matches.value.size / 2) _matches.value = incoming else mergeMatches(incoming)
            }
            "value_bets" -> decodeBets(msg.data)?.let { _valueBets.value = sortBets(it) }
            "alert" -> handleAlert(msg.data)
        }
        _lastUpdate.value = System.currentTimeMillis()
    }

    private fun mergeMatches(incoming: List<Match>) {
        val map = LinkedHashMap<String, Match>()
        _matches.value.forEach { map[it.key] = it }
        incoming.forEach { map[it.key] = it }
        _matches.value = map.values.toList()
    }

    private fun decodeMatches(el: JsonElement?): List<Match>? {
        val arr = when (el) {
            is JsonArray -> el
            is JsonObject -> el["matches"] as? JsonArray
            else -> null
        } ?: return null
        return arr.mapNotNull {
            runCatching { Network.json.decodeFromJsonElement(Match.serializer(), it) }.getOrNull()
        }
    }

    private fun decodeBets(el: JsonElement?): List<ValueBet>? {
        val arr = when (el) {
            is JsonArray -> el
            is JsonObject -> el["value_bets"] as? JsonArray
            else -> null
        } ?: return null
        return arr.mapNotNull {
            runCatching { Network.json.decodeFromJsonElement(ValueBet.serializer(), it) }.getOrNull()
        }
    }

    private fun handleAlert(data: JsonElement?) {
        val obj = data as? JsonObject ?: return
        val nested = (obj["value_bet"] ?: obj["bet"]) as? JsonObject
        val edge = (obj["edge"] ?: nested?.get("edge")).asDoubleOrNull() ?: return
        if (edge.asFraction() <= 0.05) return
        if (!prefs.value.notificationsEnabled) return
        val selection = (obj["selection"] ?: nested?.get("selection")).asStringOrNull().orEmpty()
        val playerA = (obj["player_a"] ?: nested?.get("player_a")).asStringOrNull()
        val playerB = (obj["player_b"] ?: nested?.get("player_b")).asStringOrNull()
        val odds = (obj["odds"] ?: nested?.get("odds")).asDoubleOrNull()
        val message = obj["message"].asStringOrNull()
        val id = (obj["id"] ?: nested?.get("id")).asStringOrNull()
            ?: "${obj["match_id"].asStringOrNull()}-$selection"
        synchronized(notifiedAlerts) {
            if (!notifiedAlerts.add(id)) return
        }
        val title = "Value bet ${edge.signedPct()} · ${selection.ifBlank { "AKERATEN" }}"
        val text = buildString {
            if (playerA != null && playerB != null) append("$playerA vs $playerB. ")
            if (odds != null) append("Cuota $odds. ")
            if (message != null) append(message)
            if (isEmpty()) append("Nueva oportunidad detectada por el modelo.")
        }
        notifier.notifyValueBet(id.hashCode(), title, text)
    }

    // ------------------------------------------------------------------ Detail calls

    fun findMatch(id: String): Match? = _matches.value.firstOrNull { it.key == id || it.matchId == id }

    fun findBet(id: String): ValueBet? = _valueBets.value.firstOrNull { it.key == id }

    private suspend fun <T> loadOrDemo(block: suspend () -> T, demo: () -> T): Loaded<T> {
        if (_mode.value == DataMode.OFFLINE_DEMO) return Loaded(demo(), true)
        return try {
            Loaded(block(), false)
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            Loaded(demo(), true)
        }
    }

    suspend fun matchDetail(id: String): Loaded<Match> = loadOrDemo(
        block = { Network.api(prefs.value.baseUrl).match(id) },
        demo = { DemoData.matchDetail(id, findMatch(id)) },
    )

    suspend fun prediction(matchId: String): Loaded<Prediction> = loadOrDemo(
        block = { Network.api(prefs.value.baseUrl).predict(matchId) },
        demo = { DemoData.prediction(matchId, findMatch(matchId)) },
    )

    suspend fun experts(): Loaded<List<Expert>> = loadOrDemo(
        block = { Network.api(prefs.value.baseUrl).experts() },
        demo = { DemoData.experts() },
    )

    suspend fun stats(): Loaded<Stats> = loadOrDemo(
        block = { Network.api(prefs.value.baseUrl).stats() },
        demo = { DemoData.stats(prefs.value.settings.bankroll) },
    )

    suspend fun checkHealth(): Health? = try {
        Network.api(prefs.value.baseUrl).health().also { _health.value = it }
    } catch (e: CancellationException) {
        throw e
    } catch (e: Exception) {
        null
    }

    /** Pulls settings from the backend (if reachable) and stores them locally. */
    suspend fun pullBackendSettings(): AppSettings? = try {
        val remote = Network.api(prefs.value.baseUrl).settings()
        settingsStore.saveSettings(remote)
        remote
    } catch (e: CancellationException) {
        throw e
    } catch (e: Exception) {
        null
    }

    /** Saves locally and tries to sync with the backend. Returns true if the backend accepted. */
    suspend fun saveSettings(settings: AppSettings): Boolean {
        settingsStore.saveSettings(settings)
        return try {
            Network.api(prefs.value.baseUrl).updateSettings(settings)
            true
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            false
        }
    }

    suspend fun setBaseUrl(url: String) {
        settingsStore.setBaseUrl(url)
        reconnect()
    }

    suspend fun setNotifications(enabled: Boolean) = settingsStore.setNotifications(enabled)
}
