package com.matthew4yang.dopafountain

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Button
import android.widget.SeekBar
import android.widget.TextView
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.materialswitch.MaterialSwitch

class MainActivity : AppCompatActivity() {
    private lateinit var status: TextView
    private lateinit var historyText: TextView

    private val notificationPermission =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            if (granted) testOnlineMessage()
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        val enabled = findViewById<MaterialSwitch>(R.id.switchEnabled)
        val seek = findViewById<SeekBar>(R.id.intervalSeek)
        val label = findViewById<TextView>(R.id.intervalLabel)
        status = findViewById(R.id.statusText)
        val test = findViewById<Button>(R.id.testButton)
        historyText = findViewById(R.id.historyText)
        val clearHistory = findViewById<Button>(R.id.clearHistoryButton)

        val current = Preferences.averageMinutes(this)
        seek.progress = (current - 15).coerceIn(0, 75)
        label.text = "平均间隔：$current 分钟"
        enabled.isChecked = Preferences.enabled(this)
        updateStatus(enabled.isChecked)
        refreshHistory()

        if (enabled.isChecked) {
            NotificationScheduler.scheduleNext(this)
        }

        enabled.setOnCheckedChangeListener { _, checked ->
            Preferences.setEnabled(this, checked)
            if (checked) {
                requestNotificationsIfNeeded()
                NotificationScheduler.scheduleNext(this)
            } else {
                NotificationScheduler.cancel(this)
            }
            updateStatus(checked)
        }

        seek.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(bar: SeekBar?, progress: Int, fromUser: Boolean) {
                val minutes = progress + 15
                label.text = "平均间隔：$minutes 分钟"
                if (fromUser) Preferences.setAverageMinutes(this@MainActivity, minutes)
            }

            override fun onStartTrackingTouch(bar: SeekBar?) = Unit

            override fun onStopTrackingTouch(bar: SeekBar?) {
                if (Preferences.enabled(this@MainActivity)) {
                    NotificationScheduler.scheduleNext(this@MainActivity)
                }
            }
        })

        clearHistory.setOnClickListener {
            HistoryStore.clear(this)
            refreshHistory()
        }

        test.setOnClickListener {
            if (Build.VERSION.SDK_INT >= 33 &&
                checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
            ) {
                notificationPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
            } else {
                testOnlineMessage()
            }
        }
    }

    override fun onResume() {
        super.onResume()
        refreshHistory()
        if (Preferences.enabled(this)) {
            NotificationScheduler.scheduleNext(this)
        }
    }

    private fun refreshHistory() {
        val items = HistoryStore.load(this)
        if (items.isEmpty()) {
            historyText.text = "尚无历史消息"
            return
        }
        val fmt = SimpleDateFormat("MM-dd HH:mm", Locale.getDefault())
        historyText.text = items.take(40).joinToString("\n\n") { item ->
            val whenText = fmt.format(Date(item.shownAt))
            val head = listOf(item.category, item.source, whenText)
                .filter { it.isNotBlank() }
                .joinToString(" · ")
            val fact = item.text.ifBlank { item.title }
            "$head\n$fact"
        }
    }

    private fun testOnlineMessage() {
        status.text = "正在从互联网消息池取一条……"
        Thread {
            val item = GoodNewsRepository.next(this, forceRefresh = true)
            runOnUiThread {
                if (item == null) {
                    status.text = "当前没有取得合格的在线硬核消息；不会用空泛内容补位。"
                } else {
                    NotificationHelper.show(this, item)
                    status.text = "已取得在线消息 · ${item.source}"
                }
            }
        }.start()
    }

    private fun updateStatus(enabled: Boolean) {
        val count = GoodNewsRepository.cachedCount(this)
        status.text = if (enabled) {
            if (count > 0) "在线硬核消息池 · 缓存 $count 条 · 随机推送中"
            else "在线硬核消息池 · 等待首次获取"
        } else {
            "喷泉尚未开启"
        }
    }

    private fun requestNotificationsIfNeeded() {
        if (Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) {
            notificationPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
    }
}
