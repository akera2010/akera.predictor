package com.akeraten.valuebetmonitor.ui.theme

import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color

object Ak {
    val Bg = Color(0xFF060A14)
    val BgDeep = Color(0xFF03060D)
    val Surface = Color(0xFF0D1426)
    val SurfaceHigh = Color(0xFF141D35)
    val SurfaceGlass = Color(0x1AFFFFFF)
    val Border = Color(0x26FFFFFF)

    val Lime = Color(0xFFC6FF00)
    val LimeDim = Color(0xFF8DB600)
    val Cyan = Color(0xFF00E5FF)
    val Orange = Color(0xFFFF8A00)
    val Magenta = Color(0xFFFF3D9A)
    val Red = Color(0xFFFF4D6D)
    val Green = Color(0xFF00E676)
    val Amber = Color(0xFFFFC400)
    val Violet = Color(0xFF8C7BFF)

    val TextPrimary = Color(0xFFEAF0FF)
    val TextSecondary = Color(0xFF8A97B8)
    val TextMuted = Color(0xFF5B6685)

    val BackgroundBrush: Brush = Brush.verticalGradient(
        listOf(Color(0xFF0A1330), Bg, BgDeep),
    )
    val CardBrush: Brush = Brush.linearGradient(
        listOf(Color(0xFF18234A), Color(0xFF0E1630), Color(0xFF0A1022)),
    )
    val LimeBrush: Brush = Brush.horizontalGradient(listOf(Lime, Color(0xFF64DD17)))
    val TtBrush: Brush = Brush.horizontalGradient(listOf(Cyan, Orange))

    fun sportColor(sport: String): Color =
        if (sport.equals("table_tennis", ignoreCase = true)) Cyan else Lime

    fun sportAccent2(sport: String): Color =
        if (sport.equals("table_tennis", ignoreCase = true)) Orange else Green

    /** Edge (fraction) -> badge colour. */
    fun edgeColor(edgeFraction: Double): Color = when {
        edgeFraction >= 0.10 -> Green
        edgeFraction >= 0.05 -> Lime
        edgeFraction >= 0.03 -> Amber
        else -> TextSecondary
    }

    fun confidenceColor(conf: String): Color = when (conf.lowercase()) {
        "alta" -> Green
        "media" -> Amber
        else -> Orange
    }
}
