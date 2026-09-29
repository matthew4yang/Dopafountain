package com.matthew4yang.dopafountain

import android.content.Context
import androidx.work.Worker
import androidx.work.WorkerParameters
import java.time.LocalTime

class GoodNewsWorker(appContext: Context, params: WorkerParameters) : Worker(appContext, params) {
    override fun doWork(): Result {
        if (!Preferences.enabled(applicationContext)) return Result.success()

        val now = LocalTime.now()
        val quiet = now >= LocalTime.of(23, 0) || now < LocalTime.of(8, 0)

        if (quiet) {
            NotificationScheduler.scheduleAfterQuietHours(applicationContext)
            return Result.success()
        }

        val item = GoodNewsRepository.next(applicationContext)
        if (item != null) {
            NotificationHelper.show(applicationContext, item)
        }

        NotificationScheduler.scheduleNext(applicationContext)
        return Result.success()
    }
}
