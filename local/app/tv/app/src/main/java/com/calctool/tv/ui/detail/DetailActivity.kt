package com.calctool.tv.ui.detail

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.leanback.app.RowsSupportFragment
import androidx.leanback.widget.*
import com.calctool.tv.App
import com.calctool.tv.R
import com.calctool.tv.models.*
import com.calctool.tv.ui.player.VideoPlayerActivity
import kotlinx.coroutines.*

/**
 * 影片详情页
 * 展示海报、简介、播放线路、剧集列表、相关推荐
 */
class DetailActivity : AppCompatActivity() {

    private val repository = App.instance.repository
    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())

    private lateinit var videoItem: VideoItem
    private lateinit var detail: VideoDetail
    private lateinit var adapter: ArrayObjectAdapter
    private var selectedSource: PlaySource? = null
    private var selectedEpisode: Episode? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_detail)

        videoItem = VideoItem(
            id = intent.getStringExtra("video_id") ?: "",
            title = intent.getStringExtra("video_title") ?: "",
            coverUrl = intent.getStringExtra("video_cover") ?: "",
            detailUrl = intent.getStringExtra("detail_url") ?: "",
            category = intent.getStringExtra("category") ?: "",
            region = intent.getStringExtra("region") ?: "",
            year = intent.getStringExtra("year") ?: "",
        )

        adapter = ArrayObjectAdapter(ListRowPresenter())
        val rowsFragment = supportFragmentManager
            .findFragmentById(R.id.detail_rows) as? RowsSupportFragment
        rowsFragment?.adapter = adapter

        loadDetail()
    }

    private fun loadDetail() {
        scope.launch {
            detail = withContext(Dispatchers.IO) { repository.getVideoDetail(videoItem) }
            buildDetailRows()
        }
    }

    private fun buildDetailRows() {
        adapter.clear()

        // 基本信息行
        val infoAdapter = ArrayObjectAdapter(DetailInfoPresenter())
        infoAdapter.add(detail)
        adapter.add(ListRow(HeaderItem("影片信息"), infoAdapter))

        // 播放线路行
        if (detail.playSources.isNotEmpty()) {
            val sourceAdapter = ArrayObjectAdapter(SourcePresenter())
            detail.playSources.forEach { sourceAdapter.add(it) }
            adapter.add(ListRow(HeaderItem("播放线路"), sourceAdapter))
        }

        // 剧集列表行
        if (detail.episodes.isNotEmpty()) {
            val episodeAdapter = ArrayObjectAdapter(EpisodePresenter())
            detail.episodes.forEach { episodeAdapter.add(it) }
            adapter.add(ListRow(HeaderItem("剧集列表"), episodeAdapter))
        }

        // 播放按钮行
        val actionAdapter = ArrayObjectAdapter(ActionPresenter())
        actionAdapter.add("立即播放")
        adapter.add(ListRow(HeaderItem(""), actionAdapter))

        // 相关推荐行
        if (detail.relatedVideos.isNotEmpty()) {
            val relatedAdapter = ArrayObjectAdapter(RelatedPresenter())
            detail.relatedVideos.take(10).forEach { relatedAdapter.add(it) }
            adapter.add(ListRow(HeaderItem("相关推荐"), relatedAdapter))
        }
    }

    /**
     * 开始播放
     */
    private fun playEpisode(episode: Episode) {
        scope.launch {
            val playResult = withContext(Dispatchers.IO) {
                repository.resolvePlayUrl(episode)
            }
            when (playResult) {
                is PlayUrlResult.Success -> {
                    val intent = Intent(this@DetailActivity, VideoPlayerActivity::class.java).apply {
                        putExtra("video_url", playResult.url)
                        putExtra("video_format", playResult.format.name)
                        putExtra("video_title", videoItem.title)
                        putExtra("episode_title", episode.title)
                        putExtra("video_id", videoItem.id)
                        putExtra("episode_index", episode.index)
                    }
                    startActivity(intent)
                }
                is PlayUrlResult.Error -> {
                    Toast.makeText(
                        this@DetailActivity,
                        "播放失败: ${playResult.message}",
                        Toast.LENGTH_LONG
                    ).show()
                }
            }
        }
    }

    // --- Presenters ---

    inner class DetailInfoPresenter : Presenter() {
        override fun onCreateViewHolder(parent: android.view.ViewGroup) =
            object : Presenter.ViewHolder(
                layoutInflater.inflate(R.layout.presenter_detail_info, parent, false)
            ) {}

        override fun onBindViewHolder(viewHolder: Presenter.ViewHolder, item: Any) {
            val d = item as VideoDetail
            viewHolder.view.apply {
                // 标题
                findViewById<android.widget.TextView>(R.id.detail_title).text = d.baseInfo.title
                // 简介
                findViewById<android.widget.TextView>(R.id.detail_desc).text =
                    d.description.ifEmpty { "暂无简介" }
                // 类型
                findViewById<android.widget.TextView>(R.id.detail_genres).text =
                    d.genres.joinToString(" · ")
                // 导演
                findViewById<android.widget.TextView>(R.id.detail_directors).text =
                    d.directors.joinToString(", ").ifEmpty { "未知" }
                // 主演
                findViewById<android.widget.TextView>(R.id.detail_actors).text =
                    d.actors.take(5).joinToString(", ").ifEmpty { "未知" }
            }
        }

        override fun onUnbindViewHolder(viewHolder: Presenter.ViewHolder) {}
    }

    inner class SourcePresenter : Presenter() {
        override fun onCreateViewHolder(parent: android.view.ViewGroup): Presenter.ViewHolder {
            val textView = android.widget.TextView(parent.context).apply {
                isFocusable = true
                isFocusableInTouchMode = true
                setPadding(32, 16, 32, 16)
                textSize = 20f
                setTextColor(resources.getColor(R.color.text_primary, null))
            }
            return object : Presenter.ViewHolder(textView) {
                init {
                    textView.setOnClickListener {
                        val source = textView.tag as? PlaySource
                        selectedSource = source
                        if (source?.episodes?.isNotEmpty() == true) {
                            playEpisode(source.episodes[0])
                        }
                    }
                    textView.setOnFocusChangeListener { _, hasFocus ->
                        textView.isSelected = hasFocus
                        if (hasFocus) textView.setTextColor(
                            resources.getColor(R.color.brand, null)
                        )
                        else textView.setTextColor(
                            resources.getColor(R.color.text_primary, null)
                        )
                    }
                }
            }
        }

        override fun onBindViewHolder(viewHolder: Presenter.ViewHolder, item: Any) {
            val source = item as PlaySource
            viewHolder.view.tag = source
            val tv = viewHolder.view as android.widget.TextView
            tv.text = "${source.name} (${source.episodes.size}集)"
        }

        override fun onUnbindViewHolder(viewHolder: Presenter.ViewHolder) {}
    }

    inner class EpisodePresenter : Presenter() {
        override fun onCreateViewHolder(parent: android.view.ViewGroup): Presenter.ViewHolder {
            val textView = android.widget.TextView(parent.context).apply {
                isFocusable = true
                isFocusableInTouchMode = true
                setPadding(24, 12, 24, 12)
                textSize = 18f
                setTextColor(resources.getColor(R.color.text_secondary, null))
                background = resources.getDrawable(R.drawable.episode_bg, null)
            }
            return object : Presenter.ViewHolder(textView) {
                init {
                    textView.setOnClickListener {
                        val ep = textView.tag as? Episode ?: return@setOnClickListener
                        playEpisode(ep)
                    }
                    textView.setOnFocusChangeListener { _, hasFocus ->
                        textView.isSelected = hasFocus
                    }
                }
            }
        }

        override fun onBindViewHolder(viewHolder: Presenter.ViewHolder, item: Any) {
            val ep = item as Episode
            viewHolder.view.tag = ep
            (viewHolder.view as android.widget.TextView).text = ep.title.ifEmpty { "第${ep.index}集" }
        }

        override fun onUnbindViewHolder(viewHolder: Presenter.ViewHolder) {}
    }

    inner class ActionPresenter : Presenter() {
        override fun onCreateViewHolder(parent: android.view.ViewGroup): Presenter.ViewHolder {
            val button = android.widget.Button(parent.context).apply {
                text = "▶ 立即播放"
                isFocusable = true
                isFocusableInTouchMode = true
                textSize = 18f
                setTextColor(android.graphics.Color.WHITE)
                setBackgroundColor(resources.getColor(R.color.brand, null))
                setPadding(48, 16, 48, 16)
            }
            return object : Presenter.ViewHolder(button) {
                init {
                    button.setOnClickListener {
                        val ep = detail.episodes.firstOrNull()
                            ?: detail.playSources.firstOrNull()?.episodes?.firstOrNull()
                        if (ep != null) playEpisode(ep)
                        else Toast.makeText(
                            this@DetailActivity,
                            "暂无可用播放源",
                            Toast.LENGTH_SHORT
                        ).show()
                    }
                }
            }
        }

        override fun onBindViewHolder(viewHolder: Presenter.ViewHolder, item: Any) {}
        override fun onUnbindViewHolder(viewHolder: Presenter.ViewHolder) {}
    }

    inner class RelatedPresenter : Presenter() {
        override fun onCreateViewHolder(parent: android.view.ViewGroup): Presenter.ViewHolder {
            val card = ImageCardView(parent.context).apply {
                isFocusable = true
                isFocusableInTouchMode = true
                setMainImageDimensions(220, 310)
            }
            return object : Presenter.ViewHolder(card) {
                init {
                    card.setOnClickListener {
                        val v = card.tag as? VideoItem ?: return@setOnClickListener
                        val intent = Intent(this@DetailActivity, DetailActivity::class.java).apply {
                            putExtra("video_id", v.id)
                            putExtra("video_title", v.title)
                            putExtra("video_cover", v.coverUrl)
                            putExtra("detail_url", v.detailUrl)
                        }
                        startActivity(intent)
                    }
                }
            }
        }

        override fun onBindViewHolder(viewHolder: Presenter.ViewHolder, item: Any) {
            val video = item as VideoItem
            viewHolder.view.tag = video
            val card = viewHolder.view as ImageCardView
            card.titleText = video.title
            card.contentText = video.category
        }

        override fun onUnbindViewHolder(viewHolder: Presenter.ViewHolder) {}
    }

    override fun onDestroy() {
        super.onDestroy()
        scope.cancel()
    }
}
