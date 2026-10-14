package com.akeraten.valuebetmonitor.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.akeraten.valuebetmonitor.data.model.Match
import com.akeraten.valuebetmonitor.ui.theme.Ak
import com.akeraten.valuebetmonitor.ui.theme.MonoNumbers
import kotlinx.serialization.json.JsonArray
import com.akeraten.valuebetmonitor.util.fmt
import com.akeraten.valuebetmonitor.util.asDoubleOrNull
import com.akeraten.valuebetmonitor.util.fairImpliedA
import com.akeraten.valuebetmonitor.util.flagEmoji
import com.akeraten.valuebetmonitor.util.shortTime
import com.akeraten.valuebetmonitor.util.sportEmoji

fun statusLabel(status: String): String = when (status.lowercase()) {
    "live" -> "EN VIVO"
    "upcoming", "scheduled" -> "PRÓXIMO"
    "finished", "ended" -> "FINAL"
    else -> status.uppercase()
}

private fun splitPoints(points: String?): Pair<String, String>? {
    if (points.isNullOrBlank()) return null
    val parts = points.split("-", ":").map { it.trim() }
    return if (parts.size == 2) parts[0] to parts[1] else points to ""
}

/** Table tennis: games won [a, b] from score.games. */
fun ttGamesWon(match: Match): Pair<Int?, Int?> {
    if (!match.isTableTennis) return null to null
    val arr = match.score.games as? JsonArray ?: return null to null
    if (arr.size != 2) return null to null
    return arr[0].asDoubleOrNull()?.toInt() to arr[1].asDoubleOrNull()?.toInt()
}

private fun lastName(name: String): String = name.trim().split(" ").lastOrNull()?.ifBlank { name } ?: name

@Composable
fun MatchCard(match: Match, onClick: () -> Unit, modifier: Modifier = Modifier) {
    val sportColor = Ak.sportColor(match.sport)
    GlassCard(modifier = modifier.fillMaxWidth(), accent = sportColor, onClick = onClick) {
        // ---- header
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(sportEmoji(match.sport), fontSize = 16.sp)
            Spacer(Modifier.width(6.dp))
            val category = match.category
            if (!category.isNullOrBlank()) {
                Pill(category, sportColor)
                Spacer(Modifier.width(6.dp))
            }
            Text(
                match.tournament,
                color = Ak.TextSecondary,
                style = MaterialTheme.typography.labelMedium,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.weight(1f),
            )
            when {
                match.isLive -> LiveBadge()
                else -> Text(
                    if (match.status.equals("finished", true)) "FINAL" else shortTime(match.startTime),
                    color = Ak.TextSecondary,
                    style = MaterialTheme.typography.labelSmall,
                )
            }
        }
        if (!match.surface.isNullOrBlank()) {
            Text(
                "${match.surface} · Mejor de ${match.bestOf}",
                color = Ak.TextMuted,
                style = MaterialTheme.typography.labelSmall,
            )
        }
        Spacer(Modifier.height(10.dp))

        // ---- scoreboard
        val points = splitPoints(match.score.points)
        val sets = match.score.sets
        val (gamesA, gamesB) = ttGamesWon(match)
        PlayerScoreRow(
            name = match.playerA,
            country = match.countryA,
            rank = match.rankA,
            serving = match.isLive && match.server.equals("a", true),
            setScores = sets.map { it.getOrNull(0) },
            opponentScores = sets.map { it.getOrNull(1) },
            points = if (match.isLive) points?.first else null,
            live = match.isLive,
            accent = sportColor,
            gamesWon = gamesA,
        )
        Spacer(Modifier.height(6.dp))
        PlayerScoreRow(
            name = match.playerB,
            country = match.countryB,
            rank = match.rankB,
            serving = match.isLive && match.server.equals("b", true),
            setScores = sets.map { it.getOrNull(1) },
            opponentScores = sets.map { it.getOrNull(0) },
            points = if (match.isLive) points?.second else null,
            live = match.isLive,
            accent = sportColor,
            gamesWon = gamesB,
        )

        // ---- model vs market
        Spacer(Modifier.height(12.dp))
        val implied = fairImpliedA(match.odds?.playerA, match.odds?.playerB)
        val shortA = lastName(match.playerA)
        ProbBar(label = "Modelo $shortA", value = match.modelProbA, color = sportColor, barHeight = 8.dp)
        Spacer(Modifier.height(4.dp))
        ProbBar(label = "Mercado $shortA", value = implied, color = Ak.Cyan.takeIf { !match.isTableTennis } ?: Ak.Orange, barHeight = 8.dp)
        Spacer(Modifier.height(8.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            val odds = match.odds
            Text(
                if (odds != null) "Cuotas ${odds.playerA.fmt()} · ${odds.playerB.fmt()}" else "Sin cuotas",
                color = Ak.TextSecondary,
                style = MaterialTheme.typography.labelMedium,
                modifier = Modifier.weight(1f),
            )
            if (match.valueBetCount > 0) {
                Pill(
                    "${match.valueBetCount} VALUE BET${if (match.valueBetCount > 1) "S" else ""}",
                    Ak.Lime,
                    filled = true,
                )
            }
        }
    }
}

