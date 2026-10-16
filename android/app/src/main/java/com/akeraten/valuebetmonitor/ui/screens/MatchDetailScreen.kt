package com.akeraten.valuebetmonitor.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.akeraten.valuebetmonitor.data.Loaded
import com.akeraten.valuebetmonitor.data.Repository
import com.akeraten.valuebetmonitor.data.model.Match
import com.akeraten.valuebetmonitor.data.model.Prediction
import com.akeraten.valuebetmonitor.ui.components.ChartLegend
import com.akeraten.valuebetmonitor.ui.components.ChartSeries
import com.akeraten.valuebetmonitor.ui.components.DistributionBars
import com.akeraten.valuebetmonitor.ui.components.EdgeBadge
import com.akeraten.valuebetmonitor.ui.components.FormChips
import com.akeraten.valuebetmonitor.ui.components.GlassCard
import com.akeraten.valuebetmonitor.ui.components.LineChart
import com.akeraten.valuebetmonitor.ui.components.LiveBadge
import com.akeraten.valuebetmonitor.ui.components.LoadingBox
import com.akeraten.valuebetmonitor.ui.components.Pill
import com.akeraten.valuebetmonitor.ui.components.PlayerScoreRow
import com.akeraten.valuebetmonitor.ui.components.SectionTitle
import com.akeraten.valuebetmonitor.ui.components.SplitBar
import com.akeraten.valuebetmonitor.ui.components.statusLabel
import com.akeraten.valuebetmonitor.ui.components.ttGamesWon
import com.akeraten.valuebetmonitor.ui.theme.Ak
import com.akeraten.valuebetmonitor.util.asFraction
import com.akeraten.valuebetmonitor.util.fmt
import com.akeraten.valuebetmonitor.util.displayText
import com.akeraten.valuebetmonitor.util.fairImpliedA
import com.akeraten.valuebetmonitor.util.impliedFromOdds
import com.akeraten.valuebetmonitor.util.pct
import com.akeraten.valuebetmonitor.util.prettyKey
import com.akeraten.valuebetmonitor.util.shortTime
import com.akeraten.valuebetmonitor.util.sportEmoji
import com.akeraten.valuebetmonitor.util.sportLabel
import kotlinx.coroutines.launch
import kotlinx.serialization.json.JsonArray

@Composable
fun MatchDetailScreen(
    repository: Repository,
    matchId: String,
    onBack: () -> Unit,
    onOpenAnalysis: (String) -> Unit,
) {
    val liveMatches by repository.matches.collectAsState()
    var detail by remember(matchId) { mutableStateOf<Loaded<Match>?>(null) }
    var prediction by remember(matchId) { mutableStateOf<Loaded<Prediction>?>(null) }

    LaunchedEffect(matchId) {
        launch { detail = repository.matchDetail(matchId) }
        launch { prediction = repository.prediction(matchId) }
    }

    val loaded = detail
    val live = liveMatches.firstOrNull { it.key == matchId }
    val match: Match? = when {
        loaded == null -> live
        live == null -> loaded.data
        else -> loaded.data.copy(
            status = live.status,
            score = live.score,
            server = live.server,
            odds = live.odds ?: loaded.data.odds,
            modelProbA = live.modelProbA ?: loaded.data.modelProbA,
            modelProbB = live.modelProbB ?: loaded.data.modelProbB,
        )
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 16.dp, vertical = 8.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onBack) {
                Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Volver", tint = Ak.TextPrimary)
            }
            Text(
                "Detalle de partido",
                style = MaterialTheme.typography.titleLarge,
                color = Ak.TextPrimary,
                modifier = Modifier.weight(1f),
            )
            if (loaded?.demo == true) Pill("DEMO", Ak.Orange, filled = true)
        }

        if (match == null) {
            LoadingBox(text = "Cargando partido…")
        } else {
            DetailBody(match, prediction?.data, onOpenAnalysis)
        }
    }
}

