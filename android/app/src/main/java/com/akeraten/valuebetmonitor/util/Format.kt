package com.akeraten.valuebetmonitor.util

import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import java.util.Locale
import kotlin.math.abs

private val ES: Locale = Locale.forLanguageTag("es-ES")

/** Accepts either a fraction (0.07) or a percentage (7.0) and returns a fraction. */
fun Double.asFraction(): Double = if (abs(this) > 1.0) this / 100.0 else this

fun Double?.pct(decimals: Int = 1): String {
    if (this == null || this.isNaN()) return "—"
    return String.format(ES, "%.${decimals}f %%", this.asFraction() * 100.0)
}

fun Double?.signedPct(decimals: Int = 1): String {
    if (this == null || this.isNaN()) return "—"
    val v = this.asFraction() * 100.0
    val sign = if (v > 0) "+" else ""
    return sign + String.format(ES, "%.${decimals}f %%", v)
}

fun Double?.euros(): String {
    if (this == null || this.isNaN()) return "—"
    return String.format(ES, "%,.2f €", this)
}

fun Double?.fmt(decimals: Int = 2): String {
    if (this == null || this.isNaN()) return "—"
    return String.format(ES, "%.${decimals}f", this)
}

/** Implied probability from decimal odds (no margin removal). */
fun impliedFromOdds(odds: Double?): Double? =
    if (odds == null || odds <= 1.0) null else 1.0 / odds

/** Implied probability for player A, normalised to remove the bookmaker margin. */
fun fairImpliedA(oddsA: Double?, oddsB: Double?): Double? {
    val ia = impliedFromOdds(oddsA) ?: return null
    val ib = impliedFromOdds(oddsB) ?: return ia
    val total = ia + ib
    return if (total <= 0.0) null else ia / total
}

/** Emoji flag from an ISO-3166 alpha-2 (or common alpha-3 / IOC) country code. */
fun flagEmoji(code: String?): String {
    if (code.isNullOrBlank()) return "🏳️"
    val raw = code.trim().uppercase(Locale.ROOT)
    val iso2 = when {
        raw.length == 2 -> raw
        else -> ISO3_TO_ISO2[raw] ?: return "🏳️"
    }
    if (!iso2.all { it in 'A'..'Z' }) return "🏳️"
    val first = Character.toChars(0x1F1E6 + (iso2[0] - 'A'))
    val second = Character.toChars(0x1F1E6 + (iso2[1] - 'A'))
    return String(first) + String(second)
}

private val ISO3_TO_ISO2: Map<String, String> = mapOf(
    "ESP" to "ES", "USA" to "US", "GBR" to "GB", "FRA" to "FR", "GER" to "DE", "DEU" to "DE",
    "ITA" to "IT", "SRB" to "RS", "RUS" to "RU", "SUI" to "CH", "CHE" to "CH", "AUT" to "AT",
    "AUS" to "AU", "ARG" to "AR", "BRA" to "BR", "CAN" to "CA", "CHN" to "CN", "JPN" to "JP",
    "KOR" to "KR", "TPE" to "TW", "TWN" to "TW", "HKG" to "HK", "SWE" to "SE", "NOR" to "NO",
    "DEN" to "DK", "DNK" to "DK", "POL" to "PL", "CZE" to "CZ", "SVK" to "SK", "CRO" to "HR",
    "HRV" to "HR", "GRE" to "GR", "GRC" to "GR", "POR" to "PT", "PRT" to "PT", "NED" to "NL",
    "NLD" to "NL", "BEL" to "BE", "BUL" to "BG", "BGR" to "BG", "ROU" to "RO", "UKR" to "UA",
    "BLR" to "BY", "KAZ" to "KZ", "CHI" to "CL", "CHL" to "CL", "COL" to "CO", "MEX" to "MX",
    "IND" to "IN", "EGY" to "EG", "TUN" to "TN", "RSA" to "ZA", "ZAF" to "ZA", "SLO" to "SI",
    "SVN" to "SI", "HUN" to "HU", "FIN" to "FI", "SGP" to "SG", "BRN" to "BH", "NGR" to "NG",
    "IRI" to "IR", "IRN" to "IR", "SWI" to "CH", "LAT" to "LV", "LTU" to "LT", "EST" to "EE",
)

fun JsonElement?.asDoubleOrNull(): Double? {
    val p = this as? JsonPrimitive ?: return null
    if (p is JsonNull) return null
    return p.content.toDoubleOrNull()
}

fun JsonElement?.asStringOrNull(): String? {
    val p = this as? JsonPrimitive ?: return null
    if (p is JsonNull) return null
    return p.content
}

fun JsonElement?.obj(): JsonObject? = this as? JsonObject

/** Human readable text for an arbitrary JSON value. */
fun JsonElement?.displayText(): String = when (this) {
    null, is JsonNull -> "—"
    is JsonPrimitive -> {
        val d = content.toDoubleOrNull()
        when {
            isString -> content
            d != null && d != Math.floor(d) -> String.format(ES, "%.2f", d)
            else -> content
        }
    }
    is JsonArray -> joinToString(" · ") { it.displayText() }
    is JsonObject -> entries.joinToString(", ") { "${it.key}: ${it.value.displayText()}" }
}

fun prettyKey(key: String): String =
    key.replace('_', ' ').replaceFirstChar { if (it.isLowerCase()) it.titlecase(ES) else it.toString() }

/** "2026-10-14T18:30:00Z" -> "14/10 18:30" (best effort, no java.time parsing failures). */
fun shortTime(iso: String?): String {
    if (iso.isNullOrBlank()) return ""
    val m = Regex("""(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})""").find(iso) ?: return iso.take(16)
    val (_, mo, d, h, mi) = m.destructured
    return "$d/$mo $h:$mi"
}

fun sportLabel(sport: String): String =
    if (sport.equals("table_tennis", ignoreCase = true)) "Tenis de mesa" else "Tenis"

fun sportEmoji(sport: String): String =
    if (sport.equals("table_tennis", ignoreCase = true)) "🏓" else "🎾"
