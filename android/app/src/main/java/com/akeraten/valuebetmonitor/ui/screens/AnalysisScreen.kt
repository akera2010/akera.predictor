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
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
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
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.akeraten.valuebetmonitor.data.Loaded
import com.akeraten.valuebetmonitor.data.Repository
import com.akeraten.valuebetmonitor.data.model.Prediction
import com.akeraten.valuebetmonitor.ui.components.ConfidenceChip
import com.akeraten.valuebetmonitor.ui.components.DisclaimerCard
import com.akeraten.valuebetmonitor.ui.components.DistributionBars
import com.akeraten.valuebetmonitor.ui.components.EdgeBadge
import com.akeraten.valuebetmonitor.ui.components.GlassCard
import com.akeraten.valuebetmonitor.ui.components.LoadingBox
import com.akeraten.valuebetmonitor.ui.components.ModelBar
import com.akeraten.valuebetmonitor.ui.components.Pill
import com.akeraten.valuebetmonitor.ui.components.RingProgress
import com.akeraten.valuebetmonitor.ui.components.SectionTitle
import com.akeraten.valuebetmonitor.ui.components.SuspiciousBadge
import com.akeraten.valuebetmonitor.ui.theme.Ak
import com.akeraten.valuebetmonitor.util.asFraction
import com.akeraten.valuebetmonitor.util.fmt
import com.akeraten.valuebetmonitor.util.euros
import com.akeraten.valuebetmonitor.util.pct
import com.akeraten.valuebetmonitor.util.signedPct