@Composable
private fun DetailBody(match: Match, pred: Prediction?, onOpenAnalysis: (String) -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Scoreboard(match)
        ProbabilityCard(match)
        OddsVsModelCard(match)

        val dist = setScoreDistribution(pred)
        if (dist.isNotEmpty()) {
            GlassCard(accent = Ak.Orange) {
                SectionTitle("Monte Carlo · distribución de sets", accent = Ak.Orange)
                val iters = monteCarloIterations(pred)
                if (iters != null) {
                    Text("$iters simulaciones", color = Ak.TextMuted, style = MaterialTheme.typography.labelSmall)
                }
                Spacer(Modifier.height(12.dp))
                val accent = Ak.sportColor(match.sport)
                DistributionBars(
                    entries = dist,
                    colorFor = { if (isScoreForA(it)) accent else Ak.Magenta },
                )
                Spacer(Modifier.height(8.dp))
                Row {
                    Text("■ ${match.playerA}", color = accent, style = MaterialTheme.typography.labelSmall, modifier = Modifier.weight(1f), maxLines = 1, overflow = TextOverflow.Ellipsis)
                    Text("■ ${match.playerB}", color = Ak.Magenta, style = MaterialTheme.typography.labelSmall, modifier = Modifier.weight(1f), maxLines = 1, overflow = TextOverflow.Ellipsis, textAlign = TextAlign.End)
                }
            }
        }

        H2HCard(match)
        FormCard(match)
        StatsCard(match)

        Button(
            onClick = { onOpenAnalysis(match.key) },
            modifier = Modifier
                .fillMaxWidth()
                .height(52.dp),
            shape = RoundedCornerShape(16.dp),
            colors = ButtonDefaults.buttonColors(containerColor = Ak.Lime, contentColor = Color(0xFF0B1200)),
        ) {
            Text("Ver análisis completo del modelo", fontWeight = FontWeight.Black)
        }
        Spacer(Modifier.height(16.dp))
    }
}

@Composable
private fun Scoreboard(match: Match) {
    val accent = Ak.sportColor(match.sport)
    val shape = RoundedCornerShape(24.dp)
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(
                Brush.linearGradient(
                    listOf(accent.copy(alpha = 0.22f), Color(0xFF101A3A), Color(0xFF0A1024)),
                ),
                shape,
            )
            .padding(16.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(sportEmoji(match.sport) + " " + sportLabel(match.sport), color = accent, style = MaterialTheme.typography.labelLarge)
            Spacer(Modifier.width(8.dp))
            val category = match.category
            if (!category.isNullOrBlank()) Pill(category, accent)
            Spacer(Modifier.weight(1f))
            if (match.isLive) LiveBadge() else Pill(statusLabel(match.status), Ak.TextSecondary)
        }
        Spacer(Modifier.height(6.dp))
        Text(match.tournament, color = Ak.TextPrimary, style = MaterialTheme.typography.titleMedium)
        Text(
            listOfNotNull(match.surface, "Mejor de ${match.bestOf}", shortTime(match.startTime).ifBlank { null })
                .joinToString(" · "),
            color = Ak.TextSecondary,
            style = MaterialTheme.typography.labelMedium,
        )
        Spacer(Modifier.height(14.dp))
        val sets = match.score.sets
        val points = match.score.points?.split("-", ":")?.map { it.trim() }
        val (gamesA, gamesB) = ttGamesWon(match)
        PlayerScoreRow(
            name = match.playerA,
            country = match.countryA,
            rank = match.rankA,
            serving = match.isLive && match.server.equals("a", true),
            setScores = sets.map { it.getOrNull(0) },
            opponentScores = sets.map { it.getOrNull(1) },
            points = if (match.isLive) points?.getOrNull(0) else null,
            live = match.isLive,
            accent = accent,
            gamesWon = gamesA,
        )
        Spacer(Modifier.height(8.dp))
        PlayerScoreRow(
            name = match.playerB,
            country = match.countryB,
            rank = match.rankB,
            serving = match.isLive && match.server.equals("b", true),
            setScores = sets.map { it.getOrNull(1) },
            opponentScores = sets.map { it.getOrNull(0) },
            points = if (match.isLive) points?.getOrNull(1) else null,
            live = match.isLive,
            accent = accent,
            gamesWon = gamesB,
        )
    }
}

