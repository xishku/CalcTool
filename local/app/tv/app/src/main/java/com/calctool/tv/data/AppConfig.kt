package com.calctool.tv.data

import com.calctool.tv.models.CacheConfig
import com.calctool.tv.models.PlayerConfig
import com.calctool.tv.models.RequestConfig

/**
 * 应用全局配置
 */
object AppConfig {
    val request = RequestConfig()
    val cache = CacheConfig()
    val player = PlayerConfig()

    fun toJson(): String = """
        {
          "base_url": "${request.baseUrl}",
          "request": {
            "timeout_seconds": ${request.timeoutSeconds},
            "interval_ms": ${request.intervalMs},
            "max_retries": ${request.maxRetries},
            "user_agent": "${request.userAgent}"
          },
          "player": {
            "seek_step_seconds": ${player.seekStepSeconds},
            "buffer_size_mb": ${player.bufferSizeMb},
            "auto_play_next": ${player.autoPlayNext}
          },
          "cache": {
            "homepage_ttl_minutes": ${cache.homepageTtlMinutes},
            "image_cache_mb": ${cache.imageCacheMb},
            "max_history_days": ${cache.maxHistoryDays}
          }
        }
    """.trimIndent()
}
