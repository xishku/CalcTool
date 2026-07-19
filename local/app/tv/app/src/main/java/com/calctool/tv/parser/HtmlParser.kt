package com.calctool.tv.parser

import org.jsoup.Jsoup
import org.jsoup.nodes.Document

/**
 * HTML 解析工具基类
 */
object HtmlParser {

    fun parse(html: String): Document = Jsoup.parse(html)

    fun parse(html: String, baseUri: String): Document = Jsoup.parse(html, baseUri)

    /**
     * 从 DOM 中提取文本，null-safe
     */
    fun textOrEmpty(doc: Document, cssQuery: String): String {
        return try {
            doc.selectFirst(cssQuery)?.text()?.trim() ?: ""
        } catch (e: Exception) {
            ""
        }
    }

    /**
     * 从 DOM 中提取属性，null-safe
     */
    fun attrOrEmpty(doc: Document, cssQuery: String, attr: String): String {
        return try {
            doc.selectFirst(cssQuery)?.attr(attr)?.trim() ?: ""
        } catch (e: Exception) {
            ""
        }
    }

    /**
     * 提取所有匹配元素的文本列表
     */
    fun texts(doc: Document, cssQuery: String): List<String> {
        return try {
            doc.select(cssQuery).map { it.text().trim() }
        } catch (e: Exception) {
            emptyList()
        }
    }

    /**
     * 提取 src 属性并补全为绝对 URL
     */
    fun absoluteSrc(doc: Document, cssQuery: String, baseUri: String): String {
        val raw = attrOrEmpty(doc, cssQuery, "src")
        if (raw.isEmpty()) return ""
        return if (raw.startsWith("http")) raw else "$baseUri/$raw".replace("//", "/")
            .replace(":/", "://")
    }

    /**
     * 提取 href 属性并补全为绝对 URL
     */
    fun absoluteHref(doc: Document, cssQuery: String, baseUri: String): String {
        val raw = attrOrEmpty(doc, cssQuery, "href")
        if (raw.isEmpty()) return ""
        if (raw.startsWith("http")) return raw
        return if (raw.startsWith("/")) "$baseUri$raw" else "$baseUri/$raw"
    }

    /**
     * 从页面 script 中提取 JSON 对象
     */
    fun extractJsonFromScript(html: String, varKey: String): String? {
        val regex = Regex("""$varKey\s*[:=]\s*(\{.*?});""", RegexOption.DOT_MATCHES_ALL)
        return regex.find(html)?.groupValues?.getOrNull(1)
    }

    /**
     * 从页面中提取 iframe src
     */
    fun extractIframeSrc(html: String): String? {
        val regex = Regex("""<iframe[^>]+src=["']([^"']+)["']""", RegexOption.IGNORE_CASE)
        return regex.find(html)?.groupValues?.getOrNull(1)
    }

    /**
     * 提取视频流地址（M3U8 / MP4）
     */
    fun extractVideoUrl(html: String): String? {
        val patterns = listOf(
            Regex("""["']?(https?://[^"'\s]+\.m3u8[^"'\s]*)["']?""", RegexOption.IGNORE_CASE),
            Regex("""["']?(https?://[^"'\s]+\.mp4[^"'\s]*)["']?""", RegexOption.IGNORE_CASE),
            Regex("""url\s*[:=]\s*["']([^"']+)["']"""),
            Regex("""video_url\s*[:=]\s*["']([^"']+)["']"""),
            Regex("""src\s*[:=]\s*["']([^"']+\.(?:m3u8|mp4))["']"""),
        )
        for (pattern in patterns) {
            val match = pattern.find(html)
            if (match != null) {
                val url = match.groupValues[1].trim()
                if (isLikelyVideoUrl(url)) return url
            }
        }
        return null
    }

    fun isLikelyVideoUrl(url: String): Boolean {
        if (url.isEmpty()) return false
        return url.contains(".m3u8", ignoreCase = true) ||
                url.contains(".mp4", ignoreCase = true) ||
                url.contains("video", ignoreCase = true) ||
                url.contains("play", ignoreCase = true) ||
                url.contains("stream", ignoreCase = true)
    }
}
