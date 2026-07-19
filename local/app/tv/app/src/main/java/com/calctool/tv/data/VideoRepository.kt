package com.calctool.tv.data

import com.calctool.tv.models.*
import com.calctool.tv.parser.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * 数据仓库：统一管理网络请求、解析、缓存
 */
class VideoRepository(private val cacheManager: CacheManager) {

    /**
     * 获取首页数据（优先读缓存）
     */
    suspend fun getHomeData(): HomeData = withContext(Dispatchers.IO) {
        cacheManager.loadHomeData()?.let { return@withContext it }

        val result = ApiClient.getHtmlWithRetry(AppConfig.request.baseUrl + "/")
        if (result.isFailure) {
            return@withContext HomeData() // 返回空数据
        }

        val homeData = HomeParser.parse(result.getOrThrow())
        if (!homeData.isEmpty) {
            cacheManager.saveHomeData(homeData)
        }
        homeData
    }

    /**
     * 获取分类列表
     */
    suspend fun getCategoryList(
        category: String,
        subCategory: String? = null,
        region: String? = null,
        page: Int = 1,
    ): Pair<List<VideoItem>, Int> = withContext(Dispatchers.IO) {
        val url = CategoryParser.buildCategoryUrl(category, subCategory, region, page)
        val result = ApiClient.getHtmlWithRetry(url)
        if (result.isFailure) return@withContext emptyList<VideoItem>() to 1

        CategoryParser.parseCategoryWithPageInfo(result.getOrThrow())
    }

    /**
     * 获取影片详情
     */
    suspend fun getVideoDetail(videoItem: VideoItem): VideoDetail = withContext(Dispatchers.IO) {
        val url = videoItem.detailUrl.ifEmpty {
            "${AppConfig.request.baseUrl}/detail/${videoItem.id}"
        }
        val result = ApiClient.getHtmlWithRetry(url)
        if (result.isFailure) return@withContext VideoDetail(baseInfo = videoItem)

        DetailParser.parse(result.getOrThrow(), videoItem)
    }

    /**
     * 解析播放地址
     */
    suspend fun resolvePlayUrl(episode: Episode): PlayUrlResult = withContext(Dispatchers.IO) {
        val url = episode.playUrl.ifEmpty {
            return@withContext PlayUrlResult.Error("播放地址为空")
        }

        // 第一步：请求播放页
        val pageResult = ApiClient.getHtmlWithRetry(url)
        if (pageResult.isFailure) {
            return@withContext PlayUrlResult.Error("请求播放页失败: ${pageResult.exceptionOrNull()?.message}")
        }

        val html = pageResult.getOrThrow()

        // 第二步：解析视频流地址
        val playResult = PlayUrlParser.parse(html)

        // 如果返回的是二次跳转地址（iframe），继续请求
        if (playResult is PlayUrlResult.Success &&
            !playResult.url.contains(".m3u8") &&
            !playResult.url.contains(".mp4") &&
            playResult.url.startsWith("http")) {
            val iframeResult = ApiClient.getHtmlWithRetry(playResult.url)
            if (iframeResult.isSuccess) {
                return@withContext PlayUrlParser.parse(iframeResult.getOrThrow())
            }
        }

        playResult
    }

    /**
     * 搜索影片
     */
    suspend fun search(keyword: String): List<VideoItem> = withContext(Dispatchers.IO) {
        val url = SearchParser.buildSearchUrl(keyword)
        val result = ApiClient.getHtmlWithRetry(url)
        if (result.isFailure) return@withContext emptyList()
        SearchParser.parseSearchResults(result.getOrThrow())
    }

    /**
     * 保存/获取播放进度
     */
    fun savePlayState(state: PlayState) {
        cacheManager.savePlayState(state)
    }

    fun getPlayState(videoId: String, episodeIndex: Int = 0): PlayState? {
        return cacheManager.getPlayState(videoId, episodeIndex)
    }

    fun getPlayHistory(): List<PlayState> {
        return cacheManager.loadPlayHistory()
    }

    /**
     * 收藏管理
     */
    fun addFavorite(item: VideoItem) = cacheManager.addFavorite(item)
    fun removeFavorite(videoId: String) = cacheManager.removeFavorite(videoId)
    fun isFavorite(videoId: String) = cacheManager.isFavorite(videoId)
    fun getFavorites(): List<VideoItem> = cacheManager.loadFavorites()

    /**
     * 缓存清理
     */
    fun clearExpiredCache() = cacheManager.clearExpiredCache()
}
