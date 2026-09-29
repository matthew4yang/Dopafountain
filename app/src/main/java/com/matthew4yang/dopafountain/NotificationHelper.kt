package com.matthew4yang.dopafountain

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat

object NotificationHelper {
    private const val CHANNEL_ID = "dopafountain_hard_news"

    fun show(context: Context, item: GoodNews) {
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            manager.createNotificationChannel(
                NotificationChannel(CHANNEL_ID, "硬核好消息", NotificationManager.IMPORTANCE_DEFAULT).apply {
                    description = "来自互联网权威来源的事实型好消息"
                }
            )
        }

        if (Build.VERSION.SDK_INT >= 33 &&
            ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS)
            != PackageManager.PERMISSION_GRANTED
        ) return

        val openIntent = if (item.url.isNotBlank()) {
            PendingIntent.getActivity(
                context,
                item.id.hashCode(),
                Intent(Intent.ACTION_VIEW, Uri.parse(item.url)),
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
        } else null

        val builder = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle(item.title)
            .setAutoCancel(true)
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)

        if (item.text.isNotBlank() && item.text != item.title) {
            builder
                .setContentText(item.text)
                .setStyle(NotificationCompat.BigTextStyle().bigText(item.text))
        }

        if (item.source.isNotBlank()) builder.setSubText(item.source)
        if (openIntent != null) builder.setContentIntent(openIntent)

        NotificationManagerCompat.from(context)
            .notify(item.id.hashCode(), builder.build())
    }
}
