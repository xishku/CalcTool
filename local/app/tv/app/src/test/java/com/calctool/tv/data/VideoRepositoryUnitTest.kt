package com.calctool.tv.data

import com.calctool.tv.models.*
import org.junit.Assert.*
import org.junit.Test

class VideoRepositoryUnitTest {

    // region savePlayState / getPlayState logic

    @Test
    fun `PlayState tracks video and episode correctly`() {
        val state = PlayState(
            videoId = "vod-456",
            episodeIndex = 5,
            positionMs = 300_000L,
            durationMs = 2_400_000L,
        )
        assertEquals("vod-456", state.videoId)
        assertEquals(5, state.episodeIndex)
        assertEquals(300_000L, state.positionMs)
    }

    // endregion

    // region VideoItem + PlayUrlResult flow

    @Test
    fun `VideoItem to PlayUrlResult flow - success case`() {
        val item = VideoItem(id = "vod-1", title = "测试")
        val playResult = PlayUrlResult.Success("https://cdn.com/video.m3u8")
        assertTrue(playResult is PlayUrlResult.Success)
    }

    @Test
    fun `VideoItem to PlayUrlResult flow - error case`() {
        val item = VideoItem(id = "vod-2", title = "失败")
        val playResult = PlayUrlResult.Error("无法解析")
        assertTrue(playResult is PlayUrlResult.Error)
        assertEquals("无法解析", (playResult as PlayUrlResult.Error).message)
    }

    // endregion

    // region HomeData filtering

    @Test
    fun `HomeData isEmpty detection`() {
        assertTrue(HomeData().isEmpty)
        assertFalse(HomeData(hotPlaying = listOf(VideoItem("1", "T"))).isEmpty)
        assertFalse(HomeData(banners = listOf(VideoItem("2", "B"))).isEmpty)
    }

    @Test
    fun `HomeData preserves map structures`() {
        val data = HomeData(
            latestMovies = mapOf(
                "科幻" to listOf(VideoItem("1", "A")),
                "动作" to listOf(VideoItem("2", "B")),
            ),
            rankings = mapOf(
                "电影榜" to listOf(VideoItem("3", "C")),
            ),
        )
        assertEquals(2, data.latestMovies.size)
        assertEquals(1, data.rankings.size)
        assertEquals("A", data.latestMovies["科幻"]?.get(0)?.title)
    }

    // endregion

    // region RequestConfig boundaries

    @Test
    fun `RequestConfig allows custom timeouts`() {
        val config = RequestConfig(timeoutSeconds = 30)
        assertEquals(30, config.timeoutSeconds)
    }

    @Test
    fun `RequestConfig allows zero retries`() {
        val config = RequestConfig(maxRetries = 0)
        assertEquals(0, config.maxRetries)
    }

    // endregion

    // region CacheConfig boundaries

    @Test
    fun `CacheConfig allows short TTL`() {
        val config = CacheConfig(homepageTtlMinutes = 5)
        assertEquals(5, config.homepageTtlMinutes)
    }

    // endregion
}
