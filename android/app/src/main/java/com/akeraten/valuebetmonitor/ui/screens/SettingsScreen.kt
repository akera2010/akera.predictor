package com.akeraten.valuebetmonitor.ui.screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Slider
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.akeraten.valuebetmonitor.BuildConfig
import com.akeraten.valuebetmonitor.data.Loaded
import com.akeraten.valuebetmonitor.data.Repository
import com.akeraten.valuebetmonitor.data.model.AppSettings
import com.akeraten.valuebetmonitor.data.model.DataMode
import com.akeraten.valuebetmonitor.data.model.Stats
import com.akeraten.valuebetmonitor.ui.components.APP_AUTHOR
import com.akeraten.valuebetmonitor.ui.components.APP_TITLE
import com.akeraten.valuebetmonitor.ui.components.AkLogo
import com.akeraten.valuebetmonitor.ui.components.ChartSeries
import com.akeraten.valuebetmonitor.ui.components.DisclaimerCard
import com.akeraten.valuebetmonitor.ui.components.GlassCard
import com.akeraten.valuebetmonitor.ui.components.KpiTile
import com.akeraten.valuebetmonitor.ui.components.LineChart
import com.akeraten.valuebetmonitor.ui.components.LoadingBox
import com.akeraten.valuebetmonitor.ui.components.NeonSegmented
import com.akeraten.valuebetmonitor.ui.components.Pill
import com.akeraten.valuebetmonitor.ui.components.SectionTitle
import com.akeraten.valuebetmonitor.ui.components.akFieldColors
import com.akeraten.valuebetmonitor.ui.theme.Ak
import com.akeraten.valuebetmonitor.util.asDoubleOrNull
import com.akeraten.valuebetmonitor.util.fmt
import com.akeraten.valuebetmonitor.util.euros
import com.akeraten.valuebetmonitor.util.obj
import com.akeraten.valuebetmonitor.util.pct
import com.akeraten.valuebetmonitor.util.signedPct
import com.akeraten.valuebetmonitor.util.sportLabel
import kotlinx.coroutines.launch

private val RISK_OPTIONS = listOf(
    "conservador" to "Conservador",
    "moderado" to "Moderado",
    "agresivo" to "Agresivo",
)

private fun applyRiskPreset(s: AppSettings, profile: String): AppSettings = when (profile) {
    "conservador" -> s.copy(riskProfile = profile, kellyFraction = 0.25, maxStakePct = 0.02)
    "agresivo" -> s.copy(riskProfile = profile, kellyFraction = 0.75, maxStakePct = 0.08)
    else -> s.copy(riskProfile = "moderado", kellyFraction = 0.5, maxStakePct = 0.05)
}

