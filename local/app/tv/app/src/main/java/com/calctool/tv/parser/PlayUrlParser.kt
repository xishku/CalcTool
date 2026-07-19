package com.calctool.tv.parser

import com.calctool.tv.models.PlayUrlResult
import com.calctool.tv.models.VideoFormat

/**
 * 播放地址解析器
 * 从播放页 HTML 中提取真实视频流地址
 */
object PlayUrlParser {

    /**
     * 从播放页 HTML 中提取视频流地址
     * 优先级：M3U8 > MP4 > iframe src > 脚本提取
     */
    fun parse(html: String): PlayUrlResult {
        if (html.isBlank()) return PlayUrlResult.Error("播放页为空")

        // 1. 直接匹配 M3U8
        val m3u8 = HtmlParser.extractVideoUrl(html)
        if (m3u8 != null && m3u8.contains(".m3u8", ignoreCase = true)) {
            return PlayUrlResult.Success(m3u8, VideoFormat.HLS)
        }

        // 1.5 提取 <video> 标签 src
        val doc = HtmlParser.parse(html)
        val videoSrc = doc.select("video[src]").attr("src").ifEmpty {
            doc.select("video source[src]").attr("src")
        }
        if (videoSrc.isNotEmpty() && HtmlParser.isLikelyVideoUrl(videoSrc)) {
            val format = if (videoSrc.contains(".mp4")) VideoFormat.MP4 else VideoFormat.HLS
            return PlayUrlResult.Success(videoSrc, format)
        }

        // 2. 提取 iframe src
        val iframeSrc = HtmlParser.extractIframeSrc(html)
        if (iframeSrc != null && iframeSrc.contains(".m3u8", ignoreCase = true)) {
            return PlayUrlResult.Success(iframeSrc, VideoFormat.HLS)
        }
        if (iframeSrc != null && HtmlParser.isLikelyVideoUrl(iframeSrc)) {
            val format = if (iframeSrc.contains(".mp4")) VideoFormat.MP4 else VideoFormat.HLS
            return PlayUrlResult.Success(iframeSrc, format)
        }

        // 3. 从 script 块提取
        val scripts = HtmlParser.parse(html).select("script").map { it.html() }
        for (script in scripts) {
            val url = HtmlParser.extractVideoUrl(script)
            if (url != null) {
                val format = if (url.contains(".mp4")) VideoFormat.MP4
                else if (url.contains(".m3u8")) VideoFormat.HLS
                else VideoFormat.HLS
                return PlayUrlResult.Success(url, format)
            }
        }

        // 4. 从 JSON 配置提取
        for (script in scripts) {
            for (key in listOf("player_aaaa", "player_data", "video_config", "playerConfig")) {
                val json = HtmlParser.extractJsonFromScript(script, key)
                if (json != null) {
                    val url = HtmlParser.extractVideoUrl(json)
                    if (url != null) {
                        return PlayUrlResult.Success(url, VideoFormat.HLS)
                    }
                }
            }
        }

        // 5. 如果是二次跳转页（说明需要进一步请求 iframe 地址），返回 iframe
        if (iframeSrc != null && iframeSrc.startsWith("http")) {
            return PlayUrlResult.Success(iframeSrc, VideoFormat.HLS)
        }

        return PlayUrlResult.Error("无法解析播放地址")
    }
}
