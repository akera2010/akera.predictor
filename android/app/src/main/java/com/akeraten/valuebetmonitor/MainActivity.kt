package com.akeraten.valuebetmonitor

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import com.akeraten.valuebetmonitor.ui.AkeratenRoot
import com.akeraten.valuebetmonitor.ui.theme.AkeratenTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge(
            statusBarStyle = SystemBarStyle.dark(android.graphics.Color.TRANSPARENT),
            navigationBarStyle = SystemBarStyle.dark(android.graphics.Color.TRANSPARENT),
        )
        super.onCreate(savedInstanceState)
        val container = (application as AkeratenApp).container
        setContent {
            AkeratenTheme {
                AkeratenRoot(container)
            }
        }
    }
}
