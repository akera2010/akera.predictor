package com.akeraten.valuebetmonitor.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.akeraten.valuebetmonitor.data.Loaded
import com.akeraten.valuebetmonitor.data.Repository
import com.akeraten.valuebetmonitor.data.model.Expert
import com.akeraten.valuebetmonitor.data.model.ExpertPick
import com.akeraten.valuebetmonitor.ui.components.DisclaimerCard
import com.akeraten.valuebetmonitor.ui.components.EmptyState
import com.akeraten.valuebetmonitor.ui.components.GlassCard
import com.akeraten.valuebetmonitor.ui.components.LoadingBox
import com.akeraten.valuebetmonitor.ui.components.NeonChip
import com.akeraten.valuebetmonitor.ui.components.Pill
import com.akeraten.valuebetmonitor.ui.components.ProbBar
import com.akeraten.valuebetmonitor.ui.components.RingProgress
import com.akeraten.valuebetmonitor.ui.theme.Ak
import com.akeraten.valuebetmonitor.util.asDoubleOrNull
import com.akeraten.valuebetmonitor.util.asFraction
import com.akeraten.valuebetmonitor.util.asStringOrNull
import com.akeraten.valuebetmonitor.util.pct
import com.akeraten.valuebetmonitor.util.shortTime
import com.akeraten.valuebetmonitor.util.signedPct
import com.akeraten.valuebetmonitor.util.sportEmoji
import com.akeraten.valuebetmonitor.util.sportLabel

private data class PlatformStyle(val glyph: String, val color: Color)

private fun platformStyle(platform: String): PlatformStyle {
    val p = platform.lowercase()
    return when {
        p == "x" || p.contains("twitter") -> PlatformStyle("𝕏", Color(0xFFE7E9EA))
        p.contains("telegram") -> PlatformStyle("✈", Color(0xFF29B6F6))
        p.contains("youtube") -> PlatformStyle("▶", Color(0xFFFF1744))
        p.contains("instagram") -> PlatformStyle("◎", Color(0xFFE040FB))
        p.contains("tiktok") -> PlatformStyle("♪", Color(0xFF00F2EA))
        p.contains("discord") -> PlatformStyle("◆", Color(0xFF7C4DFF))
        p.contains("blog") || p.contains("web") -> PlatformStyle("✎", Ak.Amber)
        else -> PlatformStyle(platform.take(1).uppercase().ifBlank { "?" }, Ak.Cyan)
    }
}

@Composable
fun ExpertsScreen(repository: Repository) {
    var reloadKey by remember { mutableIntStateOf(0) }
    var state by remember { mutableStateOf<Loaded<List<Expert>>?>(null) }
    var sport by rememberSaveable { mutableStateOf("all") }
    LaunchedEffect(reloadKey) { state = repository.experts() }

    val loaded = state
    val experts = loaded?.data.orEmpty()
        .filter { sport == "all" || it.sport.equals(sport, true) }
        .sortedByDescending { it.weight }

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item(key = "header") {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text("Expertos", style = MaterialTheme.typography.headlineSmall, color = Ak.TextPrimary)
                    Text(
                        "Tipsters seguidos y su peso en el ensemble",
                        color = Ak.TextSecondary,
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
                if (loaded?.demo == true) Pill("DEMO", Ak.Orange, filled = true)
                IconButton(onClick = { reloadKey += 1 }) {
                    Icon(Icons.Filled.Refresh, contentDescription = "Actualizar", tint = Ak.Lime)
                }
            }
        }
        item(key = "filters") {
            Row(
                Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                NeonChip("Todos", sport == "all", { sport = "all" })
                NeonChip("🎾 Tenis", sport == "tennis", { sport = "tennis" })
                NeonChip("🏓 Tenis de mesa", sport == "table_tennis", { sport = "table_tennis" }, color = Ak.Cyan)
            }
        }
        when {
            loaded == null -> item(key = "loading") { LoadingBox(text = "Cargando expertos…") }
            experts.isEmpty() -> item(key = "empty") {
                EmptyState("Sin expertos", "No hay expertos para este filtro.", emoji = "🧠")
            }
            else -> itemsIndexed(experts, key = { i, e -> "ex-$i-${e.name}" }) { _, e ->
                ExpertCard(e)
            }
        }
        item(key = "disclaimer") { DisclaimerCard(compact = true) }
    }
}

