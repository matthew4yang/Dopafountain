package com.matthew4yang.dopafountain

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Button
import android.widget.SeekBar
import android.widget.TextView
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.materialswitch.MaterialSwitch

class MainActivity : AppCompatActivity() {
    private val notificationPermission =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            if (granted) NotificationHelper.show(this)
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        val enabled = findViewById<MaterialSwitch>(R.id.switchEnabled)
        val seek = findViewById<SeekBar>(R.id.intervalSeek)
        val label = findViewById<TextView>(R.id.intervalLabel)
        val status = findViewById<TextView>(R.id.statusText)
        val test = findViewById<Button>(R.id.testButton)

        val current = Preferences.averageMinutes(this)
        seek.progress = (current - 15).coerceIn(0, 75)
        label.text = "平均间隔：$current 分钟"
        enabled.isChecked = Preferences.enabled(this)
        status.text = if (enabled.isChecked) "喷泉正在运行" else "喷泉尚未开启"

        enabled.setOnCheckedChangeListener { _, checked ->
            Preferences.setEnabled(this, checked)
            if (checked) {
                requestNotificationsIfNeeded()
                NotificationScheduler.scheduleNext(this)
                status.text = "喷泉正在运行"
            } else {
                NotificationScheduler.cancel(this)
                status.text = "喷泉尚未开启"
            }
        }

        seek.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(bar: SeekBar?, progress: Int, fromUser: Boolean) {
                val minutes = progress + 15
                label.text = "平均间隔：$minutes 分钟"
                if (fromUser) Preferences.setAverageMinutes(this@MainActivity, minutes)
            }
            override fun onStartTrackingTouch(bar: SeekBar?) = Unit
            override fun onStopTrackingTouch(bar: SeekBar?) {
                if (Preferences.enabled(this@MainActivity)) NotificationScheduler.scheduleNext(this@MainActivity)
            }
        })

        test.setOnClickListener {
            if (Build.VERSION.SDK_INT >= 33 &&
                checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                notificationPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
            } else {
                NotificationHelper.show(this)
            }
        }
    }

    private fun requestNotificationsIfNeeded() {
        if (Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            notificationPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
    }
}
