package com.akeraten.valuebetmonitor.data.demo

import com.akeraten.valuebetmonitor.data.model.BankrollPoint
import com.akeraten.valuebetmonitor.data.model.Expert
import com.akeraten.valuebetmonitor.data.model.ExpertPick
import com.akeraten.valuebetmonitor.data.model.H2H
import com.akeraten.valuebetmonitor.data.model.Match
import com.akeraten.valuebetmonitor.data.model.ModelProbs
import com.akeraten.valuebetmonitor.data.model.Odds
import com.akeraten.valuebetmonitor.data.model.Prediction
import com.akeraten.valuebetmonitor.data.model.ProbPoint
import com.akeraten.valuebetmonitor.data.model.Score
import com.akeraten.valuebetmonitor.data.model.Stats
import com.akeraten.valuebetmonitor.data.model.ValueBet
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonArray
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt
import kotlin.random.Random

/**
 * Offline sample data so the APK is fully navigable without a backend.
 * Everything produced here is clearly labelled "MODO DEMO SIN CONEXIÓN" in the UI.
 */
object DemoData {

    private data class Seed(
        val id: String,
        val sport: String,
        val category: String,
        val a: String, val ca: String, val ra: Int,
        val b: String, val cb: String, val rb: Int,
        val tournament: String,
        val surface: String?,
        val status: String,
        val bestOf: Int,
        val oddsA: Double, val oddsB: Double,
        val modelA: Double,
        val sets: List<List<Int>>,
        val points: String?,
        val server: String?,
        val start: String,
    )

    private val seeds = listOf(
        Seed("demo-t1", "tennis", "ATP", "Carlos Alcaraz", "ES", 3, "Jannik Sinner", "IT", 1,
            "ATP 500 Viena", "Pista dura (indoor)", "live", 3, 2.10, 1.74, 0.53,
            listOf(listOf(6, 4), listOf(3, 2)), "30-15", "a", "2026-10-14T16:00:00Z"),
        Seed("demo-t2", "tennis", "WTA", "Paula Badosa", "ES", 14, "Iga Swiatek", "PL", 2,
            "WTA 500 Tokio", "Pista dura", "live", 3, 3.40, 1.33, 0.31,
            listOf(listOf(4, 6), listOf(5, 4)), "40-30", "b", "2026-10-14T15:30:00Z"),
        Seed("demo-t3", "tennis", "Challenger", "Martín Landaluce", "ES", 112, "Luca Nardi", "IT", 98,
            "Challenger Olbia", "Tierra batida", "live", 3, 1.95, 1.87, 0.55,
            listOf(listOf(2, 1)), "15-0", "a", "2026-10-14T16:20:00Z"),
        Seed("demo-tt1", "table_tennis", "WTT", "Álvaro Robles", "ES", 41, "Truls Moregard", "SE", 9,
            "WTT Champions Montpellier", null, "live", 5, 3.10, 1.38, 0.39,
            listOf(listOf(11, 8), listOf(9, 11), listOf(7, 5)), null, "a", "2026-10-14T16:10:00Z"),
        Seed("demo-tt2", "table_tennis", "ITTF", "Lin Shidong", "CN", 2, "Hugo Calderano", "BR", 4,
            "ITTF World Cup", null, "live", 5, 1.45, 2.75, 0.71,
            listOf(listOf(11, 6), listOf(11, 13), listOf(4, 3)), null, "b", "2026-10-14T16:05:00Z"),
        Seed("demo-t4", "tennis", "ATP", "Alejandro Davidovich", "ES", 24, "Holger Rune", "DK", 12,
            "ATP 500 Basilea", "Pista dura (indoor)", "upcoming", 3, 2.30, 1.62, 0.47,
            emptyList(), null, null, "2026-10-14T19:00:00Z"),
        Seed("demo-t5", "tennis", "ITF", "Jéssica Bouzas", "ES", 48, "Linda Noskova", "CZ", 27,
            "ITF W100 Les Franqueses", "Pista dura", "upcoming", 3, 2.55, 1.52, 0.42,
            emptyList(), null, null, "2026-10-15T10:30:00Z"),
        Seed("demo-tt3", "table_tennis", "WTT", "María Xiao", "ES", 38, "Mima Ito", "JP", 11,
            "WTT Star Contender Doha", null, "upcoming", 5, 3.60, 1.30, 0.30,
            emptyList(), null, null, "2026-10-14T21:15:00Z"),
        Seed("demo-t6", "tennis", "ATP", "Daniil Medvedev", "RU", 8, "Taylor Fritz", "US", 5,
            "ATP 500 Viena", "Pista dura (indoor)", "finished", 3, 2.05, 1.80, 0.50,
            listOf(listOf(7, 6), listOf(4, 6), listOf(6, 3)), null, null, "2026-10-14T11:00:00Z"),
        Seed("demo-tt4", "table_tennis", "WTT", "Wang Chuqin", "CN", 1, "Tomokazu Harimoto", "JP", 5,
            "WTT Champions Montpellier", null, "finished", 5, 1.35, 3.20, 0.74,
            listOf(listOf(11, 7), listOf(11, 9), listOf(8, 11), listOf(11, 6)), null, null, "2026-10-14T12:00:00Z"),
    )

