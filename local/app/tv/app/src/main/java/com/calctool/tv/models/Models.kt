package com.calctool.tv.models

/**
 * 影片列表项（卡片展示用）
 */
data class VideoItem(
    val id: String,
    val title: String,
    val coverUrl: String = "",
    val category: String = "",
    val region: String = "",
    val year: String = "",
    val rating: String = "",
    val updateInfo: String = "",
    val detailUrl: String = "",
)

/**
 * 影片详情（详情页展示用）
 */
data class VideoDetail(
    val baseInfo: VideoItem,
    val description: String = "",
    val genres: List<String> = emptyList(),
    val directors: List<String> = emptyList(),
    val actors: List<String> = emptyList(),
    val playSources: List<PlaySource> = emptyList(),
    val episodes: List<Episode> = emptyList(),
    val relatedVideos: List<VideoItem> = emptyList(),
)

/**
 * 播放线路
 */
data class PlaySource(
    val name: String,
    val episodes: List<Episode> = emptyList(),
)

/**
 * 剧集
 */
data class Episode(
    val index: Int,
    val title: String = "",
    val playUrl: String = "",
)

/**
 * 播放状态（断点续播）
 */
data class PlayState(
    val videoId: String = "",
    val episodeIndex: Int = 0,
    val positionMs: Long = 0L,
    val durationMs: Long = 0L,
    val timestamp: Long = System.currentTimeMillis(),
)

/**
 * 首页聚合数据
 */
data class HomeData(
    val banners: List<VideoItem> = emptyList(),
    val hotPlaying: List<VideoItem> = emptyList(),
    val latestMovies: Map<String, List<VideoItem>> = emptyMap(),
    val latestTVs: Map<String, List<VideoItem>> = emptyMap(),
    val microShorts: List<VideoItem> = emptyList(),
    val variety: List<VideoItem> = emptyList(),
    val anime: List<VideoItem> = emptyList(),
    val rankings: Map<String, List<VideoItem>> = emptyMap(),
) {
    val isEmpty: Boolean
        get() = banners.isEmpty() && hotPlaying.isEmpty()
}

/**
 * 视频流 URL 解析结果
 */
sealed class PlayUrlResult {
    data class Success(val url: String, val format: VideoFormat = VideoFormat.HLS) : PlayUrlResult()
    data class Error(val message: String) : PlayUrlResult()
}

enum class VideoFormat { HLS, MP4, DASH }

/**
 * 网络请求配置
 */
data class RequestConfig(
    val baseUrl: String = "https://www.3ckk.com",
    val timeoutSeconds: Int = 15,
    val intervalMs: Long = 3000L,
    val maxRetries: Int = 2,
    val userAgent: String = "Mozilla/5.0 (Linux; Android 9; Smart TV; Android TV) " +
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
)

/**
 * 缓存配置
 */
data class CacheConfig(
    val homepageTtlMinutes: Int = 30,
    val imageCacheMb: Int = 100,
    val maxHistoryDays: Int = 30,
)

/**
 * 播放器配置
 */
data class PlayerConfig(
    val seekStepSeconds: Int = 10,
    val bufferSizeMb: Int = 50,
    val autoPlayNext: Boolean = true,
)
