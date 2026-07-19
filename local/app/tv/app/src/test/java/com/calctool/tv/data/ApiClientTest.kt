package com.calctool.tv.data

import com.calctool.tv.models.RequestConfig
import okhttp3.Request
import org.junit.Assert.*
import org.junit.Test

class ApiClientTest {

    @Test
    fun `buildRequest - creates valid request with correct headers`() {
        val url = "https://www.3ckk.com/"
        val request = ApiClient.buildRequest(url)
        assertEquals(url, request.url.toString())
        assertNotNull(request.header("User-Agent"))
        assertNotNull(request.header("Accept"))
        assertNotNull(request.header("Accept-Language"))
    }

    @Test
    fun `buildRequest - User-Agent contains Android TV`() {
        val request = ApiClient.buildRequest("https://test.com")
        val ua = request.header("User-Agent") ?: ""
        assertTrue(ua.contains("Android TV"))
    }

    @Test
    fun `client is singleton`() {
        val client1 = ApiClient.client
        val client2 = ApiClient.client
        assertSame(client1, client2)
    }

    @Test
    fun `getHtml - returns failure for invalid URL`() {
        val result = ApiClient.getHtml("not-a-valid-url://///")
        assertTrue(result.isFailure)
    }

    @Test
    fun `getHtmlWithRetry - retries on failure`() {
        val result = ApiClient.getHtmlWithRetry("http://0.0.0.0:1/")
        assertTrue(result.isFailure)
    }
}
