package com.calctool.tv.parser

import com.calctool.tv.data.AppConfig
import com.calctool.tv.models.HomeData
import com.calctool.tv.models.VideoItem
import org.jsoup.nodes.Document
import org.jsoup.nodes.Element

/**
 * 首页 HTML 解析器 — 适配 maccms (Apple CMS) 模板
 * 解析 3ckk.com 首页结构：.module > .module-poster-item
 */
object HomeParser {

    private val baseUrl = AppConfig.request.baseUrl

    fun parse(html: String): HomeData {
        if (html.isBlank()) return HomeData()
        val doc = HtmlParser.parse(html)

        return HomeData(
            banners = parseBanners(doc),
            hotPlaying = parseSection(doc, "正在热映"),
            latestMovies = parseSectionWithTabs(doc, "最新电影"),
            latestTVs = parseSectionWithTabs(doc, "最新电视剧"),
            microShorts = parseSection(doc, "微短剧"),
            variety = parseSection(doc, "综艺"),
            anime = parseSection(doc, "动漫"),
            rankings = parseRankings(doc),
        )
    }

    // --- 轮播 Banner ---
    private fun parseBanners(doc: Document): List<VideoItem> {
        val items = mutableListOf<VideoItem>()

        // 大图轮播 .swiper-big .swiper-slide a.banner
        val bigSlides = doc.select(".swiper-big .swiper-slide a.banner")
        for (link in bigSlides) {
            val href = link.attr("href")
            val title = link.attr("title").trim()
            if (title.isEmpty()) continue
            val bgStyle = link.attr("style")
            val coverUrl = extractUrlFromStyle(bgStyle)
            items.add(VideoItem(
                id = extractId(href),
                title = title,
                coverUrl = coverUrl,
                detailUrl = absoluteUrl(href),
            ))
        }

        // 小图轮播 .swiper-small .swiper-slide
        if (items.isEmpty()) {
            val smallSlides = doc.select(".swiper-small .swiper-slide")
            for (slide in smallSlides) {
                val link = slide.selectFirst("a[href*=/detail/]") ?: continue
                val href = link.attr("href")
                val img = slide.selectFirst("img")
                val title = img?.attr("alt")?.trim()?.ifEmpty {
                    slide.selectFirst(".title")?.text()?.trim() ?: ""
                } ?: ""
                if (title.isEmpty()) continue
                items.add(VideoItem(
                    id = extractId(href),
                    title = title,
                    coverUrl = img?.attr("src") ?: img?.attr("data-original") ?: "",
                    detailUrl = absoluteUrl(href),
                ))
            }
        }
        return items.distinctBy { it.id }
    }

    // --- 普通分区（无 Tab） ---
    private fun parseSection(doc: Document, sectionName: String): List<VideoItem> {
        val module = findModuleByTitle(doc, sectionName) ?: return emptyList()
        return extractVideoItems(module)
    }

    // --- 带 Tab 分区（如"最新电影"按类型、"最新电视剧"按地区） ---
    private fun parseSectionWithTabs(doc: Document, sectionName: String): Map<String, List<VideoItem>> {
        val module = findModuleByTitle(doc, sectionName) ?: return emptyMap()
        val result = mutableMapOf<String, List<VideoItem>>()

        // 获取 Tab 名称列表
        val tabItems = module.select(".module-tab-item")
        if (tabItems.isEmpty()) {
            // 无 Tab，直接提取全部
            val items = extractVideoItems(module)
            if (items.isNotEmpty()) result["全部"] = items
            return result
        }

        // 获取所有 tab-list
        val tabLists = module.select(".module-main.tab-list")
        if (tabLists.isEmpty()) {
            // 只有一个 main 区域
            val items = extractVideoItems(module)
            if (items.isNotEmpty()) result["全部"] = items
            return result
        }

        // 每个 Tab 与对应的 tab-list 按顺序对应
        for (i in tabItems.indices) {
            if (i >= tabLists.size) break
            val tabName = tabItems[i].attr("data-dropdown-value").ifEmpty {
                tabItems[i].text().trim()
            }
            val items = extractVideoItems(tabLists[i])
            if (items.isNotEmpty()) {
                result[tabName] = items
            }
        }
        return result
    }

