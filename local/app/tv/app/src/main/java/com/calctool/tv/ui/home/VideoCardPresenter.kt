package com.calctool.tv.ui.home

import com.calctool.tv.models.VideoItem
import android.view.ViewGroup
import androidx.leanback.widget.ImageCardView
import androidx.leanback.widget.Presenter

/**
 * 影片卡片 Presenter — TV 列表通用卡片
 */
class VideoCardPresenter : Presenter() {
    override fun onCreateViewHolder(parent: ViewGroup): ViewHolder {
        val card = ImageCardView(parent.context).apply {
            isFocusable = true
            isFocusableInTouchMode = true
            setMainImageDimensions(280, 400)
            cardType = ImageCardView.CARD_TYPE_INFO_UNDER
        }
        return ViewHolder(card)
    }

    override fun onBindViewHolder(viewHolder: ViewHolder, item: Any) {
        val video = item as VideoItem
        val card = viewHolder.view as ImageCardView
        card.titleText = video.title
        card.contentText = listOfNotNull(
            video.year.takeIf { it.isNotBlank() },
            video.region.takeIf { it.isNotBlank() },
            video.updateInfo.takeIf { it.isNotBlank() },
            video.rating.takeIf { it.isNotBlank() }?.let { "★$it" },
        ).joinToString("  ")
    }

    override fun onUnbindViewHolder(viewHolder: ViewHolder) {
        val card = viewHolder.view as ImageCardView
        card.mainImage = null
    }
}
