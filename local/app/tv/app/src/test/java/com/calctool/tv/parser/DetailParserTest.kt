package com.calctool.tv.parser

import com.calctool.tv.models.VideoItem
import org.junit.Assert.*
import org.junit.Test

class DetailParserTest {

    private val testItem = VideoItem(
        id = "vod-123",
        title = "测试影片",
        coverUrl = "https://img.example.com/cover.jpg",
        detailUrl = "https://www.3ckk.com/detail/vod-123",
    )

    @Test
    fun `parse - empty HTML returns detail with fallback`() {
        val result = DetailParser.parse("", testItem)
        assertEquals("测试影片", result.baseInfo.title)
        assertEquals("", result.description)
        assertTrue(result.playSources.isEmpty())
    }

    @Test
    fun `parse - extracts description`() {
        val html = """
            <html><body>
            <div class="description">这是一部精彩的电影，讲述了...</div>
            </body></html>
        """.trimIndent()
        val result = DetailParser.parse(html, testItem)
        assertTrue(result.description.contains("精彩的电影"))
    }

    @Test
    fun `parse - extracts genres`() {
        val html = """
            <html><body>
            <div class="genres"><a>科幻</a><a>动作</a><a>冒险</a></div>
            </body></html>
        """.trimIndent()
        val result = DetailParser.parse(html, testItem)
        assertEquals(3, result.genres.size)
        assertTrue(result.genres.contains("科幻"))
    }

    @Test
    fun `parse - extracts play sources with episodes`() {
        val html = """
            <html><body>
            <div class="play-list">
                <a href="/play/1">第1集</a>
                <a href="/play/2">第2集</a>
                <a href="/play/3">第3集</a>
            </div>
            </body></html>
        """.trimIndent()
        val result = DetailParser.parse(html, testItem)
        assertEquals(1, result.playSources.size)
        assertEquals("线路一", result.playSources[0].name)
        assertEquals(3, result.playSources[0].episodes.size)
        assertEquals(1, result.playSources[0].episodes[0].index)
    }

    @Test
    fun `parse - extracts actors`() {
        val html = """
            <html><body>
            <div class="actor-list">
                <a>演员A</a>
                <a>演员B</a>
            </div>
            </body></html>
        """.trimIndent()
        val result = DetailParser.parse(html, testItem)
        assertEquals(2, result.actors.size)
    }

    @Test
    fun `parse - extracts related videos`() {
        val html = """
            <html><body>
            <div class="related">
                <div class="related-item">
                    <a href="/detail/456">
                        <img src="/img/related.jpg" alt="相关影片">
                    </a>
                </div>
            </div>
            </body></html>
        """.trimIndent()
        val result = DetailParser.parse(html, testItem)
        assertEquals(1, result.relatedVideos.size)
        assertEquals("相关影片", result.relatedVideos[0].title)
    }
}