    // --- 热榜 ---
    private fun parseRankings(doc: Document): Map<String, List<VideoItem>> {
        val result = mutableMapOf<String, List<VideoItem>>()
        val rankModules = doc.select(".module").filter { module ->
            val title = module.selectFirst(".module-heading h2")?.text() ?: ""
            title.contains("热榜") || title.contains("排行") || title.contains("榜单")
        }
        // 也通过链接查找
        val allRankModules = if (rankModules.isEmpty()) {
            doc.select(".module").filter { module ->
                val link = module.selectFirst(".module-heading a[href*=label/hot]")
                link != null
            }
        } else rankModules

        for (module in allRankModules) {
            val title = module.selectFirst(".module-heading h2")?.text()?.trim() ?: "热榜"
            val items = extractVideoItems(module)
            if (items.isNotEmpty()) {
                result[title] = items
            }
        }
        return result
    }

    // --- 根据标题查找 .module ---
    private fun findModuleByTitle(doc: Document, titleKeyword: String): Element? {
        return doc.select(".module").firstOrNull { module ->
            val headingText = module.selectFirst(".module-heading h2")?.text()?.trim() ?: ""
            val linkText = module.selectFirst(".module-heading h2 a")?.text()?.trim() ?: ""
            headingText.contains(titleKeyword, ignoreCase = true) ||
                    linkText.contains(titleKeyword, ignoreCase = true)
        }
    }

    // --- 从 Element 中提取所有影片卡片 ---
    private fun extractVideoItems(parent: Element): List<VideoItem> {
        val items = mutableListOf<VideoItem>()
        val cards = parent.select(".module-poster-item")

        for (card in cards) {
            val link = card.selectFirst("a[href*=/detail/]") ?: continue
            val href = link.attr("href")
            if (href.isBlank()) continue

            val title = link.attr("title").trim().ifEmpty {
                card.selectFirst(".module-poster-item-title")?.text()?.trim() ?: ""
            }
            if (title.isEmpty()) continue

            // 图片：优先 data-original（懒加载），其次 src
            val img = card.selectFirst("img.lazy")
            val coverUrl = img?.attr("data-original")?.trim()?.ifEmpty {
                card.selectFirst("img")?.attr("src")?.trim() ?: ""
            } ?: (card.selectFirst("img")?.attr("src")?.trim() ?: "")

            val updateInfo = card.selectFirst(".module-item-note")?.text()?.trim() ?: ""

            items.add(VideoItem(
                id = extractId(href),
                title = title,
                coverUrl = coverUrl,
                updateInfo = updateInfo,
                detailUrl = absoluteUrl(href),
            ))
        }
        return items.distinctBy { it.id }
    }

    // --- 辅助方法 ---

    private fun extractUrlFromStyle(style: String): String {
        val regex = Regex("""url\(["' ]*(.+?)["' ]*\)""", RegexOption.IGNORE_CASE)
        return regex.find(style)?.groupValues?.getOrNull(1)?.trim() ?: ""
    }

    private fun extractId(href: String): String {
        if (href.isBlank()) return ""
        // 从 /vodtype-X/category-Y/123456/detail.html 提取 ID
        val parts = href.trimEnd('/').split("/")
        // 寻找纯数字部分作为 ID
        for (i in parts.indices.reversed()) {
            val part = parts[i]
            if (part.all { it.isDigit() } && part.length >= 4) {
                return part
            }
        }
        return parts.lastOrNull()?.ifEmpty { href.hashCode().toString() } ?: href.hashCode().toString()
    }

    private fun absoluteUrl(path: String): String {
        if (path.isEmpty()) return ""
        if (path.startsWith("http")) return path
        return if (path.startsWith("/")) "$baseUrl$path" else "$baseUrl/$path"
    }
}