    private fun ttGames(sets: List<List<Int>>, live: Boolean): JsonArray {
        val done = if (live) sets.dropLast(1) else sets
        return buildJsonArray {
            add(JsonPrimitive(done.count { it[0] > it[1] }))
            add(JsonPrimitive(done.count { it[1] > it[0] }))
        }
    }

    fun matches(): List<Match> = seeds.map { s ->
        val vb = if (edgeFor(s.modelA, s.oddsA) > 0.03 || edgeFor(1 - s.modelA, s.oddsB) > 0.03) 1 else 0
        Match(
            id = s.id,
            matchId = s.id,
            sport = s.sport,
            source = "demo",
            category = s.category,
            playerA = s.a,
            playerB = s.b,
            tournament = s.tournament,
            surface = s.surface,
            status = s.status,
            startTime = s.start,
            bestOf = s.bestOf,
            server = s.server,
            rankA = s.ra,
            rankB = s.rb,
            countryA = s.ca,
            countryB = s.cb,
            score = Score(
                sets = s.sets,
                games = if (s.sport == "table_tennis") ttGames(s.sets, s.status == "live") else null,
                points = s.points,
            ),
            odds = Odds(s.oddsA, s.oddsB),
            modelProbA = s.modelA,
            modelProbB = 1 - s.modelA,
            valueBetCount = vb,
            timestamp = "2026-10-14T16:30:00Z",
        )
    }

    private fun edgeFor(p: Double, odds: Double): Double = p * odds - 1.0

    fun valueBets(bankroll: Double = 1000.0, kellyFraction: Double = 0.5): List<ValueBet> {
        val out = mutableListOf<ValueBet>()
        seeds.filter { it.status != "finished" }.forEachIndexed { idx, s ->
            val candidates = listOf(
                Triple("a", s.modelA, s.oddsA),
                Triple("b", 1 - s.modelA, s.oddsB),
            )
            for ((side, p, o) in candidates) {
                val edge = edgeFor(p, o)
                if (edge <= 0.02) continue
                val kellyFull = max(0.0, (p * o - 1.0) / (o - 1.0))
                val stake = min(bankroll * kellyFull * kellyFraction, bankroll * 0.05)
                val conf = when {
                    edge > 0.12 -> "media"
                    edge > 0.06 -> "alta"
                    else -> "baja"
                }
                val name = if (side == "a") s.a else s.b
                out += ValueBet(
                    id = "vb-${s.id}-$side",
                    matchId = s.id,
                    sport = s.sport,
                    tournament = s.tournament,
                    category = s.category,
                    playerA = s.a,
                    playerB = s.b,
                    status = s.status,
                    market = "Ganador del partido",
                    selection = name,
                    selectionSide = side,
                    odds = o,
                    bookmaker = listOf("Bet365", "Pinnacle", "Betfair", "Codere")[idx % 4],
                    modelProb = p,
                    impliedProb = 1.0 / o,
                    fairProb = p,
                    edge = edge,
                    kellyFull = kellyFull,
                    kellyFraction = kellyFraction,
                    stake = (stake * 100).roundToInt() / 100.0,
                    confidence = conf,
                    confidenceScore = (0.55 + edge).coerceAtMost(0.95),
                    suspicious = edge > 0.15,
                    createdAt = "2026-10-14T16:2${idx % 10}:00Z",
                    models = ModelProbs(
                        elo = (p - 0.04).coerceIn(0.02, 0.98),
                        ml = (p + 0.02).coerceIn(0.02, 0.98),
                        monteCarlo = (p + 0.01).coerceIn(0.02, 0.98),
                        experts = if (idx % 2 == 0) (p - 0.01).coerceIn(0.02, 0.98) else null,
                        ensemble = p,
                    ),
                )
            }
        }
        return out.sortedByDescending { it.edge }
    }

