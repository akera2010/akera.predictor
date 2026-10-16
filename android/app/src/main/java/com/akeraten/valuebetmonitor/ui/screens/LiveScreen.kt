package com.akeraten.valuebetmonitor.ui.screens

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.akeraten.valuebetmonitor.data.Repository
import com.akeraten.valuebetmonitor.data.model.Match
import com.akeraten.valuebetmonitor.ui.components.DisclaimerCard
import com.akeraten.valuebetmonitor.ui.components.EmptyState
import com.akeraten.valuebetmonitor.ui.components.MatchCard
import com.akeraten.valuebetmonitor.ui.components.NeonChip
import com.akeraten.valuebetmonitor.ui.components.Pill
import com.akeraten.valuebetmonitor.ui.components.akFieldColors
import com.akeraten.valuebetmonitor.ui.theme.Ak
import kotlinx.coroutines.launch

private fun statusMatches(m: Match, status: String): Boolean = when (status) {
    "all" -> true
    "live" -> m.isLive
    "upcoming" -> m.status.equals("upcoming", true) || m.status.equals("scheduled", true)
    "finished" -> m.status.equals("finished", true) || m.status.equals("ended", true)
    else -> true
}

@Composable
fun LiveScreen(repository: Repository, onOpenMatch: (String) -> Unit) {
    val matches by repository.matches.collectAsState()
    val refreshing by repository.refreshing.collectAsState()
    val valueBets by repository.valueBets.collectAsState()
    val scope = rememberCoroutineScope()

    var sport by rememberSaveable { mutableStateOf("all") }
    var status by rememberSaveable { mutableStateOf("live") }
    var query by rememberSaveable { mutableStateOf("") }

    val filtered = remember(matches, sport, status, query) {
        val q = query.trim().lowercase()
        matches
            .asSequence()
            .filter { sport == "all" || it.sport.equals(sport, true) }
            .filter { statusMatches(it, status) }
            .filter {
                q.isEmpty() ||
                    it.tournament.lowercase().contains(q) ||
                    it.playerA.lowercase().contains(q) ||
                    it.playerB.lowercase().contains(q) ||
                    (it.category?.lowercase()?.contains(q) == true)
            }
            .distinctBy { it.key }
            .sortedWith(compareByDescending<Match> { it.isLive }.thenByDescending { it.valueBetCount })
            .toList()
    }
    val liveCount = matches.count { it.isLive }

    val transition = rememberInfiniteTransition(label = "refresh")
    val spin by transition.animateFloat(
        initialValue = 0f,
        targetValue = 360f,
        animationSpec = infiniteRepeatable(tween(900, easing = LinearEasing), RepeatMode.Restart),
        label = "spin",
    )

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item(key = "header") {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text("En Vivo", style = MaterialTheme.typography.headlineSmall, color = Ak.TextPrimary)
                    Text(
                        "$liveCount partidos en directo · ${valueBets.size} value bets",
                        color = Ak.TextSecondary,
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
                IconButton(onClick = { scope.launch { repository.refresh() } }) {
                    Icon(
                        Icons.Filled.Refresh,
                        contentDescription = "Actualizar",
                        tint = Ak.Lime,
                        modifier = Modifier.rotate(if (refreshing) spin else 0f),
                    )
                }
            }
        }
        item(key = "sport_filters") {
            Row(
                Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                NeonChip("Todos", sport == "all", { sport = "all" })
                NeonChip("🎾 Tenis", sport == "tennis", { sport = "tennis" }, color = Ak.Lime)
                NeonChip("🏓 Tenis de mesa", sport == "table_tennis", { sport = "table_tennis" }, color = Ak.Cyan)
            }
        }
        item(key = "status_filters") {
            Row(
                Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                NeonChip("● En vivo", status == "live", { status = "live" }, color = Ak.Red)
                NeonChip("Próximos", status == "upcoming", { status = "upcoming" }, color = Ak.Orange)
                NeonChip("Finalizados", status == "finished", { status = "finished" }, color = Ak.Violet)
                NeonChip("Todos", status == "all", { status = "all" }, color = Ak.Cyan)
            }
        }
        item(key = "search") {
            OutlinedTextField(
                value = query,
                onValueChange = { query = it },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                placeholder = { Text("Buscar torneo, jugador o categoría") },
                leadingIcon = { Icon(Icons.Filled.Search, contentDescription = null) },
                shape = MaterialTheme.shapes.large,
                colors = akFieldColors(),
            )
        }
        if (filtered.isEmpty()) {
            item(key = "empty") {
                EmptyState(
                    title = if (matches.isEmpty()) "Conectando con el backend…" else "Sin partidos para este filtro",
                    subtitle = if (matches.isEmpty()) {
                        "Si no hay conexión se cargará el modo demo automáticamente."
                    } else {
                        "Prueba con otro estado, deporte o búsqueda."
                    },
                )
            }
        } else {
            item(key = "count") {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Pill("${filtered.size} PARTIDOS", Ak.Lime)
                    Spacer(Modifier.width(8.dp))
                    Text(
                        "Toca un partido para ver el análisis",
                        color = Ak.TextMuted,
                        style = MaterialTheme.typography.labelSmall,
                        fontWeight = FontWeight.Medium,
                    )
                }
            }
            itemsIndexed(filtered, key = { i, m -> "m-" + m.key.ifBlank { "idx$i" } }) { _, m ->
                MatchCard(
                    match = m,
                    onClick = { onOpenMatch(m.key) },
                    modifier = Modifier.animateItem(),
                )
            }
        }
        item(key = "disclaimer") {
            Column {
                Spacer(Modifier.height(4.dp))
                DisclaimerCard(compact = true)
            }
        }
    }
}
