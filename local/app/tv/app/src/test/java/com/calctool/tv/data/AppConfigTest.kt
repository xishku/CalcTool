package com.calctool.tv.data

import org.junit.Assert.*
import org.junit.Test

class AppConfigTest {

    @Test
    fun `request config has correct defaults`() {
        val config = AppConfig.request
        assertEquals("https://www.3ckk.com", config.baseUrl)
        assertEquals(15, config.timeoutSeconds)
        assertEquals(3000L, config.intervalMs)
        assertEquals(2, config.maxRetries)
        assertTrue(config.userAgent.contains("Android"))
    }

    @Test
    fun `cache config has correct defaults`() {
        val config = AppConfig.cache
        assertEquals(30, config.homepageTtlMinutes)
        assertEquals(100, config.imageCacheMb)
        assertEquals(30, config.maxHistoryDays)
    }

    @Test
    fun `player config has correct defaults`() {
        val config = AppConfig.player
        assertEquals(10, config.seekStepSeconds)
        assertEquals(50, config.bufferSizeMb)
        assertTrue(config.autoPlayNext)
    }

    @Test
    fun `toJson - produces valid JSON with config values`() {
        val json = AppConfig.toJson()
        assertTrue(json.contains("https://www.3ckk.com"))
        assertTrue(json.contains("\"timeout_seconds\""))
        assertTrue(json.contains("\"seek_step_seconds\""))
        assertTrue(json.contains("\"homepage_ttl_minutes\""))
    }

    @Test
    fun `toJson - is valid JSON format`() {
        val json = AppConfig.toJson()
        assertTrue(json.startsWith("{"))
        assertTrue(json.endsWith("}"))
        assertTrue(json.contains("\"base_url\""))
        assertTrue(json.contains("\"request\""))
        assertTrue(json.contains("\"player\""))
        assertTrue(json.contains("\"cache\""))
    }
}
