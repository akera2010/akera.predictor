package com.akeraten.valuebetmonitor.ui.screens

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.akeraten.valuebetmonitor.ui.components.APP_AUTHOR
import com.akeraten.valuebetmonitor.ui.components.AkLogo
import com.akeraten.valuebetmonitor.ui.theme.Ak
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

@Composable
fun SplashScreen(onFinished: () -> Unit) {
    val logoScale = remember { Animatable(0.4f) }
    val textAlpha = remember { Animatable(0f) }
    LaunchedEffect(Unit) {
        launch { logoScale.animateTo(1f, tween(700, easing = FastOutSlowInEasing)) }
        delay(300)
        textAlpha.animateTo(1f, tween(600))
        delay(900)
        onFinished()
    }
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.radialGradient(
                    listOf(Color(0xFF1A2A00), Color(0xFF0A1330), Ak.BgDeep),
                ),
            ),
        contentAlignment = Alignment.Center,
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
            AkLogo(
                size = 132.dp,
                modifier = Modifier.graphicsLayer {
                    scaleX = logoScale.value
                    scaleY = logoScale.value
                },
            )
            Spacer(Modifier.height(24.dp))
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier.graphicsLayer { alpha = textAlpha.value },
            ) {
                Text(
                    "AKERATEN",
                    color = Ak.TextPrimary,
                    fontWeight = FontWeight.Black,
                    fontSize = 38.sp,
                    letterSpacing = 6.sp,
                )
                Text(
                    "v.0.1",
                    color = Ak.Lime,
                    fontWeight = FontWeight.Bold,
                    fontSize = 18.sp,
                    letterSpacing = 3.sp,
                )
                Spacer(Modifier.height(12.dp))
                Box(
                    Modifier
                        .width(120.dp)
                        .height(3.dp)
                        .background(Ak.TtBrush, RoundedCornerShape(2.dp)),
                )
                Spacer(Modifier.height(12.dp))
                Text(
                    "Value-betting monitor · Tenis & Tenis de mesa",
                    color = Ak.TextSecondary,
                    fontSize = 13.sp,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.padding(horizontal = 24.dp),
                )
                Spacer(Modifier.height(28.dp))
                Text(APP_AUTHOR, color = Ak.TextMuted, fontSize = 12.sp)
            }
        }
    }
}
