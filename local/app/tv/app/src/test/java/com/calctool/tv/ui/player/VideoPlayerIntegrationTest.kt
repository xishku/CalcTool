package com.calctool.tv.ui.player

import com.calctool.tv.models.PlayState
import com.calctool.tv.models.VideoFormat
import org.junit.Assert.*
import org.junit.Test

class VideoPlayerIntegrationTest {

    @Test
    fun `PlayState saves correct video ID and episode`() {
        val state = PlayState(
            videoId = "vod-123",
            episodeIndex = 3,
            positionMs = 120_000L,
            durationMs = 3_600_000L,
        )
        assertEquals("vod-123", state.videoId)
        assertEquals(3, state.episodeIndex)
        assertEquals(120_000L, state.positionMs)
        assertEquals(3_600_000L, state.durationMs)
    }

    @Test
    fun `VideoFormat enum values`() {
        assertEquals(3, VideoFormat.values().size)
        assertEquals(VideoFormat.HLS, VideoFormat.valueOf("HLS"))
        assertEquals(VideoFormat.MP4, VideoFormat.valueOf("MP4"))
        assertEquals(VideoFormat.DASH, VideoFormat.valueOf("DASH"))
    }

    @Test
    fun `seekStep defaults are reasonable`() {
        val step = PlayerController.SeekStep()
        assertEquals(10_000L, step.forwardMs)
        assertEquals(10_000L, step.backwardMs)
    }

    @Test
    fun `VolumeStep defaults are reasonable`() {
        val step = PlayerController.VolumeStep()
        assertEquals(0.05f, step.delta)
    }
}
