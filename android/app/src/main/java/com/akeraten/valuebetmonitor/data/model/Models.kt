package com.akeraten.valuebetmonitor.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject

/*
 * Backend contract models (FastAPI). Every field is nullable or has a default so that
 * partial / evolving payloads never crash parsing (Json is configured with
 * ignoreUnknownKeys + coerceInputValues + isLenient).
 */

@Serializable
data class SourceStatus(
    val name: String = "",
    val enabled: Boolean = true,
    val status: String? = null,
)

@Serializable
data class Health(
    val status: String = "unknown",
    val app: String? = null,
    val author: String? = null,
    val mode: String = "demo",
    val sources: List<SourceStatus> = emptyList(),
    val disclaimer: String? = null,
)

@Serializable
data class Score(
    val sets: List<List<Int>> = emptyList(),
    val games: JsonElement? = null,
    val points: String? = null,
)

@Serializable
data class Odds(
    @SerialName("player_a") val playerA: Double? = null,
    @SerialName("player_b") val playerB: Double? = null,
)

@Serializable
data class H2H(
    val a: Int = 0,
    val b: Int = 0,
    val last: List<JsonElement> = emptyList(),
)

@Serializable
data class ProbPoint(
    val t: String? = null,
    @SerialName("model_a") val modelA: Double? = null,
    @SerialName("implied_a") val impliedA: Double? = null,
)

@Serializable
data class Match(
    val id: String = "",
    @SerialName("match_id") val matchId: String? = null,
    val sport: String = "tennis",
    val source: String? = null,
    val category: String? = null,
    @SerialName("player_a") val playerA: String = "Jugador A",
    @SerialName("player_b") val playerB: String = "Jugador B",
    val tournament: String = "",
    val surface: String? = null,
    val status: String = "upcoming",
    @SerialName("start_time") val startTime: String? = null,
    @SerialName("best_of") val bestOf: Int = 3,
    val server: String? = null,
    @SerialName("rank_a") val rankA: Int? = null,
    @SerialName("rank_b") val rankB: Int? = null,
    @SerialName("country_a") val countryA: String? = null,
    @SerialName("country_b") val countryB: String? = null,
    val score: Score = Score(),
    val odds: Odds? = null,
    @SerialName("model_prob_a") val modelProbA: Double? = null,
    @SerialName("model_prob_b") val modelProbB: Double? = null,
    @SerialName("value_bet_count") val valueBetCount: Int = 0,
    val timestamp: String? = null,
    // ---- detail-only fields (GET /api/matches/{id}) ----
    val h2h: H2H? = null,
    val stats: JsonObject? = null,
    @SerialName("prob_history") val probHistory: List<ProbPoint> = emptyList(),
    @SerialName("form_a") val formA: List<String> = emptyList(),
    @SerialName("form_b") val formB: List<String> = emptyList(),
) {
    /** Id used for navigation / API calls. */
    val key: String get() = id.ifBlank { matchId.orEmpty() }
    val isLive: Boolean get() = status.equals("live", ignoreCase = true)
    val isTableTennis: Boolean get() = sport.equals("table_tennis", ignoreCase = true)
}

@Serializable
data class ModelProbs(
    val elo: Double? = null,
    val ml: Double? = null,
    @SerialName("monte_carlo") val monteCarlo: Double? = null,
    val experts: Double? = null,
    val ensemble: Double? = null,
)

@Serializable
data class ValueBet(
    val id: String = "",
    @SerialName("match_id") val matchId: String = "",
    val sport: String = "tennis",
    val tournament: String = "",
    val category: String? = null,
    @SerialName("player_a") val playerA: String = "",
    @SerialName("player_b") val playerB: String = "",
    val status: String = "upcoming",
    val market: String = "Ganador del partido",
    val selection: String = "",
    @SerialName("selection_side") val selectionSide: String? = null,
    val odds: Double = 0.0,
    val bookmaker: String? = null,
    @SerialName("model_prob") val modelProb: Double = 0.0,
    @SerialName("implied_prob") val impliedProb: Double? = null,
    @SerialName("fair_prob") val fairProb: Double? = null,
    val edge: Double = 0.0,
    @SerialName("kelly_full") val kellyFull: Double? = null,
    @SerialName("kelly_fraction") val kellyFraction: Double? = null,
    val stake: Double? = null,
    val confidence: String = "media",
    @SerialName("confidence_score") val confidenceScore: Double? = null,
    val suspicious: Boolean = false,
    @SerialName("created_at") val createdAt: String? = null,
    val models: ModelProbs? = null,
) {
    val key: String get() = id.ifBlank { "$matchId-$selection-$market" }
}

@Serializable
data class Prediction(
    @SerialName("match_id") val matchId: String = "",
    @SerialName("prob_a") val probA: Double = 0.5,
    @SerialName("prob_b") val probB: Double = 0.5,
    val breakdown: JsonObject? = null,
    val weights: JsonObject? = null,
    val explanation: List<String> = emptyList(),
)

@Serializable
data class ExpertPick(
    @SerialName("match_id") val matchId: String? = null,
    val match: String = "",
    @SerialName("predicted_winner") val predictedWinner: String = "",
    val confidence: JsonElement? = null,
    val timestamp: String? = null,
    val result: String = "pending",
)

@Serializable
data class Expert(
    val name: String = "",
    val sport: String = "tennis",
    val platform: String = "",
    val url: String? = null,
    val weight: Double = 0.0,
    @SerialName("hit_rate") val hitRate: Double = 0.0,
    @SerialName("n_picks") val nPicks: Int = 0,
    val clv: Double? = null,
    val recent: List<ExpertPick> = emptyList(),
)

@Serializable
data class BankrollPoint(
    val t: String? = null,
    val bankroll: Double = 0.0,
)

@Serializable
data class Stats(
    @SerialName("n_value_bets") val nValueBets: Int = 0,
    @SerialName("avg_edge") val avgEdge: Double = 0.0,
    @SerialName("avg_clv") val avgClv: Double = 0.0,
    @SerialName("clv_positive_pct") val clvPositivePct: Double = 0.0,
    @SerialName("roi_sim") val roiSim: Double = 0.0,
    @SerialName("bankroll_curve") val bankrollCurve: List<BankrollPoint> = emptyList(),
    @SerialName("by_sport") val bySport: JsonObject? = null,
    @SerialName("hit_rate") val hitRate: Double? = null,
)

@Serializable
data class AppSettings(
    val bankroll: Double = 1000.0,
    @SerialName("kelly_fraction") val kellyFraction: Double = 0.5,
    @SerialName("min_edge_tennis") val minEdgeTennis: Double = 0.03,
    @SerialName("min_edge_tt") val minEdgeTt: Double = 0.04,
    @SerialName("suspicious_edge") val suspiciousEdge: Double = 0.15,
    @SerialName("risk_profile") val riskProfile: String = "moderado",
    @SerialName("max_stake_pct") val maxStakePct: Double = 0.05,
    val sports: List<String> = listOf("tennis", "table_tennis"),
)

@Serializable
data class WsMessage(
    val type: String = "",
    val data: JsonElement? = null,
    val ts: String? = null,
)

/** Detail screen bundle. */
data class MatchDetail(
    val match: Match,
    val prediction: Prediction?,
)

enum class DataMode { LIVE, BACKEND_DEMO, OFFLINE_DEMO, CONNECTING }

enum class ConnectionState { CONNECTING, REALTIME, REST_ONLY, OFFLINE }
