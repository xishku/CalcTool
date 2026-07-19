package com.calctool.tv.models

import org.junit.Assert.*
import org.junit.Test

class ModelsTest {

    // region VideoItem

    @Test
    fun `videoItem - default values are empty`() {
        val item = VideoItem(id = "1", title = "Test")
        assertEquals("1", item.id)
        assertEquals("Test", item.title)
        assertEquals("", item.coverUrl)
        assertEquals("", item.category)
        assertEquals("", item.region)
        assertEquals("", item.year)
        assertEquals("", item.rating)
        assertEquals("", item.updateInfo)
        assertEquals("", item.detailUrl)
    }

    @Test
    fun `videoItem - full construction`() {
        val item = VideoItem(
            id = "vod-123",
            title = "流浪地球",
            coverUrl = "https://img.example.com/cover.jpg",
            category = "电影",
            region = "国产",
            year = "2023",
            rating = "8.5",
            updateInfo = "更新至第1集",
            detailUrl = "https://www.3ckk.com/detail/vod-123",
        )
        assertEquals("vod-123", item.id)
        assertEquals("流浪地球", item.title)
        assertEquals("https://img.example.com/cover.jpg", item.coverUrl)
        assertEquals("电影", item.category)
        assertEquals("国产", item.region)
        assertEquals("2023", item.year)
        assertEquals("8.5", item.rating)
        assertEquals("更新至第1集", item.updateInfo)
        assertEquals("https://www.3ckk.com/detail/vod-123", item.detailUrl)
    }

    @Test
    fun `videoItem - equals and hashCode`() {
        val a = VideoItem(id = "1", title = "A")
        val b = VideoItem(id = "1", title = "A")
        val c = VideoItem(id = "2", title = "A")
        assertEquals(a, b)
        assertNotEquals(a, c)
        assertEquals(a.hashCode(), b.hashCode())
    }

    @Test
    fun `videoItem - copy works`() {
        val item = VideoItem(id = "1", title = "A", year = "2023")
        val copy = item.copy(title = "B")
        assertEquals("1", copy.id)
        assertEquals("B", copy.title)
        assertEquals("2023", copy.year)
    }

    // endregion

    // region VideoDetail

    @Test
    fun `videoDetail - default empty lists`() {
        val detail = VideoDetail(
            baseInfo = VideoItem(id = "1", title = "T")
        )
        assertTrue(detail.genres.isEmpty())
        assertTrue(detail.directors.isEmpty())
        assertTrue(detail.actors.isEmpty())
        assertTrue(detail.playSources.isEmpty())
        assertTrue(detail.episodes.isEmpty())
        assertTrue(detail.relatedVideos.isEmpty())
        assertEquals("", detail.description)
    }

    @Test
    fun `videoDetail - full construction`() {
        val detail = VideoDetail(
            baseInfo = VideoItem(id = "1", title = "T"),
            description = "一部好电影",
            genres = listOf("科幻", "动作"),
            directors = listOf("张导演"),
            actors = listOf("演员A", "演员B"),
            playSources = listOf(
                PlaySource("线路一", listOf(Episode(1, "第1集", "/play/1")))
            ),
            episodes = listOf(Episode(1, "第1集", "/play/1")),
            relatedVideos = listOf(VideoItem(id = "2", title = "R")),
        )
        assertEquals("一部好电影", detail.description)
        assertEquals(2, detail.genres.size)
        assertEquals("科幻", detail.genres[0])
        assertEquals(1, detail.directors.size)
        assertEquals(2, detail.actors.size)
        assertEquals(1, detail.playSources.size)
        assertEquals(1, detail.episodes.size)
        assertEquals(1, detail.relatedVideos.size)
    }

    // endregion

    // region PlaySource

    @Test
    fun `playSource - defaults`() {
        val source = PlaySource(name = "线路一")
        assertEquals("线路一", source.name)
        assertTrue(source.episodes.isEmpty())
    }

    // endregion

    // region Episode

    @Test
    fun `episode - defaults`() {
        val ep = Episode(index = 1)
        assertEquals(1, ep.index)
        assertEquals("", ep.title)
        assertEquals("", ep.playUrl)
    }

    @Test
    fun `episode - full construction`() {
        val ep = Episode(index = 5, title = "第5集", playUrl = "/play/5")
        assertEquals(5, ep.index)
        assertEquals("第5集", ep.title)
        assertEquals("/play/5", ep.playUrl)
    }

    // endregion

    // region PlayState

    @Test
    fun `playState - default timestamp is now`() {
        val before = System.currentTimeMillis()
        val state = PlayState(videoId = "v1", episodeIndex = 1, positionMs = 5000L)
        assertTrue(state.timestamp >= before)
        assertEquals("v1", state.videoId)
        assertEquals(1, state.episodeIndex)
        assertEquals(5000L, state.positionMs)
    }

    // endregion

    // region HomeData

    @Test
    fun `homeData - empty defaults`() {
        val data = HomeData()
        assertTrue(data.isEmpty)
        assertTrue(data.banners.isEmpty())
        assertTrue(data.hotPlaying.isEmpty())
        assertTrue(data.latestMovies.isEmpty())
        assertTrue(data.latestTVs.isEmpty())
    }

    @Test
    fun `homeData - not empty when has banners`() {
        val data = HomeData(
            banners = listOf(VideoItem(id = "1", title = "B"))
        )
        assertFalse(data.isEmpty)
    }

    @Test
    fun `homeData - not empty when has hotPlaying`() {
        val data = HomeData(
            hotPlaying = listOf(VideoItem(id = "1", title = "H"))
        )
        assertFalse(data.isEmpty)
    }

    // endregion

    // region PlayUrlResult

    @Test
    fun `playUrlResult - success`() {
        val result = PlayUrlResult.Success("https://example.com/video.m3u8")
        assertTrue(result is PlayUrlResult.Success)
        assertEquals("https://example.com/video.m3u8", result.url)
        assertEquals(VideoFormat.HLS, result.format)
    }

    @Test
    fun `playUrlResult - error`() {
        val result = PlayUrlResult.Error("解析失败")
        assertTrue(result is PlayUrlResult.Error)
        assertEquals("解析失败", result.message)
    }

    // endregion

    // region RequestConfig

    @Test
    fun `requestConfig - default values`() {
        val config = RequestConfig()
        assertEquals("https://www.3ckk.com", config.baseUrl)
        assertEquals(15, config.timeoutSeconds)
        assertEquals(3000L, config.intervalMs)
        assertEquals(2, config.maxRetries)
        assertTrue(config.userAgent.contains("Android"))
        assertTrue(config.userAgent.contains("Android TV"))
    }

    // endregion

    // region CacheConfig

    @Test
    fun `cacheConfig - default values`() {
        val config = CacheConfig()
        assertEquals(30, config.homepageTtlMinutes)
        assertEquals(100, config.imageCacheMb)
        assertEquals(30, config.maxHistoryDays)
    }

    // endregion

    // region PlayerConfig

    @Test
    fun `playerConfig - default values`() {
        val config = PlayerConfig()
        assertEquals(10, config.seekStepSeconds)
        assertEquals(50, config.bufferSizeMb)
        assertTrue(config.autoPlayNext)
    }

    // endregion
}
