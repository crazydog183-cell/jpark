package com.jpark.jangkku.notification

import android.app.Notification
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import java.text.SimpleDateFormat
import java.util.ArrayDeque
import java.util.Locale

/** 다른 앱의 알림을 수신해 최근 목록을 메모리에 캐시한다. (AI 도구로 조회) */
class JangkkuNotificationListener : NotificationListenerService() {

    data class CachedNotification(
        val appLabel: String,
        val title: String,
        val text: String,
        val timeMillis: Long,
    ) {
        fun summary(): String {
            val time = SimpleDateFormat("HH:mm", Locale.US).format(timeMillis)
            return "[$time] $appLabel: $title — $text"
        }
    }

    override fun onListenerConnected() {
        super.onListenerConnected()
        connected = true
    }

    override fun onListenerDisconnected() {
        connected = false
        super.onListenerDisconnected()
    }

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        if (sbn.packageName == packageName) return // 장꾸 자신의 알림은 무시
        val extras = sbn.notification.extras
        val title = extras.getCharSequence(Notification.EXTRA_TITLE)?.toString().orEmpty()
        val text = extras.getCharSequence(Notification.EXTRA_TEXT)?.toString().orEmpty()
        if (title.isBlank() && text.isBlank()) return

        val appLabel = try {
            val info = packageManager.getApplicationInfo(sbn.packageName, 0)
            packageManager.getApplicationLabel(info).toString()
        } catch (e: Exception) {
            sbn.packageName
        }
        record(CachedNotification(appLabel, title, text, sbn.postTime))
    }

    companion object {
        private const val MAX_CACHED = 50
        private val cache = ArrayDeque<CachedNotification>()

        @Volatile
        var connected: Boolean = false
            private set

        @Synchronized
        private fun record(notification: CachedNotification) {
            cache.addFirst(notification)
            while (cache.size > MAX_CACHED) cache.removeLast()
        }

        /** 최신순 스냅샷 */
        @Synchronized
        fun snapshot(limit: Int = 15): List<CachedNotification> = cache.take(limit)
    }
}
