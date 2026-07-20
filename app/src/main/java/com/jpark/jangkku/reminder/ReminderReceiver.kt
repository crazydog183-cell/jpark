package com.jpark.jangkku.reminder

import android.app.Notification
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import com.jpark.jangkku.JangkkuApp
import com.jpark.jangkku.MainActivity

/** 리마인더 알람이 울리면 알림을 표시한다. */
class ReminderReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        val id = intent.getLongExtra(EXTRA_ID, -1)
        val content = intent.getStringExtra(EXTRA_CONTENT).orEmpty().ifBlank { "예정된 일정이 있어!" }

        val contentIntent = PendingIntent.getActivity(
            context, 0,
            Intent(context, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE,
        )
        val notification = Notification.Builder(context, JangkkuApp.CHANNEL_REMINDERS)
            .setSmallIcon(android.R.drawable.ic_popup_reminder)
            .setContentTitle("🐹 장꾸의 알림")
            .setContentText(content)
            .setStyle(Notification.BigTextStyle().bigText(content))
            .setContentIntent(contentIntent)
            .setAutoCancel(true)
            .build()

        val manager = context.getSystemService(NotificationManager::class.java)
        manager.notify(NOTIFICATION_TAG, id.toInt(), notification)
    }

    companion object {
        const val EXTRA_ID = "reminder_id"
        const val EXTRA_CONTENT = "reminder_content"
        private const val NOTIFICATION_TAG = "jangkku_reminder"
    }
}
