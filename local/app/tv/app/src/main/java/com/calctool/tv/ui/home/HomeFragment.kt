package com.calctool.tv.ui.home

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment
import androidx.leanback.app.RowsSupportFragment
import androidx.leanback.widget.*
import com.calctool.tv.App
import com.calctool.tv.models.HomeData
import com.calctool.tv.models.VideoItem
import kotlinx.coroutines.*

/**
 * 首页 Fragment — 使用 Leanback RowsSupportFragment
 * 展示轮播推荐 + 热映 + 各分类行列
 */
class HomeFragment : RowsSupportFragment() {

    private val repository = App.instance.repository
    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())
    private lateinit var adapter: ArrayObjectAdapter

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        adapter = ArrayObjectAdapter(ListRowPresenter())
        this.adapter = adapter
        loadHomeData()
    }

    override fun onDestroy() {
        super.onDestroy()
        scope.cancel()
    }

    private fun loadHomeData() {
        scope.launch {
            val homeData = withContext(Dispatchers.IO) { repository.getHomeData() }
            buildRows(homeData)
        }
    }

    private fun buildRows(data: HomeData) {
        adapter.clear()

        // 热映
        if (data.hotPlaying.isNotEmpty()) {
            adapter.add(buildRow("正在热映", data.hotPlaying))
        }

        // 最新电影按类型分组
        data.latestMovies.forEach { (type, items) ->
            if (items.isNotEmpty()) adapter.add(buildRow("最新电影 · $type", items))
        }

        // 最新电视剧按地区分组
        data.latestTVs.forEach { (region, items) ->
            if (items.isNotEmpty()) adapter.add(buildRow("最新电视剧 · $region", items))
        }

        // 综艺
        if (data.variety.isNotEmpty()) adapter.add(buildRow("综艺", data.variety))

        // 动漫
        if (data.anime.isNotEmpty()) adapter.add(buildRow("动漫", data.anime))

        // 微短剧
        if (data.microShorts.isNotEmpty()) adapter.add(buildRow("微短剧", data.microShorts))

        // 热榜
        data.rankings.forEach { (name, items) ->
            if (items.isNotEmpty()) adapter.add(buildRow(name, items))
        }
    }

    private fun buildRow(title: String, items: List<VideoItem>): ListRow {
        val rowAdapter = ArrayObjectAdapter(VideoCardPresenter())
        items.take(20).forEach { rowAdapter.add(it) }
        return ListRow(HeaderItem(title), rowAdapter)
    }
}
