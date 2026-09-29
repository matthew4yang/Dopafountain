package com.matthew4yang.dopafountain

import android.app.AlarmManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.SystemClock
import androidx.work.WorkManager
import java.time.Duration
import java.time.LocalDateTime
import kotlin.math.max
import kotlin.math.roundToInt
import kotlin.random.Random

object NotificationScheduler {
    private const val REQUEST_CODE = 24091
    private const val LEGACY_WORK = "dopafountain_next"

    fun scheduleNext(context: Context) {
        if (!Preferences.enabled(context)) return

        // Remove delayed WorkManager jobs left by older versions.
        WorkManager.getInstance(context).cancelUniqueWork(LEGACY_WORK)

        scheduleAlarm(context, nextDelayMinutes(context))
    }

    fun scheduleAfterQuietHours(context: Context) {
        if (!Preferences.enabled(context)) return

        val now = LocalDateTime.now()
        var target = now.withHour(8).withMinute(0).withSecond(0).withNano(0)
        if (!target.isAfter(now)) target = target.plusDays(1)

        // Keep morning restart slightly irregular.
        target = target.plusMinutes(Random.nextLong(0, 16))
        val minutes = max(1L, Duration.between(now, target).toMinutes())
        scheduleAlarm(context, minutes.toInt())
    }

    private fun nextDelayMinutes(context: Context): Int {
        val avg = Preferences.averageMinutes(context)

        // True centre around the selected average.
        // 15 min => roughly 10–20 min; 30 min => roughly 20–40 min.
        val low = max(5, (avg * 0.65).roundToInt())
        val high = max(low + 1, (avg * 1.35).roundToInt())

        // Two draws make the middle more common without becoming regular.
        val a = Random.nextInt(low, high + 1)
        val b = Random.nextInt(low, high + 1)
        return max(5, ((a + b) / 2.0).roundToInt())
    }

    private fun scheduleAlarm(context: Context, delayMinutes: Int) {
        val alarmManager = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        val pending = PendingIntent.getBroadcast(
            context,
            REQUEST_CODE,
            Intent(context, AlarmReceiver::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val trigger = SystemClock.elapsedRealtime() + delayMinutes * 60_000L
        alarmManager.setAndAllowWhileIdle(
            AlarmManager.ELAPSED_REALTIME_WAKEUP,
            trigger,
            pending
        )
    }

    fun cancel(context: Context) {
        val alarmManager = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        val pending = PendingIntent.getBroadcast(
            context,
            REQUEST_CODE,
            Intent(context, AlarmReceiver::class.java),
            PendingIntent.FLAG_NO_CREATE or PendingIntent.FLAG_IMMUTABLE
        )
        if (pending != null) {
            alarmManager.cancel(pending)
            pending.cancel()
        }
        WorkManager.getInstance(context).cancelUniqueWork(LEGACY_WORK)
    }
}
