package com.akeraten.valuebetmonitor.ui

import android.Manifest
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.Crossfade
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.akeraten.valuebetmonitor.AppContainer
import com.akeraten.valuebetmonitor.ui.components.BrandHeader
import com.akeraten.valuebetmonitor.ui.screens.AnalysisScreen
import com.akeraten.valuebetmonitor.ui.screens.ExpertsScreen
import com.akeraten.valuebetmonitor.ui.screens.LiveScreen
import com.akeraten.valuebetmonitor.ui.screens.MatchDetailScreen
import com.akeraten.valuebetmonitor.ui.screens.SettingsScreen
import com.akeraten.valuebetmonitor.ui.screens.SplashScreen
import com.akeraten.valuebetmonitor.ui.screens.ValueBetsScreen
import com.akeraten.valuebetmonitor.ui.theme.Ak

private data class Tab(val route: String, val label: String, val icon: ImageVector, val color: Color)

private val TABS = listOf(
    Tab(Routes.LIVE, "En Vivo", Icons.Filled.PlayArrow, Ak.Red),
    Tab(Routes.VALUE, "Value Bets", Icons.Filled.Star, Ak.Lime),
    Tab(Routes.EXPERTS, "Expertos", Icons.Filled.Person, Ak.Cyan),
    Tab(Routes.SETTINGS, "Ajustes", Icons.Filled.Settings, Ak.Orange),
)

object Routes {
    const val LIVE = "live"
    const val VALUE = "value"
    const val EXPERTS = "experts"
    const val SETTINGS = "settings"
    const val MATCH = "match/{id}"
    const val ANALYSIS = "analysis/{matchId}?bet={bet}"

    fun match(id: String) = "match/${Uri.encode(id)}"
    fun analysis(matchId: String, betKey: String?) =
        "analysis/${Uri.encode(matchId)}" + if (betKey != null) "?bet=${Uri.encode(betKey)}" else ""
}

@Composable
fun AkeratenRoot(container: AppContainer) {
    var showSplash by rememberSaveable { mutableStateOf(true) }
    NotificationPermissionRequest()
    Crossfade(targetState = showSplash, animationSpec = tween(500), label = "splash") { splash ->
        if (splash) {
            SplashScreen(onFinished = { showSplash = false })
        } else {
            MainScaffold(container)
        }
    }
}

@Composable
private fun NotificationPermissionRequest() {
    if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) return
    val context = LocalContext.current
    val launcher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { }
    LaunchedEffect(Unit) {
        val granted = ContextCompat.checkSelfPermission(
            context, Manifest.permission.POST_NOTIFICATIONS,
        ) == PackageManager.PERMISSION_GRANTED
        if (!granted) launcher.launch(Manifest.permission.POST_NOTIFICATIONS)
    }
}

@Composable
private fun MainScaffold(container: AppContainer) {
    val repository = container.repository
    val navController = rememberNavController()
    val backStack by navController.currentBackStackEntryAsState()
    val currentRoute = backStack?.destination?.route
    val mode by repository.mode.collectAsState()
    val connection by repository.connection.collectAsState()
    val showBottomBar = TABS.any { it.route == currentRoute } || currentRoute == null

    Box(
        Modifier
            .fillMaxSize()
            .background(Ak.BackgroundBrush),
    ) {
        Scaffold(
            containerColor = Color.Transparent,
            contentColor = Ak.TextPrimary,
            topBar = { BrandHeader(mode = mode, connection = connection) },
            bottomBar = {
                if (showBottomBar) {
                    BottomBar(navController, currentRoute)
                }
            },
        ) { inner ->
            NavHost(
                navController = navController,
                startDestination = Routes.LIVE,
                modifier = Modifier.padding(inner),
            ) {
                composable(Routes.LIVE) {
                    LiveScreen(
                        repository = repository,
                        onOpenMatch = { id -> navController.navigate(Routes.match(id)) },
                    )
                }
                composable(Routes.VALUE) {
                    ValueBetsScreen(
                        repository = repository,
                        onOpenAnalysis = { matchId, betKey ->
                            navController.navigate(Routes.analysis(matchId, betKey))
                        },
                    )
                }
                composable(Routes.EXPERTS) { ExpertsScreen(repository) }
                composable(Routes.SETTINGS) { SettingsScreen(repository) }
                composable(
                    route = Routes.MATCH,
                    arguments = listOf(navArgument("id") { type = NavType.StringType }),
                ) { entry ->
                    val id = entry.arguments?.getString("id").orEmpty()
                    MatchDetailScreen(
                        repository = repository,
                        matchId = id,
                        onBack = { navController.popBackStack() },
                        onOpenAnalysis = { mid -> navController.navigate(Routes.analysis(mid, null)) },
                    )
                }
                composable(
                    route = Routes.ANALYSIS,
                    arguments = listOf(
                        navArgument("matchId") { type = NavType.StringType },
                        navArgument("bet") {
                            type = NavType.StringType
                            nullable = true
                            defaultValue = null
                        },
                    ),
                ) { entry ->
                    AnalysisScreen(
                        repository = repository,
                        matchId = entry.arguments?.getString("matchId").orEmpty(),
                        betKey = entry.arguments?.getString("bet"),
                        onBack = { navController.popBackStack() },
                    )
                }
            }
        }
    }
}

@Composable
private fun BottomBar(navController: NavHostController, currentRoute: String?) {
    NavigationBar(containerColor = Color(0xF20A1124), tonalElevation = 0.dp) {
        TABS.forEach { tab ->
            val selected = currentRoute == tab.route || (currentRoute == null && tab.route == Routes.LIVE)
            NavigationBarItem(
                selected = selected,
                onClick = {
                    if (!selected) {
                        navController.navigate(tab.route) {
                            popUpTo(navController.graph.findStartDestination().id) { saveState = true }
                            launchSingleTop = true
                            restoreState = true
                        }
                    }
                },
                icon = { Icon(tab.icon, contentDescription = tab.label) },
                label = {
                    Text(tab.label, fontWeight = if (selected) FontWeight.Bold else FontWeight.Normal)
                },
                colors = NavigationBarItemDefaults.colors(
                    selectedIconColor = tab.color,
                    selectedTextColor = tab.color,
                    indicatorColor = tab.color.copy(alpha = 0.16f),
                    unselectedIconColor = Ak.TextSecondary,
                    unselectedTextColor = Ak.TextSecondary,
                ),
            )
        }
    }
}
