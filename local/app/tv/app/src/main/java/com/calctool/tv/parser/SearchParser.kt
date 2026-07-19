package com.calctool.tv.parser

import com.calctool.tv.data.AppConfig
import com.calctool.tv.models.VideoItem

/**
 * 搜索页面解析器 — 适配 maccms (Apple CMS)
 * 搜索 URL: /vodsearch/{keyword}-------------.html
 */
object SearchParser {

    private val baseUrl = AppConfig.request.baseUrl

    fun parseSearchResults(html: String): List<VideoItem> {
        if (html.isBlank()) return emptyList()
        val doc = HtmlParser.parse(html)
        val items = mutableListOf<VideoItem>()

        // maccms 搜索结果通常使用 .module-poster-item 或 .search-item
        val elements = doc.select(
            ".module-poster-item, .search-item, .result-item, " +
            "li[class*=result], div[class*=item]"
        )
        for (el in elements) {
            val link = el.selectFirst("a[href*=/detail/]") ?: el.selectFirst("a") ?: continue
            val href = link.attr("href")
            if (href.isBlank() || href == "#") continue

            val title = link.attr("title").trim().ifEmpty {
                (el.selectFirst(".module-poster-item-title")?.text()?.trim() ?: "").ifEmpty {
                    el.selectFirst(".title, .name, h4, h3")?.text()?.trim() ?: link.text().trim()
                }
            }
            if (title.isEmpty()) continue

            val img = el.selectFirst("img.lazy") ?: el.selectFirst("img")
            val coverUrl = (img?.attr("data-original")?.trim() ?: "").ifEmpty {
                img?.attr("src")?.trim() ?: ""
            }

            val updateInfo = el.selectFirst(".module-item-note")?.text()?.trim()
                ?: el.select(".update, .episode, .status").text().trim()

            items.add(VideoItem(
                id = extractId(href),
                title = title,
                coverUrl = coverUrl,
                category = el.select(".category, .type, .tag").text().trim(),
                region = el.select(".region").text().trim(),
                year = el.select(".year, .date").text().trim(),
                rating = el.select(".rating, .score").text().trim(),
                updateInfo = updateInfo,
                detailUrl = absoluteUrl(href),
            ))
        }
        return items.distinctBy { it.id }
    }

    /**
     * 构建 maccms 搜索 URL
     * 格式: /vodsearch/{keyword}-------------.html
     */
    fun buildSearchUrl(keyword: String): String {
        val encoded = java.net.URLEncoder.encode(keyword, "UTF-8")
        return "$baseUrl/vodsearch/$encoded-------------.html"
    }

    private fun extractId(href: String): String {
        if (href.isBlank()) return ""
        val parts = href.trimEnd('/').split("/")
        for (i in parts.indices.reversed()) {
            val part = parts[i]
            if (part.all { it.isDigit() } && part.length >= 4) return part
        }
        return parts.lastOrNull()?.ifEmpty { href.hashCode().toString() } ?: href.hashCode().toString()
    }

    private fun absoluteUrl(path: String): String {
        if (path.isEmpty()) return ""
        if (path.startsWith("http")) return path
        return if (path.startsWith("/")) "$baseUrl$path" else "$baseUrl/$path"
    }
}