@Composable
fun SettingsScreen(repository: Repository) {
    val prefs by repository.prefs.collectAsState()
    val health by repository.health.collectAsState()
    val mode by repository.mode.collectAsState()
    val discovering by repository.discovering.collectAsState()
    val scope = rememberCoroutineScope()

    var urlText by remember(prefs.baseUrl) { mutableStateOf(prefs.baseUrl) }
    var draft by remember(prefs.settings) { mutableStateOf(prefs.settings) }
    var bankrollText by remember(prefs.settings.bankroll) { mutableStateOf(prefs.settings.bankroll.fmt(2).replace(',', '.')) }
    var message by remember { mutableStateOf<String?>(null) }
    var stats by remember { mutableStateOf<Loaded<Stats>?>(null) }
    var statsKey by remember { mutableStateOf(0) }

    LaunchedEffect(statsKey) {
        repository.checkHealth()
        stats = repository.stats()
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .imePadding()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 16.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Text("Ajustes", style = MaterialTheme.typography.headlineSmall, color = Ak.TextPrimary)
        DisclaimerCard()

        // ------------------------------------------------------------- Stats dashboard
        StatsDashboard(stats)

        // ------------------------------------------------------------- Connection
        GlassCard(accent = Ak.Cyan) {
            SectionTitle("Conexión con el backend", accent = Ak.Cyan)
            OutlinedTextField(
                value = urlText,
                onValueChange = { urlText = it },
                label = { Text("URL del backend") },
                placeholder = { Text("http://10.0.2.2:8000/") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri),
                colors = akFieldColors(Ak.Cyan),
            )
            Spacer(Modifier.height(10.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(
                    onClick = {
                        scope.launch {
                            repository.setBaseUrl(urlText)
                            message = "URL guardada. Reconectando…"
                            statsKey += 1
                        }
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = Ak.Cyan, contentColor = Color(0xFF001F24)),
                    shape = RoundedCornerShape(12.dp),
                ) { Text("Guardar y reconectar", fontWeight = FontWeight.Bold) }
                OutlinedButton(
                    onClick = {
                        scope.launch {
                            val h = repository.checkHealth()
                            message = if (h != null) {
                                "Conectado: ${h.app ?: "backend"} · modo ${h.mode}"
                            } else {
                                "Sin respuesta del backend. Se mantiene el modo demo."
                            }
                        }
                    },
                    border = BorderStroke(1.dp, Ak.Cyan),
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = Ak.Cyan),
                    shape = RoundedCornerShape(12.dp),
                ) { Text("Probar") }
            }
            Spacer(Modifier.height(8.dp))
            Button(
                onClick = {
                    scope.launch {
                        message = "Buscando tu PC en la Wi-Fi…"
                        val found = repository.discoverPc()
                        message = if (found != null) {
                            statsKey += 1
                            "PC encontrado: $found"
                        } else {
                            "No encuentro el PC. Comprueba que INICIAR_AKERATEN está abierto y que el móvil está en la misma Wi-Fi."
                        }
                    }
                },
                enabled = !discovering,
                modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.buttonColors(containerColor = Ak.Lime, contentColor = Color(0xFF111800)),
                shape = RoundedCornerShape(12.dp),
            ) { Text(if (discovering) "Buscando…" else "Buscar mi PC", fontWeight = FontWeight.Bold) }
            Spacer(Modifier.height(10.dp))
            val h = health
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("Estado: ", color = Ak.TextSecondary, style = MaterialTheme.typography.labelMedium)
                when {
                    mode == DataMode.OFFLINE_DEMO -> Pill("MODO DEMO SIN CONEXIÓN", Ak.Orange, filled = true)
                    h != null && h.mode.equals("live", true) -> Pill("BACKEND LIVE", Ak.Green, filled = true)
                    h != null -> Pill("BACKEND DEMO", Ak.Violet, filled = true)
                    else -> Pill("COMPROBANDO", Ak.Cyan)
                }
            }
            if (h != null && h.sources.isNotEmpty()) {
                Spacer(Modifier.height(8.dp))
                Text("FUENTES DE DATOS", color = Ak.TextMuted, style = MaterialTheme.typography.labelSmall)
                h.sources.forEach { src ->
                    val ok = src.enabled && (src.status == null || src.status.equals("ok", true) || src.status.equals("up", true))
                    Row(Modifier.padding(vertical = 3.dp), verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            Modifier
                                .size(8.dp)
                                .background(if (ok) Ak.Green else if (src.enabled) Ak.Amber else Ak.TextMuted, CircleShape),
                        )
                        Spacer(Modifier.width(8.dp))
                        Text(src.name, color = Ak.TextPrimary, style = MaterialTheme.typography.bodySmall, modifier = Modifier.weight(1f))
                        Text(
                            if (!src.enabled) "desactivada" else src.status ?: "ok",
                            color = Ak.TextSecondary,
                            style = MaterialTheme.typography.labelSmall,
                        )
                    }
                }
            }
            val disclaimer = h?.disclaimer
            if (!disclaimer.isNullOrBlank()) {
                Spacer(Modifier.height(6.dp))
                Text(disclaimer, color = Ak.TextMuted, style = MaterialTheme.typography.labelSmall)
            }
        }

        // ------------------------------------------------------------- Bankroll & Kelly
        GlassCard(accent = Ak.Lime) {
            SectionTitle("Bankroll y Kelly", accent = Ak.Lime)
            OutlinedTextField(
                value = bankrollText,
                onValueChange = { txt ->
                    bankrollText = txt
                    txt.replace(',', '.').toDoubleOrNull()?.let { if (it > 0) draft = draft.copy(bankroll = it) }
                },
                label = { Text("Bankroll (€)") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                colors = akFieldColors(),
            )
            Spacer(Modifier.height(8.dp))
            LabeledSlider(
                title = "Fracción de Kelly",
                valueText = "${kellyLabel(draft.kellyFraction)} (${draft.kellyFraction.fmt(2)})",
                value = draft.kellyFraction.toFloat(),
                range = 0.1f..1f,
                steps = 17,
                color = Ak.Lime,
                onChange = { draft = draft.copy(kellyFraction = (it * 20).toInt() / 20.0) },
            )
            LabeledSlider(
                title = "Stake máximo por apuesta",
                valueText = "${draft.maxStakePct.pct()} · ${(draft.bankroll * draft.maxStakePct).euros()}",
                value = draft.maxStakePct.toFloat(),
                range = 0.01f..0.10f,
                steps = 8,
                color = Ak.Amber,
                onChange = { draft = draft.copy(maxStakePct = (it * 100).toInt() / 100.0) },
            )
            Spacer(Modifier.height(8.dp))
            Text("PERFIL DE RIESGO", color = Ak.TextMuted, style = MaterialTheme.typography.labelSmall)
            Spacer(Modifier.height(6.dp))
            NeonSegmented(
                options = RISK_OPTIONS,
                selected = draft.riskProfile,
                onSelect = { draft = applyRiskPreset(draft, it) },
                colorFor = {
                    when (it) {
                        "conservador" -> Ak.Green
                        "agresivo" -> Ak.Red
                        else -> Ak.Lime
                    }
                },
            )
        }

        // ------------------------------------------------------------- Thresholds
        GlassCard(accent = Ak.Orange) {
            SectionTitle("Umbrales de edge", accent = Ak.Orange)
            LabeledSlider(
                title = "Edge mínimo · Tenis",
                valueText = draft.minEdgeTennis.pct(),
                value = draft.minEdgeTennis.toFloat(),
                range = 0f..0.15f,
                steps = 14,
                color = Ak.Lime,
                onChange = { draft = draft.copy(minEdgeTennis = (it * 100).toInt() / 100.0) },
            )
            LabeledSlider(
                title = "Edge mínimo · Tenis de mesa",
                valueText = draft.minEdgeTt.pct(),
                value = draft.minEdgeTt.toFloat(),
                range = 0f..0.15f,
                steps = 14,
                color = Ak.Cyan,
                onChange = { draft = draft.copy(minEdgeTt = (it * 100).toInt() / 100.0) },
            )
            LabeledSlider(
                title = "Edge sospechoso (aviso)",
                valueText = draft.suspiciousEdge.pct(),
                value = draft.suspiciousEdge.toFloat(),
                range = 0.05f..0.40f,
                steps = 34,
                color = Ak.Red,
                onChange = { draft = draft.copy(suspiciousEdge = (it * 100).toInt() / 100.0) },
            )
        }

        // ------------------------------------------------------------- Notifications
        GlassCard(accent = Ak.Magenta) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text("Notificaciones", color = Ak.TextPrimary, style = MaterialTheme.typography.titleSmall)
                    Text(
                        "Aviso local cuando llegue una alerta con edge > 5 %",
                        color = Ak.TextSecondary,
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
                Switch(
                    checked = prefs.notificationsEnabled,
                    onCheckedChange = { checked -> scope.launch { repository.setNotifications(checked) } },
                    colors = SwitchDefaults.colors(
                        checkedThumbColor = Color(0xFF0B1200),
                        checkedTrackColor = Ak.Lime,
                        uncheckedThumbColor = Ak.TextSecondary,
                        uncheckedTrackColor = Ak.SurfaceHigh,
                    ),
                )
            }
        }

        // ------------------------------------------------------------- Save
        Button(
            onClick = {
                scope.launch {
                    val synced = repository.saveSettings(draft)
                    message = if (synced) {
                        "Ajustes guardados y sincronizados con el backend ✔"
                    } else {
                        "Ajustes guardados en el dispositivo (backend no disponible)"
                    }
                }
            },
            modifier = Modifier
                .fillMaxWidth()
                .height(52.dp),
            shape = RoundedCornerShape(16.dp),
            colors = ButtonDefaults.buttonColors(containerColor = Ak.Lime, contentColor = Color(0xFF0B1200)),
        ) { Text("Guardar ajustes", fontWeight = FontWeight.Black) }
        OutlinedButton(
            onClick = {
                scope.launch {
                    val remote = repository.pullBackendSettings()
                    message = if (remote != null) "Ajustes cargados desde el backend" else "No se pudo leer /api/settings"
                }
            },
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(16.dp),
            border = BorderStroke(1.dp, Ak.Lime),
            colors = ButtonDefaults.outlinedButtonColors(contentColor = Ak.Lime),
        ) { Text("Cargar ajustes del backend") }
        val msg = message
        if (msg != null) {
            Text(msg, color = Ak.Lime, style = MaterialTheme.typography.bodySmall)
        }

        // ------------------------------------------------------------- About
        GlassCard {
            Row(verticalAlignment = Alignment.CenterVertically) {
                AkLogo(size = 48.dp)
                Spacer(Modifier.width(12.dp))
                Column {
                    Text(APP_TITLE, color = Ak.TextPrimary, fontWeight = FontWeight.Black, fontSize = 18.sp)
                    Text(APP_AUTHOR, color = Ak.TextSecondary, style = MaterialTheme.typography.bodySmall)
                    Text(
                        "Versión ${BuildConfig.VERSION_NAME} · Monitor de value bets de tenis y tenis de mesa",
                        color = Ak.TextMuted,
                        style = MaterialTheme.typography.labelSmall,
                    )
                }
            }
            Spacer(Modifier.height(8.dp))
            Text(
                "Herramienta informativa. Las probabilidades son estimaciones de modelos estadísticos y pueden fallar. " +
                    "No es asesoramiento financiero. Prohibido para menores de 18 años.",
                color = Ak.TextMuted,
                style = MaterialTheme.typography.labelSmall,
            )
        }
        Spacer(Modifier.height(16.dp))
    }
}

