package com.calctool.tv

import android.app.Application
import com.calctool.tv.data.CacheManager
import com.calctool.tv.data.VideoRepository

class App : Application() {

    lateinit var repository: VideoRepository
        private set

    lateinit var cacheManager: CacheManager
        private set

    override fun onCreate() {
        super.onCreate()
        instance = this
        cacheManager = CacheManager(this)
        repository = VideoRepository(cacheManager)
        // 启动时清理过期缓存
        cacheManager.clearExpiredCache()
    }

    companion object {
        lateinit var instance: App
            private set
    }
}