    fun matchDetail(id: String, current: Match?): Match {
        val base = current ?: matches().firstOrNull { it.id == id } ?: matches().first()
        val rnd = Random(base.id.hashCode())
        val pA = base.modelProbA ?: 0.5
        val impliedA = run {
            val ia = 1.0 / (base.odds?.playerA ?: 2.0)
            val ib = 1.0 / (base.odds?.playerB ?: 2.0)
            ia / (ia + ib)
        }
        val history = (0 until 24).map { i ->
            val k = i / 23.0
            val wobble = (rnd.nextDouble() - 0.5) * 0.06
            ProbPoint(
                t = "t$i",
                modelA = (0.5 + (pA - 0.5) * k + wobble).coerceIn(0.03, 0.97),
                impliedA = (0.5 + (impliedA - 0.5) * k + wobble * 0.6).coerceIn(0.03, 0.97),
            )
        }
        val form = listOf("W", "L")
        val isTt = base.isTableTennis
        val stats = buildJsonObject {
            if (isTt) {
                put("puntos_ganados_saque", buildJsonArray { add(JsonPrimitive(58)); add(JsonPrimitive(52)) })
                put("puntos_ganados_resto", buildJsonArray { add(JsonPrimitive(46)); add(JsonPrimitive(42)) })
                put("rachas_max", buildJsonArray { add(JsonPrimitive(5)); add(JsonPrimitive(4)) })
                put("winrate_temporada", buildJsonArray { add(JsonPrimitive("64 %")); add(JsonPrimitive("71 %")) })
            } else {
                put("aces", buildJsonArray { add(JsonPrimitive(7)); add(JsonPrimitive(5)) })
                put("dobles_faltas", buildJsonArray { add(JsonPrimitive(2)); add(JsonPrimitive(3)) })
                put("primer_saque_pct", buildJsonArray { add(JsonPrimitive("64 %")); add(JsonPrimitive("61 %")) })
                put("puntos_ganados_1er_saque", buildJsonArray { add(JsonPrimitive("78 %")); add(JsonPrimitive("72 %")) })
                put("break_points", buildJsonArray { add(JsonPrimitive("2/5")); add(JsonPrimitive("1/3")) })
                put("elo_superficie", buildJsonArray { add(JsonPrimitive(2105)); add(JsonPrimitive(2140)) })
            }
            put("fuente", "demo")
        }
        return base.copy(
            h2h = H2H(
                a = 2 + rnd.nextInt(4),
                b = 1 + rnd.nextInt(4),
                last = listOf(
                    JsonPrimitive("2026 · ${base.tournament} · ${base.playerA}"),
                    JsonPrimitive("2025 · Final · ${base.playerB}"),
                    JsonPrimitive("2025 · R16 · ${base.playerA}"),
                ),
            ),
            stats = stats,
            probHistory = history,
            formA = (0 until 5).map { form[if (rnd.nextDouble() < pA) 0 else 1] },
            formB = (0 until 5).map { form[if (rnd.nextDouble() < 1 - pA) 0 else 1] },
        )
    }

