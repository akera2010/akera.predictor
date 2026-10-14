package com.akeraten.valuebetmonitor.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextFieldColors
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.akeraten.valuebetmonitor.ui.theme.Ak

@Composable
fun akFieldColors(accent: Color = Ak.Lime): TextFieldColors = OutlinedTextFieldDefaults.colors(
    focusedTextColor = Ak.TextPrimary,
    unfocusedTextColor = Ak.TextPrimary,
    focusedBorderColor = accent,
    unfocusedBorderColor = Ak.Border,
    cursorColor = accent,
    focusedLabelColor = accent,
    unfocusedLabelColor = Ak.TextSecondary,
    focusedLeadingIconColor = accent,
    unfocusedLeadingIconColor = Ak.TextSecondary,
    focusedPlaceholderColor = Ak.TextMuted,
    unfocusedPlaceholderColor = Ak.TextMuted,
    focusedContainerColor = Color(0x0FFFFFFF),
    unfocusedContainerColor = Color(0x0AFFFFFF),
)

/** Custom neon segmented control (no experimental Material APIs). */
@Composable
fun NeonSegmented(
    options: List<Pair<String, String>>,
    selected: String,
    onSelect: (String) -> Unit,
    modifier: Modifier = Modifier,
    colorFor: (String) -> Color = { Ak.Lime },
) {
    val outer = RoundedCornerShape(14.dp)
    Row(
        modifier = modifier
            .fillMaxWidth()
            .clip(outer)
            .background(Color(0x0FFFFFFF), outer)
            .border(1.dp, Ak.Border, outer)
            .padding(4.dp),
    ) {
        options.forEach { (value, label) ->
            val isSel = value == selected
            val color = colorFor(value)
            val inner = RoundedCornerShape(10.dp)
            Box(
                modifier = Modifier
                    .weight(1f)
                    .clip(inner)
                    .background(if (isSel) color.copy(alpha = 0.22f) else Color.Transparent, inner)
                    .border(1.dp, if (isSel) color else Color.Transparent, inner)
                    .clickable { onSelect(value) }
                    .padding(vertical = 10.dp),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    label,
                    color = if (isSel) color else Ak.TextSecondary,
                    style = MaterialTheme.typography.labelLarge,
                    textAlign = TextAlign.Center,
                    maxLines = 1,
                )
            }
        }
    }
}
