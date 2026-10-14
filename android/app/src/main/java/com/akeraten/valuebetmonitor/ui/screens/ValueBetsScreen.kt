package com.akeraten.valuebetmonitor.ui.screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.akeraten.valuebetmonitor.data.Repository
import com.akeraten.valuebetmonitor.data.model.AppSettings
import com.akeraten.valuebetmonitor.data.model.ValueBet
import com.akeraten.valuebetmonitor.ui.components.ConfidenceChip
import com.akeraten.valuebetmonitor.ui.components.DisclaimerCard
import com.akeraten.valuebetmonitor.ui.components.EdgeBadge
import com.akeraten.valuebetmonitor.ui.components.EmptyState
import com.akeraten.valuebetmonitor.ui.components.GlassCard
import com.akeraten.valuebetmonitor.ui.components.LiveBadge
import com.akeraten.valuebetmonitor.ui.components.NeonChip
import com.akeraten.valuebetmonitor.ui.components.Pill
import com.akeraten.valuebetmonitor.ui.components.ProbBar
import com.akeraten.valuebetmonitor.ui.components.SuspiciousBadge
import com.akeraten.valuebetmonitor.ui.theme.Ak
import com.akeraten.valuebetmonitor.util.asFraction
import com.akeraten.valuebetmonitor.util.fmt
import com.akeraten.valuebetmonitor.util.euros
import com.akeraten.valuebetmonitor.util.pct
import com.akeraten.valuebetmonitor.util.signedPct
import com.akeraten.valuebetmonitor.util.sportEmoji
import kotlin.math.max
import kotlin.math.min

/** Recommended stake: backend value if present, otherwise fractional Kelly capped by max stake %. */
fun recommendedStake(bet: ValueBet, s: AppSettings): Double {
    bet.stake?.let { if (it > 0.0) return it }
    val p = bet.modelProb.asFraction()
    val o = bet.odds
    val kellyFull = bet.kellyFull ?: if (o > 1.0) max(0.0, (p * o - 1.0) / (o - 1.0)) else 0.0
    val raw = s.bankroll * kellyFull * s.kellyFraction
    return min(raw, s.bankroll * s.maxStakePct.asFraction())
}

fun kellyLabel(fraction: Double): String = when {
    kotlin.math.abs(fraction - 0.5) < 1e-6 -> "Half-Kelly"
    kotlin.math.abs(fraction - 0.25) < 1e-6 -> "Quarter-Kelly"
    kotlin.math.abs(fraction - 1.0) < 1e-6 -> "Kelly completo"
    else -> "Kelly ×${fraction.fmt(2)}"
}

@Composable
fun ValueBetsScreen(repository: Repository, onOpenAnalysis: (matchId: String, betKey: String) -> Unit) {
    val bets by repository.valueBets.collectAsState()
    val prefs by repository.prefs.collectAsState()
    val settings = prefs.settings

    var sport by rememberSaveable { mutableStateOf("all") }
    var confidence by rememberSaveable { mutableStateOf("all") }
    var hideSuspicious by rememberSaveable { mutableStateOf(false) }

    val filtered = remember(bets, sport, confidence, hideSuspicious) {
        bets.filter { sport == "all" || it.sport.equals(sport, true) }
            .filter { confidence == "all" || it.confidence.equals(confidence, true) }
            .filter { !hideSuspicious || !it.suspicious }
            .distinctBy { it.key }
            .sortedByDescending { it.edge.asFraction() }
    }

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item(key = "hero") { SummaryHero(filtered, settings) }
        item(key = "filters") {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Row(
                    Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    NeonChip("Todos", sport == "all", { sport = "all" })
                    NeonChip("🎾 Tenis", sport == "tennis", { sport = "tennis" })
                    NeonChip("🏓 Tenis de mesa", sport == "table_tennis", { sport = "table_tennis" }, color = Ak.Cyan)
                }
                Row(
                    Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    NeonChip("Confianza: todas", confidence == "all", { confidence = "all" }, color = Ak.Cyan)
                    NeonChip("Alta", confidence == "alta", { confidence = "alta" }, color = Ak.Green)
                    NeonChip("Media", confidence == "media", { confidence = "media" }, color = Ak.Amber)
                    NeonChip("Baja", confidence == "baja", { confidence = "baja" }, color = Ak.Orange)
                    NeonChip("Ocultar sospechosas", hideSuspicious, { hideSuspicious = !hideSuspicious }, color = Ak.Red)
                }
            }
        }
        if (filtered.isEmpty()) {
            item(key = "empty") {
                EmptyState(
                    title = "Sin value bets ahora mismo",
                    subtitle = "El modelo avisará cuando detecte un edge superior a tus umbrales.",
                    emoji = "🔎",
                )
            }
        } else {
            itemsIndexed(filtered, key = { i, b -> "vb-" + b.key.ifBlank { "idx$i" } }) { index, bet ->
                ValueBetCard(
                    rank = index + 1,
                    bet = bet,
                    settings = settings,
                    onAnalysis = { onOpenAnalysis(bet.matchId, bet.key) },
                    modifier = Modifier.animateItem(),
                )
            }
        }
        item(key = "disclaimer") { DisclaimerCard(compact = true) }
    }
}

