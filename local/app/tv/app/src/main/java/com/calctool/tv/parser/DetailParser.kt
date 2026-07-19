package com.calctool.tv.parser

import com.calctool.tv.data.AppConfig
import com.calctool.tv.models.*

/**
 * 详情页解析器
 */
object DetailParser {

    private val baseUrl = AppConfig.request.baseUrl

    fun parse(html: String, currentItem: VideoItem): VideoDetail {
        if (html.isBlank()) return VideoDetail(baseInfo = currentItem)

        val doc = HtmlParser.parse(html)

        return VideoDetail(
            baseInfo = parseBaseInfo(doc, currentItem),
            description = parseDescription(doc),
            genres = parseGenres(doc),
            directors = parseDirectors(doc),
            actors = parseActors(doc),
            playSources = parsePlaySources(doc),
            episodes = parseEpisodes(doc),
            relatedVideos = parseRelated(doc),
        )
    }

    private fun parseBaseInfo(doc: org.jsoup.nodes.Document, fallback: VideoItem): VideoItem {
        return VideoItem(
            id = fallback.id,
            title = fallback.title.ifEmpty {
                doc.selectFirst("h1, .detail-title, .video-title")?.text() ?: ""
            },
            coverUrl = fallback.coverUrl.ifEmpty {
                doc.selectFirst(".poster img, .cover img, .detail-poster img")?.attr("src") ?: ""
            },
            category = doc.select(".category, .tag, .type").text().ifEmpty { fallback.category },
            region = doc.select(".region, .area").text().ifEmpty { fallback.region },
            year = doc.select(".year, .date, .release-date").text().ifEmpty { fallback.year },
            rating = doc.select(".rating, .score, .star").text().ifEmpty { fallback.rating },
            updateInfo = doc.select(".update, .episode-info").text().ifEmpty { fallback.updateInfo },
            detailUrl = fallback.detailUrl,
        )
    }

    private fun parseDescription(doc: org.jsoup.nodes.Document): String {
        return doc.select(".description, .summary, .intro, .plot, .content, .detail-desc, #intro")
            .map { it.text().trim() }
            .firstOrNull { it.length > 10 } ?: ""
    }

    private fun parseGenres(doc: org.jsoup.nodes.Document): List<String> {
        return doc.select(".genres a, .tags a, .genre, .tag, .category-list a")
            .map { it.text().trim() }
            .filter { it.isNotEmpty() }
    }

    private fun parseDirectors(doc: org.jsoup.nodes.Document): List<String> {
        return doc.select(".director, .directors")
            .text()
            .replace(Regex("导演[：:]?\\s*"), "")
            .split(Regex("[,，/\\s]+"))
            .map { it.trim() }
            .filter { it.isNotEmpty() }
    }

    private fun parseActors(doc: org.jsoup.nodes.Document): List<String> {
        return doc.select(".actor, .actors, .cast, .starring a, .actor-list a")
            .map { it.text().trim() }
            .filter { it.isNotEmpty() }
    }

    /**
     * 解析播放线路
     */
    private fun parsePlaySources(doc: org.jsoup.nodes.Document): List<PlaySource> {
        val sources = mutableListOf<PlaySource>()

        // 方式1：线路 Tab + 剧集列表
        val sourceTabs = doc.select(".source-tab, .play-source, .play-tab, .source-list li, .server")
        if (sourceTabs.isNotEmpty()) {
            for (tab in sourceTabs) {
                val name = tab.text().trim()
                val targetId = tab.attr("data-target").ifEmpty { tab.attr("data-id") }
                val episodeContainer = if (targetId.isNotEmpty())
                    doc.select("#$targetId")
                else
                    doc.select(".episode-list, .play-list")

                val episodes = parseEpisodesFromContainer(episodeContainer)
                if (episodes.isNotEmpty()) {
                    sources.add(PlaySource(name = name, episodes = episodes))
                }
            }
        }

        // 方式2：无线路切换，直接剧集
        if (sources.isEmpty()) {
            val episodes = parseEpisodesFromContainer(doc.select(".episode-list, .play-list, .play-urls"))
            if (episodes.isNotEmpty()) {
                sources.add(PlaySource(name = "线路一", episodes = episodes))
            }
        }

        // 方式3：解析播放地址脚本块
        if (sources.isEmpty()) {
            val scripts = doc.select("script").map { it.html() }
            for (script in scripts) {
                val urls = extractPlayUrlsFromScript(script)
                if (urls.isNotEmpty()) {
                    sources.add(PlaySource(name = "线路一", episodes = urls.mapIndexed { i, url ->
                        Episode(index = i + 1, title = "第${i + 1}集", playUrl = url)
                    }))
                    break
                }
            }
        }

        return sources
    }

    private fun parseEpisodesFromContainer(container: org.jsoup.select.Elements): List<Episode> {
        val episodes = mutableListOf<Episode>()
        val links = container.select("a[href], li")
        for ((idx, el) in links.withIndex()) {
            val link = if (el.tagName() == "a") el else el.selectFirst("a") ?: continue
            val href = link.attr("href").trim()
            if (href.isBlank() || href == "#") continue
            episodes.add(Episode(
                index = idx + 1,
                title = link.text().trim(),
                playUrl = if (href.startsWith("http")) href else "$baseUrl/$href".replace("//", "/")
                    .replace(":/", "://"),
            ))
        }
        return episodes
    }

    private fun parseEpisodes(doc: org.jsoup.nodes.Document): List<Episode> {
        return parseEpisodesFromContainer(
            doc.select(".episode-list, .play-list, .episodes, .series-list")
        )
    }

    /**
     * 解析相关推荐
     */
    private fun parseRelated(doc: org.jsoup.nodes.Document): List<VideoItem> {
        val items = mutableListOf<VideoItem>()
        val cards = doc.select(".related-item, .recommend-item, .related .card, .like-item, .side-list .item")
        for (card in cards) {
            val link = card.selectFirst("a") ?: continue
            val img = card.selectFirst("img")
            val href = link.attr("href")
            items.add(VideoItem(
                id = href.trimEnd('/').split("/").lastOrNull() ?: "",
                title = img?.attr("alt") ?: link.attr("title").ifEmpty { link.text() },
                coverUrl = img?.attr("src") ?: img?.attr("data-src") ?: "",
                category = card.select(".category, .tag").text(),
                year = card.select(".year").text(),
                detailUrl = if (href.startsWith("http")) href else "$baseUrl/$href".replace("//", "/")
                    .replace(":/", "://"),
            ))
        }
        return items
    }

    /**
     * 从 JS 脚本中提取播放地址数组
     */
    private fun extractPlayUrlsFromScript(script: String): List<String> {
        val urls = mutableListOf<String>()
        val patterns = listOf(
            Regex("""urls?\s*[:=]\s*\[(.*?)]""", RegexOption.DOT_MATCHES_ALL),
            Regex("""play_urls?\s*[:=]\s*\[(.*?)]""", RegexOption.DOT_MATCHES_ALL),
            Regex("""episodes?\s*[:=]\s*\[(.*?)]""", RegexOption.DOT_MATCHES_ALL),
        )
        for (pattern in patterns) {
            val match = pattern.find(script) ?: continue
            val content = match.groupValues[1]
            val urlPattern = Regex("""["']([^"']*)["']""")
            urlPattern.findAll(content).forEach { u ->
                val url = u.groupValues[1]
                if (url.contains("http") || url.contains(".m3u8") || url.contains(".mp4")) {
                    urls.add(url)
                }
            }
            if (urls.isNotEmpty()) break
        }
        return urls
    }
}
