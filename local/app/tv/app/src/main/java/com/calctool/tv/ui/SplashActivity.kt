package com.calctool.tv.ui

import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.calctool.tv.R
import java.io.PrintWriter
import java.io.StringWriter

/**
 * 启动页
 * 展示 Logo + 加载动画，预加载首页数据
 */
class SplashActivity : AppCompatActivity() {

    private val handler = Handler(Looper.getMainLooper())

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_splash)

        try {
            // 最小展示 1.5s，确保动画完成
            handler.postDelayed({
                startActivity(Intent(this, MainActivity::class.java))
                finish()
            }, 1500L)
        } catch (e: Exception) {
            val sw = StringWriter()
            e.printStackTrace(PrintWriter(sw))
            val msg = "启动失败: ${e.javaClass.simpleName}\n${e.message}\n\n${sw.toString().take(500)}"
            // 在界面上显示错误便于调试
            findViewById<TextView>(R.id.splash_error)?.text = msg
        }
    }
}
