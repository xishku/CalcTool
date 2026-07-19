package com.calctool.tv.parser

import org.junit.Assert.*
import org.junit.Test

class HomeParserTest {

    @Test
    fun `parse - empty HTML returns empty HomeData`() {
        val result = HomeParser.parse("")
        assertTrue(result.isEmpty)
        assertTrue(result.banners.isEmpty())
        assertTrue(result.hotPlaying.isEmpty())
    }

    @Test
    fun `parse - extracts banners from swiper`() {
        val html = """
            <html><body>
            <div class="swiper-slide">
                <a href="/detail/123" title="电影标题">
                    <img src="/images/cover.jpg" alt="电影标题">
                </a>
            </div>
            </body></html>
        """.trimIndent()
        val result = HomeParser.parse(html)
        assertEquals(1, result.banners.size)
        assertEquals("电影标题", result.banners[0].title)
        assertEquals("/images/cover.jpg", result.banners[0].coverUrl)
    }

    @Test
    fun `parse - extracts hot playing items`() {
        val html = """
            <html><body>
            <div class="hot-list">
                <div class="item">
                    <a href="/detail/1">
                        <img src="/img/1.jpg" alt="热映电影">
                    </a>
                </div>
            </div>
            </body></html>
        """.trimIndent()
        val result = HomeParser.parse(html)
        assertTrue(result.hotPlaying.isNotEmpty())
        assertEquals("热映电影", result.hotPlaying[0].title)
    }

    @Test
    fun `parse - handles blank HTML gracefully`() {
        val result = HomeParser.parse("   ")
        assertTrue(result.isEmpty)
    }

    @Test
    fun `parse - handles malformed HTML`() {
        val html = "<<malformed>><<>>"
        val result = HomeParser.parse(html)
        // Should not throw; just return empty or whatever it can parse
        assertNotNull(result)
    }
}
