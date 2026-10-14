package com.akeraten.valuebetmonitor.ui.components

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.akeraten.valuebetmonitor.data.model.ConnectionState
import com.akeraten.valuebetmonitor.data.model.DataMode
import com.akeraten.valuebetmonitor.ui.theme.Ak
import com.akeraten.valuebetmonitor.util.asFraction
import com.akeraten.valuebetmonitor.util.signedPct

const val APP_TITLE = "AKERATEN v.0.1"
const val APP_AUTHOR = "Sandra Blanco (España | 2026)"
const val DISCLAIMER = "Las apuestas conllevan riesgo. No se garantizan ganancias. +18. Juega con responsabilidad."

/** Glassy gradient card with a hairline gradient border. */
@Composable
fun GlassCard(
    modifier: Modifier = Modifier,
    accent: Color = Ak.Border,
    onClick: (() -> Unit)? = null,
    contentPadding: Dp = 16.dp,
    content: @Composable ColumnScope.() -> Unit,
) {
    val shape = RoundedCornerShape(22.dp)
    val clickMod = if (onClick != null) Modifier.clickable(onClick = onClick) else Modifier
    Column(
        modifier = modifier
            .clip(shape)
            .background(Ak.CardBrush, shape)
            .border(
                width = 1.dp,
                brush = Brush.linearGradient(listOf(accent.copy(alpha = 0.55f), Ak.Border, Color.Transparent)),
                shape = shape,
            )
            .then(clickMod)
            .padding(contentPadding),
        content = content,
    )
}

/** Custom neon filter chip (avoids experimental chip APIs). */
@Composable
fun NeonChip(
    text: String,
    selected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    color: Color = Ak.Lime,
) {
    val shape = RoundedCornerShape(50)
    Box(
        modifier = modifier
            .clip(shape)
            .background(if (selected) color.copy(alpha = 0.18f) else Ak.SurfaceGlass, shape)
            .border(1.dp, if (selected) color else Ak.Border, shape)
            .clickable(onClick = onClick)
            .padding(horizontal = 14.dp, vertical = 8.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = text,
            color = if (selected) color else Ak.TextSecondary,
            style = MaterialTheme.typography.labelLarge,
            maxLines = 1,
        )
    }
}

@Composable
fun Pill(
    text: String,
    color: Color,
    modifier: Modifier = Modifier,
    filled: Boolean = false,
    textStyle: TextStyle = MaterialTheme.typography.labelSmall,
) {
    val shape = RoundedCornerShape(50)
    Box(
        modifier = modifier
            .clip(shape)
            .background(if (filled) color else color.copy(alpha = 0.14f), shape)
            .border(1.dp, color.copy(alpha = if (filled) 1f else 0.6f), shape)
            .padding(horizontal = 9.dp, vertical = 3.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = text,
            color = if (filled) Color(0xFF07101E) else color,
            style = textStyle,
            maxLines = 1,
        )
    }
}

@Composable
fun PulsingDot(color: Color, modifier: Modifier = Modifier, dotSize: Dp = 9.dp) {
    val transition = rememberInfiniteTransition(label = "pulse")
    val scale by transition.animateFloat(
        initialValue = 1f,
        targetValue = 2.6f,
        animationSpec = infiniteRepeatable(tween(1100, easing = FastOutSlowInEasing), RepeatMode.Restart),
        label = "pulseScale",
    )
    val haloAlpha by transition.animateFloat(
        initialValue = 0.7f,
        targetValue = 0f,
        animationSpec = infiniteRepeatable(tween(1100), RepeatMode.Restart),
        label = "pulseAlpha",
    )
    Box(modifier = modifier.size(dotSize * 2.8f), contentAlignment = Alignment.Center) {
        Box(
            Modifier
                .size(dotSize)
                .graphicsLayer {
                    scaleX = scale
                    scaleY = scale
                    alpha = haloAlpha
                }
                .background(color, CircleShape),
        )
        Box(Modifier.size(dotSize).background(color, CircleShape))
    }
}

@Composable
fun LiveBadge(modifier: Modifier = Modifier) {
    Row(modifier = modifier, verticalAlignment = Alignment.CenterVertically) {
        PulsingDot(Ak.Red, dotSize = 7.dp)
        Text("LIVE", color = Ak.Red, style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Black)
    }
}