@Composable
private fun LabeledSlider(
    title: String,
    valueText: String,
    value: Float,
    range: ClosedFloatingPointRange<Float>,
    steps: Int,
    color: Color,
    onChange: (Float) -> Unit,
) {
    Column(Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(title, color = Ak.TextPrimary, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.weight(1f))
            Text(valueText, color = color, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.labelLarge)
        }
        Slider(
            value = value.coerceIn(range.start, range.endInclusive),
            onValueChange = onChange,
            valueRange = range,
            steps = steps,
            colors = SliderDefaults.colors(
                thumbColor = color,
                activeTrackColor = color,
                inactiveTrackColor = Color(0x22FFFFFF),
                activeTickColor = Color.Transparent,
                inactiveTickColor = Color.Transparent,
            ),
        )
    }
}

@Composable
private fun StatsDashboard(loaded: Loaded<Stats>?) {
    GlassCard(accent = Ak.Green) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            SectionTitle("Rendimiento del modelo", accent = Ak.Green, modifier = Modifier.weight(1f))
            if (loaded?.demo == true) Pill("DEMO", Ak.Orange, filled = true)
        }
        if (loaded == null) {
            LoadingBox(text = "Cargando estadísticas…")
        } else {
            StatsBody(loaded.data)
        }
    }
}

