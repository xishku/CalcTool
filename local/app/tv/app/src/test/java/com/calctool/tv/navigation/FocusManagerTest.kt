package com.calctool.tv.navigation

import android.view.KeyEvent
import org.junit.Assert.*
import org.junit.Test

class FocusManagerTest {

    @Test
    fun `isDirectionKey - true for DPAD_UP`() {
        assertTrue(FocusManager.isDirectionKey(KeyEvent.KEYCODE_DPAD_UP))
    }

    @Test
    fun `isDirectionKey - true for DPAD_DOWN`() {
        assertTrue(FocusManager.isDirectionKey(KeyEvent.KEYCODE_DPAD_DOWN))
    }

    @Test
    fun `isDirectionKey - true for DPAD_LEFT`() {
        assertTrue(FocusManager.isDirectionKey(KeyEvent.KEYCODE_DPAD_LEFT))
    }

    @Test
    fun `isDirectionKey - true for DPAD_RIGHT`() {
        assertTrue(FocusManager.isDirectionKey(KeyEvent.KEYCODE_DPAD_RIGHT))
    }

    @Test
    fun `isDirectionKey - false for OK key`() {
        assertFalse(FocusManager.isDirectionKey(KeyEvent.KEYCODE_DPAD_CENTER))
    }

    @Test
    fun `isDirectionKey - false for BACK`() {
        assertFalse(FocusManager.isDirectionKey(KeyEvent.KEYCODE_BACK))
    }

    @Test
    fun `isOkKey - true for DPAD_CENTER`() {
        assertTrue(FocusManager.isOkKey(KeyEvent.KEYCODE_DPAD_CENTER))
    }

    @Test
    fun `isOkKey - true for ENTER`() {
        assertTrue(FocusManager.isOkKey(KeyEvent.KEYCODE_ENTER))
    }

    @Test
    fun `isOkKey - false for DPAD_UP`() {
        assertFalse(FocusManager.isOkKey(KeyEvent.KEYCODE_DPAD_UP))
    }

    @Test
    fun `isBackKey - true for BACK`() {
        assertTrue(FocusManager.isBackKey(KeyEvent.KEYCODE_BACK))
    }

    @Test
    fun `isBackKey - false for MENU`() {
        assertFalse(FocusManager.isBackKey(KeyEvent.KEYCODE_MENU))
    }

    @Test
    fun `isMenuKey - true for MENU`() {
        assertTrue(FocusManager.isMenuKey(KeyEvent.KEYCODE_MENU))
    }

    @Test
    fun `isMenuKey - false for BACK`() {
        assertFalse(FocusManager.isMenuKey(KeyEvent.KEYCODE_BACK))
    }

    @Test
    fun `DEFAULT_ANIMATION has correct values`() {
        assertEquals(1.05f, FocusManager.DEFAULT_ANIMATION.scale)
        assertEquals(250L, FocusManager.DEFAULT_ANIMATION.durationMs)
    }
}
