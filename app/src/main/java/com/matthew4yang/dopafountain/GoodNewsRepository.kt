package com.matthew4yang.dopafountain

import android.content.Context
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

object GoodNewsRepository {
    private const val FEED_URL =
        "https://raw.githubusercontent.com/matthew4yang/Dopafountain/main/data/goodnews.json"
    private const val PREFS = "dopafountain_news"
    private const val CACHE_JSON = "cache_json"
    private const val CACHE_TIME = "cache_time"
    private const val SEEN_IDS = "seen_ids"
    private const val CACHE_TTL_MS = 60L * 60L * 1000L

    fun next(context: Context, forceRefresh: Boolean = false): GoodNews? {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val cached = prefs.getString(CACHE_JSON, null)
        val lastFetch = prefs.getLong(CACHE_TIME, 0L)
        val freshEnough = System.currentTimeMillis() - lastFetch < CACHE_TTL_MS

        val raw = when {
            !forceRefresh && freshEnough && !cached.isNullOrBlank() -> cached
            else -> fetchRemote()?.also {
                prefs.edit()
                    .putString(CACHE_JSON, it)
                    .putLong(CACHE_TIME, System.currentTimeMillis())
                    .apply()
            } ?: cached
        } ?: return null

        val items = parse(raw).filter {
            it.category == "宇宙探索" ||
            it.category == "粒子物理" ||
            it.category == "古生物学"
        }
        if (items.isEmpty()) return null

        val seen = prefs.getStringSet(SEEN_IDS, emptySet())?.toMutableSet() ?: mutableSetOf()
        var candidates = items.filterNot { it.id in seen }

        if (candidates.isEmpty()) {
            seen.clear()
            candidates = items
        }

        val item = candidates.random()
        seen.add(item.id)
        prefs.edit().putStringSet(SEEN_IDS, seen).apply()
        return item
    }

    fun cachedCount(context: Context): Int {
        val raw = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getString(CACHE_JSON, null) ?: return 0
        return parse(raw).size
    }

    private fun fetchRemote(): String? {
        return try {
            val connection = (URL(FEED_URL).openConnection() as HttpURLConnection).apply {
                connectTimeout = 10000
                readTimeout = 12000
                requestMethod = "GET"
                setRequestProperty("User-Agent", "Dopafountain/0.2 Android")
                useCaches = false
            }
            try {
                if (connection.responseCode !in 200..299) return null
                connection.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() }
            } finally {
                connection.disconnect()
            }
        } catch (_: Exception) {
            null
        }
    }

    private fun parse(raw: String): List<GoodNews> {
        return try {
            val root = JSONObject(raw)
            val array = root.optJSONArray("items") ?: return emptyList()
            buildList {
                for (i in 0 until array.length()) {
                    val o = array.optJSONObject(i) ?: continue
                    val id = o.optString("id")
                    val title = o.optString("title").trim()
                    if (id.isBlank() || title.isBlank()) continue
                    add(
                        GoodNews(
                            id = id,
                            category = o.optString("category").trim(),
                            title = title,
                            text = o.optString("text").trim(),
                            source = o.optString("source").trim(),
                            url = o.optString("url").trim(),
                            publishedAt = o.optString("published_at").trim()
                        )
                    )
                }
            }
        } catch (_: Exception) {
            emptyList()
        }
    }
}