@Composable
private fun StatsBody(s: Stats) {
    Column {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            KpiTile("Value bets", "${s.nValueBets}", Ak.Lime, Modifier.weight(1f))
            KpiTile("Edge medio", s.avgEdge.pct(), Ak.Cyan, Modifier.weight(1f))
            KpiTile("ROI sim.", s.roiSim.signedPct(), if (s.roiSim >= 0) Ak.Green else Ak.Red, Modifier.weight(1f))
        }
        Spacer(Modifier.height(8.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            KpiTile("CLV medio", s.avgClv.signedPct(), if (s.avgClv >= 0) Ak.Green else Ak.Red, Modifier.weight(1f))
            KpiTile("CLV positivo", s.clvPositivePct.pct(0), Ak.Violet, Modifier.weight(1f))
            KpiTile("Acierto", s.hitRate.pct(), Ak.Amber, Modifier.weight(1f))
        }
        val curve = s.bankrollCurve
        if (curve.size >= 2) {
            Spacer(Modifier.height(14.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("Curva de bankroll (simulada)", color = Ak.TextSecondary, style = MaterialTheme.typography.labelMedium, modifier = Modifier.weight(1f))
                Text(curve.last().bankroll.euros(), color = Ak.Lime, fontWeight = FontWeight.Black)
            }
            Spacer(Modifier.height(8.dp))
            val start = curve.first().bankroll
            val up = curve.last().bankroll >= start
            LineChart(
                series = listOf(
                    ChartSeries("Bankroll", curve.map { it.bankroll.toFloat() }, if (up) Ak.Lime else Ak.Red, fill = true),
                ),
                modifier = Modifier
                    .fillMaxWidth()
                    .height(150.dp),
                referenceY = start.toFloat(),
            )
            Row {
                Text("Inicio ${start.euros()}", color = Ak.TextMuted, style = MaterialTheme.typography.labelSmall, modifier = Modifier.weight(1f))
                Text(
                    "Máx ${curve.maxOf { it.bankroll }.euros()} · Mín ${curve.minOf { it.bankroll }.euros()}",
                    color = Ak.TextMuted,
                    style = MaterialTheme.typography.labelSmall,
                )
            }
        }
        val bySport = s.bySport
        if (bySport != null && bySport.isNotEmpty()) {
            Spacer(Modifier.height(10.dp))
            bySport.entries.forEach { (sport, v) ->
                val obj = v.obj()
                val roi = obj?.get("roi").asDoubleOrNull()
                val n = obj?.get("n").asDoubleOrNull()?.toInt()
                Row(Modifier.padding(vertical = 3.dp), verticalAlignment = Alignment.CenterVertically) {
                    Box(Modifier.size(8.dp).background(Ak.sportColor(sport), CircleShape))
                    Spacer(Modifier.width(8.dp))
                    Text(sportLabel(sport), color = Ak.TextPrimary, style = MaterialTheme.typography.bodySmall, modifier = Modifier.weight(1f))
                    if (n != null) Text("$n apuestas · ", color = Ak.TextSecondary, style = MaterialTheme.typography.labelSmall)
                    Text("ROI ${roi.signedPct()}", color = if ((roi ?: 0.0) >= 0) Ak.Green else Ak.Red, style = MaterialTheme.typography.labelMedium)
                }
            }
        }
    }
}