@Composable
fun AnalysisScreen(
    repository: Repository,
    matchId: String,
    betKey: String?,
    onBack: () -> Unit,
) {
    val bets by repository.valueBets.collectAsState()
    val matches by repository.matches.collectAsState()
    val prefs by repository.prefs.collectAsState()
    var prediction by remember(matchId) { mutableStateOf<Loaded<Prediction>?>(null) }
    LaunchedEffect(matchId) { prediction = repository.prediction(matchId) }

    val bet = betKey?.let { k -> bets.firstOrNull { it.key == k } }
    val match = matches.firstOrNull { it.key == matchId || it.matchId == matchId }
    val playerA = bet?.playerA ?: match?.playerA ?: "Jugador A"
    val playerB = bet?.playerB ?: match?.playerB ?: "Jugador B"
    val sideB = when {
        bet == null -> false
        bet.selectionSide != null -> bet.selectionSide.equals("b", ignoreCase = true)
        else -> bet.selection == playerB
    }
    val selection = bet?.selection ?: if (sideB) playerB else playerA
    val sport = bet?.sport ?: match?.sport ?: "tennis"
    val accent = Ak.sportColor(sport)

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
                "Análisis completo",
                style = MaterialTheme.typography.titleLarge,
                color = Ak.TextPrimary,
                modifier = Modifier.weight(1f),
            )
            if (prediction?.demo == true) Pill("DEMO", Ak.Orange, filled = true)
        }

        val loaded = prediction
        if (loaded == null) {
            LoadingBox(text = "Calculando modelos…")
        } else {
            val pred = loaded.data
            val entries = modelEntries(pred, bet, sideB)
            val ensemble = entries.last().prob

            // ---- hero
            val shape = RoundedCornerShape(24.dp)
            Column(
                Modifier
                    .fillMaxWidth()
                    .background(
                        Brush.linearGradient(listOf(accent.copy(alpha = 0.25f), Color(0xFF111B3D), Color(0xFF0A1024))),
                        shape,
                    )
                    .padding(18.dp),
            ) {
                Text("$playerA vs $playerB", color = Ak.TextSecondary, style = MaterialTheme.typography.labelMedium, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Spacer(Modifier.height(4.dp))
                Text(
                    "Selección: $selection",
                    color = accent,
                    fontWeight = FontWeight.Black,
                    fontSize = 20.sp,
                    maxLines = 2,
                )
                if (bet != null) {
                    Text(bet.market, color = Ak.TextMuted, style = MaterialTheme.typography.labelSmall)
                }
                Spacer(Modifier.height(14.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    RingProgress(
                        progress = (ensemble ?: 0.0).toFloat(),
                        color = accent,
                        ringSize = 104.dp,
                        strokeWidth = 11.dp,
                    ) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Text(ensemble.pct(0), color = Ak.TextPrimary, fontWeight = FontWeight.Black, fontSize = 22.sp)
                            Text("ENSEMBLE", color = Ak.TextSecondary, fontSize = 9.sp, fontWeight = FontWeight.Bold)
                        }
                    }
                    Spacer(Modifier.width(16.dp))
                    Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        if (bet != null) {
                            KeyValue("Cuota", bet.odds.fmt(), Ak.TextPrimary)
                            KeyValue("Prob. implícita", (bet.impliedProb ?: if (bet.odds > 1) 1 / bet.odds else null).pct(), Ak.Cyan)
                            KeyValue("Prob. justa", bet.fairProb.pct(), Ak.Violet)
                            EdgeBadge(bet.edge, big = true)
                        } else {
                            KeyValue("Prob. $playerA", pred.probA.pct(), accent)
                            KeyValue("Prob. $playerB", pred.probB.pct(), Ak.Magenta)
                        }
                    }
                }
                if (bet != null) {
                    Spacer(Modifier.height(10.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        ConfidenceChip(bet.confidence)
                        if (bet.suspicious) SuspiciousBadge()
                    }
                }
            }

            // ---- model breakdown
            GlassCard(accent = Ak.Violet) {
                SectionTitle("Desglose de modelos", accent = Ak.Violet)
                Text(
                    "Probabilidad estimada para «$selection» según cada modelo",
                    color = Ak.TextMuted,
                    style = MaterialTheme.typography.labelSmall,
                )
                Spacer(Modifier.height(8.dp))
                entries.forEach { e ->
                    val note = buildString {
                        append(e.note ?: "")
                        if (e.weight != null) append(" · peso ${e.weight.pct(0)}")
                    }
                    ModelBar(name = e.name, value = e.prob, color = e.color, note = note.ifBlank { null })
                }
                val implied = bet?.impliedProb ?: bet?.let { if (it.odds > 1) 1 / it.odds else null }
                if (implied != null) {
                    ModelBar(name = "Mercado", value = implied, color = Ak.TextSecondary, note = "Probabilidad implícita en la cuota")
                }
            }

            // ---- Kelly
            if (bet != null) {
                val s = prefs.settings
                GlassCard(accent = Ak.Lime) {
                    SectionTitle("Gestión de stake (Kelly)", accent = Ak.Lime)
                    val kellyFull = bet.kellyFull ?: run {
                        val p = bet.modelProb.asFraction()
                        if (bet.odds > 1) ((p * bet.odds - 1) / (bet.odds - 1)).coerceAtLeast(0.0) else 0.0
                    }
                    KeyValue("Edge", bet.edge.signedPct(), Ak.edgeColor(bet.edge.asFraction()))
                    KeyValue("Kelly completo", kellyFull.pct(), Ak.TextPrimary)
                    KeyValue("Fracción aplicada", kellyLabel(bet.kellyFraction ?: s.kellyFraction), Ak.Cyan)
                    KeyValue("Límite por apuesta", s.maxStakePct.pct(), Ak.Amber)
                    Spacer(Modifier.height(6.dp))
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("Stake recomendado", color = Ak.TextSecondary, modifier = Modifier.weight(1f))
                        Text(recommendedStake(bet, s).euros(), color = Ak.Lime, fontWeight = FontWeight.Black, fontSize = 24.sp)
                    }
                }
            }

            // ---- Monte Carlo
            val dist = setScoreDistribution(pred)
            if (dist.isNotEmpty()) {
                GlassCard(accent = Ak.Orange) {
                    SectionTitle("Monte Carlo · marcadores", accent = Ak.Orange)
                    Spacer(Modifier.height(10.dp))
                    DistributionBars(entries = dist, colorFor = { if (isScoreForA(it)) accent else Ak.Magenta })
                    Spacer(Modifier.height(6.dp))
                    Text("Marcador en sets: $playerA – $playerB", color = Ak.TextMuted, style = MaterialTheme.typography.labelSmall)
                }
            }

            // ---- Explanation
            if (pred.explanation.isNotEmpty()) {
                GlassCard(accent = Ak.Cyan) {
                    SectionTitle("¿Por qué?", accent = Ak.Cyan)
                    pred.explanation.forEach { line ->
                        Row(Modifier.padding(vertical = 4.dp)) {
                            Box(
                                Modifier
                                    .padding(top = 7.dp)
                                    .size(6.dp)
                                    .background(Ak.Cyan, CircleShape),
                            )
                            Spacer(Modifier.width(10.dp))
                            Text(line, color = Ak.TextPrimary, style = MaterialTheme.typography.bodyMedium)
                        }
                    }
                }
            }
        }

        DisclaimerCard()
        Spacer(Modifier.height(16.dp))
    }
}

@Composable
private fun KeyValue(key: String, value: String, color: Color) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Text(key, color = Ak.TextSecondary, style = MaterialTheme.typography.labelMedium, modifier = Modifier.weight(1f))
        Text(value, color = color, fontWeight = FontWeight.Bold)
    }
}
