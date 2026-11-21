package com.fraudshield.app

import android.app.Application
import dagger.hilt.android.HiltAndroidApp
import androidx.hilt.work.HiltWorkerFactory
import androidx.work.Configuration
import com.fraudshield.app.data.monitoring.WarningPublisher
import javax.inject.Inject

@HiltAndroidApp
class FraudShieldApplication : Application(), Configuration.Provider {
    @Inject lateinit var workerFactory: HiltWorkerFactory
    @Inject lateinit var publisher: WarningPublisher
    override val workManagerConfiguration: Configuration get() = Configuration.Builder()
        .setWorkerFactory(workerFactory).setMinimumLoggingLevel(android.util.Log.WARN).build()
    override fun onCreate() { super.onCreate(); publisher.createChannels() }
}