@Composable
private fun ExpertCard(expert: Expert) {
    val uriHandler = LocalUriHandler.current
    val sportColor = Ak.sportColor(expert.sport)
    val hit = expert.hitRate.asFraction()
    val ringColor = when {
        hit >= 0.6 -> Ak.Green
        hit >= 0.53 -> Ak.Lime
        else -> Ak.Amber
    }
    val style = platformStyle(expert.platform)
    GlassCard(accent = sportColor) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            RingProgress(progress = hit.toFloat(), color = ringColor, ringSize = 74.dp, strokeWidth = 8.dp) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text("${(hit * 100).toInt()}%", color = Ak.TextPrimary, fontWeight = FontWeight.Black, fontSize = 17.sp)
                    Text("ACIERTO", color = Ak.TextSecondary, fontSize = 8.sp, fontWeight = FontWeight.Bold)
                }
            }
            Spacer(Modifier.width(14.dp))
            Column(Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        Modifier
                            .size(26.dp)
                            .clip(RoundedCornerShape(8.dp))
                            .background(style.color.copy(alpha = 0.18f))
                            .border(1.dp, style.color, RoundedCornerShape(8.dp)),
                        contentAlignment = Alignment.Center,
                    ) {
                        Text(style.glyph, color = style.color, fontSize = 13.sp, fontWeight = FontWeight.Black)
                    }
                    Spacer(Modifier.width(8.dp))
                    Text(
                        expert.name,
                        color = Ak.TextPrimary,
                        style = MaterialTheme.typography.titleMedium,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                Spacer(Modifier.height(4.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    Pill("${sportEmoji(expert.sport)} ${sportLabel(expert.sport)}", sportColor)
                    Pill(expert.platform.ifBlank { "Web" }, style.color)
                }
                Spacer(Modifier.height(6.dp))
                Text(
                    "${expert.nPicks} picks · CLV ${expert.clv.signedPct()}",
                    color = if ((expert.clv ?: 0.0) >= 0) Ak.Green else Ak.Red,
                    style = MaterialTheme.typography.labelMedium,
                )
            }
        }
        Spacer(Modifier.height(10.dp))
        ProbBar("Peso", expert.weight, Ak.Violet, labelWidth = 54.dp, barHeight = 8.dp, valueText = expert.weight.pct(0))
        val url = expert.url
        if (!url.isNullOrBlank()) {
            Text(
                "Abrir perfil ↗",
                color = Ak.Cyan,
                style = MaterialTheme.typography.labelMedium,
                modifier = Modifier
                    .padding(top = 6.dp)
                    .clickable { runCatching { uriHandler.openUri(url) } },
            )
        }
        if (expert.recent.isNotEmpty()) {
            Spacer(Modifier.height(10.dp))
            Text("PICKS RECIENTES", color = Ak.TextMuted, style = MaterialTheme.typography.labelSmall)
            Spacer(Modifier.height(4.dp))
            expert.recent.take(5).forEach { PickRow(it) }
        }
    }
}

@Composable
private fun PickRow(pick: ExpertPick) {
    val (label, color) = when (pick.result.lowercase()) {
        "win", "won", "acierto" -> "ACIERTO" to Ak.Green
        "loss", "lost", "fallo" -> "FALLO" to Ak.Red
        else -> "PENDIENTE" to Ak.Amber
    }
    val conf = pick.confidence.asDoubleOrNull()
    val confText = when {
        conf != null -> conf.pct(0)
        else -> pick.confidence.asStringOrNull()
    }
    Row(
        Modifier
            .fillMaxWidth()
            .padding(vertical = 5.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f)) {
            Text(pick.match, color = Ak.TextPrimary, style = MaterialTheme.typography.bodySmall, maxLines = 1, overflow = TextOverflow.Ellipsis)
            Text(
                listOfNotNull(
                    "→ ${pick.predictedWinner}",
                    confText?.let { "conf. $it" },
                    shortTime(pick.timestamp).ifBlank { null },
                ).joinToString(" · "),
                color = Ak.TextSecondary,
                style = MaterialTheme.typography.labelSmall,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
        Spacer(Modifier.width(8.dp))
        Pill(label, color, filled = label != "PENDIENTE")
    }
}
