package com.akeraten.valuebetmonitor.ui.components

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.akeraten.valuebetmonitor.ui.theme.Ak
import kotlin.math.max

data class ChartSeries(
    val label: String,
    val values: List<Float>,
    val color: Color,
    val dashed: Boolean = false,
    val fill: Boolean = false,
)

/** Animated multi-series line chart drawn on Canvas. */
@Composable
fun LineChart(
    series: List<ChartSeries>,
    modifier: Modifier = Modifier,
    yMin: Float? = null,
    yMax: Float? = null,
    referenceY: Float? = null,
) {
    val progress = remember { Animatable(0f) }
    val key = series.sumOf { it.values.size } + series.size * 31
    LaunchedEffect(key) {
        progress.snapTo(0f)
        progress.animateTo(1f, tween(1100, easing = FastOutSlowInEasing))
    }
    Canvas(modifier = modifier) {
        val all = series.flatMap { it.values }
        if (all.isEmpty()) return@Canvas
        val lo = yMin ?: all.min()
        val hi = yMax ?: all.max()
        val range = if (hi - lo < 1e-6f) 1f else hi - lo
        val w = size.width
        val h = size.height
        fun yOf(v: Float): Float = h - ((v - lo) / range) * h

        // grid
        for (i in 0..4) {
            val y = h * i / 4f
            drawLine(Color(0x18FFFFFF), Offset(0f, y), Offset(w, y), strokeWidth = 1f)
        }
        if (referenceY != null && referenceY in lo..hi) {
            drawLine(
                color = Color(0x66FFFFFF),
                start = Offset(0f, yOf(referenceY)),
                end = Offset(w, yOf(referenceY)),
                strokeWidth = 1.5f,
                pathEffect = PathEffect.dashPathEffect(floatArrayOf(8f, 8f)),
            )
        }

        series.forEach { s ->
            val n = s.values.size
            if (n < 2) return@forEach
            val visible = max(2, (n * progress.value).toInt().coerceAtMost(n))
            val path = Path()
            var lastX = 0f
            var lastY = 0f
            for (i in 0 until visible) {
                val x = w * i / (n - 1).toFloat()
                val y = yOf(s.values[i])
                if (i == 0) path.moveTo(x, y) else path.lineTo(x, y)
                lastX = x
                lastY = y
            }
            if (s.fill) {
                val fillPath = Path()
                fillPath.addPath(path)
                fillPath.lineTo(lastX, h)
                fillPath.lineTo(0f, h)
                fillPath.close()
                drawPath(
                    path = fillPath,
                    brush = Brush.verticalGradient(listOf(s.color.copy(alpha = 0.35f), Color.Transparent)),
                )
            }
            drawPath(
                path = path,
                color = s.color,
                style = Stroke(
                    width = 3.dp.toPx(),
                    cap = StrokeCap.Round,
                    join = StrokeJoin.Round,
                    pathEffect = if (s.dashed) PathEffect.dashPathEffect(floatArrayOf(14f, 10f)) else null,
                ),
            )
            drawCircle(s.color.copy(alpha = 0.3f), radius = 9.dp.toPx(), center = Offset(lastX, lastY))
            drawCircle(s.color, radius = 4.dp.toPx(), center = Offset(lastX, lastY))
        }
    }
}

@Composable
fun ChartLegend(series: List<ChartSeries>, modifier: Modifier = Modifier) {
    Row(modifier = modifier, horizontalArrangement = Arrangement.spacedBy(14.dp)) {
        series.forEach { s ->
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(Modifier.size(10.dp).background(s.color, CircleShape))
                Spacer(Modifier.width(6.dp))
                Text(s.label, color = Ak.TextSecondary, style = MaterialTheme.typography.labelMedium)
            }
        }
    }
}

/** Animated circular progress ring (e.g. expert hit-rate). */
@Composable
fun RingProgress(
    progress: Float,
    color: Color,
    modifier: Modifier = Modifier,
    ringSize: Dp = 72.dp,
    strokeWidth: Dp = 8.dp,
    center: @Composable BoxScope.() -> Unit = {},
) {
    val anim by animateFloatAsState(
        targetValue = progress.coerceIn(0f, 1f),
        animationSpec = tween(1200, easing = FastOutSlowInEasing),
        label = "ring",
    )
    Box(modifier = modifier.size(ringSize), contentAlignment = Alignment.Center) {
        Canvas(modifier = Modifier.matchParentSize()) {
            val sw = strokeWidth.toPx()
            val arcSize = Size(size.width - sw, size.height - sw)
            val topLeft = Offset(sw / 2f, sw / 2f)
            drawArc(
                color = Color(0x1FFFFFFF),
                startAngle = -90f,
                sweepAngle = 360f,
                useCenter = false,
                topLeft = topLeft,
                size = arcSize,
                style = Stroke(width = sw),
            )
            drawArc(
                brush = Brush.sweepGradient(listOf(color.copy(alpha = 0.4f), color, color)),
                startAngle = -90f,
                sweepAngle = 360f * anim,
                useCenter = false,
                topLeft = topLeft,
                size = arcSize,
                style = Stroke(width = sw, cap = StrokeCap.Round),
            )
        }
        center()
    }
}

/** Vertical distribution bars (Monte Carlo set-score distribution). */
@Composable
fun DistributionBars(
    entries: List<Pair<String, Double>>,
    modifier: Modifier = Modifier,
    colorFor: (String) -> Color = { Ak.Lime },
    maxBarHeight: Dp = 110.dp,
) {
    if (entries.isEmpty()) return
    val maxV = entries.maxOf { it.second }.takeIf { it > 0.0 } ?: 1.0
    Row(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceEvenly,
        verticalAlignment = Alignment.Bottom,
    ) {
        entries.forEach { (label, v) ->
            val frac = (v / maxV).toFloat().coerceIn(0.02f, 1f)
            val anim by animateFloatAsState(frac, tween(900), label = "dist")
            val color = colorFor(label)
            Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.weight(1f)) {
                Text(
                    "${(v * 100).toInt()}%",
                    color = color,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                    textAlign = TextAlign.Center,
                )
                Spacer(Modifier.height(4.dp))
                Box(
                    Modifier
                        .width(22.dp)
                        .height(maxBarHeight * anim)
                        .background(
                            Brush.verticalGradient(listOf(color, color.copy(alpha = 0.25f))),
                            RoundedCornerShape(topStart = 6.dp, topEnd = 6.dp),
                        ),
                )
                Spacer(Modifier.height(4.dp))
                Text(label, color = Ak.TextSecondary, fontSize = 11.sp, fontWeight = FontWeight.SemiBold)
            }
        }
    }
}

/** Labelled horizontal bar with weight / value text, used for model breakdowns. */
@Composable
fun ModelBar(
    name: String,
    value: Double?,
    color: Color,
    modifier: Modifier = Modifier,
    note: String? = null,
) {
    Column(modifier = modifier.fillMaxWidth().padding(vertical = 4.dp)) {
        ProbBar(label = name, value = value, color = color, labelWidth = 104.dp, barHeight = 12.dp)
        if (note != null) {
            Text(
                note,
                color = Ak.TextMuted,
                style = MaterialTheme.typography.labelSmall,
                modifier = Modifier.padding(start = 104.dp, top = 2.dp),
            )
        }
    }
}
