package com.calctool.tv.parser

import org.junit.Assert.*
import org.junit.Test

class CategoryParserTest {

    @Test
    fun `parseCategory - empty HTML returns empty list`() {
        val result = CategoryParser.parseCategory("", 1)
        assertTrue(result.isEmpty())
    }

    @Test
    fun `parseCategory - extracts video items from list`() {
        val html = """
            <html><body>
            <div class="video-item">
                <a href="/detail/abc">
                    <img src="/img/1.jpg" alt="影片A">
                </a>
                <span class="year">2024</span>
                <span class="rating">8.5</span>
            </div>
            </body></html>
        """.trimIndent()
        val result = CategoryParser.parseCategory(html)
        assertEquals(1, result.size)
        assertEquals("影片A", result[0].title)
        assertEquals("2024", result[0].year)
    }

    @Test
    fun `parseCategoryWithPageInfo - extracts page count`() {
        val html = """
            <html><body>
            <div class="pagination">
                <a>1</a><a>2</a><a>3</a><a>4</a><a>5</a>
            </div>
            </body></html>
        """.trimIndent()
        val (items, totalPages) = CategoryParser.parseCategoryWithPageInfo(html)
        assertEquals(5, totalPages)
    }

    @Test
    fun `parseCategoryWithPageInfo - defaults to 1 page`() {
        val html = "<html><body><p>No pagination</p></body></html>"
        val (_, totalPages) = CategoryParser.parseCategoryWithPageInfo(html)
        assertEquals(1, totalPages)
    }

    @Test
    fun `buildCategoryUrl - movie with no filters`() {
        val url = CategoryParser.buildCategoryUrl("电影")
        assertTrue(url.contains("/movies"))
    }

    @Test
    fun `buildCategoryUrl - TV with region and page`() {
        val url = CategoryParser.buildCategoryUrl("电视剧", region = "国产", page = 3)
        assertTrue(url.contains("/tv"))
        assertTrue(url.contains("region=国产"))
        assertTrue(url.contains("page=3"))
    }

    @Test
    fun `buildCategoryUrl - anime with type`() {
        val url = CategoryParser.buildCategoryUrl("动漫", subCategory = "日韩")
        assertTrue(url.contains("/anime"))
        assertTrue(url.contains("type=日韩"))
    }
}
