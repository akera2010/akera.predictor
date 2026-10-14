package com.akeraten.valuebetmonitor

import android.app.Application
import android.content.Context
import com.akeraten.valuebetmonitor.data.Repository
import com.akeraten.valuebetmonitor.data.local.SettingsStore
import com.akeraten.valuebetmonitor.notifications.Notifier
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob

/** Manual dependency container (no DI framework). */
class AppContainer(context: Context) {
    val appScope: CoroutineScope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    val settingsStore = SettingsStore(context)
    val notifier = Notifier(context)
    val repository = Repository(settingsStore, notifier, appScope)
}

class AkeratenApp : Application() {
    lateinit var container: AppContainer
        private set

    override fun onCreate() {
        super.onCreate()
        container = AppContainer(this)
        container.notifier.createChannel()
        container.repository.start()
    }
}