    fun prediction(matchId: String, current: Match?): Prediction {
        val m = current ?: matches().firstOrNull { it.id == matchId } ?: matches().first()
        val p = m.modelProbA ?: 0.5
        val bestOf = if (m.isTableTennis) 5 else m.bestOf
        val dist = buildJsonObject {
            if (bestOf >= 5) {
                put("3-0", p * p * 0.42)
                put("3-1", p * 0.30)
                put("3-2", p * 0.22)
                put("2-3", (1 - p) * 0.22)
                put("1-3", (1 - p) * 0.30)
                put("0-3", (1 - p) * (1 - p) * 0.42)
            } else {
                put("2-0", p * 0.58)
                put("2-1", p * 0.42)
                put("1-2", (1 - p) * 0.42)
                put("0-2", (1 - p) * 0.58)
            }
        }
        return Prediction(
            matchId = m.key,
            probA = p,
            probB = 1 - p,
            breakdown = buildJsonObject {
                put("elo", buildJsonObject {
                    put("prob_a", (p - 0.04).coerceIn(0.02, 0.98))
                    put("rating_a", 2050 + (p * 200).roundToInt())
                    put("rating_b", 2100)
                })
                put("ml", buildJsonObject {
                    put("prob_a", (p + 0.02).coerceIn(0.02, 0.98))
                    put("modelo", "Gradient Boosting")
                })
                put("monte_carlo", buildJsonObject {
                    put("prob_a", (p + 0.01).coerceIn(0.02, 0.98))
                    put("iterations", 10000)
                    put("set_score_dist", dist)
                })
                put("experts", buildJsonObject {
                    put("consensus_a", (p - 0.01).coerceIn(0.02, 0.98))
                    put("n", 4)
                })
            },
            weights = buildJsonObject {
                put("elo", 0.25)
                put("ml", 0.35)
                put("monte_carlo", 0.25)
                put("experts", 0.15)
            },
            explanation = listOf(
                "El Elo ajustado por superficie favorece a ${if (p >= 0.5) m.playerA else m.playerB}.",
                "El modelo ML (forma reciente, saque/resto, fatiga) estima ${(p * 100).roundToInt()} % para ${m.playerA}.",
                "Monte Carlo (10.000 simulaciones punto a punto) confirma la tendencia.",
                "La cuota implícita del mercado difiere ${(abs(p - (1.0 / (m.odds?.playerA ?: 2.0))) * 100).roundToInt()} pp del modelo.",
                "Datos de demostración: no representan cuotas reales.",
            ),
        )
    }

