package com.calctool.tv.parser

import com.calctool.tv.models.PlayUrlResult
import com.calctool.tv.models.VideoFormat
import org.junit.Assert.*
import org.junit.Test

class PlayUrlParserTest {

    @Test
    fun `parse - empty HTML returns Error`() {
        val result = PlayUrlParser.parse("")
        assertTrue(result is PlayUrlResult.Error)
    }

    @Test
    fun `parse - extracts M3U8 URL`() {
        val html = """
            <html><script>
            var url = "https://cdn.example.com/stream/video.m3u8";
            </script></html>
        """.trimIndent()
        val result = PlayUrlParser.parse(html)
        assertTrue(result is PlayUrlResult.Success)
        val success = result as PlayUrlResult.Success
        assertTrue(success.url.contains(".m3u8"))
        assertEquals(VideoFormat.HLS, success.format)
    }

    @Test
    fun `parse - extracts MP4 URL`() {
        val html = """
            <video src="https://cdn.example.com/video.mp4"></video>
        """.trimIndent()
        val result = PlayUrlParser.parse(html)
        assertTrue(result is PlayUrlResult.Success)
    }

    @Test
    fun `parse - extracts iframe src`() {
        val html = """
            <iframe src="https://player.example.com/embed/abc"></iframe>
        """.trimIndent()
        val result = PlayUrlParser.parse(html)
        // Should return Success with the iframe URL for further processing
        assertTrue(result is PlayUrlResult.Success)
    }

    @Test
    fun `parse - returns Error when no video found`() {
        val html = "<html><body><p>no video here</p></body></html>"
        val result = PlayUrlParser.parse(html)
        assertTrue(result is PlayUrlResult.Error)
    }

    @Test
    fun `parse - handles script with player_data JSON`() {
        val html = """
            <script>
            var player_data = {"url":"https://cdn.com/play.m3u8"};
            </script>
        """.trimIndent()
        val result = PlayUrlParser.parse(html)
        assertTrue(result is PlayUrlResult.Success)
    }
}
