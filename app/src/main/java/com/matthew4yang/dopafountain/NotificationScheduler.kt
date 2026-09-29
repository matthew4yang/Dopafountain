package com.matthew4yang.dopafountain

import android.content.Context
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import java.util.concurrent.TimeUnit
import kotlin.math.max
import kotlin.random.Random

object NotificationScheduler {
    private const val UNIQUE_WORK = "dopafountain_next"

    fun scheduleNext(context: Context) {
        if (!Preferences.enabled(context)) return
        val avg = Preferences.averageMinutes(context)
        val min = max(15, (avg * 0.5).toInt())
        val max = max(min + 1, (avg * 2.0).toInt())
        val a = Random.nextInt(min, max + 1)
        val b = Random.nextInt(min, max + 1)
        var delay = (a + b) / 2
        if (Random.nextInt(100) < 7) delay += Random.nextInt(15, 46)

        val request = OneTimeWorkRequestBuilder<GoodNewsWorker>()
            .setInitialDelay(delay.toLong(), TimeUnit.MINUTES)
            .build()

        WorkManager.getInstance(context).enqueueUniqueWork(
            UNIQUE_WORK, ExistingWorkPolicy.REPLACE, request
        )
    }

    fun cancel(context: Context) =
        WorkManager.getInstance(context).cancelUniqueWork(UNIQUE_WORK)
}