@Composable
fun EdgeBadge(edge: Double, modifier: Modifier = Modifier, big: Boolean = false) {
    val f = edge.asFraction()
    val color = Ak.edgeColor(f)
    Pill(
        text = "EDGE ${edge.signedPct()}",
        color = color,
        filled = f >= 0.05,
        modifier = modifier,
        textStyle = if (big) MaterialTheme.typography.labelLarge else MaterialTheme.typography.labelSmall,
    )
}

@Composable
fun ConfidenceChip(confidence: String, modifier: Modifier = Modifier) {
    val label = when (confidence.lowercase()) {
        "alta" -> "CONFIANZA ALTA"
        "media" -> "CONFIANZA MEDIA"
        "baja" -> "CONFIANZA BAJA"
        else -> confidence.uppercase()
    }
    Pill(label, Ak.confidenceColor(confidence), modifier)
}

@Composable
fun SuspiciousBadge(modifier: Modifier = Modifier) {
    val shape = RoundedCornerShape(50)
    Row(
        modifier = modifier
            .clip(shape)
            .background(Ak.Red.copy(alpha = 0.18f), shape)
            .border(1.dp, Ak.Red, shape)
            .padding(horizontal = 8.dp, vertical = 3.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(Icons.Filled.Warning, contentDescription = null, tint = Ak.Red, modifier = Modifier.size(12.dp))
        Spacer(Modifier.width(4.dp))
        Text("SOSPECHOSA", color = Ak.Red, style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Black)
    }
}

/** Tennis-ball + paddle mini logo drawn with Canvas. */
@Composable
fun AkLogo(modifier: Modifier = Modifier, size: Dp = 40.dp) {
    Canvas(modifier = modifier.size(size)) {
        val r = this.size.minDimension * 0.36f
        val c = Offset(this.size.width * 0.42f, this.size.height * 0.42f)
        // paddle
        val pc = Offset(this.size.width * 0.72f, this.size.height * 0.72f)
        drawCircle(Ak.Orange, radius = r * 0.62f, center = pc)
        drawCircle(Color(0xFFFF5A1F), radius = r * 0.40f, center = pc)
        // glow + ball
        drawCircle(Ak.Lime.copy(alpha = 0.25f), radius = r * 1.25f, center = c)
        drawCircle(Ak.Lime, radius = r, center = c)
        val seam = Stroke(width = r * 0.14f, cap = StrokeCap.Round)
        val sr = r * 0.85f
        drawArc(
            color = Color.White,
            startAngle = -45f,
            sweepAngle = 90f,
            useCenter = false,
            topLeft = Offset(c.x - 0.55f * r - sr, c.y - sr),
            size = Size(sr * 2, sr * 2),
            style = seam,
        )
        drawArc(
            color = Color.White,
            startAngle = 135f,
            sweepAngle = 90f,
            useCenter = false,
            topLeft = Offset(c.x + 0.55f * r - sr, c.y - sr),
            size = Size(sr * 2, sr * 2),
            style = seam,
        )
    }
}

/** Top brand bar: "AKERATEN v.0.1" + author + connection status. */
@Composable
fun BrandHeader(mode: DataMode, connection: ConnectionState, modifier: Modifier = Modifier) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .background(Brush.verticalGradient(listOf(Color(0xFF0B1636), Color(0xF00A1124))))
            .statusBarsPadding(),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            AkLogo(size = 38.dp)
            Spacer(Modifier.width(10.dp))
            Column(Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.Bottom) {
                    Text(
                        "AKERATEN",
                        color = Ak.TextPrimary,
                        fontWeight = FontWeight.Black,
                        fontSize = 20.sp,
                        letterSpacing = 2.sp,
                    )
                    Spacer(Modifier.width(6.dp))
                    Text("v.0.1", color = Ak.Lime, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                }
                Text(APP_AUTHOR, color = Ak.TextSecondary, fontSize = 11.sp, maxLines = 1)
            }
            ConnectionPill(mode, connection)
        }
        DemoBanner(mode)
    }
}

