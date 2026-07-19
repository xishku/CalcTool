package com.calctool.tv.parser

import org.junit.Assert.*
import org.junit.Test

class HtmlParserTest {

    // region parse

    @Test
    fun `parse - valid HTML returns Document`() {
        val html = "<html><head><title>Test</title></head><body><p>Hello</p></body></html>"
        val doc = HtmlParser.parse(html)
        assertEquals("Test", doc.title())
        assertEquals("Hello", doc.selectFirst("p")?.text())
    }

    @Test
    fun `parse - empty HTML returns empty Document`() {
        val doc = HtmlParser.parse("")
        assertEquals("", doc.title())
    }

    // endregion

    // region textOrEmpty

    @Test
    fun `textOrEmpty - extracts text from selector`() {
        val html = "<div><span class='name'>Hello World</span></div>"
        val doc = HtmlParser.parse(html)
        assertEquals("Hello World", HtmlParser.textOrEmpty(doc, ".name"))
    }

    @Test
    fun `textOrEmpty - returns empty for missing selector`() {
        val doc = HtmlParser.parse("<div></div>")
        assertEquals("", HtmlParser.textOrEmpty(doc, ".missing"))
    }

    // endregion

    // region attrOrEmpty

    @Test
    fun `attrOrEmpty - extracts attribute`() {
        val html = """<a href="/detail/123" class="link">Link</a>"""
        val doc = HtmlParser.parse(html)
        assertEquals("/detail/123", HtmlParser.attrOrEmpty(doc, "a", "href"))
    }

    @Test
    fun `attrOrEmpty - returns empty for missing attribute`() {
        val html = """<a class="link">Link</a>"""
        val doc = HtmlParser.parse(html)
        assertEquals("", HtmlParser.attrOrEmpty(doc, "a", "href"))
    }

    // endregion

    // region texts

    @Test
    fun `texts - extracts multiple texts`() {
        val html = "<ul><li>A</li><li>B</li><li>C</li></ul>"
        val doc = HtmlParser.parse(html)
        assertEquals(listOf("A", "B", "C"), HtmlParser.texts(doc, "li"))
    }

    @Test
    fun `texts - returns empty list for no matches`() {
        val doc = HtmlParser.parse("<div></div>")
        assertEquals(emptyList<String>(), HtmlParser.texts(doc, ".none"))
    }

    // endregion

    // region absoluteSrc

    @Test
    fun `absoluteSrc - resolves relative image path`() {
        val html = """<img src="/images/poster.jpg">"""
        val doc = HtmlParser.parse(html)
        val result = HtmlParser.absoluteSrc(doc, "img", "https://www.3ckk.com")
        assertEquals("https://www.3ckk.com/images/poster.jpg", result)
    }

    @Test
    fun `absoluteSrc - keeps absolute URLs`() {
        val html = """<img src="https://cdn.example.com/img.jpg">"""
        val doc = HtmlParser.parse(html)
        val result = HtmlParser.absoluteSrc(doc, "img", "https://www.3ckk.com")
        assertEquals("https://cdn.example.com/img.jpg", result)
    }

    @Test
    fun `absoluteSrc - returns empty for missing img`() {
        val doc = HtmlParser.parse("<div></div>")
        assertEquals("", HtmlParser.absoluteSrc(doc, "img", "https://www.3ckk.com"))
    }

    // endregion

    // region absoluteHref

    @Test
    fun `absoluteHref - resolves relative path`() {
        val html = """<a href="/detail/abc">Link</a>"""
        val doc = HtmlParser.parse(html)
        val result = HtmlParser.absoluteHref(doc, "a", "https://www.3ckk.com")
        assertEquals("https://www.3ckk.com/detail/abc", result)
    }

    @Test
    fun `absoluteHref - keeps absolute URLs`() {
        val html = """<a href="https://www.3ckk.com/detail/abc">Link</a>"""
        val doc = HtmlParser.parse(html)
        val result = HtmlParser.absoluteHref(doc, "a", "https://www.3ckk.com")
        assertEquals("https://www.3ckk.com/detail/abc", result)
    }

    // endregion

    // region extractVideoUrl

    @Test
    fun `extractVideoUrl - finds m3u8 URL`() {
        val html = """var url = "https://cdn.example.com/video.m3u8";"""
        val result = HtmlParser.extractVideoUrl(html)
        assertEquals("https://cdn.example.com/video.m3u8", result)
    }

    @Test
    fun `extractVideoUrl - finds mp4 URL`() {
        val html = """<video src="https://cdn.example.com/video.mp4"></video>"""
        val result = HtmlParser.extractVideoUrl(html)
        assertEquals("https://cdn.example.com/video.mp4", result)
    }

    @Test
    fun `extractVideoUrl - returns null for no video`() {
        val html = "<div>Hello World</div>"
        assertNull(HtmlParser.extractVideoUrl(html))
    }

    @Test
    fun `extractVideoUrl - handles empty input`() {
        assertNull(HtmlParser.extractVideoUrl(""))
    }

    // endregion

    // region extractIframeSrc

    @Test
    fun `extractIframeSrc - finds iframe src`() {
        val html = """<iframe src="https://player.example.com/embed/123" width="100%"></iframe>"""
        val result = HtmlParser.extractIframeSrc(html)
        assertEquals("https://player.example.com/embed/123", result)
    }

    @Test
    fun `extractIframeSrc - returns null when no iframe`() {
        assertNull(HtmlParser.extractIframeSrc("<div></div>"))
    }

    // endregion

    // region extractJsonFromScript

    @Test
    fun `extractJsonFromScript - extracts JSON object`() {
        val html = """var player_data = {"url":"test.m3u8","autoplay":true};"""
        val result = HtmlParser.extractJsonFromScript(html, "player_data")
        assertNotNull(result)
        assertTrue(result!!.contains("test.m3u8"))
    }

    @Test
    fun `extractJsonFromScript - returns null for missing key`() {
        val html = """var something = {};"""
        assertNull(HtmlParser.extractJsonFromScript(html, "player_data"))
    }

    // endregion

    // region isLikelyVideoUrl

    @Test
    fun `isLikelyVideoUrl - true for m3u8`() {
        assertTrue(HtmlParser.isLikelyVideoUrl("https://cdn.com/video.m3u8"))
    }

    @Test
    fun `isLikelyVideoUrl - true for mp4`() {
        assertTrue(HtmlParser.isLikelyVideoUrl("https://cdn.com/video.mp4"))
    }

    @Test
    fun `isLikelyVideoUrl - true for stream path`() {
        assertTrue(HtmlParser.isLikelyVideoUrl("https://cdn.com/stream/play"))
    }

    @Test
    fun `isLikelyVideoUrl - false for non-video`() {
        assertFalse(HtmlParser.isLikelyVideoUrl("https://www.3ckk.com/detail/123"))
    }

    @Test
    fun `isLikelyVideoUrl - false for empty`() {
        assertFalse(HtmlParser.isLikelyVideoUrl(""))
    }

    // endregion
}
