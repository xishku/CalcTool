package com.calctool.tv.ui.search

import android.os.Bundle
import android.view.KeyEvent
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.EditText
import androidx.fragment.app.Fragment
import androidx.leanback.app.RowsSupportFragment
import androidx.leanback.widget.*
import com.calctool.tv.App
import com.calctool.tv.R
import com.calctool.tv.models.VideoItem
import com.calctool.tv.ui.home.VideoCardPresenter
import kotlinx.coroutines.*

/**
 * 搜索页面
 * 虚拟键盘 + 搜索结果列表
 */
class SearchFragment : Fragment() {

    private val repository = App.instance.repository
    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())

    private lateinit var adapter: ArrayObjectAdapter
    private lateinit var searchInput: EditText
    private var searchHistory = mutableListOf<String>()

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View? {
        return inflater.inflate(R.layout.fragment_search, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        searchInput = view.findViewById(R.id.search_input)

        adapter = ArrayObjectAdapter(ListRowPresenter())
        val rowsFragment = childFragmentManager
            .findFragmentById(R.id.search_results_container) as? RowsSupportFragment
        rowsFragment?.adapter = adapter

        searchInput.setOnKeyListener { _, keyCode, event ->
            if (event.action == KeyEvent.ACTION_DOWN) {
                when (keyCode) {
                    KeyEvent.KEYCODE_DPAD_CENTER,
                    KeyEvent.KEYCODE_ENTER -> {
                        doSearch()
                        return@setOnKeyListener true
                    }
                }
            }
            false
        }
    }

    private fun doSearch() {
        val keyword = searchInput.text.toString().trim()
        if (keyword.isEmpty()) return

        // 保存搜索历史
        addSearchHistory(keyword)

        scope.launch {
            val results = withContext(Dispatchers.IO) { repository.search(keyword) }
            adapter.clear()
            if (results.isEmpty()) {
                // 显示空结果
                return@launch
            }
            val rowAdapter = ArrayObjectAdapter(VideoCardPresenter())
            results.forEach { rowAdapter.add(it) }
            adapter.add(ListRow(HeaderItem("搜索结果: $keyword"), rowAdapter))
        }
    }

    private fun addSearchHistory(keyword: String) {
        searchHistory.remove(keyword)
        searchHistory.add(0, keyword)
        if (searchHistory.size > 10) {
            searchHistory = searchHistory.take(10).toMutableList()
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        scope.cancel()
    }
}
