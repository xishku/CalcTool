package com.calctool.tv.ui.player

/**
 * 播放器控制器辅助类
 * 封装遥控器按键处理逻辑
 */
object PlayerController {

    data class SeekStep(
        val forwardMs: Long = 10_000L,
        val backwardMs: Long = 10_000L,
    )

    data class VolumeStep(val delta: Float = 0.05f)

    /**
     * 计算快进位置
     */
    fun seekForward(currentMs: Long, durationMs: Long, stepMs: Long): Long {
        return minOf(durationMs, currentMs + stepMs)
    }

    /**
     * 计算快退位置
     */
    fun seekBackward(currentMs: Long, stepMs: Long): Long {
        return maxOf(0L, currentMs - stepMs)
    }

    /**
     * 格式化播放时间
     */
    fun formatTime(ms: Long): String {
        val totalSeconds = (ms / 1000).toInt()
        val hours = totalSeconds / 3600
        val minutes = (totalSeconds % 3600) / 60
        val seconds = totalSeconds % 60
        return if (hours > 0) {
            String.format("%d:%02d:%02d", hours, minutes, seconds)
        } else {
            String.format("%02d:%02d", minutes, seconds)
        }
    }

    /**
     * 格式化 OSD 文本
     */
    fun osdText(
        positionMs: Long,
        durationMs: Long,
        title: String,
        episode: String,
    ): String {
        val pos = formatTime(positionMs)
        val dur = formatTime(durationMs)
        return "$title · $episode  [$pos / $dur]"
    }
}
