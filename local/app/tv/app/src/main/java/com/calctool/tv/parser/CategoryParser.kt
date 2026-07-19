package com.calctool.tv.parser

import com.calctool.tv.data.AppConfig
import com.calctool.tv.models.VideoItem
import org.jsoup.nodes.Document

/**
 * 分类列表页解析器 — 适配 maccms (Apple CMS)
 * vodtype-1=电影, vodtype-2=电视剧, vodtype-3=综艺, vodtype-4=动漫, vodtype-69=微短剧
 */
object CategoryParser {

    private val baseUrl = AppConfig.request.baseUrl

    fun parseCategory(html: String, page: Int = 1): List<VideoItem> {
        if (html.isBlank()) return emptyList()
        val doc = HtmlParser.parse(html)
        return parseItems(doc)
    }

    fun parseCategoryWithPageInfo(html: String): Pair<List<VideoItem>, Int> {
        val doc = HtmlParser.parse(html)
        val items = parseItems(doc)
        val totalPages = parseTotalPages(doc)
        return items to totalPages
    }

    private fun parseItems(doc: Document): List<VideoItem> {
        val items = mutableListOf<VideoItem>()
        // maccms 模板：.module-poster-item 或通用列表项
        val cards = doc.select(
            ".module-poster-item, " +
            ".video-item, .movie-item, " +
            "li[class*=item], div[class*=item]"
        )
        for (card in cards) {
            val link = card.selectFirst("a[href*=/detail/]") ?: card.selectFirst("a") ?: continue
            val href = link.attr("href")
            if (href.isBlank() || href == "#") continue

            val title = link.attr("title").trim().ifEmpty {
                (card.selectFirst(".module-poster-item-title")?.text()?.trim() ?: "").ifEmpty {
                    card.selectFirst(".title, .name, h4, h3")?.text()?.trim() ?: ""
                }
            }
            if (title.isEmpty()) continue

            val img = card.selectFirst("img.lazy") ?: card.selectFirst("img")
            val coverUrl = (img?.attr("data-original")?.trim() ?: "").ifEmpty {
                img?.attr("src")?.trim() ?: ""
            }

            val updateInfo = card.selectFirst(".module-item-note")?.text()?.trim() ?: ""

            items.add(VideoItem(
                id = extractId(href),
                title = title,
                coverUrl = coverUrl,
                category = card.select(".category, .tag, .type").text().trim(),
                region = card.select(".region, .area").text().trim(),
                year = card.select(".year, .date").text().trim(),
                rating = card.select(".rating, .score, .star").text().trim(),
                updateInfo = updateInfo,
                detailUrl = absoluteUrl(href),
            ))
        }
        return items.distinctBy { it.id }
    }

    private fun parseTotalPages(doc: Document): Int {
        val pageLinks = doc.select(".page-link, .pagination a, .paginate_button, .pager a")
        val maxPage = pageLinks.map { it.text().trim() }
            .filter { it.toIntOrNull() != null }
            .maxOfOrNull { it.toInt() } ?: 1
        return maxPage
    }

    /**
     * 构建 maccms 分类列表页 URL
     * 电影: /vodtype-1/index.html
     * 电视剧: /vodtype-2/index.html
     * 综艺: /vodtype-3/index.html
     * 动漫: /vodtype-4/index.html
     * 微短剧: /vodtype-69/index.html
     */
    fun buildCategoryUrl(
        category: String,
        subCategory: String? = null,
        region: String? = null,
        page: Int = 1,
    ): String {
        val typeId = categoryToTypeId(category)
        val path = if (page <= 1) "/vodtype-$typeId/index.html"
        else "/vodtype-$typeId/index-$page.html"

        // 子分类通过 page 参数或筛选参数传递
        // maccms 的筛选通常在分类页通过 JS 实现，这里简化处理
        return "$baseUrl$path"
    }

    private fun categoryToTypeId(category: String): Int {
        return when (category.lowercase().trim()) {
            "电影", "movie", "movies" -> 1
            "电视剧", "tv", "drama", "剧集" -> 2
            "综艺", "variety", "show" -> 3
            "动漫", "anime", "dongman" -> 4
            "微短剧", "shorts", "短剧" -> 69
            else -> 1  // 默认电影
        }
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
