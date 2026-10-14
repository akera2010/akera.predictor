package com.akeraten.valuebetmonitor.ui.screens

import androidx.compose.ui.graphics.Color
import com.akeraten.valuebetmonitor.data.model.Prediction
import com.akeraten.valuebetmonitor.data.model.ValueBet
import com.akeraten.valuebetmonitor.ui.theme.Ak
import com.akeraten.valuebetmonitor.util.asDoubleOrNull
import com.akeraten.valuebetmonitor.util.asFraction
import com.akeraten.valuebetmonitor.util.obj
import kotlinx.serialization.json.JsonObject

/** One model in the ensemble, probability expressed for the selected side. */
data class ModelEntry(
    val key: String,
    val name: String,
    val prob: Double?,
    val weight: Double?,
    val color: Color,
    val note: String? = null,
)

private fun JsonObject?.probA(vararg keys: String): Double? {
    if (this == null) return null
    for (k in keys) {
        val v = this[k].asDoubleOrNull()
        if (v != null) return v.asFraction()
    }
    return null
}

/** Monte Carlo set-score distribution as (score, probability) pairs. */
fun setScoreDistribution(prediction: Prediction?): List<Pair<String, Double>> {
    val mc = prediction?.breakdown?.get("monte_carlo").obj() ?: return emptyList()
    val dist = mc["set_score_dist"].obj() ?: return emptyList()
    return dist.entries.mapNotNull { e -> e.value.asDoubleOrNull()?.let { e.key to it.asFraction() } }
}

fun monteCarloIterations(prediction: Prediction?): Int? {
    val mc = prediction?.breakdown?.get("monte_carlo").obj() ?: return null
    return mc["iterations"].asDoubleOrNull()?.toInt()
}

fun expertsCount(prediction: Prediction?): Int? {
    val ex = prediction?.breakdown?.get("experts").obj() ?: return null
    return ex["n"].asDoubleOrNull()?.toInt()
}

/** True when the set score (e.g. "2-1") is a win for player A. */
fun isScoreForA(score: String): Boolean {
    val parts = score.split("-", ":").mapNotNull { it.trim().toIntOrNull() }
    return parts.size == 2 && parts[0] > parts[1]
}

/**
 * Builds the model breakdown list. Values come from the value bet (already expressed for
 * the selection) when available, otherwise from the prediction breakdown (player A, flipped
 * when the selection is player B).
 */
fun modelEntries(prediction: Prediction?, bet: ValueBet?, sideB: Boolean): List<ModelEntry> {
    val bd = prediction?.breakdown
    val weights = prediction?.weights
    fun flip(p: Double?): Double? = p?.let { if (sideB) 1.0 - it else it }
    fun w(key: String): Double? = weights?.get(key).asDoubleOrNull()

    val elo = bet?.models?.elo?.asFraction() ?: flip(bd?.get("elo").obj().probA("prob_a", "prob", "p_a"))
    val ml = bet?.models?.ml?.asFraction() ?: flip(bd?.get("ml").obj().probA("prob_a", "prob", "p_a"))
    val mc = bet?.models?.monteCarlo?.asFraction() ?: flip(bd?.get("monte_carlo").obj().probA("prob_a", "prob"))
    val ex = bet?.models?.experts?.asFraction() ?: flip(bd?.get("experts").obj().probA("consensus_a", "prob_a"))
    val ens = bet?.models?.ensemble?.asFraction()
        ?: bet?.modelProb?.asFraction()
        ?: prediction?.let { if (sideB) it.probB.asFraction() else it.probA.asFraction() }

    val nExperts = expertsCount(prediction)
    val iters = monteCarloIterations(prediction)
    return listOf(
        ModelEntry("elo", "Elo", elo, w("elo"), Ak.Cyan, "Rating Elo ajustado por superficie"),
        ModelEntry("ml", "ML", ml, w("ml"), Ak.Violet, "Gradient boosting con forma, saque/resto y fatiga"),
        ModelEntry(
            "monte_carlo", "Monte Carlo", mc, w("monte_carlo"), Ak.Orange,
            if (iters != null) "$iters simulaciones punto a punto" else "Simulación punto a punto",
        ),
        ModelEntry(
            "experts", "Expertos", ex, w("experts"), Ak.Magenta,
            if (ex == null) "Sin consenso de expertos" else if (nExperts != null) "Consenso de $nExperts expertos" else "Consenso de expertos",
        ),
        ModelEntry("ensemble", "Ensemble", ens, null, Ak.Lime, "Combinación ponderada final"),
    )
}
