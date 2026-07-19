package com.calctool.tv.ui.player

import org.junit.Assert.*
import org.junit.Test

class PlayerControllerTest {

    @Test
    fun `seekForward - within duration`() {
        val result = PlayerController.seekForward(0L, 60000L, 10000L)
        assertEquals(10000L, result)
    }

    @Test
    fun `seekForward - clamps to duration`() {
        val result = PlayerController.seekForward(55000L, 60000L, 10000L)
        assertEquals(60000L, result)
    }

    @Test
    fun `seekForward - exact boundary`() {
        val result = PlayerController.seekForward(50000L, 60000L, 10000L)
        assertEquals(60000L, result)
    }

    @Test
    fun `seekBackward - within range`() {
        val result = PlayerController.seekBackward(30000L, 10000L)
        assertEquals(20000L, result)
    }

    @Test
    fun `seekBackward - clamps to zero`() {
        val result = PlayerController.seekBackward(5000L, 10000L)
        assertEquals(0L, result)
    }

    @Test
    fun `formatTime - less than one minute`() {
        assertEquals("00:30", PlayerController.formatTime(30_000L))
    }

    @Test
    fun `formatTime - several minutes`() {
        assertEquals("05:30", PlayerController.formatTime(330_000L))
    }

    @Test
    fun `formatTime - over one hour`() {
        assertEquals("1:05:30", PlayerController.formatTime(3_930_000L))
    }

    @Test
    fun `formatTime - exactly one hour`() {
        assertEquals("1:00:00", PlayerController.formatTime(3_600_000L))
    }

    @Test
    fun `formatTime - zero`() {
        assertEquals("00:00", PlayerController.formatTime(0L))
    }

    @Test
    fun `osdText - formats correctly`() {
        val text = PlayerController.osdText(60000L, 360000L, "电影标题", "第1集")
        assertTrue(text.contains("电影标题"))
        assertTrue(text.contains("第1集"))
        assertTrue(text.contains("01:00"))
        assertTrue(text.contains("06:00"))
    }

    @Test
    fun `osdText - with hours`() {
        val text = PlayerController.osdText(3_600_000L, 7_200_000L, "长电影", "全1集")
        assertTrue(text.contains("1:00:00"))
        assertTrue(text.contains("2:00:00"))
    }
}
