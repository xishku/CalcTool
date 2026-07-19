package com.calctool.tv.data

import android.content.Context
import com.calctool.tv.models.HomeData
import com.calctool.tv.models.PlayState
import com.calctool.tv.models.VideoDetail
import com.calctool.tv.models.VideoItem
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import java.io.File

/**
 * 本地缓存管理器
 * - 首页数据缓存（TTL 30 分钟）
 * - 播放历史记录
 * - 收藏管理
 * - 自动清理过期数据
 */
class CacheManager(private val context: Context) {

    private val gson = Gson()
    private val cacheDir: File
        get() = File(context.cacheDir, "tv_cache").also { it.mkdirs() }

    private val homeDataFile get() = File(cacheDir, "home_data.json")
    private val historyFile get() = File(cacheDir, "play_history.json")
    private val favoritesFile get() = File(cacheDir, "favorites.json")
    private val metadataFile get() = File(cacheDir, "cache_metadata.json")

    // --- 首页数据缓存 ---

    fun saveHomeData(data: HomeData) {
        try {
            homeDataFile.writeText(gson.toJson(data))
            saveMetadata("home_cache_time", System.currentTimeMillis())
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    fun loadHomeData(): HomeData? {
        return try {
            if (!isHomeDataValid()) return null
            gson.fromJson(homeDataFile.readText(), HomeData::class.java)
        } catch (e: Exception) {
            null
        }
    }

    fun isHomeDataValid(): Boolean {
        if (!homeDataFile.exists()) return false
        val metadata = loadMetadata()
        val cacheTime = metadata["home_cache_time"] ?: return false
        val ttlMs = AppConfig.cache.homepageTtlMinutes * 60L * 1000L
        return (System.currentTimeMillis() - cacheTime) < ttlMs
    }

    // --- 播放历史 ---

    fun savePlayState(state: PlayState) {
        try {
            val list = loadPlayHistory().toMutableList()
            list.removeAll { it.videoId == state.videoId && it.episodeIndex == state.episodeIndex }
            list.add(0, state)
            // 最多保留 50 条
            val trimmed = list.take(50)
            historyFile.writeText(gson.toJson(trimmed))
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    fun loadPlayHistory(): List<PlayState> {
        return try {
            if (!historyFile.exists()) return emptyList()
            val type = object : TypeToken<List<PlayState>>() {}.type
            gson.fromJson(historyFile.readText(), type) ?: emptyList()
        } catch (e: Exception) {
            emptyList()
        }
    }

    fun getPlayState(videoId: String, episodeIndex: Int = 0): PlayState? {
        return loadPlayHistory().find {
            it.videoId == videoId && it.episodeIndex == episodeIndex
        }
    }

    // --- 收藏 ---

    fun addFavorite(item: VideoItem) {
        try {
            val list = loadFavorites().toMutableList()
            if (list.none { it.id == item.id }) {
                list.add(item)
                favoritesFile.writeText(gson.toJson(list))
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    fun removeFavorite(videoId: String) {
        try {
            val list = loadFavorites().filter { it.id != videoId }
            favoritesFile.writeText(gson.toJson(list))
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    fun isFavorite(videoId: String): Boolean {
        return loadFavorites().any { it.id == videoId }
    }

    fun loadFavorites(): List<VideoItem> {
        return try {
            if (!favoritesFile.exists()) return emptyList()
            val type = object : TypeToken<List<VideoItem>>() {}.type
            gson.fromJson(favoritesFile.readText(), type) ?: emptyList()
        } catch (e: Exception) {
            emptyList()
        }
    }

    // --- 缓存清理 ---

    fun clearExpiredCache() {
        val maxAgeMs = AppConfig.cache.maxHistoryDays * 24L * 3600L * 1000L
        cacheDir.listFiles()?.forEach { file ->
            if (file.name != "favorites.json" &&
                System.currentTimeMillis() - file.lastModified() > maxAgeMs) {
                file.delete()
            }
        }
    }

    fun clearAll() {
        cacheDir.listFiles()?.forEach { it.delete() }
    }

    // --- 内部辅助 ---

    private fun saveMetadata(key: String, value: Long) {
        try {
            val map = loadMetadata().toMutableMap()
            map[key] = value
            metadataFile.writeText(gson.toJson(map))
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    private fun loadMetadata(): Map<String, Long> {
        return try {
            if (!metadataFile.exists()) return emptyMap()
            val type = object : TypeToken<Map<String, Long>>() {}.type
            gson.fromJson(metadataFile.readText(), type) ?: emptyMap()
        } catch (e: Exception) {
            emptyMap()
        }
    }
}
