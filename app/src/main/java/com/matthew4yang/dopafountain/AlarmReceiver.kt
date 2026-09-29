package com.matthew4yang.dopafountain

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager

class AlarmReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent?) {
        if (!Preferences.enabled(context)) return

        val request = OneTimeWorkRequestBuilder<GoodNewsWorker>().build()
        WorkManager.getInstance(context).enqueue(request)
    }
}
