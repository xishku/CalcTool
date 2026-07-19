package com.calctool.tv.data

import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.IOException
import java.util.concurrent.TimeUnit

/**
 * 统一网络请求客户端
 * 单例 OkHttpClient，复用连接池
 */
object ApiClient {
    private val config = AppConfig.request

    val client: OkHttpClient by lazy {
        OkHttpClient.Builder()
            .connectTimeout(config.timeoutSeconds.toLong(), TimeUnit.SECONDS)
            .readTimeout(config.timeoutSeconds.toLong(), TimeUnit.SECONDS)
            .writeTimeout(config.timeoutSeconds.toLong(), TimeUnit.SECONDS)
            .retryOnConnectionFailure(true)
            .build()
    }

    fun buildRequest(url: String): Request = Request.Builder()
        .url(url)
        .header("User-Agent", config.userAgent)
        .header("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
        .header("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8")
        .build()

    /**
     * 同步 GET 请求，返回 HTML 字符串
     */
    fun getHtml(url: String): Result<String> {
        return try {
            val request = buildRequest(url)
            val response = client.newCall(request).execute()
            if (response.isSuccessful) {
                val body = response.body?.string() ?: ""
                response.close()
                Result.success(body)
            } else {
                response.close()
                Result.failure(IOException("HTTP ${response.code}: ${response.message}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * 带重试的 GET 请求
     */
    fun getHtmlWithRetry(url: String): Result<String> {
        var lastError: Throwable? = null
        repeat(config.maxRetries + 1) { attempt ->
            if (attempt > 0) {
                Thread.sleep(config.intervalMs)
            }
            val result = getHtml(url)
            if (result.isSuccess) return result
            lastError = result.exceptionOrNull()
        }
        return Result.failure(lastError ?: IOException("Unknown error"))
    }
}
