package com.matthew4yang.dopafountain

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

data class HistoryEntry(
    val id: String,
    val category: String,
    val title: String,
    val text: String,
    val source: String,
    val url: String,
    val publishedAt: String,
    val shownAt: Long
)

object HistoryStore {
    private const val PREFS = "dopafountain_history"
    private const val KEY = "items"
    private const val DELIVERED_KEY = "delivered_ids"
    private const val MAX_ITEMS = 200
    private const val MAX_DELIVERED_IDS = 5000

    fun add(context: Context, item: GoodNews) {
        val current = load(context).toMutableList()
        current.removeAll { it.id == item.id }
        current.add(
            0,
            HistoryEntry(
                id = item.id,
                category = item.category,
                title = item.title,
                text = item.text,
                source = item.source,
                url = item.url,
                publishedAt = item.publishedAt,
                shownAt = System.currentTimeMillis()
            )
        )
        save(context, current.take(MAX_ITEMS))

        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val delivered = prefs.getStringSet(DELIVERED_KEY, emptySet())
            ?.toMutableSet() ?: mutableSetOf()
        delivered.add(item.id)

        // Guard against unbounded growth while retaining years of typical use.
        val compact = if (delivered.size > MAX_DELIVERED_IDS) {
            current.map { it.id }.toMutableSet()
        } else {
            delivered
        }
        prefs.edit().putStringSet(DELIVERED_KEY, compact).apply()
    }

    fun deliveredIds(context: Context): Set<String> {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val stored = prefs.getStringSet(DELIVERED_KEY, emptySet()) ?: emptySet()
        if (stored.isNotEmpty()) return stored.toSet()

        // Upgrade path: bootstrap the permanent dedupe set from existing history.
        val fromHistory = load(context).map { it.id }.filter { it.isNotBlank() }.toSet()
        if (fromHistory.isNotEmpty()) {
            prefs.edit().putStringSet(DELIVERED_KEY, fromHistory).apply()
        }
        return fromHistory
    }

    fun load(context: Context): List<HistoryEntry> {
        val raw = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getString(KEY, null) ?: return emptyList()
        return try {
            val arr = JSONArray(raw)
            buildList {
                for (i in 0 until arr.length()) {
                    val o = arr.optJSONObject(i) ?: continue
                    add(
                        HistoryEntry(
                            id = o.optString("id"),
                            category = o.optString("category"),
                            title = o.optString("title"),
                            text = o.optString("text"),
                            source = o.optString("source"),
                            url = o.optString("url"),
                            publishedAt = o.optString("published_at"),
                            shownAt = o.optLong("shown_at")
                        )
                    )
                }
            }
        } catch (_: Exception) {
            emptyList()
        }
    }

    fun clear(context: Context) {
        // Clearing the visible history does not make old facts eligible again.
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().remove(KEY).apply()
    }

    private fun save(context: Context, items: List<HistoryEntry>) {
        val arr = JSONArray()
        items.forEach { item ->
            arr.put(
                JSONObject().apply {
                    put("id", item.id)
                    put("category", item.category)
                    put("title", item.title)
                    put("text", item.text)
                    put("source", item.source)
                    put("url", item.url)
                    put("published_at", item.publishedAt)
                    put("shown_at", item.shownAt)
                }
            )
        }
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putString(KEY, arr.toString()).apply()
    }
}