@Composable
private fun ProbabilityCard(match: Match) {
    val accent = Ak.sportColor(match.sport)
    val implied = fairImpliedA(match.odds?.playerA, match.odds?.playerB)
    GlassCard(accent = accent) {
        SectionTitle("Probabilidad: modelo vs mercado", accent = accent)
        Row(Modifier.fillMaxWidth()) {
            Column(Modifier.weight(1f)) {
                Text("MODELO", color = Ak.TextSecondary, style = MaterialTheme.typography.labelSmall)
                Text(match.modelProbA.pct(), color = accent, fontWeight = FontWeight.Black, fontSize = 26.sp)
                Text(match.playerA, color = Ak.TextMuted, style = MaterialTheme.typography.labelSmall, maxLines = 1, overflow = TextOverflow.Ellipsis)
            }
            Column(Modifier.weight(1f), horizontalAlignment = Alignment.End) {
                Text("MERCADO (sin margen)", color = Ak.TextSecondary, style = MaterialTheme.typography.labelSmall)
                Text(implied.pct(), color = Ak.Cyan, fontWeight = FontWeight.Black, fontSize = 26.sp)
                val modelA = match.modelProbA
                val diff = if (modelA != null && implied != null) modelA.asFraction() - implied else null
                Text(
                    if (diff != null) "Diferencia ${if (diff >= 0) "+" else ""}${(diff * 100).fmt(1)} pp" else "—",
                    color = if ((diff ?: 0.0) > 0) Ak.Green else Ak.TextMuted,
                    style = MaterialTheme.typography.labelSmall,
                )
            }
        }
        Spacer(Modifier.height(12.dp))
        val history = match.probHistory
        if (history.size >= 2) {
            val series = buildList {
                add(ChartSeries("Modelo", carryForward(history.map { it.modelA }), accent, fill = true))
                if (history.any { it.impliedA != null }) {
                    add(ChartSeries("Implícita", carryForward(history.map { it.impliedA }), Ak.Cyan, dashed = true))
                }
            }
            LineChart(
                series = series,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(170.dp),
                yMin = 0f,
                yMax = 1f,
                referenceY = 0.5f,
            )
            Spacer(Modifier.height(8.dp))
            ChartLegend(series)
            Text(
                "Probabilidad de ${match.playerA} a lo largo del partido (línea discontinua = 50 %)",
                color = Ak.TextMuted,
                style = MaterialTheme.typography.labelSmall,
            )
        } else {
            Text("Sin historial de probabilidades todavía.", color = Ak.TextMuted, style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable
private fun OddsVsModelCard(match: Match) {
    val accent = Ak.sportColor(match.sport)
    GlassCard(accent = Ak.Cyan) {
        SectionTitle("Cuotas vs modelo", accent = Ak.Cyan)
        Row(Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
            HeaderCell("Jugador", Modifier.weight(1.6f))
            HeaderCell("Cuota", Modifier.weight(0.8f))
            HeaderCell("Impl.", Modifier.weight(0.8f))
            HeaderCell("Modelo", Modifier.weight(0.9f))
        }
        val rows = listOf(
            Triple(match.playerA, match.odds?.playerA, match.modelProbA),
            Triple(match.playerB, match.odds?.playerB, match.modelProbB ?: match.modelProbA?.let { 1 - it.asFraction() }),
        )
        rows.forEach { (name, odds, model) ->
            Row(Modifier.fillMaxWidth().padding(vertical = 6.dp), verticalAlignment = Alignment.CenterVertically) {
                Text(name, color = Ak.TextPrimary, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.weight(1.6f), maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text(odds.fmt(), color = Ak.TextPrimary, fontWeight = FontWeight.Bold, modifier = Modifier.weight(0.8f))
                Text(impliedFromOdds(odds).pct(0), color = Ak.Cyan, modifier = Modifier.weight(0.8f))
                Text(model.pct(0), color = accent, fontWeight = FontWeight.Bold, modifier = Modifier.weight(0.9f))
            }
            val edge = if (odds != null && model != null) model.asFraction() * odds - 1.0 else null
            if (edge != null && edge > 0.0) {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                    EdgeBadge(edge)
                }
            }
        }
    }
}

@Composable
private fun HeaderCell(text: String, modifier: Modifier) {
    Text(text.uppercase(), color = Ak.TextMuted, style = MaterialTheme.typography.labelSmall, modifier = modifier)
}

@Composable
private fun H2HCard(match: Match) {
    val h2h = match.h2h ?: return
    val accent = Ak.sportColor(match.sport)
    GlassCard(accent = Ak.Violet) {
        SectionTitle("Head to Head", accent = Ak.Violet)
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Text(match.playerA, color = Ak.TextSecondary, modifier = Modifier.weight(1f), maxLines = 1, overflow = TextOverflow.Ellipsis)
            Text("${h2h.a}", color = accent, fontWeight = FontWeight.Black, fontSize = 30.sp)
            Text("  –  ", color = Ak.TextMuted, fontSize = 22.sp)
            Text("${h2h.b}", color = Ak.Magenta, fontWeight = FontWeight.Black, fontSize = 30.sp)
            Text(match.playerB, color = Ak.TextSecondary, modifier = Modifier.weight(1f), maxLines = 1, overflow = TextOverflow.Ellipsis, textAlign = TextAlign.End)
        }
        Spacer(Modifier.height(8.dp))
        val total = h2h.a + h2h.b
        SplitBar(if (total > 0) h2h.a.toDouble() / total else 0.5, accent, Ak.Magenta)
        if (h2h.last.isNotEmpty()) {
            Spacer(Modifier.height(10.dp))
            Text("Últimos enfrentamientos", color = Ak.TextSecondary, style = MaterialTheme.typography.labelMedium)
            h2h.last.take(5).forEach { item ->
                Text("• " + item.displayText(), color = Ak.TextPrimary, style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

@Composable
private fun FormCard(match: Match) {
    if (match.formA.isEmpty() && match.formB.isEmpty()) return
    GlassCard(accent = Ak.Green) {
        SectionTitle("Forma reciente", accent = Ak.Green)
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Text(match.playerA, color = Ak.TextPrimary, modifier = Modifier.weight(1f), maxLines = 1, overflow = TextOverflow.Ellipsis)
            FormChips(match.formA)
        }
        Spacer(Modifier.height(8.dp))
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Text(match.playerB, color = Ak.TextPrimary, modifier = Modifier.weight(1f), maxLines = 1, overflow = TextOverflow.Ellipsis)
            FormChips(match.formB)
        }
    }
}

@Composable
private fun StatsCard(match: Match) {
    val stats = match.stats ?: return
    if (stats.isEmpty()) return
    val accent = Ak.sportColor(match.sport)
    GlassCard(accent = accent) {
        SectionTitle("Estadísticas", accent = accent)
        stats.entries.forEach { (key, value) ->
            if (value is JsonArray && value.size == 2) {
                Row(Modifier.fillMaxWidth().padding(vertical = 5.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text(value[0].displayText(), color = accent, fontWeight = FontWeight.Bold, modifier = Modifier.weight(1f))
                    Text(
                        prettyKey(key),
                        color = Ak.TextSecondary,
                        style = MaterialTheme.typography.labelMedium,
                        textAlign = TextAlign.Center,
                        modifier = Modifier.weight(2f),
                    )
                    Text(value[1].displayText(), color = Ak.Magenta, fontWeight = FontWeight.Bold, modifier = Modifier.weight(1f), textAlign = TextAlign.End)
                }
            } else {
                Row(Modifier.fillMaxWidth().padding(vertical = 5.dp)) {
                    Text(prettyKey(key), color = Ak.TextSecondary, style = MaterialTheme.typography.labelMedium, modifier = Modifier.weight(1f))
                    Box(Modifier.weight(1f), contentAlignment = Alignment.CenterEnd) {
                        Text(value.displayText(), color = Ak.TextPrimary, style = MaterialTheme.typography.bodySmall, textAlign = TextAlign.End)
                    }
                }
            }
        }
    }
}

/** Replaces null points with the previous known value (first known value for leading nulls). */
private fun carryForward(values: List<Double?>): List<Float> {
    val firstKnown = values.firstOrNull { it != null } ?: 0.5
    var last = firstKnown
    return values.map { v ->
        if (v != null) last = v
        last.asFraction().toFloat()
    }
}
