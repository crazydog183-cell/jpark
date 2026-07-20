package com.jpark.jangkku

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager

class JangkkuApp : Application() {

    override fun onCreate() {
        super.onCreate()
        createNotificationChannels()
    }

    private fun createNotificationChannels() {
        val manager = getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(
            NotificationChannel(
                CHANNEL_PET_SERVICE,
                "장꾸 실행 상태",
                NotificationManager.IMPORTANCE_LOW,
            ).apply { description = "장꾸가 화면 위에서 활동 중일 때 표시되는 알림" }
        )
        manager.createNotificationChannel(
            NotificationChannel(
                CHANNEL_REMINDERS,
                "장꾸 리마인더",
                NotificationManager.IMPORTANCE_HIGH,
            ).apply { description = "등록한 일정 시간이 되면 장꾸가 알려줘요" }
        )
    }

    companion object {
        const val CHANNEL_PET_SERVICE = "pet_service"
        const val CHANNEL_REMINDERS = "reminders"
    }
}
