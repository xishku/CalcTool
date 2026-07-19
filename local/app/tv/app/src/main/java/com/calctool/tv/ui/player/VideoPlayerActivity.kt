package com.calctool.tv.ui.player

import android.app.PictureInPictureParams
import android.os.Build
import android.os.Bundle
import android.util.Rational
import android.view.KeyEvent
import android.view.View
import android.view.WindowManager
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.ui.PlayerView
import com.calctool.tv.App
import com.calctool.tv.R
import com.calctool.tv.data.AppConfig
import com.calctool.tv.models.PlayState
import kotlinx.coroutines.*

/**
 * 视频播放器 Activity
 * ExoPlayer + 遥控器控制
 */
class VideoPlayerActivity : AppCompatActivity() {

    private val repository = App.instance.repository
    private val config = AppConfig.player

    private lateinit var playerView: PlayerView
    private lateinit var player: ExoPlayer

    private var videoUrl: String = ""
    private var videoFormat: String = ""
    private var videoTitle: String = ""
    private var episodeTitle: String = ""
    private var videoId: String = ""
    private var episodeIndex: Int = 0

    private var playbackPositionMs: Long = 0L
    private var savedDurationMs: Long = 0L
    private var lastSaveTime: Long = 0L

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // 全屏播放
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        window.decorView.systemUiVisibility = (
                View.SYSTEM_UI_FLAG_FULLSCREEN or
                        View.SYSTEM_UI_FLAG_HIDE_NAVIGATION or
                        View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                )

        setContentView(R.layout.activity_player)
        playerView = findViewById(R.id.player_view)
        parseIntent()
        initPlayer()
    }

    private fun parseIntent() {
        val intent = intent
        videoUrl = intent.getStringExtra("video_url") ?: ""
        videoFormat = intent.getStringExtra("video_format") ?: "HLS"
        videoTitle = intent.getStringExtra("video_title") ?: ""
        episodeTitle = intent.getStringExtra("episode_title") ?: ""
        videoId = intent.getStringExtra("video_id") ?: ""
        episodeIndex = intent.getIntExtra("episode_index", 1)
    }

    private fun initPlayer() {
        player = ExoPlayer.Builder(this).build().apply {
            playWhenReady = true
        }
        playerView.player = player

        // 设置媒体源
        val mediaItem = MediaItem.fromUri(videoUrl)
        player.setMediaItem(mediaItem)

        // 恢复播放进度
        val savedState = repository.getPlayState(videoId, episodeIndex)
        if (savedState != null && savedState.positionMs > 0) {
            player.seekTo(savedState.positionMs)
            savedDurationMs = savedState.durationMs
            Toast.makeText(this, "已恢复播放进度", Toast.LENGTH_SHORT).show()
        }

        // 保持在屏幕常亮
        playerView.keepScreenOn = true

        // 播放器事件监听
        player.addListener(object : Player.Listener {
            override fun onPlaybackStateChanged(state: Int) {
                if (state == Player.STATE_READY) {
                    savedDurationMs = player.duration
                } else if (state == Player.STATE_ENDED) {
                    saveProgress()
                    if (config.autoPlayNext) {
                        finish() // 回到详情页后可自动播下一集
                    }
                }
            }

            override fun onPlayerError(error: androidx.media3.common.PlaybackException) {
                Toast.makeText(
                    this@VideoPlayerActivity,
                    "播放出错: ${error.localizedMessage}",
                    Toast.LENGTH_LONG
                ).show()
                // 播放器崩溃自动恢复
                player.prepare()
            }
        })

        player.prepare()
    }

    /**
     * 遥控器按键映射
     */
    override fun onKeyDown(keyCode: Int, event: KeyEvent?): Boolean {
        if (event?.action == KeyEvent.ACTION_DOWN || event?.repeatCount ?: 0 > 0) {
            when (keyCode) {
                // OK → 暂停/播放
                KeyEvent.KEYCODE_DPAD_CENTER,
                KeyEvent.KEYCODE_ENTER -> {
                    togglePlayPause()
                    return true
                }

                // ← 快退 10s
                KeyEvent.KEYCODE_DPAD_LEFT -> {
                    val pos = maxOf(0L, player.currentPosition - config.seekStepSeconds * 1000L)
                    player.seekTo(pos)
                    showSeekToast("<< -${config.seekStepSeconds}s")
                    return true
                }

                // → 快进 10s
                KeyEvent.KEYCODE_DPAD_RIGHT -> {
                    val pos = minOf(
                        player.duration,
                        player.currentPosition + config.seekStepSeconds * 1000L
                    )
                    player.seekTo(pos)
                    showSeekToast(">> +${config.seekStepSeconds}s")
                    return true
                }

                // ↑ 音量+
                KeyEvent.KEYCODE_DPAD_UP -> {
                    player.volume = minOf(1f, player.volume + 0.05f)
                    showSeekToast("音量: ${(player.volume * 100).toInt()}%")
                    return true
                }

                // ↓ 音量-
                KeyEvent.KEYCODE_DPAD_DOWN -> {
                    player.volume = maxOf(0f, player.volume - 0.05f)
                    showSeekToast("音量: ${(player.volume * 100).toInt()}%")
                    return true
                }

                // BACK → 退出播放
                KeyEvent.KEYCODE_BACK -> {
                    saveProgress()
                    finish()
                    return true
                }

                // MENU → 显示设置
                KeyEvent.KEYCODE_MENU -> {
                    showPlaySettings()
                    return true
                }
            }
        }
        return super.onKeyDown(keyCode, event)
    }

    private fun togglePlayPause() {
        if (player.isPlaying) {
            player.pause()
            saveProgress()
            showSeekToast("⏸ 暂停")
        } else {
            player.play()
            showSeekToast("▶ 播放")
        }
    }

    private fun saveProgress() {
        val now = System.currentTimeMillis()
        // 防抖：至少间隔 3 秒
        if (now - lastSaveTime < 3000L) return
        lastSaveTime = now

        val state = PlayState(
            videoId = videoId,
            episodeIndex = episodeIndex,
            positionMs = player.currentPosition,
            durationMs = if (savedDurationMs > 0) savedDurationMs else player.duration,
            timestamp = now,
        )
        repository.savePlayState(state)
    }

    private fun showSeekToast(message: String) {
        Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
    }

    private fun showPlaySettings() {
        // 简单开关：画中画模式（Android 8+）
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val params = PictureInPictureParams.Builder()
                .setAspectRatio(Rational(16, 9))
                .build()
            enterPictureInPictureMode(params)
        }
    }

    override fun onPause() {
        super.onPause()
        saveProgress()
        if (player.isPlaying) player.pause()
    }

    override fun onStop() {
        super.onStop()
        saveProgress()
    }

    override fun onDestroy() {
        super.onDestroy()
        saveProgress()
        player.release()
    }
}