@Composable
fun ConnectionPill(mode: DataMode, connection: ConnectionState) {
    val (label, color) = when {
        mode == DataMode.OFFLINE_DEMO -> "OFFLINE" to Ak.Orange
        connection == ConnectionState.REALTIME -> "TIEMPO REAL" to Ak.Green
        connection == ConnectionState.REST_ONLY -> "REST" to Ak.Amber
        else -> "CONECTANDO" to Ak.Cyan
    }
    Row(verticalAlignment = Alignment.CenterVertically) {
        if (connection == ConnectionState.REALTIME && mode != DataMode.OFFLINE_DEMO) {
            PulsingDot(color, dotSize = 6.dp)
        }
        Pill(label, color)
    }
}

@Composable
fun DemoBanner(mode: DataMode) {
    val text = when (mode) {
        DataMode.OFFLINE_DEMO -> "MODO DEMO SIN CONEXIÓN · datos de ejemplo generados en la app"
        DataMode.BACKEND_DEMO -> "Backend en modo DEMO · datos simulados"
        else -> null
    } ?: return
    val brush = if (mode == DataMode.OFFLINE_DEMO) {
        Brush.horizontalGradient(listOf(Ak.Orange, Color(0xFFFF3D00)))
    } else {
        Brush.horizontalGradient(listOf(Ak.Violet, Ak.Cyan))
    }
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .background(brush)
            .padding(horizontal = 12.dp, vertical = 5.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text,
            color = Color(0xFF0A0A0A),
            fontWeight = FontWeight.Black,
            fontSize = 11.sp,
            textAlign = TextAlign.Center,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

@Composable
fun SectionTitle(text: String, modifier: Modifier = Modifier, accent: Color = Ak.Lime) {
    Row(modifier = modifier.padding(vertical = 6.dp), verticalAlignment = Alignment.CenterVertically) {
        Box(
            Modifier
                .width(4.dp)
                .height(18.dp)
                .background(accent, RoundedCornerShape(2.dp)),
        )
        Spacer(Modifier.width(8.dp))
        Text(text, style = MaterialTheme.typography.titleMedium, color = Ak.TextPrimary)
    }
}

/** Horizontal probability bar with animated fill. */
@Composable
fun ProbBar(
    label: String,
    value: Double?,
    color: Color,
    modifier: Modifier = Modifier,
    valueText: String? = null,
    labelWidth: Dp = 86.dp,
    barHeight: Dp = 10.dp,
) {
    val v = (value?.asFraction() ?: 0.0).coerceIn(0.0, 1.0).toFloat()
    val anim by animateFloatAsState(targetValue = v, animationSpec = tween(800), label = "probBar")
    Row(modifier = modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Text(
            label,
            color = Ak.TextSecondary,
            style = MaterialTheme.typography.labelMedium,
            modifier = Modifier.width(labelWidth),
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
        Box(
            Modifier
                .weight(1f)
                .height(barHeight)
                .clip(RoundedCornerShape(50))
                .background(Color(0x14FFFFFF)),
        ) {
            Box(
                Modifier
                    .fillMaxHeight()
                    .fillMaxWidth(anim)
                    .clip(RoundedCornerShape(50))
                    .background(Brush.horizontalGradient(listOf(color.copy(alpha = 0.55f), color))),
            )
        }
        Spacer(Modifier.width(8.dp))
        Text(
            valueText ?: if (value == null) "—" else "${(v * 100).toInt()} %",
            color = color,
            style = MaterialTheme.typography.labelLarge,
            modifier = Modifier.width(52.dp),
            textAlign = TextAlign.End,
        )
    }
}

/** Two-tone split bar: player A share (left) vs player B. */
@Composable
fun SplitBar(fractionA: Double?, colorA: Color, colorB: Color, modifier: Modifier = Modifier, height: Dp = 8.dp) {
    val f = (fractionA?.asFraction() ?: 0.5).coerceIn(0.0, 1.0).toFloat()
    val anim by animateFloatAsState(targetValue = f, animationSpec = tween(800), label = "split")
    Row(
        modifier
            .fillMaxWidth()
            .height(height)
            .clip(RoundedCornerShape(50)),
    ) {
        if (anim > 0.001f) Box(Modifier.weight(anim).fillMaxHeight().background(colorA))
        if (anim < 0.999f) Box(Modifier.weight(1f - anim).fillMaxHeight().background(colorB))
    }
}

/** Animated (rolling) text for score digits. */
@Composable
fun RollingText(
    text: String,
    color: Color,
    style: TextStyle,
    modifier: Modifier = Modifier,
    fontWeight: FontWeight? = null,
) {
    AnimatedContent(
        targetState = text,
        transitionSpec = {
            (slideInVertically(animationSpec = tween(350)) { h -> h } + fadeIn(tween(350))) togetherWith
                (slideOutVertically(animationSpec = tween(350)) { h -> -h } + fadeOut(tween(350)))
        },
        label = "rolling",
        modifier = modifier,
    ) { value ->
        Text(value, color = color, style = style, fontWeight = fontWeight, textAlign = TextAlign.Center)
    }
}

@Composable
fun FormChips(form: List<String>, modifier: Modifier = Modifier) {
    Row(modifier = modifier, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
        form.take(10).forEach { r ->
            val win = r.equals("W", ignoreCase = true) || r.equals("V", ignoreCase = true)
            val color = if (win) Ak.Green else Ak.Red
            Box(
                Modifier
                    .size(22.dp)
                    .clip(RoundedCornerShape(6.dp))
                    .background(color.copy(alpha = 0.2f))
                    .border(1.dp, color, RoundedCornerShape(6.dp)),
                contentAlignment = Alignment.Center,
            ) {
                Text(if (win) "V" else "D", color = color, fontSize = 11.sp, fontWeight = FontWeight.Black)
            }
        }
    }
}

@Composable
fun KpiTile(label: String, value: String, color: Color, modifier: Modifier = Modifier, sub: String? = null) {
    GlassCard(modifier = modifier, accent = color, contentPadding = 12.dp) {
        Text(label.uppercase(), color = Ak.TextSecondary, style = MaterialTheme.typography.labelSmall, maxLines = 1)
        Spacer(Modifier.height(4.dp))
        Text(value, color = color, fontWeight = FontWeight.Black, fontSize = 20.sp, maxLines = 1)
        if (sub != null) {
            Text(sub, color = Ak.TextMuted, style = MaterialTheme.typography.labelSmall, maxLines = 1)
        }
    }
}

@Composable
fun LoadingBox(modifier: Modifier = Modifier, text: String = "Cargando…") {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        CircularProgressIndicator(color = Ak.Lime, strokeWidth = 3.dp)
        Spacer(Modifier.height(12.dp))
        Text(text, color = Ak.TextSecondary)
    }
}

@Composable
fun EmptyState(title: String, subtitle: String, modifier: Modifier = Modifier, emoji: String = "🎾") {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(emoji, fontSize = 42.sp)
        Spacer(Modifier.height(8.dp))
        Text(title, color = Ak.TextPrimary, style = MaterialTheme.typography.titleMedium, textAlign = TextAlign.Center)
        Text(subtitle, color = Ak.TextSecondary, style = MaterialTheme.typography.bodySmall, textAlign = TextAlign.Center)
    }
}

@Composable
fun DisclaimerCard(modifier: Modifier = Modifier, compact: Boolean = false) {
    val shape = RoundedCornerShape(18.dp)
    Row(
        modifier = modifier
            .fillMaxWidth()
            .clip(shape)
            .background(Brush.horizontalGradient(listOf(Color(0x33FF4D6D), Color(0x22FF8A00))), shape)
            .border(1.dp, Ak.Red.copy(alpha = 0.7f), shape)
            .padding(if (compact) 10.dp else 16.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(
            Modifier
                .size(if (compact) 30.dp else 42.dp)
                .background(Ak.Red, CircleShape),
            contentAlignment = Alignment.Center,
        ) {
            Text("+18", color = Color.White, fontWeight = FontWeight.Black, fontSize = if (compact) 11.sp else 14.sp)
        }
        Spacer(Modifier.width(12.dp))
        Column(Modifier.weight(1f)) {
            if (!compact) {
                Text(
                    "JUEGO RESPONSABLE",
                    color = Ak.Red,
                    fontWeight = FontWeight.Black,
                    style = MaterialTheme.typography.labelLarge,
                )
            }
            Text(
                DISCLAIMER,
                color = Ak.TextPrimary,
                style = if (compact) MaterialTheme.typography.bodySmall else MaterialTheme.typography.bodyMedium,
            )
        }
    }
}
