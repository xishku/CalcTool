package com.calctool.tv.ui

import android.os.Bundle
import androidx.fragment.app.FragmentActivity
import androidx.leanback.app.BrowseSupportFragment
import androidx.leanback.widget.*
import com.calctool.tv.App
import com.calctool.tv.R
import com.calctool.tv.ui.detail.DetailActivity
import com.calctool.tv.models.VideoItem
import com.calctool.tv.ui.home.HomeFragment
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * 主界面
 * Leanback BrowseSupportFragment 提供横向导航栏 + 内容区域
 */
class MainActivity : FragmentActivity() {

    private lateinit var mainFragment: BrowseSupportFragment

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        setupMainFragment()
    }

    private fun setupMainFragment() {
        mainFragment = MainBrowseFragment()
        supportFragmentManager.beginTransaction()
            .replace(R.id.main_container, mainFragment)
            .commit()
    }
}

class MainBrowseFragment : BrowseSupportFragment() {

    private val repository = App.instance.repository

    override fun onActivityCreated(savedInstanceState: Bundle?) {
        super.onActivityCreated(savedInstanceState)
        title = "3C电影"

        // 设置品牌颜色（华为智慧屏风格）
        brandColor = resources.getColor(R.color.brand, null)

        // 设置导航栏 Header
        headersState = HEADERS_ENABLED
        setupHeaders()

        // 设置主页行
        setupHomeRows()
    }

    private fun setupHeaders() {
        // BrowseSupportFragment 的 HeaderItem 由各行 ListRow 的 HeaderItem 自动提取
        // 无需额外设置，详见 setupHomeRows()
    }

    private fun setupHomeRows() {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val homeData = repository.getHomeData()
                withContext(Dispatchers.Main) {
                    val adapter = ArrayObjectAdapter(ListRowPresenter())

                    // 热映
                    if (homeData.hotPlaying.isNotEmpty()) {
                        adapter.add(createVideoRow("正在热映", homeData.hotPlaying))
                    }

                    // 最新电影
                    homeData.latestMovies.forEach { (type, items) ->
                        if (items.isNotEmpty()) {
                            adapter.add(createVideoRow("最新电影 · $type", items))
                        }
                    }

                    // 最新电视剧
                    homeData.latestTVs.forEach { (region, items) ->
                        if (items.isNotEmpty()) {
                            adapter.add(createVideoRow("最新电视剧 · $region", items))
                        }
                    }

                    // 综艺
                    if (homeData.variety.isNotEmpty()) {
                        adapter.add(createVideoRow("综艺", homeData.variety))
                    }

                    // 动漫
                    if (homeData.anime.isNotEmpty()) {
                        adapter.add(createVideoRow("动漫", homeData.anime))
                    }

                    // 微短剧
                    if (homeData.microShorts.isNotEmpty()) {
                        adapter.add(createVideoRow("微短剧", homeData.microShorts))
                    }

                    // 设置 adapter
                    this@MainBrowseFragment.adapter = adapter
                }
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }

    private fun createVideoRow(title: String, items: List<VideoItem>): ListRow {
        val cardPresenter = CardPresenter()
        val listRowAdapter = ArrayObjectAdapter(cardPresenter)
        items.take(20).forEach { listRowAdapter.add(it) }
        return ListRow(HeaderItem(title), listRowAdapter)
    }

    /**
     * 影片卡片 Presenter
     */
    inner class CardPresenter : Presenter() {
        override fun onCreateViewHolder(parent: android.view.ViewGroup): Presenter.ViewHolder {
            val cardView = ImageCardView(parent.context).apply {
                isFocusable = true
                isFocusableInTouchMode = true
                // 适配 4K：卡片尺寸
                setMainImageDimensions(280, 400)
            }
            return object : Presenter.ViewHolder(cardView) {}
        }

        override fun onBindViewHolder(viewHolder: Presenter.ViewHolder, item: Any) {
            val video = item as VideoItem
            val cardView = viewHolder.view as ImageCardView
            cardView.titleText = video.title
            cardView.contentText = "${video.year}  ${video.rating}".trim()
            cardView.setMainImageDimensions(280, 400)
            // 封面图使用 Coil 加载（在外部 Activity 中通过 Glide/Coil 设置）
            cardView.setOnClickListener {
                openDetail(video)
            }
        }

        override fun onUnbindViewHolder(viewHolder: Presenter.ViewHolder) {}
    }

    private fun openDetail(video: VideoItem) {
        val intent = android.content.Intent(activity, DetailActivity::class.java).apply {
            putExtra("video_id", video.id)
            putExtra("video_title", video.title)
            putExtra("video_cover", video.coverUrl)
            putExtra("detail_url", video.detailUrl)
            putExtra("category", video.category)
            putExtra("region", video.region)
            putExtra("year", video.year)
        }
        startActivity(intent)
    }
}
