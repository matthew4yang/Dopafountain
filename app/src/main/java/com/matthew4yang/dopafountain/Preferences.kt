package com.matthew4yang.dopafountain

import android.content.Context

object Preferences {
    private const val NAME = "dopafountain"
    fun enabled(context: Context): Boolean =
        context.getSharedPreferences(NAME, Context.MODE_PRIVATE).getBoolean("enabled", false)
    fun setEnabled(context: Context, value: Boolean) =
        context.getSharedPreferences(NAME, Context.MODE_PRIVATE).edit().putBoolean("enabled", value).apply()
    fun averageMinutes(context: Context): Int =
        context.getSharedPreferences(NAME, Context.MODE_PRIVATE).getInt("avg_minutes", 30)
    fun setAverageMinutes(context: Context, value: Int) =
        context.getSharedPreferences(NAME, Context.MODE_PRIVATE).edit().putInt("avg_minutes", value).apply()
}