    fun experts(): List<Expert> = listOf(
        Expert(
            name = "Tenis Analytics ES", sport = "tennis", platform = "X", url = "https://x.com",
            weight = 0.32, hitRate = 0.61, nPicks = 412, clv = 0.034,
            recent = listOf(
                ExpertPick("demo-t1", "Alcaraz vs Sinner", "Carlos Alcaraz", JsonPrimitive(0.62), "2026-10-14T15:00:00Z", "pending"),
                ExpertPick("demo-t6", "Medvedev vs Fritz", "Daniil Medvedev", JsonPrimitive(0.55), "2026-10-14T10:00:00Z", "win"),
                ExpertPick(null, "Rune vs Draper", "Jack Draper", JsonPrimitive(0.58), "2026-10-13T10:00:00Z", "loss"),
            ),
        ),
        Expert(
            name = "PingPong Pro Picks", sport = "table_tennis", platform = "Telegram", url = "https://telegram.org",
            weight = 0.27, hitRate = 0.66, nPicks = 958, clv = 0.041,
            recent = listOf(
                ExpertPick("demo-tt2", "Lin Shidong vs Calderano", "Lin Shidong", JsonPrimitive(0.7), "2026-10-14T15:30:00Z", "pending"),
                ExpertPick("demo-tt4", "Wang Chuqin vs Harimoto", "Wang Chuqin", JsonPrimitive(0.74), "2026-10-14T11:00:00Z", "win"),
                ExpertPick(null, "Ma Long vs Ovtcharov", "Ma Long", JsonPrimitive(0.66), "2026-10-13T19:00:00Z", "win"),
            ),
        ),
        Expert(
            name = "Court Vision", sport = "tennis", platform = "YouTube", url = "https://youtube.com",
            weight = 0.18, hitRate = 0.57, nPicks = 233, clv = 0.012,
            recent = listOf(
                ExpertPick("demo-t2", "Badosa vs Swiatek", "Iga Swiatek", JsonPrimitive(0.68), "2026-10-14T14:00:00Z", "pending"),
                ExpertPick(null, "Sabalenka vs Gauff", "Coco Gauff", JsonPrimitive(0.52), "2026-10-13T12:00:00Z", "loss"),
            ),
        ),
        Expert(
            name = "Value Hunter Blog", sport = "tennis", platform = "Blog", url = "https://example.com",
            weight = 0.12, hitRate = 0.54, nPicks = 1290, clv = -0.006,
            recent = listOf(
                ExpertPick("demo-t3", "Landaluce vs Nardi", "Martín Landaluce", JsonPrimitive(0.6), "2026-10-14T15:50:00Z", "pending"),
            ),
        ),
    )

    fun stats(startBankroll: Double = 1000.0): Stats {
        val rnd = Random(2026)
        var b = startBankroll
        val curve = (0 until 40).map { i ->
            b *= 1.0 + (rnd.nextDouble() - 0.43) * 0.04
            BankrollPoint(t = "d$i", bankroll = (b * 100).roundToInt() / 100.0)
        }
        return Stats(
            nValueBets = 184,
            avgEdge = 0.061,
            avgClv = 0.027,
            clvPositivePct = 0.64,
            roiSim = (b - startBankroll) / startBankroll,
            bankrollCurve = curve,
            bySport = buildJsonObject {
                put("tennis", buildJsonObject { put("n", 121); put("roi", 0.071) })
                put("table_tennis", buildJsonObject { put("n", 63); put("roi", 0.094) })
            },
            hitRate = 0.552,
        )
    }

    /** Advances demo live scores a little so the offline "En Vivo" feed feels alive. */
    fun tick(current: List<Match>, rnd: Random = Random.Default): List<Match> = current.map { m ->
        if (!m.isLive || rnd.nextDouble() > 0.55) return@map m
        val tt = m.isTableTennis
        val sets = m.score.sets.map { it.toMutableList() }.toMutableList()
        if (sets.isEmpty()) sets += mutableListOf(0, 0)
        val cur = sets.last()
        val aWins = rnd.nextDouble() < (m.modelProbA ?: 0.5)
        if (aWins) cur[0] = cur[0] + 1 else cur[1] = cur[1] + 1
        val target = if (tt) 11 else 6
        val top = max(cur[0], cur[1])
        val finishedSet = (top >= target && abs(cur[0] - cur[1]) >= 2) || (!tt && top >= 7)
        val points: String? = if (tt) null else listOf("0-0", "15-0", "15-15", "30-15", "30-30", "40-30", "15-30", "0-15")[rnd.nextInt(8)]
        if (finishedSet) {
            val maxSets = if (tt) 4 else 2
            if (sets.size >= maxSets + 1) {
                sets.clear(); sets += mutableListOf(0, 0)
            } else {
                sets += mutableListOf(0, 0)
            }
        }
        val drift = (rnd.nextDouble() - 0.5) * 0.04
        val newP = ((m.modelProbA ?: 0.5) + drift).coerceIn(0.05, 0.95)
        m.copy(
            score = m.score.copy(
                sets = sets.map { it.toList() },
                games = if (tt) ttGames(sets, true) else m.score.games,
                points = points,
            ),
            server = if (rnd.nextBoolean()) "a" else "b",
            modelProbA = newP,
            modelProbB = 1 - newP,
        )
    }
}