@Composable
fun PlayerScoreRow(
    name: String,
    country: String?,
    rank: Int?,
    serving: Boolean,
    setScores: List<Int?>,
    opponentScores: List<Int?>,
    points: String?,
    live: Boolean,
    accent: Color,
    modifier: Modifier = Modifier,
    gamesWon: Int? = null,
) {
    Row(modifier = modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Text(flagEmoji(country), fontSize = 18.sp)
        Spacer(Modifier.width(8.dp))
        Column(Modifier.weight(1f)) {
            Text(
                name,
                color = Ak.TextPrimary,
                style = MaterialTheme.typography.titleSmall,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            if (rank != null) {
                Text("#$rank", color = Ak.TextMuted, fontSize = 10.sp)
            }
        }
        // server indicator
        Box(Modifier.size(14.dp), contentAlignment = Alignment.Center) {
            if (serving) {
                PulsingDot(accent, dotSize = 6.dp)
            }
        }
        Spacer(Modifier.width(4.dp))
        if (gamesWon != null) {
            RollingText(
                text = gamesWon.toString(),
                color = accent,
                style = MonoNumbers.copy(fontSize = 18.sp),
                fontWeight = FontWeight.Black,
                modifier = Modifier.widthIn(min = 22.dp),
            )
            Spacer(Modifier.width(4.dp))
        }
        Row(horizontalArrangement = Arrangement.spacedBy(3.dp)) {
            setScores.forEachIndexed { i, s ->
                val current = live && i == setScores.lastIndex
                val opp = opponentScores.getOrNull(i)
                val won = !current && s != null && opp != null && s > opp
                val shape = RoundedCornerShape(6.dp)
                Box(
                    Modifier
                        .widthIn(min = 24.dp)
                        .clip(shape)
                        .background(if (current) accent.copy(alpha = 0.18f) else Color(0x10FFFFFF), shape)
                        .border(1.dp, if (current) accent.copy(alpha = 0.8f) else Color.Transparent, shape)
                        .padding(horizontal = 4.dp, vertical = 2.dp),
                    contentAlignment = Alignment.Center,
                ) {
                    RollingText(
                        text = s?.toString() ?: "-",
                        color = when {
                            current -> accent
                            won -> Ak.TextPrimary
                            else -> Ak.TextSecondary
                        },
                        style = MonoNumbers.copy(fontSize = 14.sp),
                        fontWeight = if (won || current) FontWeight.Black else FontWeight.Medium,
                    )
                }
            }
        }
        if (points != null) {
            Spacer(Modifier.width(6.dp))
            Box(
                Modifier
                    .widthIn(min = 34.dp)
                    .clip(CircleShape)
                    .background(Ak.Cyan.copy(alpha = 0.15f))
                    .padding(horizontal = 6.dp, vertical = 2.dp),
                contentAlignment = Alignment.Center,
            ) {
                RollingText(text = points, color = Ak.Cyan, style = MonoNumbers.copy(fontSize = 13.sp))
            }
        }
    }
}
