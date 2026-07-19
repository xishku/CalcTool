package com.calctool.tv.navigation

import android.view.KeyEvent

/**
 * 遥控器焦点管理器
 * 处理 TV 上的方向键导航和焦点逻辑
 */
object FocusManager {

    /**
     * 判断按键是否是方向键
     */
    fun isDirectionKey(keyCode: Int): Boolean = when (keyCode) {
        KeyEvent.KEYCODE_DPAD_UP,
        KeyEvent.KEYCODE_DPAD_DOWN,
        KeyEvent.KEYCODE_DPAD_LEFT,
        KeyEvent.KEYCODE_DPAD_RIGHT -> true
        else -> false
    }

    /**
     * 判断按键是否是确认键
     */
    fun isOkKey(keyCode: Int): Boolean = when (keyCode) {
        KeyEvent.KEYCODE_DPAD_CENTER,
        KeyEvent.KEYCODE_ENTER,
        KeyEvent.KEYCODE_NUMPAD_ENTER -> true
        else -> false
    }

    /**
     * 判断按键是否是返回键
     */
    fun isBackKey(keyCode: Int): Boolean = keyCode == KeyEvent.KEYCODE_BACK

    /**
     * 判断按键是否是菜单键
     */
    fun isMenuKey(keyCode: Int): Boolean = keyCode == KeyEvent.KEYCODE_MENU

    /**
     * 焦点放大动画参数
     */
    data class FocusAnimation(
        val scale: Float = 1.05f,
        val durationMs: Long = 250L,
    )

    val DEFAULT_ANIMATION = FocusAnimation()
}
