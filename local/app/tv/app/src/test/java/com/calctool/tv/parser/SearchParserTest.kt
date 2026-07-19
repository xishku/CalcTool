package com.calctool.tv.parser

import org.junit.Assert.*
import org.junit.Test

class SearchParserTest {

    @Test
    fun `parseSearchResults - empty HTML returns empty list`() {
        val result = SearchParser.parseSearchResults("")
        assertTrue(result.isEmpty())
    }

    @Test
    fun `parseSearchResults - extracts search items`() {
        val html = """
            <html><body>
            <div class="search-item">
                <a href="/detail/abc">
                    <img src="/img/cover.jpg" alt="搜索结果1">
                </a>
                <span class="year">2024</span>
            </div>
            <div class="search-item">
                <a href="/detail/def">
                    <img src="/img/cover2.jpg" alt="搜索结果2">
                </a>
            </div>
            </body></html>
        """.trimIndent()
        val result = SearchParser.parseSearchResults(html)
        assertEquals(2, result.size)
        assertEquals("搜索结果1", result[0].title)
        assertEquals("搜索结果2", result[1].title)
    }

    @Test
    fun `parseSearchResults - skips items without links`() {
        val html = """
            <html><body>
            <div class="search-item">
                <span>No link here</span>
            </div>
            <div class="search-item">
                <a href="/detail/valid">
                    <img src="/img/cover.jpg" alt="有效结果">
                </a>
            </div>
            </body></html>
        """.trimIndent()
        val result = SearchParser.parseSearchResults(html)
        assertEquals(1, result.size)
        assertEquals("有效结果", result[0].title)
    }

    @Test
    fun `buildSearchUrl - encodes keyword`() {
        val url = SearchParser.buildSearchUrl("流浪地球")
        assertTrue(url.contains("search"))
        assertTrue(url.contains("%E6%B5%81") || url.contains("流浪地球"))
    }

    @Test
    fun `buildSearchUrl - handles special characters`() {
        val url = SearchParser.buildSearchUrl("test & search")
        assertTrue(url.contains("search"))
    }
}
