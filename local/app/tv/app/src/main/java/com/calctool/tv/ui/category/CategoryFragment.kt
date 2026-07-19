package com.calctool.tv.ui.category

import android.os.Bundle
import androidx.leanback.app.BrowseSupportFragment
import androidx.leanback.widget.*
import com.calctool.tv.App
import com.calctool.tv.models.VideoItem
import com.calctool.tv.ui.home.VideoCardPresenter
import kotlinx.coroutines.*

/**
 * 分类浏览页面
 * 支持子分类 Tab 切换 + 无限翻页
 */
class CategoryFragment : androidx.fragment.app.Fragment() {

    private val repository = App.instance.repository
    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())

    private var category: String = ""
    private var subCategories: List<String> = emptyList()

    private lateinit var rowsAdapter: ArrayObjectAdapter
    private var currentPage = 1
    private var isLoading = false
    private var hasMore = true

    companion object {
        fun newInstance(category: String): CategoryFragment {
            return CategoryFragment().apply {
                arguments = Bundle().apply { putString("category", category) }
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        category = arguments?.getString("category") ?: "电影"
        rowsAdapter = ArrayObjectAdapter(ListRowPresenter())
    }

    override fun onResume() {
        super.onResume()
        loadData()
    }

    override fun onDestroy() {
        super.onDestroy()
        scope.cancel()
    }

    fun loadData(subCategory: String? = null, page: Int = 1) {
        if (isLoading) return
        isLoading = true

        scope.launch {
            try {
                val (items, totalPages) = withContext(Dispatchers.IO) {
                    repository.getCategoryList(category, subCategory, page = page)
                }
                currentPage = page
                hasMore = page < totalPages

                rowsAdapter.clear()
                val rowAdapter = ArrayObjectAdapter(VideoCardPresenter())
                items.forEach { rowAdapter.add(it) }
                rowsAdapter.add(ListRow(HeaderItem("$category · ${subCategory ?: "全部"}"), rowAdapter))
            } finally {
                isLoading = false
            }
        }
    }

    fun loadNextPage(subCategory: String? = null) {
        if (hasMore && !isLoading) {
            loadData(subCategory, currentPage + 1)
        }
    }
}
