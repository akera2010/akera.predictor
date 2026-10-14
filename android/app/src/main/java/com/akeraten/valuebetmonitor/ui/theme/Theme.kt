package com.akeraten.valuebetmonitor.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

private val AkColors = darkColorScheme(
    primary = Ak.Lime,
    onPrimary = Color(0xFF0B1200),
    primaryContainer = Color(0xFF2B3A00),
    onPrimaryContainer = Ak.Lime,
    secondary = Ak.Cyan,
    onSecondary = Color(0xFF001F24),
    tertiary = Ak.Orange,
    onTertiary = Color(0xFF2A1400),
    background = Ak.Bg,
    onBackground = Ak.TextPrimary,
    surface = Ak.Surface,
    onSurface = Ak.TextPrimary,
    surfaceVariant = Ak.SurfaceHigh,
    onSurfaceVariant = Ak.TextSecondary,
    surfaceContainer = Ak.Surface,
    error = Ak.Red,
    onError = Color.White,
    outline = Ak.Border,
)

private val Base = Typography()

private val AkTypography = Typography(
    displaySmall = Base.displaySmall.copy(fontWeight = FontWeight.Black, letterSpacing = (-0.5).sp),
    headlineMedium = Base.headlineMedium.copy(fontWeight = FontWeight.ExtraBold),
    headlineSmall = Base.headlineSmall.copy(fontWeight = FontWeight.ExtraBold),
    titleLarge = Base.titleLarge.copy(fontWeight = FontWeight.Bold),
    titleMedium = Base.titleMedium.copy(fontWeight = FontWeight.SemiBold),
    titleSmall = Base.titleSmall.copy(fontWeight = FontWeight.SemiBold),
    bodyLarge = Base.bodyLarge,
    bodyMedium = Base.bodyMedium,
    bodySmall = Base.bodySmall,
    labelLarge = Base.labelLarge.copy(fontWeight = FontWeight.Bold),
    labelMedium = Base.labelMedium.copy(fontWeight = FontWeight.SemiBold),
    labelSmall = Base.labelSmall.copy(fontWeight = FontWeight.SemiBold, letterSpacing = 0.8.sp),
)

val MonoNumbers = TextStyle(fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold)

@Composable
fun AkeratenTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = AkColors,
        typography = AkTypography,
        content = content,
    )
}