@Composable
private fun SummaryHero(bets: List<ValueBet>, settings: AppSettings) {
    val shape = RoundedCornerShape(24.dp)
    val best = bets.maxByOrNull { it.edge.asFraction() }
    val avgEdge = if (bets.isEmpty()) null else bets.map { it.edge.asFraction() }.average()
    val totalStake = bets.sumOf { recommendedStake(it, settings) }
    Column(
        Modifier
            .fillMaxWidth()
            .background(
                Brush.linearGradient(listOf(Color(0xFF2B3A00), Color(0xFF12204A), Color(0xFF0A1024))),
                shape,
            )
            .padding(18.dp),
    ) {
        Text("Value Bets", style = MaterialTheme.typography.headlineSmall, color = Ak.TextPrimary)
        Text(
            "Priorizadas por edge · ${kellyLabel(settings.kellyFraction)} sobre ${settings.bankroll.euros()}",
            color = Ak.TextSecondary,
            style = MaterialTheme.typography.bodySmall,
        )
        Spacer(Modifier.height(14.dp))
        Row(Modifier.fillMaxWidth()) {
            HeroStat("Activas", "${bets.size}", Ak.Lime, Modifier.weight(1f))
            HeroStat("Mejor edge", best?.edge.signedPct(), Ak.Green, Modifier.weight(1f))
            HeroStat("Edge medio", avgEdge.pct(), Ak.Cyan, Modifier.weight(1f))
        }
        Spacer(Modifier.height(10.dp))
        Text(
            "Exposición sugerida total: ${totalStake.euros()}",
            color = Ak.Lime,
            style = MaterialTheme.typography.labelLarge,
        )
    }
}

@Composable
private fun HeroStat(label: String, value: String, color: Color, modifier: Modifier) {
    Column(modifier) {
        Text(label.uppercase(), color = Ak.TextSecondary, style = MaterialTheme.typography.labelSmall)
        Text(value, color = color, fontWeight = FontWeight.Black, fontSize = 22.sp, maxLines = 1)
    }
}

@Composable
fun ValueBetCard(
    rank: Int,
    bet: ValueBet,
    settings: AppSettings,
    onAnalysis: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val edgeF = bet.edge.asFraction()
    val accent = if (bet.suspicious) Ak.Red else Ak.edgeColor(edgeF)
    val sportColor = Ak.sportColor(bet.sport)
    GlassCard(modifier = modifier.fillMaxWidth(), accent = accent) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Pill("#$rank", accent, filled = true)
            Spacer(Modifier.width(6.dp))
            Text(sportEmoji(bet.sport), fontSize = 15.sp)
            Spacer(Modifier.width(4.dp))
            val category = bet.category
            if (!category.isNullOrBlank()) {
                Pill(category, sportColor)
                Spacer(Modifier.width(6.dp))
            }
            Text(
                bet.tournament,
                color = Ak.TextSecondary,
                style = MaterialTheme.typography.labelMedium,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.weight(1f),
            )
            if (bet.status.equals("live", true)) LiveBadge()
        }
        Spacer(Modifier.height(6.dp))
        Text(
            "${bet.playerA} vs ${bet.playerB}",
            color = Ak.TextPrimary,
            style = MaterialTheme.typography.titleSmall,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
        Spacer(Modifier.height(10.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(bet.market.uppercase(), color = Ak.TextMuted, style = MaterialTheme.typography.labelSmall)
                Text(
                    bet.selection,
                    color = sportColor,
                    fontWeight = FontWeight.Black,
                    fontSize = 19.sp,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            Column(horizontalAlignment = Alignment.End) {
                Text("@ ${bet.odds.fmt()}", color = Ak.TextPrimary, fontWeight = FontWeight.Black, fontSize = 24.sp)
                val bookmaker = bet.bookmaker
                if (!bookmaker.isNullOrBlank()) {
                    Text(bookmaker, color = Ak.TextMuted, style = MaterialTheme.typography.labelSmall)
                }
            }
        }
        Spacer(Modifier.height(10.dp))
        val implied = bet.impliedProb ?: if (bet.odds > 1.0) 1.0 / bet.odds else null
        ProbBar("Modelo", bet.modelProb, sportColor, labelWidth = 76.dp, barHeight = 8.dp)
        Spacer(Modifier.height(4.dp))
        ProbBar("Implícita", implied, Ak.Cyan, labelWidth = 76.dp, barHeight = 8.dp)
        Spacer(Modifier.height(10.dp))
        Row(
            horizontalArrangement = Arrangement.spacedBy(6.dp),
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.horizontalScroll(rememberScrollState()),
        ) {
            EdgeBadge(bet.edge, big = true)
            ConfidenceChip(bet.confidence)
            if (bet.suspicious) SuspiciousBadge()
        }
        Spacer(Modifier.height(10.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(
                    "STAKE ${kellyLabel(bet.kellyFraction ?: settings.kellyFraction).uppercase()}",
                    color = Ak.TextMuted,
                    style = MaterialTheme.typography.labelSmall,
                )
                Text(
                    recommendedStake(bet, settings).euros(),
                    color = Ak.Lime,
                    fontWeight = FontWeight.Black,
                    fontSize = 22.sp,
                )
            }
            OutlinedButton(
                onClick = onAnalysis,
                shape = RoundedCornerShape(14.dp),
                border = BorderStroke(1.dp, Ak.Lime),
                colors = ButtonDefaults.outlinedButtonColors(contentColor = Ak.Lime),
            ) {
                Text("Ver análisis completo", fontWeight = FontWeight.Bold)
            }
        }
        if (bet.suspicious) {
            Spacer(Modifier.height(8.dp))
            Text(
                "⚠ Edge anormalmente alto: posible error de cuota, lesión o información no reflejada. Verifica antes de apostar.",
                color = Ak.Red,
                style = MaterialTheme.typography.labelSmall,
            )
        }
    }
}
